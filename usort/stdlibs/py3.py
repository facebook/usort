# Copyright (c) 2013 Timothy Edmund Crosley
#
# (Originally from isort)
#
# This source code is licensed under the MIT license found in the LICENSE file
# in the root directory of this source tree.

from . import py35, py36, py37, py38

stdlib = py35.stdlib | py36.stdlib | py37.stdlib | py38.stdlib
