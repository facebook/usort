# Copyright (c) 2013 Timothy Edmund Crosley
#
# (Originally from isort)
#
# This source code is licensed under the MIT license found in the LICENSE file
# in the root directory of this source tree.

from . import py2, py3

stdlib = py2.stdlib | py3.stdlib
