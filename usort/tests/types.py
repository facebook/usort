# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import unittest
from textwrap import dedent

from .. import types


class TypesTest(unittest.TestCase):
    maxDiff = None

    def test_import_item_comments_add(self) -> None:
        a = types.ImportItemComments(
            before=["# hi"], inline=["# type: ignore"], following=[]
        )
        b = types.ImportItemComments(
            before=[],
            inline=["# noqa"],
            following=["# bye"],
        )
        expected = types.ImportItemComments(
            before=["# hi"],
            inline=["# type: ignore", "# noqa"],
            following=["# bye"],
        )

        with self.subTest("add"):
            self.assertEqual(expected, a + b)

        with self.subTest("inplace"):
            a += b
            self.assertEqual(expected, a)

        with self.subTest("bad types"):
            with self.assertRaisesRegex(
                TypeError, "unsupported.+'ImportItemComments'.+'int'"
            ):
                a += 10  # type: ignore

    def test_import_comments_add(self) -> None:
        a = types.ImportComments(
            before=["# header"],
            first_inline=[],
            initial=[],
            inline=[],
            final=[],
            last_inline=["# footer"],
        )
        b = types.ImportComments(
            before=[],
            first_inline=["# noqa"],
            initial=[],
            inline=[],
            final=[],
            last_inline=["# goodbye"],
        )
        expected = types.ImportComments(
            before=["# header"],
            first_inline=["# noqa"],
            initial=[],
            inline=[],
            final=[],
            last_inline=["# footer", "# goodbye"],
        )

        with self.subTest("add"):
            self.assertEqual(expected, a + b)

        with self.subTest("inplace"):
            a += b
            self.assertEqual(expected, a)

        with self.subTest("bad types"):
            with self.assertRaisesRegex(
                TypeError, "unsupported.+'ImportComments'.+'int'"
            ):
                a += 10  # type: ignore

    def test_sortable_import_item_add(self) -> None:
        a = types.SortableImportItem(
            name="foo",
            asname="foofoo",
            comments=types.ImportItemComments(
                inline=["# noqa"],
            ),
        )
        b = types.SortableImportItem(
            name="foo",
            asname="foofoo",
            comments=types.ImportItemComments(
                before=["# hello"],
            ),
        )
        expected = types.SortableImportItem(
            name="foo",
            asname="foofoo",
            comments=types.ImportItemComments(
                before=["# hello"],
                inline=["# noqa"],
            ),
        )

        with self.subTest("add"):
            self.assertEqual(expected, a + b)

        with self.subTest("inplace"):
            a += b
            self.assertEqual(expected, a)

        with self.subTest("bad types"):
            with self.assertRaisesRegex(
                TypeError, "unsupported.+'SortableImportItem'.+'int'"
            ):
                a += 10  # type: ignore

    def test_sortable_import_add(self) -> None:
        a = types.SortableImport(
            stem="foo",
            items=[
                types.SortableImportItem(
                    name="bar",
                    asname=None,
                    comments=types.ImportItemComments(
                        before=["# hello"],
                    ),
                ),
                types.SortableImportItem(
                    name="baz",
                    asname=None,
                    comments=types.ImportItemComments(
                        inline=["# noqa"],
                    ),
                ),
            ],
            comments=types.ImportComments(
                before=["# original block"],
            ),
            indent="",
        )
        b = types.SortableImport(
            stem="foo",
            items=[
                types.SortableImportItem(
                    name="bar",
                    asname=None,
                    comments=types.ImportItemComments(
                        inline=["# noqa"],
                    ),
                ),
                types.SortableImportItem(
                    name="baz",
                    asname="bazz",
                    comments=types.ImportItemComments(),
                ),
                types.SortableImportItem(
                    name="buzz",
                    asname=None,
                    comments=types.ImportItemComments(),
                ),
            ],
            comments=types.ImportComments(
                before=["# added block"],
            ),
            indent="",
        )
        expected = types.SortableImport(
            stem="foo",
            items=[
                types.SortableImportItem(
                    name="bar",
                    asname=None,
                    comments=types.ImportItemComments(
                        before=["# hello"],
                        inline=["# noqa"],
                    ),
                ),
                types.SortableImportItem(
                    name="baz",
                    asname=None,
                    comments=types.ImportItemComments(
                        inline=["# noqa"],
                    ),
                ),
                types.SortableImportItem(
                    name="baz",
                    asname="bazz",
                    comments=types.ImportItemComments(),
                ),
                types.SortableImportItem(
                    name="buzz",
                    asname=None,
                    comments=types.ImportItemComments(),
                ),
            ],
            comments=types.ImportComments(
                before=["# original block", "# added block"],
            ),
            indent="",
        )

        with self.subTest("add"):
            self.assertEqual(expected, a + b)

        with self.subTest("inplace"):
            a += b
            self.assertEqual(expected, a)

        with self.subTest("bad types"):
            with self.assertRaisesRegex(
                TypeError, "unsupported.+'SortableImport'.+'int'"
            ):
                a += 10  # type: ignore

    def test_sortable_block_repr(self) -> None:
        imp = types.SortableBlock(
            start_idx=0,
            end_idx=2,
            imports=[
                types.SortableImport(
                    stem="foo",
                    items=[
                        types.SortableImportItem(
                            "bar", None, types.ImportItemComments()
                        ),
                        types.SortableImportItem(
                            "baz", "buzz", types.ImportItemComments()
                        ),
                    ],
                    comments=types.ImportComments(),
                    indent="    ",
                ),
                types.SortableImport(
                    stem="apple",
                    items=[
                        types.SortableImportItem(
                            "core", None, types.ImportItemComments()
                        ),
                    ],
                    comments=types.ImportComments(),
                    indent="    ",
                ),
            ],
        )

        expected_repr = dedent(
            """
                SortableBlock(
                    start_idx = 0,
                    end_idx = 2,
                    imports = [
                        SortableImport(
                            # sort_key = SortKey(category_index=2, is_from_import=True, ndots=0),
                            stem = 'foo',
                            items = [
                                SortableImportItem(name='bar', asname=None, comments=ImportItemComments(before=[], inline=[], following=[])),
                                SortableImportItem(name='baz', asname='buzz', comments=ImportItemComments(before=[], inline=[], following=[])),
                            ],
                            comments = ImportComments(before=[], first_inline=[], initial=[], inline=[], final=[], last_inline=[]),
                            indent = '    ',
                        ),
                        SortableImport(
                            # sort_key = SortKey(category_index=2, is_from_import=True, ndots=0),
                            stem = 'apple',
                            items = [
                                SortableImportItem(name='core', asname=None, comments=ImportItemComments(before=[], inline=[], following=[])),
                            ],
                            comments = ImportComments(before=[], first_inline=[], initial=[], inline=[], final=[], last_inline=[]),
                            indent = '    ',
                        ),
                    ],
                    imported_names = {},
                )
            """
        ).strip()
        self.assertEqual(expected_repr, repr(imp))
