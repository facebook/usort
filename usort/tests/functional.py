# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from textwrap import dedent
from typing import Optional

from ..api import usort, usort_path
from ..config import Config
from ..translate import import_from_node
from ..util import parse_import

DEFAULT_CONFIG = Config()


class BasicOrderingTest(unittest.TestCase):
    maxDiff = None

    def test_order(self) -> None:
        items_in_order = [
            "from __future__ import division",
            "import os",
            "from os import path",
            "import tp",
            "from tp import x",
            "from .. import c",
            "from . import a",
            "from . import b",
            "from .a import z",
        ]

        nodes = [
            import_from_node(parse_import(x), config=DEFAULT_CONFIG)
            for x in items_in_order
        ]
        self.assertSequenceEqual(nodes, sorted(nodes))


class UsortStringFunctionalTest(unittest.TestCase):
    def assertUsortResult(
        self, before: str, after: str, config: Optional[Config] = None
    ) -> None:
        before = dedent(before)
        after = dedent(after)
        config = config or DEFAULT_CONFIG
        result1 = usort(before.encode(), config)  # first pass
        result2 = usort(result1.output, config)  # enforce stable sorting on second pass
        if result1.error:
            raise result1.error
        if result2.error:
            raise result2.error
        if result2.output != result1.output:
            self.fail(
                "µsort result was not stable on second pass:\n\n"
                f"Before:\n-------\n{before}\n"
                f"First Pass:\n-----------\n{result1.output.decode()}\n"
                f"Second Pass:\n------------\n{result2.output.decode()}"
            )
        if result2.output.decode() != after:
            self.fail(
                "µsort result did not match expected value:\n\n"
                f"Before:\n-------\n{before}\n"
                f"Expected:\n---------\n{after}\n"
                f"Result:\n-------\n{result1.output.decode()}"
            )

    def test_sort_ordering(self) -> None:
        # This only tests ordering, not any of the comment or whitespace
        # modifications.
        self.assertUsortResult(
            """
                import a
                import a.b
                from a.b import foo2
                from a import foo
                import b
            """,
            """
                import a
                import a.b
                import b
                from a import foo
                from a.b import foo2
            """,
        )

    def test_sort_blocks(self) -> None:
        # This only tests that there are two blocks and we only reorder within a
        # block
        self.assertUsortResult(
            """
                import d
                import c
                print("hi")
                import b
                import a
            """,
            """
                import c
                import d
                print("hi")
                import a
                import b
            """,
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

    def test_star_imports(self) -> None:
        # Test that we create a second block with the star import
        self.assertUsortResult(
            """
                import d
                import c
                from x import *
                import b
                import a
            """,
            """
                import c
                import d
                from x import *
                import a
                import b
            """,
        )

    def test_shadowed_import(self) -> None:
        # Test that a new block is started when there's a duplicate name
        self.assertUsortResult(
            """
                import b as b
                import a as b
            """,
            """
                import b as b
                import a as b
            """,
        )

    def test_shadowed_import_ok(self) -> None:
        self.assertUsortResult(
            """
                import a.d
                import a.c
                import a.b
            """,
            """
                import a.b
                import a.c
                import a.d
            """,
        )

    def test_shadowed_relative_import_ok(self) -> None:
        self.assertUsortResult(
            """
                from os import path as path
                from os import path
                import os.path as path
            """,
            """
                import os.path as path
                from os import path, path as path
            """,
        )

    def test_dot_handling(self) -> None:
        # Test that 'from .. import b' comes before 'from ..a import foo'
        self.assertUsortResult(
            """
                from ..a import foo
                from .. import b
                from . import d
                from fp import z
                import fp
                from .c import e
            """,
            """
                import fp
                from fp import z

                from .. import b
                from ..a import foo
                from . import d
                from .c import e
            """,
        )

    def test_customized_sections(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "pyproject.toml").write_text(
                """\
[tool.usort]
categories = ["future", "standard_library", "numpy", "third_party", "first_party"]
[tool.usort.known]
numpy = ["numpy", "pandas"]
"""
            )
            sample = Path(d) / "sample.py"
            conf = Config.find(sample)
            self.assertUsortResult(
                """
                    import os
                    from . import foo
                    import numpy as np
                    import aaa
                """,
                """
                    import os

                    import numpy as np

                    import aaa

                    from . import foo
                """,
                conf,
            )

    def test_non_module_imports(self) -> None:
        self.assertUsortResult(
            """
                if True:
                    import b
                    import a

                def func():
                    import d
                    import c
                    if True:
                        import f
                        import e
                        pass
                        import a
            """,
            """
                if True:
                    import a
                    import b

                def func():
                    import c
                    import d
                    if True:
                        import e
                        import f
                        pass
                        import a
            """,
        )

    def test_whitespace_between_sections(self) -> None:
        self.assertUsortResult(
            """
                from __future__ import unicode_literals
                from __future__ import division
                import sys



                import third_party
                #comment
                from . import first_party
            """,
            """
                from __future__ import division, unicode_literals

                import sys

                import third_party

                #comment
                from . import first_party
            """,
        )

    def test_whitespace_between_sections_indented(self) -> None:
        self.assertUsortResult(
            """
                import sys
                def foo():
                    import os
                    from something import nothing
            """,
            # TODO: maybe we should add whitespace after the last import in a block?
            """
                import sys
                def foo():
                    import os

                    from something import nothing
            """,
        )

    def test_case_insensitive_sorting(self) -> None:
        content = """
            import calendar
            import cProfile
            import dataclasses

            from fissix.main import diff_texts
            from IPython import start_ipython
            from libcst import Module
        """
        self.assertUsortResult(content, content)

    def test_side_effect_modules(self) -> None:
        config = replace(
            DEFAULT_CONFIG,
            side_effect_modules=["tracemalloc", "fizzbuzz", "foo.bar.baz"],
        )
        content = """
            from zipfile import ZipFile
            from tracemalloc import start
            from collections import defaultdict

            import fizzbuzz
            import attr
            import solar
            import foo.bar.baz
            from foo import bar
            from star import sun
            from foo.bar import baz
            from attr import evolve
        """
        self.assertUsortResult(content, content, config)

    def test_match_black_blank_line_before_comment(self) -> None:
        content = """
            import a
            import b

            # comment
            import c
        """
        self.assertUsortResult(content, content)

    def test_multi_line_comments(self) -> None:
        self.assertUsortResult(
            """
                from fuzz import buzz
                # one
                from foo import (  # two
                    # three
                    beta,  # four
                    # five
                    gamma, # six
                    alpha # seven
                    , # eight
                    # nine
                )  # ten
                # eleven
            """,
            """
                # one
                from foo import (  # two
                    alpha,  # seven  # eight
                    # three
                    beta,  # four
                    # five
                    gamma,  # six
                    # nine
                )  # ten
                from fuzz import buzz
                # eleven
            """,
        )

    def test_multi_line_maintain(self) -> None:
        self.assertUsortResult(
            """
                from fuzz import buzz
                # one
                from foo import (  # two
                    # three
                    bar,  # four
                    # five
                    baz # six
                    , # seven
                    # eight
                )  # nine
                # ten
            """,
            """
                # one
                from foo import (  # two
                    # three
                    bar,  # four
                    # five
                    baz,  # six  # seven
                    # eight
                )  # nine
                from fuzz import buzz
                # ten
            """,
        )

    def test_multi_line_maintain_inner(self) -> None:
        self.assertUsortResult(
            """
                def foo():
                    from fuzz import buzz
                    # one
                    from foo import (  # two
                        # three
                        bar,  # four
                        # five
                        baz # six
                        , # seven
                        # eight
                    )  # nine
                    # ten
            """,
            """
                def foo():
                    # one
                    from foo import (  # two
                        # three
                        bar,  # four
                        # five
                        baz,  # six  # seven
                        # eight
                    )  # nine
                    from fuzz import buzz
                    # ten
            """,
        )

    def test_multi_line_collapse(self) -> None:
        self.assertUsortResult(
            """
                from fuzz import buzz
                # 1
                from foo import (  # 2
                    # 3
                    bar,  # 4
                    # 5
                    baz # 6
                    , # 7
                )  # 8
                # 9
            """,
            """
                # 1
                from foo import bar, baz  # 2  # 3  # 4  # 5  # 6  # 7  # 8
                from fuzz import buzz
                # 9
            """,
        )

    def test_multi_line_collapse_inner(self) -> None:
        self.assertUsortResult(
            """
                def foo():
                    from fuzz import buzz
                    # 1
                    from foo import (  # 2
                        # 3
                        bar,  # 4
                        # 5
                        baz # 6
                        , # 7
                    )  # 8
                    # 9
            """,
            """
                def foo():
                    # 1
                    from foo import bar, baz  # 2  # 3  # 4  # 5  # 6  # 7  # 8
                    from fuzz import buzz
                    # 9
            """,
        )

    def test_maintain_tabs(self) -> None:
        self.assertUsortResult(
            """
                import foo

                def a():
                \timport bar
                \t
                \tdef b():
                \t\timport baz
            """,
            """
                import foo

                def a():
                \timport bar
                \t
                \tdef b():
                \t\timport baz
            """,
        )

    def test_multi_line_expand_top_level(self) -> None:
        self.assertUsortResult(
            """
                from really_absurdly_long_python_module_name.insanely_long_submodule_name import SomeReallyObnoxiousCamelCaseClass
            """,
            """
                from really_absurdly_long_python_module_name.insanely_long_submodule_name import (
                    SomeReallyObnoxiousCamelCaseClass,
                )
            """,
        )

    def test_multi_line_expand_function(self) -> None:
        self.assertUsortResult(
            """
                def foo():
                    from really_absurdly_long_python_module_name.insanely_long_submodule_name import SomeReallyObnoxiousCamelCaseClass
            """,
            """
                def foo():
                    from really_absurdly_long_python_module_name.insanely_long_submodule_name import (
                        SomeReallyObnoxiousCamelCaseClass,
                    )
            """,
        )

    def test_multi_line_expand_inner_function(self) -> None:
        self.assertUsortResult(
            """
                def foo():
                    import b
                    import a

                    def bar():
                        from really_absurdly_long_python_module_name.insanely_long_submodule_name import SomeReallyObnoxiousCamelCaseClass
            """,
            """
                def foo():
                    import a
                    import b

                    def bar():
                        from really_absurdly_long_python_module_name.insanely_long_submodule_name import (
                            SomeReallyObnoxiousCamelCaseClass,
                        )
            """,
        )

    def test_single_line_parens(self) -> None:
        self.assertUsortResult(
            """
                from delta import echo, foxtrot
                from alfa import (bravo, charlie)  # hello
            """,
            """
                from alfa import bravo, charlie  # hello
                from delta import echo, foxtrot
            """,
        )

    def test_single_line_import_long_comment(self) -> None:
        """
        Basic import statements can't be reflowed to multiple lines
        """
        self.assertUsortResult(
            """
                import foo, bar, baz  # some really long inline comment that would can't be reflowed to a new line
            """,
            """
                import bar, baz, foo  # some really long inline comment that would can't be reflowed to a new line
            """,
        )

    def test_sorting_import_items(self) -> None:
        self.assertUsortResult(
            """
                import b, a, c
                from typing import List, Dict, Set, Optional, Pattern
            """,
            """
                from typing import Dict, List, Optional, Pattern, Set

                import a, b, c
            """,
        )

    def test_sorting_import_items_comments(self) -> None:
        self.assertUsortResult(
            """
                # zero
                from foo import (  # one
                    # two
                    gamma,  # three
                    bravo,  # four
                    delta,  # five
                    alpha,  # six
                    # seven
                )  # eight
            """,
            """
                # zero
                from foo import (  # one
                    alpha,  # six
                    bravo,  # four
                    delta,  # five
                    # two
                    gamma,  # three
                    # seven
                )  # eight
            """,
        )

    def test_merging_import_items(self) -> None:
        self.assertUsortResult(
            """
                import os
                import os.path
                from typing import List, Dict, Tuple, Set, Optional
                import os
                from typing import Union, Sequence
                from foo.bar import b, d, c
                from foo import baz
                from foo.bar import c as C, a, d
                from foo import fizz
            """,
            """
                import os
                import os.path
                from typing import Dict, List, Optional, Sequence, Set, Tuple, Union

                from foo import baz, fizz
                from foo.bar import a, b, c, c as C, d
            """,
        )

    def test_merging_imports_with_multiple_blocks(self) -> None:
        """verify that merging doesn't affect future blocks/statements"""
        self.assertUsortResult(
            """
                import os
                import os.path
                from datetime import date
                from datetime import datetime
                from typing import *
                import re
                from pathlib import Path
                print("hello world")
            """,
            """
                import os
                import os.path
                from datetime import date, datetime
                from typing import *
                import re
                from pathlib import Path
                print("hello world")
            """,
        )

    def test_merging_import_items_comments(self) -> None:
        self.assertUsortResult(
            """
                import a

                # one
                from foo import ( # two
                    # three
                    beta,  # four
                    # five
                    delta,  # six
                    # seven
                )  # eight
                # apple
                from foo import (  # banana
                    # cranberry
                    gamma,  # date
                    # elderberry
                    alpha,  # fig
                    # grape
                    beta,  # hazelnut
                    # kiwi
                ) # lime
                # mango
            """,
            """
                import a

                # one
                # apple
                from foo import (  # two  # banana
                    # elderberry
                    alpha,  # fig
                    # three
                    # grape
                    beta,  # four  # hazelnut
                    # five
                    delta,  # six
                    # cranberry
                    gamma,  # date
                    # seven
                    # kiwi
                )  # eight  # lime
                # mango
            """,
        )

    def test_merging_imports_disabled(self) -> None:
        self.assertUsortResult(
            """
                import os
                import os.path
                from typing import List, Dict, Tuple, Set, Optional
                import os
                from typing import Union, Sequence
                from foo.bar import b, d, c
                from foo import baz
                from foo.bar import c as C, a, d
                from foo import fizz
            """,
            """
                import os
                import os
                import os.path
                from typing import Dict, List, Optional, Set, Tuple
                from typing import Sequence, Union

                from foo import baz
                from foo import fizz
                from foo.bar import a, c as C, d
                from foo.bar import b, c, d
            """,
            Config(merge_imports=False),
        )

    def test_sort_implicit_blocks1(self) -> None:
        self.assertUsortResult(
            """
                from phi import phi
                from alpha import SHADOW
                from delta import delta
                from eta import eta
                from mu import SHADOW
                from chi import chi
                from beta import beta
            """,
            """
                from alpha import SHADOW
                from beta import beta
                from chi import chi
                from delta import delta
                from eta import eta
                from mu import SHADOW
                from phi import phi
            """,
        )

    def test_sort_implicit_blocks2(self) -> None:
        self.assertUsortResult(
            """
                from mu import SHADOW
                from delta import delta
                from eta import eta
                from chi import chi
                from alpha import SHADOW
                from beta import beta
            """,
            """
                from chi import chi
                from delta import delta
                from eta import eta
                from mu import SHADOW
                from alpha import SHADOW
                from beta import beta
            """,
        )

    def test_sort_implicit_blocks3(self) -> None:
        self.assertUsortResult(
            """
                from phi import phi
                from delta import SHADOW
                from eta import eta
                from chi import chi
                from alpha import SHADOW
                from beta import beta
            """,
            """
                from chi import chi
                from delta import SHADOW
                from alpha import SHADOW
                from beta import beta
                from eta import eta
                from phi import phi
            """,
        )

    def test_skip_directives(self) -> None:
        """Test both usort:skip and isort:skip on single line imports"""
        self.assertUsortResult(
            """
                from os import path
                import functools  # usort: skip
                import asyncio
                from collections import defaultdict  # isort:skip
                from asyncio import gather
            """,
            """
                from os import path
                import functools  # usort: skip
                import asyncio
                from collections import defaultdict  # isort:skip
                from asyncio import gather
            """,
        )

    def test_skip_directives_after_noqa(self) -> None:
        """Test that skips are obeyed, even if they aren't the first directive"""
        self.assertUsortResult(
            """
                from os import path
                import functools  # noqa  # usort: skip
                import asyncio
            """,
            """
                from os import path
                import functools  # noqa  # usort: skip
                import asyncio
            """,
        )

    def test_skip_directives_multiline(self) -> None:
        """Validate that skip work on both first and last line of multiline imports"""
        self.assertUsortResult(
            """
                from unittest.mock import (
                    Mock, MagicMock, call, patch, sentinel, ANY,
                )  # usort:skip
                from functools import wraps
                from asyncio import (  # usort:skip
                    gather, wait,
                )
                from collections import defaultdict
            """,
            """
                from unittest.mock import (
                    Mock, MagicMock, call, patch, sentinel, ANY,
                )  # usort:skip
                from functools import wraps
                from asyncio import (  # usort:skip
                    gather, wait,
                )
                from collections import defaultdict
            """,
        )

    def test_excludes(self) -> None:
        original_content = "import os\nimport asyncio\n"
        sorted_content = b"import asyncio\nimport os\n"
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            (tdp / "pyproject.toml").write_text(
                """\
[tool.usort]
excludes = [
    "fixtures/",
    "*generated.py",
]
"""
            )
            (tdp / "foo" / "tests" / "fixtures").mkdir(parents=True)

            excluded_paths = (
                (tdp / "foo" / "tests" / "fixtures" / "foo.py"),
                (tdp / "foo" / "tests" / "foo_generated.py"),
                (tdp / "foo" / "client_generated.py"),
            )
            sorted_paths = (
                (tdp / "foo" / "tests" / "foo.py"),
                (tdp / "foo" / "foo.py"),
                (tdp / "foo" / "generated_client.py"),
            )

            for path in excluded_paths + sorted_paths:
                path.write_text(original_content)

            results = list(usort_path(tdp / "foo"))
            for result in results:
                self.assertIn(result.path, sorted_paths)
                self.assertNotIn(result.path, excluded_paths)
                self.assertEqual(sorted_content, result.output.replace(b"\r\n", b"\n"))
            self.assertEqual(len(sorted_paths), len(results))


if __name__ == "__main__":
    unittest.main()
