# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from contextlib import contextmanager
from multiprocessing import Queue
from pathlib import Path
from time import monotonic
from typing import Callable, Generator, List, Optional, Tuple

import libcst as cst

TIMINGS_QUEUE: Optional[Queue] = None


@contextmanager
def timed(msg: str) -> Generator[None, None, None]:
    """
    Records the monotonic duration of the contained context, with a given description.

    Timings are stored for later use/printing with `print_timings()`.
    """
    before = monotonic()
    yield
    after = monotonic()
    if TIMINGS_QUEUE is not None:
        TIMINGS_QUEUE.put((msg, after - before))


def clear_timings() -> None:
    """
    Starts a new timings run by initializing a new Queue.
    """
    global TIMINGS_QUEUE
    TIMINGS_QUEUE = Queue()


def print_timings(fn: Callable[[str], None] = print) -> None:
    """
    Print all stored timing values in microseconds.
    """
    assert TIMINGS_QUEUE is not None
    while not TIMINGS_QUEUE.empty():
        msg, duration = TIMINGS_QUEUE.get()
        fn(f"{msg + ':':50} {int(duration*1000000):7} µs")


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
