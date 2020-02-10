import unittest

import libcst as cst

from ..sorting import SortableImport, SortKey


class SortableImportTest(unittest.TestCase):
    def test_from_node_Import(self):
        imp = SortableImport.from_node(cst.parse_statement("import a"))
        self.assertEqual("a", imp.first_module)
        self.assertEqual("a", imp.first_dotted_import)
        self.assertEqual({"a"}, imp.imported_names)

        imp = SortableImport.from_node(cst.parse_statement("import a, b"))
        self.assertEqual("a", imp.first_module)
        self.assertEqual("a", imp.first_dotted_import)
        self.assertEqual({"a", "b"}, imp.imported_names)

        imp = SortableImport.from_node(cst.parse_statement("import a as b"))
        self.assertEqual("a", imp.first_module)
        self.assertEqual("b", imp.first_dotted_import)
        self.assertEqual({"b"}, imp.imported_names)

    def test_from_node_ImportFrom(self):
        imp = SortableImport.from_node(cst.parse_statement("from a import b"))
        self.assertEqual("a", imp.first_module)
        self.assertEqual("b", imp.first_dotted_import)
        self.assertEqual({"b"}, imp.imported_names)

        imp = SortableImport.from_node(cst.parse_statement("from a import b as c"))
        self.assertEqual("a", imp.first_module)
        self.assertEqual("b", imp.first_dotted_import)
        self.assertEqual({"c"}, imp.imported_names)

    def test_from_node_ImportFrom_relative(self):
        imp = SortableImport.from_node(cst.parse_statement("from .a import b"))
        self.assertEqual(".a", imp.first_module)
        self.assertEqual("b", imp.first_dotted_import)
        self.assertEqual({"b"}, imp.imported_names)

        imp = SortableImport.from_node(cst.parse_statement("from . import a"))
        self.assertEqual(".a", imp.first_module)
        self.assertEqual("a", imp.first_dotted_import)
        self.assertEqual({"a"}, imp.imported_names)
