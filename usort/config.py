# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, NewType, Optional, Pattern, Sequence, Set

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
    default_category: Category = CAT_THIRD_PARTY

    # Known set of modules with import side effects. These will be implicitly treated
    # as block separators, similar to non-import statements.
    side_effect_modules: List[str] = field(default_factory=list)
    side_effect_re: Pattern[str] = field(default=re.compile(""))

    def __post_init__(self) -> None:
        self.side_effect_re = re.compile(
            "|".join(re.escape(m) + r"\b" for m in self.side_effect_modules)
        )

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
        if "default_category" in tbl:
            self.default_category = Category(tbl["default_category"])
        if "side_effect_modules" in tbl:
            self.side_effect_modules.extend(tbl["side_effect_modules"])

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
                    assert "." not in name
                    self.known[name] = cat

        # make sure generated regexes get updated
        self.__post_init__()

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
            return self.default_category

    def is_side_effect_import(self, base: str, names: List[str]) -> bool:
        """
        Determine if any of the given imports are in the list with known side effects.

        Takes a "base" (possibly empty) and a list of imported names, and checks if
        any of the base+name combinations (or a prefix of that combination) is in the
        list of know modules with side effects.
        """
        if self.side_effect_modules:
            candidates: Set[str] = set()
            for name in names:
                candidates.add(f"{base}.{name}" if base else name)
            return any(self.side_effect_re.match(candidate) for candidate in candidates)
        return False
