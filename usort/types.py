# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import libcst as cst

from .config import Config


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


@dataclass
class SortableBlock:
    start_idx: int
    end_idx: Optional[int] = None  # half-open interval

    stmts: List[SortableImport] = field(default_factory=list)
    imported_names: Dict[str, str] = field(default_factory=dict)
