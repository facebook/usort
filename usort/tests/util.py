# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import unittest

import libcst as cst

from ..util import parse_import


class UtilTest(unittest.TestCase):
    def test_parse_import_simple(self) -> None:
        node = parse_import("import a")
        self.assertIsInstance(node, cst.SimpleStatementLine)
        self.assertIsInstance(node.body[0], cst.Import)
        self.assertIsInstance(node.body[0].names[0], cst.ImportAlias)  # type: ignore
        self.assertEqual(node.body[0].names[0].name.value, "a")  # type: ignore

    def test_parse_import_from(self) -> None:
        node = parse_import("from a import x")
        self.assertIsInstance(node, cst.SimpleStatementLine)
        self.assertIsInstance(node.body[0], cst.ImportFrom)
        self.assertIsInstance(node.body[0].names[0], cst.ImportAlias)  # type: ignore
        self.assertEqual(node.body[0].module.value, "a")  # type: ignore
        self.assertEqual(node.body[0].names[0].name.value, "x")  # type: ignore

    def test_parse_import_not_an_import(self) -> None:
        with self.assertRaisesRegex(ValueError, "not an import"):
            parse_import("print('hello')")

    def test_parse_import_not_a_statement(self) -> None:
        with self.assertRaisesRegex(ValueError, "not a statement"):
            parse_import("for foo in bar: print(foo)")

    def test_parse_import_bad_syntax(self) -> None:
        with self.assertRaises(cst.ParserSyntaxError):
            parse_import("say 'hello'")
