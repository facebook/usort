# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import sys
from functools import partial
from pathlib import Path
from typing import Iterable, Optional, Tuple
from warnings import warn

from trailrunner import run, walk

from .config import Config
from .sorting import ImportSorter
from .types import Result
from .util import get_timings, timed, try_parse


__all__ = ["usort_bytes", "usort_string", "usort_path", "usort_stdin"]


def usort(data: bytes, config: Config, path: Optional[Path] = None) -> Result:
    """
    Given bytes for a module, this parses and sorts imports, and returns a Result.
    """
    if path is None:
        path = Path("<data>")

    try:
        module = try_parse(data=data, path=path)
        sorter = ImportSorter(module=module, path=path, config=config)
        new_mod = sorter.sort_module()

        return Result(
            path=path,
            content=data,
            output=new_mod.bytes,
            encoding=new_mod.encoding,
            timings=get_timings(),
            warnings=sorter.warnings,
        )

    except Exception as e:
        return Result(
            path=path,
            content=data,
            error=e,
            timings=get_timings(),
        )


def usort_bytes(
    data: bytes, config: Config, path: Optional[Path] = None
) -> Tuple[bytes, str]:
    """
    Returns (new_bytes, encoding_str) after sorting.

    DEPRECATED: use `usort()` directly instead.
    """
    warn("use usort() instead", DeprecationWarning)

    result = usort(data=data, config=config, path=path)
    if result.error:
        raise result.error

    assert result.encoding is not None
    return result.output, result.encoding


def usort_string(data: str, config: Config, path: Optional[Path] = None) -> str:
    r"""
    Whenever possible use usort_bytes instead.

    One does not just .read_text() Python source code.  That will use the system
    encoding, which if is not utf-8 would be in violation of pep 3120.

    There are two additional cases where this function does the wrong thing, but you
    won't notice on most modern file contents:

    - a string unrepresentable in utf-8, e.g. "\ud800" is a single high surrogate
    - a string with a valid pep 263 coding line, other than utf-8

    DEPRECATED: use `usort()` directly, and and encode/decode bytes as necessary.
    """
    warn("use usort() instead", DeprecationWarning, stacklevel=2)

    result = usort(data=data.encode(), config=config, path=path)
    if result.error:
        raise result.error

    return result.output.decode()


def usort_file(path: Path, *, write: bool = False) -> Result:
    """
    Format a single file and return a Result object.

    Ignores any configured :py:attr:`excludes` patterns.
    """

    try:
        config = Config.find(path.parent)
        data = path.read_bytes()
        result = usort(data, config, path)

        if result.output and write:
            path.write_bytes(result.output)

        return result

    except Exception as e:
        return Result(
            path=path,
            error=e,
            timings=get_timings(),
        )


def usort_path(path: Path, *, write: bool = False) -> Iterable[Result]:
    """
    For a given path, format it, or any python files in it, and yield :class:`Result` s.

    If given a directory, it will be searched, recursively, for any Python source files,
    excluding any files or directories that match the project root's ``.gitignore`` or
    any configured :py:attr:`excludes` patterns in the associated ``pyproject.toml``.
    """
    with timed(f"total for {path}"):
        with timed(f"walking {path}"):
            config = Config.find(path)
            paths = list(walk(path, excludes=config.excludes))

        fn = partial(usort_file, write=write)
        results = [v for v in run(paths, fn).values()]
        return results


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
