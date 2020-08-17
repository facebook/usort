# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence, Set

import toml

from .stdlibs import STDLIB_TOP_LEVEL_NAMES


# TODO these numbers are meaningless, use strings or auto?
class Category(enum.Enum):
    FUTURE = "future"
    STANDARD_LIBRARY = "standard_library"
    FIRST_PARTY = "first_party"
    THIRD_PARTY = "third_party"


@dataclass
class Config:
    known_future: Set[str] = field(default_factory=lambda: {"__future__"})
    known_first_party: Set[str] = field(default_factory=set)
    known_third_party: Set[str] = field(default_factory=set)
    known_standard_library: Set[str] = field(
        default_factory=STDLIB_TOP_LEVEL_NAMES.copy
    )

    # These names are vaguely for compatibility with isort; however while it has
    # separate sections for "current project" and "explicitly local", these are
    # handled differently as "first_party".
    categories: Sequence[Category] = (
        Category.FUTURE,
        Category.STANDARD_LIBRARY,
        Category.THIRD_PARTY,
        Category.FIRST_PARTY,
    )
    default_section: Category = Category.THIRD_PARTY

    @classmethod
    def find(cls, filename: Path) -> "Config":
        rv = cls()

        # TODO This logic should be split out to a separate project, as it's
        # reusable and deserves a number of tests to get right.  Can probably
        # also stop once finding a .hg, .git, etc
        p = filename
        while True:
            if p.is_dir():
                candidate = p / "pyproject.toml"
                if candidate.exists():
                    rv.update_from_config(candidate)
                    break

            # Stop on root (hopefully works on Windows)
            if p.parent == p:
                break
            # Stop on different volume
            if p.exists() and p.stat().st_dev != p.parent.stat().st_dev:
                break

            p = p.parent

        # Infer first-party top-level names; this only works for the common case of
        # a single package, but not multiple, or modules (pure-python or extensions).
        # In those cases, you should explicitly set `known_first_party` in the config.
        #
        # This code as-is should work for something like running against a site-packages
        # dir, but if we broaden to support multiple top-level names, it would find too
        # much.
        p = filename
        while True:
            # Stop on root (hopefully works on Windows)
            if p.parent == p:
                break
            # Stop on different volume
            if p.exists() and p.stat().st_dev != p.parent.stat().st_dev:
                break

            if (p.parent / "__init__.py").exists():
                p = p.parent
            else:
                break

        if (p / "__init__.py").exists():
            rv.known_first_party.add(p.name)

        return rv

    def update_from_config(self, toml_path: Path) -> None:
        conf = toml.loads(toml_path.read_text())
        tbl = conf.get("tool", {}).get("usort", {})
        if "known_first_party" in tbl:
            self.known_first_party.update(tbl["known_first_party"])
        if "known_third_party" in tbl:
            self.known_third_party.update(tbl["known_third_party"])
        if "known_standard_library" in tbl:
            self.known_standard_library.update(tbl["known_standard_library"])
        if "categories" in tbl:
            self.categories = [Category(x) for x in tbl["categories"]]
        if "default_section" in tbl:
            self.default_section = Category(tbl["default_section"])

    def update_from_flags(
        self,
        known_first_party: str,
        known_third_party: str,
        known_standard_library: str,
        categories: str,
        default_section: str,
    ) -> None:
        if known_first_party:
            self.known_first_party.update(known_first_party.split(","))
        if known_third_party:
            self.known_third_party.update(known_third_party.split(","))
        if known_standard_library:
            self.known_standard_library.update(known_standard_library.split(","))
        if categories:
            self.categories = [Category(x) for x in categories.split(",")]
        if default_section:
            self.default_section = Category(default_section)

    def category(self, dotted_import: str) -> Category:
        """
        Given a piece of an import string, return its category for this config.

        You can pass in ".foo" or "pkg.foo.bar" or just "os" and it should
        categorize.
        """
        first_part = dotted_import.split(".")[0]
        if first_part == "":
            # relative import
            return Category.FIRST_PARTY
        elif first_part in self.known_future:
            return Category.FUTURE
        elif first_part in self.known_first_party:
            return Category.FIRST_PARTY
        elif first_part in self.known_standard_library:
            return Category.STANDARD_LIBRARY
        elif first_part in self.known_third_party:
            return Category.THIRD_PARTY
        else:
            return self.default_section
