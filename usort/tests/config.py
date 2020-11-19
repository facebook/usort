# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import tempfile
import unittest
from pathlib import Path

from usort.config import CAT_FIRST_PARTY, CAT_FUTURE, CAT_THIRD_PARTY, Config
from .cli import chdir


class ConfigTest(unittest.TestCase):
    def test_third_party(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            # Defaults should not know about this module.
            # This is a silly value for default_category but this makes it more
            # obvious when it's in use.
            (Path(d) / "pyproject.toml").write_text(
                """\
[tool.usort]
default_category = "future"
"""
            )
            conf = Config.find(Path(d))
            self.assertNotIn("psutil", conf.known)
            self.assertEqual(CAT_FUTURE, conf.category("psutil.cpu_times"))

            # "legacy" naming
            (Path(d) / "pyproject.toml").write_text(
                """\
[tool.usort]
default_category = "future"
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
default_category = "future"
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

            f = Path(d) / "a" / "b" / "c" / "__init__.py"

            conf = Config.find(f)
            self.assertEqual(CAT_FIRST_PARTY, conf.known["b"])
            conf = Config.find(f.parent)  # c
            self.assertEqual(CAT_FIRST_PARTY, conf.known["b"])
            conf = Config.find(f.parent.parent)  # b
            self.assertEqual(CAT_FIRST_PARTY, conf.known["b"])
            conf = Config.find(Path("/"))
            self.assertNotIn("b", conf.known)

    def test_first_party_root_finding_disable(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a" / "b" / "c").mkdir(parents=True)
            (Path(d) / "a" / "b" / "__init__.py").write_text("")
            (Path(d) / "a" / "b" / "c" / "__init__.py").write_text("from b import zzz")

            f = Path(d) / "a" / "b" / "c" / "__init__.py"

            conf = Config.find(f)
            self.assertEqual(CAT_FIRST_PARTY, conf.known["b"])

            (Path(d) / "pyproject.toml").write_text(
                """\
[tool.usort]
first_party_detection = false
"""
            )

            conf = Config.find(f)
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

    def test_side_effect_init(self) -> None:
        config = Config()
        self.assertEqual([], config.side_effect_modules)
        self.assertEqual("", config.side_effect_re.pattern)
        self.assertRegex("", config.side_effect_re)

        config = Config(side_effect_modules=["fizzbuzz", "foo.bar.baz"])
        self.assertEqual(r"fizzbuzz\b|foo\.bar\.baz\b", config.side_effect_re.pattern)
        self.assertNotRegex("", config.side_effect_re)
        self.assertRegex("fizzbuzz", config.side_effect_re)
        self.assertRegex("fizzbuzz.foo", config.side_effect_re)
        self.assertNotRegex("fizzbuzz1", config.side_effect_re)
        self.assertNotRegex("fizzbuzz1.foo", config.side_effect_re)
        self.assertRegex("foo.bar.baz", config.side_effect_re)
        self.assertRegex("foo.bar.baz.qux", config.side_effect_re)
        self.assertNotRegex("foo.bar", config.side_effect_re)
        self.assertNotRegex("foo.bar.qux", config.side_effect_re)

    def test_is_side_effect(self) -> None:
        with self.subTest("fizzbuzz"):
            config = Config(side_effect_modules=["fizzbuzz"])
            # import fizzbuzz1
            self.assertFalse(config.is_side_effect_import("", ["fizzbuzz1"]))
            # import fizzbuzz
            self.assertTrue(config.is_side_effect_import("", ["fizzbuzz"]))
            # from fizzbuzz import a, b
            self.assertTrue(config.is_side_effect_import("fizzbuzz", ["a", "b"]))
            # from fizzbuzz.apple import a, b
            self.assertTrue(config.is_side_effect_import("fizzbuzz.apple", ["a", "b"]))

        with self.subTest("foo.bar.baz"):
            config = Config(side_effect_modules=["foo.bar.baz"])
            # import foo.bar
            self.assertFalse(config.is_side_effect_import("", ["foo.bar"]))
            # import foo, bar
            self.assertFalse(config.is_side_effect_import("", ["foo", "bar"]))
            # import foo.bar.baz
            self.assertTrue(config.is_side_effect_import("", ["foo.bar.baz"]))
            # import foo.bar.bazzy
            self.assertFalse(config.is_side_effect_import("", ["foo.bar.bazzy"]))
            # from foo import bar
            self.assertFalse(config.is_side_effect_import("foo", ["bar"]))
            # from foo.bar import foo
            self.assertFalse(config.is_side_effect_import("foo.bar", ["foo"]))
            # from foo.bar import baz
            self.assertTrue(config.is_side_effect_import("foo.bar", ["baz"]))
            # from foo.bar import bazzy
            self.assertFalse(config.is_side_effect_import("foo.bar", ["bazzy"]))

    def test_config_parent_walk(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            d_path = Path(d)

            (d_path / "a").mkdir(parents=True)
            (d_path / "a" / "__init__.py").write_text("")

            (d_path / "b").mkdir(parents=True)
            (d_path / "b" / "pyproject.toml").write_text(
                """\
[tool.usort.known]
first_party = ["x"]
"""
            )
            (d_path / "b" / "c").mkdir(parents=True)
            (d_path / "b" / "c" / "d").symlink_to(d_path / "a")

            # This is behavior that's worked for ages, if given an absolute path
            conf = Config.find(d_path / "b" / "c" / "d" / "__init__.py")
            self.assertEqual(CAT_FIRST_PARTY, conf.known["x"])
            self.assertEqual(CAT_FIRST_PARTY, conf.known["d"])

            # This is also something that's worked for ages, a relative path with cwd
            # above the pyproject.toml
            with chdir(d):
                conf = Config.find(Path("b") / "c" / "d" / "__init__.py")
                self.assertEqual(CAT_FIRST_PARTY, conf.known["x"])
                self.assertEqual(CAT_FIRST_PARTY, conf.known["d"])

            # This is an instance of issue 43
            with chdir((d_path / "b" / "c").as_posix()):
                conf = Config.find(Path("d") / "__init__.py")
                self.assertEqual(CAT_FIRST_PARTY, conf.known["x"])
                self.assertEqual(CAT_FIRST_PARTY, conf.known["d"])
