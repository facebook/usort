# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import unittest

import libcst as cst

from .. import util


class UtilTest(unittest.TestCase):
    def test_parse_import_simple(self) -> None:
        node = util.parse_import("import a")
        self.assertEqual(
            cst.ensure_type(
                cst.ensure_type(
                    cst.ensure_type(node, cst.SimpleStatementLine).body[0],
                    cst.Import,
                ).names[0],
                cst.ImportAlias,
            ).name.value,
            "a",
        )

    def test_parse_import_from(self) -> None:
        node = util.parse_import("from a import x")
        inner = cst.ensure_type(
            cst.ensure_type(node, cst.SimpleStatementLine).body[0],
            cst.ImportFrom,
        )
        self.assertEqual(cst.ensure_type(inner.module, cst.Name).value, "a")
        assert isinstance(inner.names, list)
        name = inner.names[0]
        self.assertEqual(
            cst.ensure_type(
                name,
                cst.ImportAlias,
            ).name.value,
            "x",
        )

    def test_parse_import_not_an_import(self) -> None:
        with self.assertRaisesRegex(ValueError, "not an import"):
            util.parse_import("print('hello')")

    def test_parse_import_not_a_statement(self) -> None:
        with self.assertRaisesRegex(ValueError, "not a statement"):
            util.parse_import("for foo in bar: print(foo)")

    def test_parse_import_bad_syntax(self) -> None:
        with self.assertRaises(cst.ParserSyntaxError):
            util.parse_import("say 'hello'")

    def test_split_inline_comment(self) -> None:
        self.assertEqual(
            ["# foo", "# bar"], util.split_inline_comment("blah  # foo  # bar\n")
        )

    def test_split_relative(self) -> None:
        self.assertEqual(("foo", 0), util.split_relative("foo"))
        self.assertEqual(("foo", 1), util.split_relative(".foo"))
        self.assertEqual(("foo", 2), util.split_relative("..foo"))
        self.assertEqual(("foo.bar", 0), util.split_relative("foo.bar"))
        self.assertEqual(("foo.bar", 1), util.split_relative(".foo.bar"))

    def test_stem_join(self) -> None:
        self.assertEqual("foo", util.stem_join(None, "foo"))
        self.assertEqual("foo.bar", util.stem_join("foo", "bar"))
        self.assertEqual("foo.bar.baz", util.stem_join("foo", "bar.baz"))
        self.assertEqual(".bar", util.stem_join(".", "bar"))
        self.assertEqual(".foo.bar", util.stem_join(".foo", "bar"))

    def test_top_level_name(self) -> None:
        self.assertEqual("foo", util.top_level_name("foo"))
        self.assertEqual("foo", util.top_level_name("foo.bar"))
        self.assertEqual("foo", util.top_level_name("foo.bar.baz"))
        self.assertEqual("", util.top_level_name(".foo"))

    def test_with_dots(self) -> None:
        self.assertEqual("foo", util.with_dots(cst.Name(value="foo")))
        self.assertEqual(
            "foo.bar.baz",
            util.with_dots(
                cst.Attribute(
                    value=cst.Attribute(
                        value=cst.Name("foo"),
                        attr=cst.Name("bar"),
                    ),
                    attr=cst.Name("baz"),
                )
            ),
        )

        with self.assertRaisesRegex(TypeError, "Can't with_dots"):
            util.with_dots("foo.bar")  # type: ignore
