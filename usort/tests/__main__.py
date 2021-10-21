# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import logging
import unittest

from usort.tests import *  # noqa: F401,F403

if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR, stream=None)
    unittest.main()
