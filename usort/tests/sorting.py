# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import unittest
from pathlib import Path

import libcst as cst

from ..config import Config
from ..sorting import ImportSorter


class SplitTest(unittest.TestCase):
    def test_split_block(self) -> None:
        mod = cst.parse_module(
            b"""\
from a import x
from b import y
from b import y
from c import x
"""
        )
        x = ImportSorter(module=mod, path=Path(), config=Config())
        blocks = x.sortable_blocks(mod.children)  # type: ignore
        self.assertEqual(2, len(blocks))
        self.assertEqual({"x": "a.x"}, blocks[0].imported_names)
        self.assertEqual({"y": "b.y", "x": "c.x"}, blocks[1].imported_names)
