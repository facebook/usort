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
