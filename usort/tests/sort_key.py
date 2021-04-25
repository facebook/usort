# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import unittest

import libcst as cst

from ..config import Config
from ..sorting import SortableBlock, SortableImport, is_sortable_import


class SortableImportTest(unittest.TestCase):
    def test_from_node_Import(self) -> None:
        imp = SortableImport.from_node(cst.parse_statement("import a"), Config())
        self.assertEqual("a", imp.first_module)
        self.assertEqual("a", imp.first_dotted_import)
        self.assertEqual({"a": "a"}, imp.imported_names)

        imp = SortableImport.from_node(cst.parse_statement("import a, b"), Config())
        self.assertEqual("a", imp.first_module)
        self.assertEqual("a", imp.first_dotted_import)
        self.assertEqual({"a": "a", "b": "b"}, imp.imported_names)

        imp = SortableImport.from_node(cst.parse_statement("import a as b"), Config())
        self.assertEqual("a", imp.first_module)
        self.assertEqual("a", imp.first_dotted_import)
        self.assertEqual({"b": "a"}, imp.imported_names)

        imp = SortableImport.from_node(cst.parse_statement("import os.path"), Config())
        self.assertEqual("os.path", imp.first_module)
        self.assertEqual("os.path", imp.first_dotted_import)
        self.assertEqual({"os": "os"}, imp.imported_names)

        imp = SortableImport.from_node(
            cst.parse_statement("import IPython.core"), Config()
        )
        self.assertEqual("IPython.core", imp.first_module)
        self.assertEqual("IPython.core", imp.first_dotted_import)
        self.assertEqual({"IPython": "IPython"}, imp.imported_names)

    def test_from_node_ImportFrom(self) -> None:
        imp = SortableImport.from_node(cst.parse_statement("from a import b"), Config())
        self.assertEqual("a", imp.first_module)
        self.assertEqual("b", imp.first_dotted_import)
        self.assertEqual({"b": "a.b"}, imp.imported_names)

        imp = SortableImport.from_node(
            cst.parse_statement("from a import b as c"), Config()
        )
        self.assertEqual("a", imp.first_module)
        self.assertEqual("b", imp.first_dotted_import)
        self.assertEqual({"c": "a.b"}, imp.imported_names)

    def test_from_node_ImportFrom_relative(self) -> None:
        imp = SortableImport.from_node(
            cst.parse_statement("from .a import b"), Config()
        )
        self.assertEqual(".a", imp.first_module)
        self.assertEqual("a", imp.first_dotted_import)
        self.assertEqual({"b": ".a.b"}, imp.imported_names)

        imp = SortableImport.from_node(
            cst.parse_statement("from ...a import b"), Config()
        )
        self.assertEqual("...a", imp.first_module)
        self.assertEqual("a", imp.first_dotted_import)
        self.assertEqual({"b": "...a.b"}, imp.imported_names)

        imp = SortableImport.from_node(cst.parse_statement("from . import a"), Config())
        self.assertEqual(".", imp.first_module)
        self.assertEqual("a", imp.first_dotted_import)
        self.assertEqual({"a": ".a"}, imp.imported_names)

        imp = SortableImport.from_node(
            cst.parse_statement("from .. import a"), Config()
        )
        self.assertEqual("..", imp.first_module)
        self.assertEqual("a", imp.first_dotted_import)
        self.assertEqual({"a": "..a"}, imp.imported_names)

        imp = SortableImport.from_node(
            cst.parse_statement("from . import a as b"), Config()
        )
        self.assertEqual(".", imp.first_module)
        self.assertEqual("a", imp.first_dotted_import)
        self.assertEqual({"b": ".a"}, imp.imported_names)


class IsSortableTest(unittest.TestCase):
    def test_is_sortable(self) -> None:
        self.assertTrue(is_sortable_import(cst.parse_statement("import a"), Config()))
        self.assertTrue(
            is_sortable_import(cst.parse_statement("from a import b"), Config())
        )
        self.assertFalse(
            is_sortable_import(cst.parse_statement("import a  # isort: skip"), Config())
        )


class SortableBlockTest(unittest.TestCase):
    def _block(self) -> SortableBlock:
        s = SortableBlock(5)
        imp = SortableImport.from_node(cst.parse_statement("from x import a"), Config())
        s.add_stmt(imp, 5)
        imp = SortableImport.from_node(cst.parse_statement("from x import b"), Config())
        s.add_stmt(imp, 6)
        imp = SortableImport.from_node(cst.parse_statement("from x import c"), Config())
        s.add_stmt(imp, 7)
        return s

    def test_init(self) -> None:
        s = SortableBlock(5)
        self.assertEqual(5, s.start_idx)
        self.assertEqual(None, s.end_idx)

        self.assertEqual(0, len(s.stmts))

        self.assertEqual(-1, s.name_overlap_idx({"a": "a"}))

    def test_unsplit_overlap_check(self) -> None:
        s = self._block()
        self.assertEqual(
            {
                "a": ("x.a", 5),
                "b": ("x.b", 6),
                "c": ("x.c", 7),
            },
            s.imported_names_idx,
        )
        # same qualname
        self.assertEqual(-1, s.name_overlap_idx({"a": "x.a"}))
        # different qualnames
        self.assertEqual(5, s.name_overlap_idx({"a": "a"}))
        self.assertEqual(6, s.name_overlap_idx({"b": "b"}))
        # multiple; this is unusual
        self.assertEqual(6, s.name_overlap_idx({"a": "a", "b": "b"}))

    def test_imported_names_split(self) -> None:
        s = self._block()

        new = s.split_inplace(6)

        self.assertEqual(5, s.start_idx)
        self.assertEqual(6, s.end_idx)
        self.assertEqual({"a": ("x.a", 5)}, s.imported_names_idx)

        self.assertEqual(6, new.start_idx)
        self.assertEqual(8, new.end_idx)
        self.assertEqual(
            {
                "b": ("x.b", 6),
                "c": ("x.c", 7),
            },
            new.imported_names_idx,
        )
