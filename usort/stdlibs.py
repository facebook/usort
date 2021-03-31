# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from typing import FrozenSet

from stdlibs import py27, py3

STDLIB_TOP_LEVEL_NAMES: FrozenSet[str] = py27.module_names | py3.module_names
