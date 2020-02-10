import unittest

from ..sorting import usort_string


class FunctionalTest(unittest.TestCase):
    def test_sort_ordering(self):
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
from a.b import foo2
from a import foo
import b
import a.b
import a
"""
            ),
        )

    def test_sort_blocks(self):
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
"""
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

    def test_shadowed_import(self):
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
"""
            ),
        )


if __name__ == "__main__":
    unittest.main()
