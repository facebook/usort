# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import os
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import volatile
from click.testing import CliRunner

from usort.cli import main


@contextmanager
def chdir(new_dir: str) -> Generator[None, None, None]:
    cur_dir = os.getcwd()
    os.chdir(new_dir)
    yield
    os.chdir(cur_dir)


@contextmanager
def sample_contents(s: str) -> Generator[str, None, None]:
    with volatile.dir() as dtmp:
        ptmp = Path(dtmp)
        (ptmp / "pyproject.toml").write_text("")
        (ptmp / "sample.py").write_text(s)
        yield dtmp


class CliTest(unittest.TestCase):
    def test_benchmark(self) -> None:
        with sample_contents("import sys\n") as dtmp:
            runner = CliRunner()
            with chdir(dtmp):
                result = runner.invoke(main, ["--benchmark", "check", "."])

        self.assertRegex(
            result.output,
            r"""walking \.:\s+\d+ µs
parsing sample\.py:\s+\d+ µs
sorting sample\.py:\s+\d+ µs
""",
        )
        self.assertEqual(0, result.exit_code)

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

    def test_diff_no_change(self) -> None:
        with sample_contents("import sys\n") as dtmp:
            runner = CliRunner()
            with chdir(dtmp):
                result = runner.invoke(main, ["diff", "."])

        self.assertEqual("", result.output)
        self.assertEqual(0, result.exit_code)

    def test_diff_with_change(self) -> None:
        with sample_contents("import sys\nimport os\n") as dtmp:
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
""",
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
            r"Error sorting sample\.py: Syntax Error @ 1:7\.",
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
            r"Error sorting sample\.py: Syntax Error @ 2:11\.",
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
