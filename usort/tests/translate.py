# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import unittest
from pathlib import Path

import libcst as cst

from ..config import Config
from ..sorting import ImportSorter
from ..translate import import_from_node
from ..util import parse_import


class SortableImportTest(unittest.TestCase):
    def test_import_from_node_Import(self) -> None:
        imp = import_from_node(parse_import("import a"), Config())
        self.assertIsNone(imp.stem)
        self.assertEqual("a", imp.items[0].name)
        self.assertEqual({"a": "a"}, imp.imported_names)

        imp = import_from_node(parse_import("import a, b"), Config())
        self.assertIsNone(imp.stem)
        self.assertEqual("a", imp.items[0].name)
        self.assertEqual("b", imp.items[1].name)
        self.assertEqual({"a": "a", "b": "b"}, imp.imported_names)

        imp = import_from_node(parse_import("import a as b"), Config())
        self.assertIsNone(imp.stem)
        self.assertEqual("a", imp.items[0].name)
        self.assertEqual("b", imp.items[0].asname)
        self.assertEqual({"b": "a"}, imp.imported_names)

        imp = import_from_node(parse_import("import os.path"), Config())
        self.assertIsNone(imp.stem)
        self.assertEqual("os.path", imp.items[0].name)
        self.assertEqual({"os": "os"}, imp.imported_names)

        imp = import_from_node(parse_import("import IPython.core"), Config())
        self.assertEqual("IPython.core", imp.items[0].name)
        self.assertEqual({"IPython": "IPython"}, imp.imported_names)

    def test_import_from_node_ImportFrom(self) -> None:
        imp = import_from_node(parse_import("from a import b"), Config())
        self.assertEqual("a", imp.stem)
        self.assertEqual("b", imp.items[0].name)
        self.assertEqual({"b": "a.b"}, imp.imported_names)

        imp = import_from_node(parse_import("from a import b as c"), Config())
        self.assertEqual("a", imp.stem)
        self.assertEqual("b", imp.items[0].name)
        self.assertEqual("c", imp.items[0].asname)
        self.assertEqual({"c": "a.b"}, imp.imported_names)

    def test_import_from_node_ImportFrom_relative(self) -> None:
        imp = import_from_node(parse_import("from .a import b"), Config())
        self.assertEqual(".a", imp.stem)
        self.assertEqual("b", imp.items[0].name)
        self.assertEqual({"b": ".a.b"}, imp.imported_names)

        imp = import_from_node(parse_import("from ...a import b"), Config())
        self.assertEqual("...a", imp.stem)
        self.assertEqual("b", imp.items[0].name)
        self.assertEqual({"b": "...a.b"}, imp.imported_names)

        imp = import_from_node(parse_import("from . import a"), Config())
        self.assertEqual(".", imp.stem)
        self.assertEqual("a", imp.items[0].name)
        self.assertEqual({"a": ".a"}, imp.imported_names)

        imp = import_from_node(parse_import("from .. import a"), Config())
        self.assertEqual("..", imp.stem)
        self.assertEqual("a", imp.items[0].name)
        self.assertEqual({"a": "..a"}, imp.imported_names)

        imp = import_from_node(parse_import("from . import a as b"), Config())
        self.assertEqual(".", imp.stem)
        self.assertEqual("a", imp.items[0].name)
        self.assertEqual("b", imp.items[0].asname)
        self.assertEqual({"b": ".a"}, imp.imported_names)


class IsSortableTest(unittest.TestCase):
    def test_is_sortable(self) -> None:
        sorter = ImportSorter(module=cst.Module([]), path=Path(), config=Config())
        self.assertTrue(sorter.is_sortable_import(parse_import("import a")))
        self.assertTrue(sorter.is_sortable_import(parse_import("from a import b")))
        self.assertFalse(
            sorter.is_sortable_import(parse_import("import a  # isort: skip"))
        )
