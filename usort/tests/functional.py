# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import unittest
from pathlib import Path

from ..config import Config
from ..sorting import SortableImport, usort_string
from ..util import try_parse

DEFAULT_CONFIG = Config(known_first_party={"fp"})


class BasicOrderingTest(unittest.TestCase):
    maxDiff = None

    def test_order(self) -> None:
        items_in_order = [
            b"from __future__ import division",
            b"import os",
            b"from os import path",
            b"import tp",
            b"from tp import x",
            b"from .. import c",
            b"from . import a",
            b"from . import b",
            b"from .a import z",
        ]

        nodes = [
            SortableImport.from_node(
                try_parse(Path("test.py"), data=x).body[0], config=DEFAULT_CONFIG
            )
            for x in items_in_order
        ]
        self.assertEqual(nodes, sorted(nodes))


class UsortStringFunctionalTest(unittest.TestCase):
    def test_sort_ordering(self) -> None:
        # This only tests ordering, not any of the comment or whitespace
        # modifications.
        self.assertEqual(
            """\
import a
import a.b
import b
from a import foo
from a.b import foo2
""",
            usort_string(
                """\
import a
import a.b
from a.b import foo2
from a import foo
import b
""",
                DEFAULT_CONFIG,
            ),
        )

    def test_sort_blocks(self) -> None:
        # This only tests that there are two blocks and we only reorder within a
        # block
        self.assertEqual(
            """\
import c
import d
print("hi")
import a
import b
""",
            usort_string(
                """\
import d
import c
print("hi")
import b
import a
""",
                DEFAULT_CONFIG,
            ),
        )

    # Disabled until wrapping is supported
    #     def test_sort_wrap_moves_comments(self):
    #         # Test that end-of-line directive comments get moved to the first line
    #         # when wrapping is going to happen.
    #         self.assertEqual(
    #             """\
    # from a (  # pylint: disable=E1
    #     import foo,
    # )
    # """,
    #             usort_string(
    #                 """\
    # from a import foo  # pylint: disable=E1
    # """,
    #                 line_limit=10,
    #             ),
    #         )

    def test_shadowed_import(self) -> None:
        # Test that a new block is started when there's a duplicate name
        self.assertEqual(
            """\
import b as b
import a as b
""",
            usort_string(
                """\
import b as b
import a as b
""",
                DEFAULT_CONFIG,
            ),
        )

    def test_dot_handling(self) -> None:
        # Test that 'from .. import b' comes before 'from ..a import foo'
        self.assertEqual(
            """\
import fp
from fp import z
from .. import b
from ..a import foo
from . import d
from .c import e
""",
            usort_string(
                """\
from ..a import foo
from .. import b
from . import d
from fp import z
import fp
from .c import e
""",
                DEFAULT_CONFIG,
            ),
        )


if __name__ == "__main__":
    unittest.main()
