# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from typing import Set

from stdlib_list.base import short_versions, stdlib_list

STDLIB_MODULES: Set[str] = set(sum((stdlib_list(v) for v in short_versions), []))

STDLIB_TOP_LEVEL_NAMES: Set[str] = set(v.split(".")[0] for v in STDLIB_MODULES)
