# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import libcst as cst

from .config import Config
from .util import with_dots


@dataclass
class Result:
    path: Path
    content: bytes
    output: bytes
    # encoding will be None on parse errors; we get this from LibCST on a successful
    # parse.
    encoding: Optional[str]
    error: Optional[Exception] = None


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
