# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# noqa: F401

try:
    from .version import version as __version__
except ImportError:
    __version__ = "dev"

from .api import usort, usort_bytes, usort_file, usort_path, usort_stdin, usort_string
from .config import Config
from .types import Result, SortWarning

__all__ = [
    "__version__",
    "Config",
    "Result",
    "SortWarning",
    "usort",
    "usort_bytes",
    "usort_file",
    "usort_path",
    "usort_stdin",
    "usort_string",
]

# DEPRECATED: preserve old api, will be removed by 1.0
from . import sorting  # usort:skip

sorting.usort_bytes = usort_bytes  # type: ignore
sorting.usort_path = usort_path  # type: ignore
sorting.usort_stdin = usort_stdin  # type: ignore
sorting.usort_string = usort_string  # type: ignore
