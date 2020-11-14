# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import os
from contextlib import contextmanager
from fnmatch import fnmatch
from pathlib import Path
from time import monotonic
from typing import Callable, Generator, Iterable, List, Optional, Tuple

import libcst as cst

TIMINGS: List[Tuple[str, float]] = []


@contextmanager
def timed(msg: str) -> Generator[None, None, None]:
    """
    Records the monotonic duration of the contained context, with a given description.

    Timings are stored for later use/printing with `print_timings()`.
    """
    before = monotonic()
    yield
    after = monotonic()
    TIMINGS.append((msg, after - before))


def print_timings(fn: Callable[[str], None] = print) -> None:
    """
    Print all stored timing values in microseconds.
    """
    for msg, duration in TIMINGS:
        fn(f"{msg + ':':50} {int(duration*1000000):7} µs")


def walk(path: Path, glob: str) -> Iterable[Path]:
    with timed(f"walking {path}"):
        paths: List[Path] = []
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            root_path = Path(root)
            for f in files:
                if fnmatch(f, glob):
                    paths.append(root_path / f)
        return paths


def try_parse(path: Path, data: Optional[bytes] = None) -> cst.Module:
    """
    Attempts to parse the file with all syntax versions known by LibCST.

    If parsing fails on all supported grammar versions, then raises the parser error
    from the first/newest version attempted.
    """
    if data is None:
        data = path.read_bytes()

    with timed(f"parsing {path}"):
        parse_error: Optional[cst.ParserSyntaxError] = None

        for version in cst.KNOWN_PYTHON_VERSION_STRINGS[::-1]:
            try:
                mod = cst.parse_module(
                    data, cst.PartialParserConfig(python_version=version)
                )
                return mod
            except cst.ParserSyntaxError as e:
                # keep the first error we see in case parsing fails on all versions
                if parse_error is None:
                    parse_error = e

        # not caring about existing traceback here because it's not useful for parse
        # errors, and usort_path is already going to wrap it in a custom class
        raise parse_error or Exception("unknown parse failure")
