# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import unittest
from textwrap import dedent

from .. import types


class TypesTest(unittest.TestCase):
    maxDiff = None

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
                )
            """
        ).strip()
        self.assertEqual(expected_repr, repr(imp))
