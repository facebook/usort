# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import sys
import traceback
from functools import partial
from pathlib import Path
from typing import Iterable, Optional, Tuple

from trailrunner import run, walk

from .config import Config
from .sorting import sort_module
from .types import Result
from .util import get_timings, timed, try_parse


__all__ = ["usort_bytes", "usort_string", "usort_path", "usort_stdin"]


def usort_bytes(
    data: bytes, config: Config, path: Optional[Path] = None
) -> Tuple[bytes, str]:
    """
    Returns (new_bytes, encoding_str) after sorting.
    """
    if path is None:
        path = Path("<data>")

    module = try_parse(data=data, path=path)
    with timed(f"sorting {path}"):
        new_mod = sort_module(module, config)
        return (new_mod.bytes, new_mod.encoding)


def usort_string(data: str, config: Config, path: Optional[Path] = None) -> str:
    r"""
    Whenever possible use usort_bytes instead.

    One does not just .read_text() Python source code.  That will use the system
    encoding, which if is not utf-8 would be in violation of pep 3120.

    There are two additional cases where this function does the wrong thing, but you
    won't notice on most modern file contents:

    - a string unrepresentable in utf-8, e.g. "\ud800" is a single high surrogate
    - a string with a valid pep 263 coding line, other than utf-8
    """
    return usort_bytes(data=data.encode(), config=config, path=path)[0].decode()


def usort_file(path: Path, *, write: bool = False) -> Result:
    """
    Format a single file and return a Result object.
    """

    data: bytes = b""
    try:
        config = Config.find(path.parent)
        data = path.read_bytes()
        output, encoding = usort_bytes(data, config, path)
        if write:
            path.write_bytes(output)
        return Result(
            path=path,
            content=data,
            output=output,
            encoding=encoding,
            timings=get_timings(),
        )

    except Exception as e:
        trace = "".join(traceback.format_exception(*sys.exc_info()))
        return Result(
            path=path, content=data, error=e, trace=trace, timings=get_timings()
        )


def usort_path(path: Path, *, write: bool = False) -> Iterable[Result]:
    """
    For a given path, format it, or any .py files in it, and yield Result objects
    """
    with timed(f"total for {path}"):
        with timed(f"walking {path}"):
            paths = walk(path)

        fn = partial(usort_file, write=write)
        return (v for v in run(paths, fn).values())


def usort_stdin() -> bool:
    """
    Read file contents from stdin, format it, and write the resulting file to stdout

    In case of error during sorting, no output will be written to stdout, and the
    exception will be written to stderr instead.

    Returns True if formatting succeeded, otherwise False
    """
    if sys.stdin.isatty():
        print("Warning: stdin is a tty", file=sys.stderr)

    try:
        config = Config.find()
        data = sys.stdin.read()
        result = usort_string(data, config, Path("<stdin>"))
        sys.stdout.write(result)
        return True

    except Exception as e:
        sys.stderr.write(repr(e))
        return False
