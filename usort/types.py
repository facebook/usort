# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from pathlib import Path
from textwrap import indent, dedent
from typing import Dict, List, Optional, Sequence

import libcst as cst
from attr import dataclass, field

from .config import CAT_FIRST_PARTY, Config
from .util import stem_join, top_level_name, Timing


def case_insensitive_ordering(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    return str.casefold(text)


@dataclass
class Result:
    path: Path
    content: bytes
    output: bytes = b""
    # encoding will be None on parse errors; we get this from LibCST on a successful
    # parse.
    encoding: Optional[str] = None
    error: Optional[Exception] = None
    timings: Sequence[Timing] = ()


@dataclass
class ImportItemComments:
    inline: List[str] = field(factory=list)
    following: List[str] = field(factory=list)


@dataclass
class ImportComments:
    before: List[str] = field(factory=list)
    first_inline: List[str] = field(factory=list)
    initial: List[str] = field(factory=list)
    inline: List[str] = field(factory=list)  # Only when no trailing comma
    final: List[str] = field(factory=list)
    last_inline: List[str] = field(factory=list)


@dataclass(order=True)
class SortKey:
    category_index: int
    is_from_import: bool
    ndots: int
    module: str


@dataclass(order=True)
class SortableImportItem:
    name: str = field(order=str.casefold)
    asname: Optional[str] = field(eq=True, order=False)
    comments: ImportItemComments = field(order=False)


@dataclass(order=True, repr=False)
class SortableImport:
    sort_key: SortKey = field(init=False)
    stem: Optional[str] = field(order=case_insensitive_ordering)  # "from" imports
    items: Sequence[SortableImportItem] = field()
    comments: ImportComments = field()

    config: Config = field(order=False, factory=Config)
    node: cst.CSTNode = field(factory=cst.EmptyLine)  # for cli/debugging only

    def __repr__(self) -> str:  # pragma: nocover
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
            )
            """
            )
            .strip()
            .format(
                sort_key=self.sort_key,
                stem=self.stem,
                items=items,
                comments=self.comments,
            )
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
                value = stem_join(stem=self.stem, name=item.name)
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
            module="",
        )


@dataclass(repr=False)
class SortableBlock:
    start_idx: int
    end_idx: Optional[int] = None  # half-open interval

    imports: List[SortableImport] = field(factory=list)
    imported_names: Dict[str, str] = field(factory=dict)

    def __repr__(self) -> str:  # pragma: nocover
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
            )
            """
            )
            .strip()
            .format(start_idx=self.start_idx, end_idx=self.end_idx, imports=imports)
        )
