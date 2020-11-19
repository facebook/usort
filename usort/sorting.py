# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import libcst as cst

from .config import Config
from .util import timed, try_parse, walk


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
    module: str


@dataclass(order=True)
class SortableImport:
    node: cst.SimpleStatementLine = field(repr=False, compare=False)
    sort_key: SortKey = field(init=False)

    # For deciding what category
    first_module: str = field(compare=False)
    # For tiebreaking sort_key
    first_dotted_import: str

    config: Config = field(repr=False, compare=False)

    # This is only used for detecting unsafe ordering, and is not used for
    # breaking ties.  e.g. `import a as b; import b.c` shadows `b`, but `import
    # os` and `import os.path` do not shadow becuase it's the same `os`
    imported_names: Dict[str, str] = field(default_factory=dict, compare=False)

    def __post_init__(self) -> None:
        if not self.first_module.startswith("."):
            ndots = 0
        else:
            # replicate ... sorting before .. before ., but after absolute
            ndots = 100 - (len(self.first_module) - len(self.first_module.lstrip(".")))
        self.sort_key = SortKey(
            # TODO this will raise on missing category
            category_index=self.config.categories.index(
                self.config.category(self.first_module)
            ),
            is_from_import=isinstance(self.node.body[0], cst.ImportFrom),
            ndots=ndots,
            module=self.first_module.casefold(),
        )

    @classmethod
    def from_node(cls, node: cst.CSTNode, config: Config) -> "SortableImport":
        # TODO: This duplicates (differently) what's in the LibCST import
        # metadata visitor.  This is also a bit hard to read.
        if isinstance(node, cst.SimpleStatementLine):
            first_module: Optional[str] = None
            first_dotted_import: Optional[str] = None
            names: Dict[str, str] = {}
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
                        names[with_dots(name.asname.name).split(".")[0]] = with_dots(
                            name.name
                        )
                    else:
                        tmp = with_dots(name.name).split(".")[0]
                        names[tmp] = tmp

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
                    name_key = sort_key
                else:
                    # from x import foo [as bar]
                    sort_key = with_dots(node.body[0].module)
                    name_key = sort_key + "."

                if node.body[0].relative:
                    first_dotted_import = sort_key
                    sort_key = "." * len(node.body[0].relative)
                    if node.body[0].module is not None:
                        sort_key += first_dotted_import
                    name_key = sort_key
                    if node.body[0].module is not None:
                        name_key += "."

                if first_module is None:
                    first_module = sort_key
                    if first_dotted_import is None:
                        for alias in node.body[0].names:
                            first_dotted_import = with_dots(alias.name)
                            break

                for alias in node.body[0].names:
                    if alias.asname:
                        assert isinstance(alias.asname.name, cst.Name)
                        names[alias.asname.name.value] = name_key + with_dots(
                            alias.name
                        )
                    else:
                        assert isinstance(alias.name, cst.Name)
                        names[alias.name.value] = name_key + alias.name.value
            else:
                raise TypeError

            assert first_module is not None
            assert first_dotted_import is not None
            return cls(
                node=node,
                first_module=first_module,
                first_dotted_import=first_dotted_import,
                imported_names=names,
                config=config,
            )
        raise ValueError("Not an import")


@dataclass
class SortableBlock:
    start_idx: int
    end_idx: Optional[int] = None  # half-open interval

    stmts: List[SortableImport] = field(default_factory=list)
    imported_names: Dict[str, str] = field(default_factory=dict)


def name_overlap(a: Dict[str, str], b: Dict[str, str]) -> bool:
    for k, v in b.items():
        if k in a and a[k] != v:
            return True
    return False


def sortable_blocks(
    body: Sequence[cst.BaseStatement], config: Config
) -> List[SortableBlock]:
    # Finds blocks of imports separated by barriers (non-import statements, or
    # dangerous imports).  We will only sort within a block, and only when there
    # are no duplicate names.

    ret: List[SortableBlock] = []
    cur: Optional[SortableBlock] = None
    for i, stmt in enumerate(body):
        # print(stmt)
        # TODO support known_side_effect_modules or so
        if is_sortable_import(stmt, config):
            imp = SortableImport.from_node(stmt, config)
            if cur is None:
                cur = SortableBlock(i, i + 1)
                ret.append(cur)

            if name_overlap(cur.imported_names, imp.imported_names):
                # This overwrites an earlier name
                cur = SortableBlock(i, i + 1)
                ret.append(cur)

            cur.end_idx = i + 1
            cur.stmts.append(imp)
            cur.imported_names.update(imp.imported_names)
        else:
            if cur:
                cur = None
    return ret


def is_sortable_import(stmt: cst.CSTNode, config: Config) -> bool:
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
            # avoid `from .` imports by checking for None, check everything else:
            #   from . import a -> module == None
            #   from foo import bar -> module == Name(foo)
            #   from a.b import c -> module == Attribute(Name(a), Name(b))
            elif stmt.body[0].module is not None:
                base = cst.helpers.get_full_name_for_node_or_raise(stmt.body[0].module)
                names = [name.evaluated_name for name in stmt.body[0].names]
                if config.is_side_effect_import(base, names):
                    return False
            return True
        elif isinstance(stmt.body[0], cst.Import):
            base = ""
            names = [name.evaluated_name for name in stmt.body[0].names]
            if config.is_side_effect_import(base, names):
                return False
            return True
        else:
            return False
    else:
        return False


def usort_string(data: str, config: Config, path: Optional[Path] = None) -> str:
    r"""
    Whenever possible use usort_bytes instead.

    One does not just .read_text() Python source code.  That will use the system
    encoding, which if is not utf-8 would be in violation of pep 3120.

    There are two additional cases where this function does the wrong thing, but you
    won't notice on most modern file contents:

    - a string unrepresentable in utf-8, e.g. "\ud800" is a single high surrogate
    - a string with a valid pep 263 coding line, other than utf-8
    """
    return usort_bytes(data=data.encode(), config=config, path=path)[0].decode()


def usort_bytes(
    data: bytes, config: Config, path: Optional[Path] = None
) -> Tuple[bytes, str]:
    """
    Returns (new_bytes, encoding_str) after sorting.
    """
    if path is None:
        path = Path("<data>")

    mod = try_parse(data=data, path=path)
    with timed(f"sorting {path}"):
        tr = ImportSortingTransformer(config)
        new_mod = mod.visit(tr)
        return (new_mod.bytes, new_mod.encoding)


def usort_stdin() -> bool:
    """
    Read file contents from stdin, format it, and write the resulting file to stdout

    In case of error during sorting, no output will be written to stdout, and the
    exception will be written to stderr instead.

    Returns True if formatting succeeded, otherwise False
    """
    if sys.stdin.isatty():
        print("Warning: stdin is a tty", file=sys.stderr)

    try:
        config = Config.find()
        data = sys.stdin.read()
        result = usort_string(data, config, Path("<stdin>"))
        sys.stdout.write(result)
        return True

    except Exception as e:
        sys.stderr.write(repr(e))
        return False


@dataclass
class Result:
    path: Path
    content: bytes
    output: bytes
    # encoding will be None on parse errors; we get this from LibCST on a successful
    # parse.
    encoding: Optional[str]
    error: Optional[Exception] = None


def usort_path(path: Path, *, write: bool = False) -> Iterable[Result]:
    """
    For a given path, format it, or any .py files in it, and yield Result objects
    """
    files: Iterable[Path]
    if path.is_dir():
        files = walk(path, "*.py")
    else:
        files = [path]

    data: bytes = b""
    for f in files:
        try:
            config = Config.find(f.parent)
            data = f.read_bytes()
            output, encoding = usort_bytes(data, config, f)
            if write:
                f.write_bytes(output)
            yield Result(f, data, output, encoding)

        except Exception as e:
            yield Result(f, data, b"", None, e)


def partition_leading_lines(
    lines: Sequence[cst.EmptyLine],
) -> Tuple[Sequence[cst.EmptyLine], Sequence[cst.EmptyLine]]:
    """
    Returns a tuple of the initial blank lines, and the comment lines.
    """
    for j in range(len(lines)):
        if lines[j].comment:
            break
    else:
        j = len(lines)

    return lines[:j], lines[j:]


def fixup_whitespace(
    initial_blank: Sequence[cst.EmptyLine], imports: List[SortableImport]
) -> List[SortableImport]:
    cur_category = None
    # TODO if they've already been reshuffled, there may have been a blank
    # (separator) line between a non-block and the first import, that's now in
    # the middle.
    for i in imports:
        old_blanks, old_comments = partition_leading_lines(i.node.leading_lines)

        if cur_category is None:
            blanks = initial_blank
        elif i.sort_key.category_index != cur_category:
            blanks = (cst.EmptyLine(),)
        elif old_comments:
            # preserves black formatting
            blanks = (cst.EmptyLine(),)
        else:
            blanks = ()

        i.node = i.node.with_changes(leading_lines=(*blanks, *old_comments))

        cur_category = i.sort_key.category_index
    return imports


class ImportSortingTransformer(cst.CSTTransformer):
    def __init__(self, config: Config) -> None:
        self.config = config

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        blocks = sortable_blocks(updated_node.body, config=self.config)
        body: List[cst.CSTNode] = list(updated_node.body)

        for b in blocks:
            initial_blank, initial_comment = partition_leading_lines(
                b.stmts[0].node.leading_lines
            )
            b.stmts[0].node = b.stmts[0].node.with_changes(
                leading_lines=initial_comment
            )
            sorted_stmts = fixup_whitespace(initial_blank, sorted(b.stmts))
            body[b.start_idx : b.end_idx] = [s.node for s in sorted_stmts]
        return updated_node.with_changes(body=body)

    def leave_IndentedBlock(
        self, original_node: cst.IndentedBlock, updated_node: cst.IndentedBlock
    ) -> cst.IndentedBlock:
        blocks = sortable_blocks(updated_node.body, config=self.config)
        body: List[cst.CSTNode] = list(updated_node.body)

        for b in blocks:
            initial_blank, initial_comment = partition_leading_lines(
                b.stmts[0].node.leading_lines
            )
            b.stmts[0].node = b.stmts[0].node.with_changes(
                leading_lines=initial_comment
            )
            sorted_stmts = fixup_whitespace(initial_blank, sorted(b.stmts))
            body[b.start_idx : b.end_idx] = [s.node for s in sorted_stmts]
        return updated_node.with_changes(body=body)
