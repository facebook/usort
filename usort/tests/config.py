# Copyright (c) Meta Platforms, Inc. and affiliates.
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

    def test_config_magic_commas(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            d_path = Path(d)
            (d_path / "foo").mkdir(parents=True)
            (d_path / "foo" / "bar.py").write_text("import os")

            with self.subTest("default"):
                (d_path / "foo" / "pyproject.toml").write_text("")
                conf = Config.find(d_path / "foo" / "bar.py")
                self.assertFalse(conf.magic_commas)

            with self.subTest("enabled"):
                (d_path / "foo" / "pyproject.toml").write_text(
                    """\
[tool.usort]
magic_commas = true
"""
                )
                conf = Config.find(d_path / "foo" / "bar.py")
                self.assertTrue(conf.magic_commas)

    def test_config_merge_imports(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            d_path = Path(d)
            (d_path / "foo").mkdir(parents=True)
            (d_path / "foo" / "bar.py").write_text("import os")

            with self.subTest("default"):
                (d_path / "foo" / "pyproject.toml").write_text("")
                conf = Config.find(d_path / "foo" / "bar.py")
                self.assertTrue(conf.merge_imports)

            with self.subTest("disabled"):
                (d_path / "foo" / "pyproject.toml").write_text(
                    """\
[tool.usort]
merge_imports = false
"""
                )
                conf = Config.find(d_path / "foo" / "bar.py")
                self.assertFalse(conf.merge_imports)

    def test_config_excludes(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            d_path = Path(d)
            (d_path / "foo").mkdir(parents=True)
            (d_path / "foo" / "bar.py").write_text("import os")

            with self.subTest("default config"):
                (d_path / "foo" / "pyproject.toml").write_text("")
                conf = Config.find(d_path / "foo" / "bar.py")
                self.assertEqual([], conf.excludes)

            with self.subTest("with black config"):
                (d_path / "foo" / "pyproject.toml").write_text(
                    """\
[tool.usort]
excludes = [
    "fixtures/",
    "*generated.py",
]
"""
                )
                conf = Config.find(d_path / "foo" / "bar.py")
                expected = ["fixtures/", "*generated.py"]
                self.assertEqual(expected, conf.excludes)

    def test_black_line_length(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            d_path = Path(d)
            (d_path / "foo").mkdir(parents=True)
            (d_path / "foo" / "bar.py").write_text("import os")

            with self.subTest("default config"):
                (d_path / "foo" / "pyproject.toml").write_text("")
                conf = Config.find(d_path / "foo" / "bar.py")
                self.assertEqual(Config.line_length, conf.line_length)

            with self.subTest("with black config"):
                (d_path / "foo" / "pyproject.toml").write_text(
                    """\
[tool.black]
line-length = 120
"""
                )
                conf = Config.find(d_path / "foo" / "bar.py")
                self.assertEqual(120, conf.line_length)

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
            conf = Config.find(
                d_path / "b" / "c" / "d" / "__init__.py"
            ).with_first_party(Path.cwd() / d_path / "b" / "c" / "d" / "__init__.py")
            self.assertEqual(CAT_FIRST_PARTY, conf.known["x"])
            self.assertEqual(CAT_FIRST_PARTY, conf.known["d"])

            # This is also something that's worked for ages, a relative path with cwd
            # above the pyproject.toml
            with chdir(d):
                conf = Config.find(
                    Path("b") / "c" / "d" / "__init__.py"
                ).with_first_party(Path.cwd() / Path("b") / "c" / "d" / "__init__.py")
                self.assertEqual(CAT_FIRST_PARTY, conf.known["x"])
                self.assertEqual(CAT_FIRST_PARTY, conf.known["d"])

            # This is an instance of issue 43
            with chdir((d_path / "b" / "c").as_posix()):
                conf = Config.find(Path("d") / "__init__.py").with_first_party(
                    Path.cwd() / Path("d") / "__init__.py"
                )
                self.assertEqual(CAT_FIRST_PARTY, conf.known["x"])
                self.assertEqual(CAT_FIRST_PARTY, conf.known["d"])

    def test_load_explicit_config(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            d_path = Path(d)
            config_file = d_path / "custom.toml"

            with self.subTest("with tool.usort"):
                config_file.write_text(
                    """
[tool.usort]
merge_imports = false
known_third_party = ["pandas"]
"""
                )
                conf = Config.load(config_file)
                self.assertFalse(conf.merge_imports)
                self.assertEqual(CAT_THIRD_PARTY, conf.known["pandas"])

            with self.subTest("with tool.black only"):
                config_file.write_text(
                    """
[tool.black]
line-length = 100
"""
                )
                # Config should still work with black settings
                conf = Config.load(config_file)
                self.assertEqual(100, conf.line_length)

            with self.subTest("with both tool.usort and tool.black"):
                config_file.write_text(
                    """
[tool.usort]
merge_imports = false

[tool.black]
line-length = 120
"""
                )
                conf = Config.load(config_file)
                self.assertFalse(conf.merge_imports)
                self.assertEqual(120, conf.line_length)

            with self.subTest("missing file"):
                missing = d_path / "nonexistent.toml"
                with self.assertRaises(FileNotFoundError):
                    Config.load(missing)

            with self.subTest("empty config file"):
                config_file.write_text("# empty\n")
                import warnings

                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    conf = Config.load(config_file)
                    self.assertEqual(1, len(w))
                    self.assertIn("missing", str(w[0].message).lower())
                # Should still create a valid config with defaults
                self.assertTrue(conf.merge_imports)  # default value
