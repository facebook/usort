# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import unittest

import libcst as cst

from ..config import Config
from ..sorting import SortableImport, is_sortable_import


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
