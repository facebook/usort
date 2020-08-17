# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import os
from fnmatch import fnmatch
from pathlib import Path
from typing import Generator, Optional

import libcst as cst


def walk(path: Path, glob: str) -> Generator[Path, None, None]:
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        root_path = Path(root)
        for f in files:
            if fnmatch(f, glob):
                yield root_path / f


def try_parse(path: Path, data: Optional[bytes] = None,) -> cst.Module:
    """
    Attempts to parse the file with all syntax versions known by LibCST.

    If none parse, raises an exception that tells you that (what we know, not an
    error that might not be the most helpful).
    """
    if data is None:
        data = path.read_bytes()

    for version in cst.KNOWN_PYTHON_VERSION_STRINGS[::-1]:
        try:
            mod = cst.parse_module(
                data, cst.PartialParserConfig(python_version=version)
            )
            return mod
        except cst.ParserSyntaxError:
            continue

    # Intentionally not raising an exception with a specific syntax error (if we
    # keep the last, meaning oldest python version, then it might complain about
    # typehints like https://github.com/psf/black/issues/1158)
    raise Exception(f"No version could parse {path}")
