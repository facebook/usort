# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Sequence, Set

import libcst as cst

from .stdlibs.all import stdlib as all_stdlib


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


@dataclass(order=True)
class SortableImport:
    node: cst.CSTNode = field(repr=False, compare=False)
    sort_key: SortKey = field(init=False)

    # For constructing the sort key...
    first_module: str
    first_dotted_import: str

    # This is intended to 1. allow sorting the names, and 2. detecting unsafe
    # ordering.  e.g. `import a as b; import b.c` shadows `b`.
    imported_names: Set[str] = field(default_factory=set, compare=False)

    def __post_init__(self):
        self.sort_key = SortKey(
            category_index=category(self.first_module),
            is_from_import=isinstance(self.node.body[0], cst.ImportFrom),
        )

    @classmethod
    def from_node(cls, node: cst.CSTNode) -> "SortableImport":
        if isinstance(node, cst.SimpleStatementLine):
            first_module: Optional[str] = None
            names: List[str] = []
            sort_key: Optional[str] = None
            if isinstance(node.body[0], cst.Import):
                for name in node.body[0].names:
                    # if sort_key is None:
                    #    sort_key = with_dots(name.name)
                    # name=Name, asname=?
                    # name=Attribute(value=Name, attr=Name), asname=?
                    if name.asname:
                        names.append(with_dots(name.asname.name))
                    else:
                        names.append(with_dots(name.name))

                    if first_module is None:
                        first_module = with_dots(name.name)

            elif isinstance(node.body[0], cst.ImportFrom):
                # module=Attribute(value=Name, attr=Name)
                if node.body[0].module is None:
                    # from . import foo
                    sort_key = node.body[0].names[0].name.value
                else:
                    sort_key = with_dots(node.body[0].module)

                if node.body[0].relative:
                    sort_key = "." * len(node.body[0].relative) + sort_key

                if first_module is None:
                    first_module = sort_key

                for alias in node.body[0].names:
                    if alias.asname:
                        names.append(alias.asname.name.value)
                    else:
                        names.append(alias.name.value)
                # names.add(sort_key.split(".")[0])
            else:
                raise TypeError

            assert first_module is not None
            return cls(
                node=node,
                first_module=first_module,
                first_dotted_import=names[0],
                imported_names=set(names),
            )
        raise ValueError("Not an import")


@dataclass
class SortableBlock:
    start_idx: int
    end_idx: Optional[int] = None  # half-open interval

    stmts: List[SortableImport] = field(default_factory=list)
    imported_names: Set[str] = field(default_factory=set)


def try_parse(path: Path, data: Optional[bytes] = None,) -> cst.Module:
    if data is None:
        data = path.read_bytes()

    # The latest released version of LibCST (0.3.1) supports the following list
    # of versions; when the python 2 support for
    # https://github.com/Instagram/LibCST/issues/184 gets merged, this should be
    # available at runtime.
    for version in ("3.8", "3.7", "3.6", "3.5"):
        try:
            mod = cst.parse_module(
                data, cst.PartialParserConfig(python_version=version)
            )
            return mod
        except cst.ParserSyntaxError:
            continue

    # Intentionally not raising an exception with a specific syntax error (if we
    # keep the last, meaning oldest python version, then it might complain about
    # typehints like https://github.com/psf/black/issues/1158)
    raise Exception(f"No version could parse {path}")


# TODO can this generalize to functions as well?
def sortable_blocks(mod: cst.Module) -> List[SortableBlock]:
    # Finds blocks of imports separated by barriers (non-import statements, or
    # dangerous imports).  We will only sort within a block, and only when there
    # are no duplicate names.

    ret: List[SortableBlock] = []
    cur: Optional[SortableBlock] = None
    for i, stmt in enumerate(mod.body):
        # print(stmt)
        if is_sortable_import(stmt):
            imp = SortableImport.from_node(stmt)
            if cur is None:
                cur = SortableBlock(i, i + 1)
                ret.append(cur)

            if cur.imported_names & imp.imported_names:
                # This overwrites an earlier name
                cur = SortableBlock(i, i + 1)
                ret.append(cur)

            cur.end_idx = i + 1
            cur.stmts.append(imp)
            cur.imported_names |= imp.imported_names
        else:
            if cur:
                cur = None
    return ret


def is_sortable_import(stmt: cst.CSTNode):
    # TODO body is a list, because of semicolons.  black would split them up,
    # but black hasn't been run yet.  We should split those up before getting to
    # this point.
    if isinstance(stmt, cst.SimpleStatementLine):
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


def category(s: str) -> int:
    # TODO(thatch): Make this far more customizable, overridable, and detect
    # firstparty packages that don't use dotted imports.
    if s == "__future__":
        return 0
    elif s.split(".")[0] in all_stdlib:
        return 1
    else:
        # 3 = third party
        # 4 = .foo
        # 5 = ..foo
        return 2 + len(s) - len(s.lstrip("."))


def usort_string(data: str) -> str:
    # Intended for unittesting
    mod = try_parse(data=data.encode(), path="<test>")
    blocks = sortable_blocks(mod)
    for b in blocks:
        sorted_stmts = sorted(b.stmts)
        mod.body[b.start_idx : b.end_idx] = [s.node for s in sorted_stmts]
    return mod.code
