# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import tempfile
import unittest
from pathlib import Path

from usort.config import CAT_FIRST_PARTY, CAT_FUTURE, CAT_THIRD_PARTY, Config


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
            self.assertNotIn("psutil", conf.known)
            self.assertEqual(CAT_FUTURE, conf.category("psutil.cpu_times"))

            # "legacy" naming
            (Path(d) / "pyproject.toml").write_text(
                """\
[tool.usort]
default_section = "future"
known_third_party = ["psutil", "cocoa"]
"""
            )

            conf = Config.find(Path(d))
            self.assertEqual(CAT_THIRD_PARTY, conf.known["cocoa"])
            self.assertEqual(CAT_THIRD_PARTY, conf.known["psutil"])
            self.assertEqual(CAT_THIRD_PARTY, conf.category("psutil.cpu_times"))

            # Works even on invalid children
            conf = Config.find(Path(d) / "foo")
            self.assertEqual(CAT_THIRD_PARTY, conf.known["cocoa"])
            self.assertEqual(CAT_THIRD_PARTY, conf.known["psutil"])
            self.assertEqual(CAT_THIRD_PARTY, conf.category("psutil.cpu_times"))

            # New naming
            (Path(d) / "pyproject.toml").write_text(
                """\
[tool.usort]
default_section = "future"
[tool.usort.known]
third_party = ["psutil", "cocoa"]
"""
            )

            new_conf = Config.find(Path(d))
            self.assertEqual(conf, new_conf)

    def test_first_party_root_finding(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a" / "b" / "c").mkdir(parents=True)
            (Path(d) / "a" / "b" / "__init__.py").write_text("")
            (Path(d) / "a" / "b" / "c" / "__init__.py").write_text("from b import zzz")

            f = Path(d) / "a" / "b" / "c" / "__init__"

            conf = Config.find(f)
            self.assertEqual(CAT_FIRST_PARTY, conf.known["b"])
            conf = Config.find(f.parent)  # c
            self.assertEqual(CAT_FIRST_PARTY, conf.known["b"])
            conf = Config.find(f.parent.parent)  # b
            self.assertEqual(CAT_FIRST_PARTY, conf.known["b"])
            conf = Config.find(Path("/"))
            self.assertNotIn("b", conf.known)

    def test_new_category_names(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "pyproject.toml").write_text(
                """\
[tool.usort]
categories = ["future", "standard_library", "numpy", "third_party", "first_party"]
[tool.usort.known]
numpy = ["numpy", "pandas"]
"""
            )
            conf = Config.find(Path(d) / "sample.py")
            self.assertEqual("numpy", conf.known["pandas"])

    def test_new_category_names_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "pyproject.toml").write_text(
                """\
[tool.usort.known]
foo = ["numpy", "pandas"]
"""
            )
            with self.assertRaisesRegex(ValueError, "Known set for foo"):
                Config.find(Path(d) / "sample.py")

    def test_from_flags(self) -> None:
        conf = Config()
        conf.update_from_flags(
            known_first_party="a,b",
            known_third_party="",
            known_standard_library="",
            categories="",
            default_section="",
        )
        self.assertEqual(CAT_FIRST_PARTY, conf.known["a"])
        self.assertEqual(CAT_FIRST_PARTY, conf.known["b"])
