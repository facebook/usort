# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import unittest

import libcst as cst

from ..config import Config
from ..sorting import SortableImport, is_side_effect_import, is_sortable_import


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
    def test_is_side_effect(self) -> None:
        config = Config(side_effect_modules=["fizzbuzz", "foo.bar.baz"])
        # import foo, bar
        self.assertFalse(is_side_effect_import("", ["foo", "bar"], config))
        # from foo import bar
        self.assertFalse(is_side_effect_import("foo", ["bar"], config))
        # from foo.bar import foo
        self.assertFalse(is_side_effect_import("foo.bar", ["foo"], config))
        # from foo.bar import baz
        self.assertTrue(is_side_effect_import("foo.bar", ["baz"], config))
        # import foo.bar.baz
        self.assertTrue(is_side_effect_import("", ["foo.bar.baz"], config))
        # import fizzbuzz
        self.assertTrue(is_side_effect_import("", ["fizzbuzz"], config))
        # from fizzbuzz import a, b
        self.assertTrue(is_side_effect_import("fizzbuzz", ["a", "b"], config))
        # from fizzbuzz.apple import a, b
        self.assertTrue(is_side_effect_import("fizzbuzz.apple", ["a", "b"], config))

    def test_is_sortable(self) -> None:
        self.assertTrue(is_sortable_import(cst.parse_statement("import a"), Config()))
        self.assertTrue(
            is_sortable_import(cst.parse_statement("from a import b"), Config())
        )
        self.assertFalse(
            is_sortable_import(cst.parse_statement("import a  # isort: skip"), Config())
        )
