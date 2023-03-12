# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import logging
import os
import unittest
from contextlib import contextmanager
from pathlib import Path
from textwrap import dedent
from typing import AnyStr, Generator
from unittest.mock import Mock, patch

import volatile
from click.testing import CliRunner

from ..cli import main


@contextmanager
def chdir(new_dir: str) -> Generator[None, None, None]:
    cur_dir = os.getcwd()
    os.chdir(new_dir)
    try:
        yield
    finally:
        os.chdir(cur_dir)


@contextmanager
def sample_contents(s: AnyStr) -> Generator[str, None, None]:
    with volatile.dir() as dtmp:
        ptmp = Path(dtmp)
        (ptmp / "pyproject.toml").write_text("")
        if isinstance(s, bytes):
            (ptmp / "sample.py").write_bytes(s)
        else:
            (ptmp / "sample.py").write_text(s)
        yield dtmp


class CliTest(unittest.TestCase):
    def test_benchmark(self) -> None:
        """Doesn't trigger multiprocessing (walk first in timings)"""
        with sample_contents("import sys\n") as dtmp:
            runner = CliRunner()
            with chdir(dtmp):
                result = runner.invoke(main, ["--benchmark", "check", "."])

        self.assertRegex(
            result.output,
            dedent(
                r"""
                walking \.:\s+\d+ µs
                parsing sample\.py:\s+\d+ µs
                sorting sample\.py:\s+\d+ µs
                total:\s+\d+ µs
                """
            ).strip(),
        )
        self.assertEqual(0, result.exit_code)

    def test_benchmark_multiple(self) -> None:
        "Does trigger multiprocessing (walk after parsing/sorting in timings)"
        with sample_contents("import sys\n") as dtmp:
            (Path(dtmp) / "foo.py").write_text("print('hello')\n")

            runner = CliRunner()
            with chdir(dtmp):
                result = runner.invoke(main, ["--benchmark", "check", "."])

        self.assertRegex(
            result.output,
            dedent(
                r"""
                parsing foo\.py:\s+\d+ µs
                sorting foo\.py:\s+\d+ µs
                """
            ).strip(),
        )

        self.assertRegex(
            result.output,
            dedent(
                r"""
                parsing sample\.py:\s+\d+ µs
                sorting sample\.py:\s+\d+ µs
                """
            ).strip(),
        )

        self.assertRegex(
            result.output,
            dedent(
                r"""
                walking \.:\s+\d+ µs
                total:\s+\d+ µs
                """
            ).strip(),
        )
        self.assertEqual(0, result.exit_code)

    @patch("usort.cli.sys")
    @patch("usort.cli.logging")
    def test_debug(self, mock_logging: Mock, mock_sys: Mock) -> None:
        mock_logging.DEBUG = logging.DEBUG
        mock_logging.WARNING = logging.WARNING
        mock_sys.stderr = object()

        with sample_contents("import foo\n") as dtmp:
            runner = CliRunner()
            with chdir(dtmp):
                with self.subTest("no debug"):
                    result = runner.invoke(main, ["check", "."])
                    mock_logging.basicConfig.assert_called_with(
                        level=logging.WARNING, stream=mock_sys.stderr
                    )
                    self.assertEqual("", result.output)

                with self.subTest("with debug"):
                    result = runner.invoke(main, ["--debug", "check", "."])
                    mock_logging.basicConfig.assert_called_with(
                        level=logging.DEBUG, stream=mock_sys.stderr
                    )
                    self.assertEqual("", result.output)

    def test_check_no_change(self) -> None:
        with sample_contents("import sys\n") as dtmp:
            runner = CliRunner()
            with chdir(dtmp):
                result = runner.invoke(main, ["check", "."])

        self.assertEqual("", result.output)
        self.assertEqual(0, result.exit_code)

    def test_check_with_change(self) -> None:
        with sample_contents("import sys\nimport os\n") as dtmp:
            runner = CliRunner()
            with chdir(dtmp):
                result = runner.invoke(main, ["check", "."])

        self.assertEqual("Would sort sample.py\n", result.output)
        self.assertEqual(2, result.exit_code)

    def test_check_with_warnings(self) -> None:
        with sample_contents(b"import os\nimport sys\nimport re as os\n") as dtmp:
            runner = CliRunner()
            with chdir(dtmp):
                result = runner.invoke(main, ["check", "."])

        self.assertEqual(
            "Warning at sample.py:3 Name 'os' shadowed by 're'; implicit block split\n"
            "Would sort sample.py\n",
            result.output,
        )

    def test_diff_no_change(self) -> None:
        with sample_contents("import sys\n") as dtmp:
            runner = CliRunner()
            with chdir(dtmp):
                result = runner.invoke(main, ["diff", "."])

        self.assertEqual("", result.output)
        self.assertEqual(0, result.exit_code)

    def test_diff_with_change(self) -> None:
        with sample_contents(b"import sys\nimport os\n") as dtmp:
            runner = CliRunner()
            with chdir(dtmp):
                result = runner.invoke(main, ["diff", "."])

        self.assertEqual(
            """\
--- a/sample.py
+++ b/sample.py
@@ -1,2 +1,2 @@
+import os
 import sys
-import os
""".replace(
                "\r", ""
            ),
            result.output,
        )

        self.assertEqual(result.exit_code, 0)

    def test_list_imports(self) -> None:
        with sample_contents("import sys\nx = 5\nimport os") as dtmp:
            runner = CliRunner()
            with chdir(dtmp):
                # TODO this takes filenames, not paths...
                result = runner.invoke(main, ["list-imports", "sample.py"])

        self.assertEqual(
            """\
sample.py 2 blocks:
  body[0:1]
Formatted:
[[[
import sys
]]]
  body[2:3]
Formatted:
[[[
import os
]]]
""",
            result.output.replace("\r\n", "\n"),
        )
        self.assertEqual(result.exit_code, 0)

    def test_format_no_change(self) -> None:
        with sample_contents("import sys\n") as dtmp:
            runner = CliRunner()
            with chdir(dtmp):
                result = runner.invoke(main, ["format", "."])

        self.assertEqual(result.output, "")
        self.assertEqual(result.exit_code, 0)

    def test_format_parse_error(self) -> None:
        """Code that has syntax that would never be valid in any version of python"""
        with sample_contents("import\n") as dtmp:
            runner = CliRunner()
            with chdir(dtmp):
                result = runner.invoke(main, ["format", "."])

        self.assertRegex(
            result.output,
            r"Error sorting sample\.py: Syntax Error @ 1:1\.\n"
            r"parser error: error at 2:0: expected NAME",
        )
        self.assertEqual(result.exit_code, 1)

    def test_format_parse_error_conflicting_syntax(self) -> None:
        """Code that contains syntax both <=2.7 and >=3.8 that could never coexist"""
        with sample_contents("while (i := foo()):\n    print 'i'\n") as dtmp:
            runner = CliRunner()
            with chdir(dtmp):
                result = runner.invoke(main, ["format", "."])

        self.assertRegex(
            result.output,
            r"Error sorting sample\.py: Syntax Error @ 2:1\.\n"
            r"parser error: error at 2:13: expected one of ",
        )
        self.assertEqual(result.exit_code, 1)

    def test_format_permission_error(self) -> None:
        """File does not have read permissions"""
        with sample_contents("print('hello world')\n") as dtmp:
            runner = CliRunner()
            # make the file unreadable
            (Path(dtmp) / "sample.py").chmod(0o000)
            with chdir(dtmp):
                result = runner.invoke(main, ["format", "."])
            # restore permissions so that cleanup can succeed on windows
            (Path(dtmp) / "sample.py").chmod(0o644)

        self.assertRegex(
            result.output,
            r"Error sorting sample\.py: .+ Permission denied:",
        )
        self.assertEqual(result.exit_code, 1)

    def test_format_with_change(self) -> None:
        with sample_contents("import sys\nimport os\n") as dtmp:
            runner = CliRunner()
            with chdir(dtmp):
                result = runner.invoke(main, ["format", "."])

            self.assertEqual(result.output, "Sorted sample.py\n")
            self.assertEqual(result.exit_code, 0)

            self.assertEqual(
                """\
import os
import sys
""",
                (Path(dtmp) / "sample.py").read_text(),
            )

    def test_format_utf8(self) -> None:
        # the string is "µ" as in "µsort"
        with sample_contents(
            b"""\
import b
import a
s = "\xc2\xb5"
"""
        ) as dtmp:
            runner = CliRunner()
            with chdir(dtmp):
                result = runner.invoke(main, ["diff", "."])

            # Diff output is unicode
            self.assertEqual(
                result.output,
                """\
--- a/sample.py
+++ b/sample.py
@@ -1,3 +1,3 @@
+import a
 import b
-import a
 s = "\u00b5"
""",
                result.output,
            )

            with chdir(dtmp):
                result = runner.invoke(main, ["format", "."])

            self.assertEqual(
                b"""\
import a
import b
s = "\xc2\xb5"
""",
                (Path(dtmp) / "sample.py").read_bytes(),
            )

    def test_format_latin_1(self) -> None:
        # the string is "µ" as in "µsort"
        with sample_contents(
            b"""\
# -*- coding: latin-1 -*-
import b
import a
s = "\xb5"
""".replace(
                b"\r", b""
            )  # git on windows might make \r\n
        ) as dtmp:
            runner = CliRunner()

            # Diff output is unicode
            with chdir(dtmp):
                result = runner.invoke(main, ["diff", "."])

            self.assertEqual(
                result.output,
                """\
--- a/sample.py
+++ b/sample.py
@@ -1,4 +1,4 @@
 # -*- coding: latin-1 -*-
+import a
 import b
-import a
 s = "\u00b5"
""".replace(
                    "\r", ""
                ),  # git on windows again
                result.output,
            )

            # Format keeps current encoding
            with chdir(dtmp):
                result = runner.invoke(main, ["format", "."])

            self.assertEqual(
                b"""\
# -*- coding: latin-1 -*-
import a
import b
s = "\xb5"
""".replace(
                    b"\r", b""
                ),  # git on windows again
                (Path(dtmp) / "sample.py").read_bytes(),
            )
