# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import sys
import traceback
from pathlib import Path
from textwrap import dedent, indent
from typing import Dict, List, Optional, Sequence

import libcst as cst
from attr import dataclass, field

from .config import CAT_FIRST_PARTY, Config
from .util import stem_join, Timing, top_level_name

COMMENT_INDENT = "  "


def case_insensitive_ordering(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    return str.casefold(text)


@dataclass
class Options:
    debug: bool


@dataclass
class SortWarning:
    line: int
    message: str


@dataclass
class Result:
    path: Path
    content: bytes = b""
    output: bytes = b""
    # encoding will be None on parse errors; we get this from LibCST on a successful
    # parse.
    encoding: Optional[str] = None
    error: Optional[Exception] = None
    trace: str = ""
    timings: Sequence[Timing] = ()
    warnings: Sequence[SortWarning] = ()

    def __attrs_post_init__(self) -> None:
        if self.error:
            exc_type, exc, tb = sys.exc_info()
            if exc_type is not None:
                self.trace = "".join(traceback.format_exception(exc_type, exc, tb))


@dataclass
class ImportItemComments:
    before: List[str] = field(factory=list)
    inline: List[str] = field(factory=list)
    following: List[str] = field(factory=list)

    def __add__(self, other: "ImportItemComments") -> "ImportItemComments":
        if not isinstance(other, ImportItemComments):
            return NotImplemented

        return ImportItemComments(
            before=[*self.before, *other.before],
            inline=[*self.inline, *other.inline],
            following=[*self.following, *other.following],
        )


@dataclass
class ImportComments:
    before: List[str] = field(factory=list)
    first_inline: List[str] = field(factory=list)
    initial: List[str] = field(factory=list)
    inline: List[str] = field(factory=list)  # Only when no trailing comma
    final: List[str] = field(factory=list)
    last_inline: List[str] = field(factory=list)

    def __add__(self, other: "ImportComments") -> "ImportComments":
        if not isinstance(other, ImportComments):
            return NotImplemented

        return ImportComments(
            before=[*self.before, *other.before],
            first_inline=[*self.first_inline, *other.first_inline],
            initial=[*self.initial, *other.initial],
            inline=[*self.inline, *other.inline],
            final=[*self.final, *other.final],
            last_inline=[*self.last_inline, *other.last_inline],
        )


@dataclass(order=True)
class SortKey:
    category_index: int
    is_from_import: bool
    ndots: int


@dataclass(order=True)
class SortableImportItem:
    name: str = field(order=str.casefold)
    asname: Optional[str] = field(eq=True, order=case_insensitive_ordering)
    comments: ImportItemComments = field(eq=False, order=False)
    stem: Optional[str] = field(order=False, default=None, repr=False)

    @property
    def fullname(self) -> str:
        return stem_join(self.stem, self.name)

    def __add__(self, other: "SortableImportItem") -> "SortableImportItem":
        if not isinstance(other, SortableImportItem):
            return NotImplemented

        if self.name != other.name and self.asname != other.asname:
            raise ValueError("name and asname must match")

        return SortableImportItem(
            name=self.name,
            asname=self.asname,
            comments=self.comments + other.comments,
            stem=self.stem,
        )


@dataclass(order=True, repr=False)
class SortableImport:
    sort_key: SortKey = field(init=False)
    stem: Optional[str] = field(order=case_insensitive_ordering)  # "from" imports
    items: List[SortableImportItem] = field()
    comments: ImportComments = field(order=False)
    indent: str = field(order=False)
    config: Config = field(eq=False, order=False, factory=Config)

    # for cli/debugging only
    node: cst.CSTNode = field(eq=False, order=False, factory=cst.EmptyLine)

    def __repr__(self) -> str:
        items = indent(("\n".join(f"{item!r}," for item in self.items)), "        ")
        return (
            dedent(
                """
                    SortableImport(
                        # sort_key = {sort_key!r},
                        stem = {stem!r},
                        items = [
                    {items}
                        ],
                        comments = {comments!r},
                        indent = {indent!r},
                    )
                """
            )
            .strip()
            .format(
                sort_key=self.sort_key,
                stem=self.stem,
                items=items,
                comments=self.comments,
                indent=self.indent,
            )
        )

    def __add__(self, other: "SortableImport") -> "SortableImport":
        if not isinstance(other, SortableImport):
            return NotImplemented

        if self.sort_key != other.sort_key and self.stem != other.stem:
            raise ValueError("sort_key and stem must match")

        # Combine the items from the other import statement with items from this import.
        # If both the name and asname match, we can safely just add-op them to combine
        # comments, and assume the other import object will get discarded. If there is
        # no match, new items from other will be appended to the end of the list.
        #
        #   from foo import a, b, c
        #   from foo import b, c as C, d
        #
        # should get combined to
        #
        #   from foo import a, b, c, c as C, d
        #
        combined_items = list(self.items)
        for item in other.items:
            if item in combined_items:
                idx = combined_items.index(item)
                combined_items[idx] += item

            else:
                combined_items.append(item)

        return SortableImport(
            stem=self.stem,
            items=combined_items,
            comments=self.comments + other.comments,
            indent=self.indent,
            config=self.config,
            node=self.node,
        )

    @property
    def imported_names(self) -> Dict[str, str]:
        results: Dict[str, str] = {}

        for item in self.items:
            key = item.asname or item.name
            if self.stem is None and not item.asname:
                key = top_level_name(item.name)
                value = key
            else:
                value = item.fullname
            results[key] = value

        return results

    def __attrs_post_init__(self) -> None:
        top: Optional[str] = None
        ndots = 0

        if self.stem is None:
            top = top_level_name(self.items[0].name)
        elif not self.stem.startswith("."):
            top = top_level_name(self.stem)
        else:
            # replicate ... sorting before .. before ., but after absolute
            ndots = 100 - (len(self.stem) - len(self.stem.lstrip(".")))

        category = self.config.category(top) if top else CAT_FIRST_PARTY

        self.sort_key = SortKey(
            # TODO this will raise on missing category
            category_index=self.config.categories.index(category),
            is_from_import=bool(self.stem),
            ndots=ndots,
        )


@dataclass(repr=False)
class SortableBlock:
    start_idx: int
    end_idx: int  # half-open interval

    imports: List[SortableImport] = field(factory=list)
    imported_names: Dict[str, str] = field(factory=dict)

    def __repr__(self) -> str:
        imports = indent("\n".join(f"{imp!r}," for imp in self.imports), "        ")
        return (
            dedent(
                """
                    SortableBlock(
                        start_idx = {start_idx!r},
                        end_idx = {end_idx!r},
                        imports = [
                    {imports}
                        ],
                        imported_names = {imported_names!r},
                    )
                """
            )
            .strip()
            .format(
                start_idx=self.start_idx,
                end_idx=self.end_idx,
                imports=imports,
                imported_names=self.imported_names,
            )
        )

    def add_import(self, imp: SortableImport, idx: int) -> None:
        self.end_idx = idx + 1
        self.imports.append(imp)
        for key, value in imp.imported_names.items():
            self.imported_names[key] = value
