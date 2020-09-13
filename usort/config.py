# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, NewType, Optional, Sequence

import toml

from .stdlibs import STDLIB_TOP_LEVEL_NAMES

Category = NewType("Category", str)

CAT_FUTURE = Category("future")
CAT_STANDARD_LIBRARY = Category("standard_library")
CAT_FIRST_PARTY = Category("first_party")
CAT_THIRD_PARTY = Category("third_party")


def known_factory() -> Dict[str, Category]:
    known = {}
    for name in STDLIB_TOP_LEVEL_NAMES:
        known[name] = CAT_STANDARD_LIBRARY

    # This is also in the stdlib list, so this override comes last...
    known["__future__"] = CAT_FUTURE

    return known


@dataclass
class Config:
    known: Dict[str, Category] = field(default_factory=known_factory)

    # These names are vaguely for compatibility with isort; however while it has
    # separate sections for "current project" and "explicitly local", these are
    # handled differently as "first_party".
    categories: Sequence[Category] = (
        CAT_FUTURE,
        CAT_STANDARD_LIBRARY,
        CAT_THIRD_PARTY,
        CAT_FIRST_PARTY,
    )
    default_section: Category = CAT_THIRD_PARTY

    @classmethod
    def find(cls, filename: Optional[Path] = None) -> "Config":
        rv = cls()

        # TODO This logic should be split out to a separate project, as it's
        # reusable and deserves a number of tests to get right.  Can probably
        # also stop once finding a .hg, .git, etc
        if filename is None:
            p = Path.cwd()
        else:
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
        if filename is None:
            p = Path.cwd()
        else:
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
            rv.known[p.name] = CAT_FIRST_PARTY

        return rv

    def update_from_config(self, toml_path: Path) -> None:
        conf = toml.loads(toml_path.read_text())
        tbl = conf.get("tool", {}).get("usort", {})

        if "categories" in tbl:
            self.categories = [Category(x) for x in tbl["categories"]]
        if "default_section" in tbl:
            self.default_section = Category(tbl["default_section"])

        for cat, names in tbl.get("known", {}).items():
            typed_cat = Category(cat)
            if cat not in self.categories:
                raise ValueError(f"Known set for {cat} without it having an order")

            for name in names:
                self.known[name] = typed_cat

        # "legacy" options
        for cat, option in [
            (CAT_FIRST_PARTY, "known_first_party"),
            (CAT_THIRD_PARTY, "known_third_party"),
            (CAT_STANDARD_LIBRARY, "known_standard_library"),
        ]:
            if option in tbl:
                for name in tbl[option]:
                    # TODO validate (no dots or whitespace, etc)
                    self.known[name] = cat

    def update_from_flags(
        self,
        known_first_party: str,
        known_third_party: str,
        known_standard_library: str,
        categories: str,
        default_section: str,
    ) -> None:
        if categories:
            self.categories = [Category(x) for x in categories.split(",")]
        if default_section:
            self.default_section = Category(default_section)

        for cat, option in [
            (CAT_FIRST_PARTY, known_first_party),
            (CAT_THIRD_PARTY, known_third_party),
            (CAT_STANDARD_LIBRARY, known_standard_library),
        ]:
            for name in option.split(","):
                # TODO validate (no dots or whitespace, etc)
                self.known[name] = cat

    def category(self, dotted_import: str) -> Category:
        """
        Given a piece of an import string, return its category for this config.

        You can pass in ".foo" or "pkg.foo.bar" or just "os" and it should
        categorize.
        """
        first_part = dotted_import.split(".")[0]
        if first_part == "":
            # relative import
            return CAT_FIRST_PARTY
        elif first_part in self.known:
            return self.known[first_part]
        else:
            return self.default_section
