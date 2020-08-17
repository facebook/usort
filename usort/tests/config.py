# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import tempfile
import unittest
from pathlib import Path

from usort.config import Category, Config


class ConfigTest(unittest.TestCase):
    def test_third_party(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            # Defaults should not know about this module.
            # This is a silly value for default_category but this makes it more
            # obvious when it's in use.
            (Path(d) / "pyproject.toml").write_text(
                """\
[tool.usort]
default_section = "future"
"""
            )
            conf = Config.find(Path(d))
            self.assertEqual(set(), conf.known_third_party)
            self.assertEqual(Category.FUTURE, conf.category("psutil.cpu_times"))

            (Path(d) / "pyproject.toml").write_text(
                """\
[tool.usort]
default_section = "future"
known_third_party = ["psutil", "cocoa"]
"""
            )

            conf = Config.find(Path(d))
            self.assertEqual({"psutil", "cocoa"}, conf.known_third_party)
            self.assertEqual(Category.THIRD_PARTY, conf.category("psutil.cpu_times"))

            # Works even on invalid children
            conf = Config.find(Path(d) / "foo")
            self.assertEqual({"psutil", "cocoa"}, conf.known_third_party)
            self.assertEqual(Category.THIRD_PARTY, conf.category("psutil.cpu_times"))

    def test_first_party_root_finding(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a" / "b" / "c").mkdir(parents=True)
            (Path(d) / "a" / "b" / "__init__.py").write_text("")
            (Path(d) / "a" / "b" / "c" / "__init__.py").write_text("from b import zzz")

            f = Path(d) / "a" / "b" / "c" / "__init__"

            conf = Config.find(f)
            self.assertEqual({"b"}, conf.known_first_party)
            conf = Config.find(f.parent)  # c
            self.assertEqual({"b"}, conf.known_first_party)
            conf = Config.find(f.parent.parent)  # b
            self.assertEqual({"b"}, conf.known_first_party)
            conf = Config.find(Path("/"))
            self.assertEqual(set(), conf.known_first_party)
