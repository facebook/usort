# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set

import libcst as cst

from .config import Config
from .util import try_parse


def with_dots(x: cst.CSTNode) -> str:
    if isinstance(x, cst.Attribute):
        return ".".join([with_dots(x.value), with_dots(x.attr)])
    elif isinstance(x, cst.Name):
        return x.value
    else:
        raise TypeError(f"Can't with_dots on {type(x)}")


@dataclass(order=True)
class SortKey:
    category_index: int
    is_from_import: bool
    ndots: int


@dataclass(order=True)
class SortableImport:
    node: cst.CSTNode = field(repr=False, compare=False)
    sort_key: SortKey = field(init=False)

    # For constructing the sort key...
    first_module: str
    first_dotted_import: str

    config: Config = field(repr=False, compare=False)

    # This is only used for detecting unsafe ordering, and is not used for
    # breaking ties.  e.g. `import a as b; import b.c` shadows `b`.
    imported_names: Set[str] = field(default_factory=set, compare=False)

    def __post_init__(self) -> None:
        if not self.first_module.startswith("."):
            ndots = 0
        else:
            # replicate ... sorting before .. before ., but after absolute
            ndots = 100 - (len(self.first_module) - len(self.first_module.lstrip(".")))
        assert isinstance(self.node, cst.SimpleStatementLine)
        self.sort_key = SortKey(
            # TODO this will raise on missing category
            category_index=self.config.categories.index(
                self.config.category(self.first_module)
            ),
            is_from_import=isinstance(self.node.body[0], cst.ImportFrom),
            ndots=ndots,
        )

    @classmethod
    def from_node(cls, node: cst.CSTNode, config: Config) -> "SortableImport":
        # TODO: This duplicates (differently) what's in the LibCST import
        # metadata visitor.  This is also a bit hard to read.
        if isinstance(node, cst.SimpleStatementLine):
            first_module: Optional[str] = None
            first_dotted_import: Optional[str] = None
            names: List[str] = []
            sort_key: Optional[str] = None

            # There are 4 basic types of import
            # Additionally some forms z can have leading dots for relative
            # imports, and there can be multiple on the right-hand side.
            #
            if isinstance(node.body[0], cst.Import):
                # import z
                # import z as y
                for name in node.body[0].names:
                    if name.asname:
                        names.append(with_dots(name.asname.name))
                    else:
                        names.append(with_dots(name.name).split(".")[0])

                    if first_module is None:
                        first_module = with_dots(name.name)
                        first_dotted_import = first_module

            elif isinstance(node.body[0], cst.ImportFrom):
                # from z import x
                # from z import x as y

                # This is treated as a barrier and should never get this far.
                assert not isinstance(node.body[0].names, cst.ImportStar)

                if node.body[0].module is None:
                    # from . import foo [as bar]
                    # (won't have dots but with_dots makes the typing easier)
                    sort_key = with_dots(node.body[0].names[0].name)
                else:
                    # from x import foo [as bar]
                    sort_key = with_dots(node.body[0].module)

                if node.body[0].relative:
                    first_dotted_import = sort_key
                    sort_key = "." * len(node.body[0].relative)
                    if node.body[0].module is not None:
                        sort_key += first_dotted_import

                if first_module is None:
                    first_module = sort_key
                    if first_dotted_import is None:
                        for alias in node.body[0].names:
                            first_dotted_import = with_dots(alias.name)
                            break

                for alias in node.body[0].names:
                    if alias.asname:
                        assert isinstance(alias.asname.name, cst.Name)
                        names.append(alias.asname.name.value)
                    else:
                        assert isinstance(alias.name, cst.Name)
                        names.append(alias.name.value)
            else:
                raise TypeError

            assert first_module is not None
            assert first_dotted_import is not None
            return cls(
                node=node,
                first_module=first_module,
                first_dotted_import=first_dotted_import,
                imported_names=set(names),
                config=config,
            )
        raise ValueError("Not an import")


@dataclass
class SortableBlock:
    start_idx: int
    end_idx: Optional[int] = None  # half-open interval

    stmts: List[SortableImport] = field(default_factory=list)
    imported_names: Set[str] = field(default_factory=set)


# TODO can this generalize to functions as well?
def sortable_blocks(mod: cst.Module, config: Config) -> List[SortableBlock]:
    # Finds blocks of imports separated by barriers (non-import statements, or
    # dangerous imports).  We will only sort within a block, and only when there
    # are no duplicate names.

    ret: List[SortableBlock] = []
    cur: Optional[SortableBlock] = None
    for i, stmt in enumerate(mod.body):
        # print(stmt)
        # TODO support known_side_effect_modules or so
        if is_sortable_import(stmt):
            imp = SortableImport.from_node(stmt, config)
            if cur is None:
                cur = SortableBlock(i, i + 1)
                ret.append(cur)

            if cur.imported_names & imp.imported_names:
                # This overwrites an earlier name
                # TODO `os` vs `os.path` shouldn't cause a separate block, but
                # will require a more complex data structure.
                cur = SortableBlock(i, i + 1)
                ret.append(cur)

            cur.end_idx = i + 1
            cur.stmts.append(imp)
            cur.imported_names |= imp.imported_names
        else:
            if cur:
                cur = None
    return ret


def is_sortable_import(stmt: cst.CSTNode) -> bool:
    if isinstance(stmt, cst.SimpleStatementLine):
        com = stmt.trailing_whitespace.comment
        if com:
            com_str = com.value.replace(" ", "")
            if com_str.startswith("#usort:skip") or com_str.startswith("#isort:skip"):
                return False

        # N.b. `body` is a list, because the SimpleStatementLine might have
        # semicolons.  We only look at the first, which is probably the most
        # dangerous thing in here.
        #
        # If black is run, it will put the semicolon pieces on different lines,
        # but we don't want to do that until we reflow and handle directives
        # like noqa.  TODO do that before calling is_sortable_import, and assert
        # that it's not a compound statement line.
        if isinstance(stmt.body[0], cst.ImportFrom):
            # `from x import *` is a barrier
            if isinstance(stmt.body[0].names, cst.ImportStar):
                return False
            return True
        elif isinstance(stmt.body[0], cst.Import):
            return True
        else:
            return False
    else:
        return False


def usort_string(data: str, config: Config) -> str:
    mod = try_parse(data=data.encode(), path=Path("<test>"))
    blocks = sortable_blocks(mod, config=config)

    # The module's body is already a list, but that's an implementation detail we
    # shouldn't rely on.  This code should eventually be run as a visitor, and
    # with_changes is the right thing to do in that case.
    body: List[cst.CSTNode] = list(mod.body)
    for b in blocks:
        sorted_stmts = sorted(b.stmts)
        body[b.start_idx : b.end_idx] = [s.node for s in sorted_stmts]
    return mod.with_changes(body=body).code
