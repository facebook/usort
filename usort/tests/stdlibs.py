# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import unittest

from usort.stdlibs import STDLIB_TOP_LEVEL_NAMES


class StdlibsTest(unittest.TestCase):
    def test_expected(self) -> None:
        # Py2 module
        self.assertIn("StringIO", STDLIB_TOP_LEVEL_NAMES)

        # This is specialcased, it appears to be a packaging decision for distros but I
        # don't want to include it.
        self.assertNotIn("test", STDLIB_TOP_LEVEL_NAMES)
        self.assertNotIn("lib", STDLIB_TOP_LEVEL_NAMES)
        self.assertNotIn("foo", STDLIB_TOP_LEVEL_NAMES)

        self.assertIn("io", STDLIB_TOP_LEVEL_NAMES)
        self.assertIn("os", STDLIB_TOP_LEVEL_NAMES)

        # Py2 module
        self.assertIn("sre", STDLIB_TOP_LEVEL_NAMES)
        for name in ("re", "sre_parse", "_sre"):
            self.assertIn(name, STDLIB_TOP_LEVEL_NAMES)
