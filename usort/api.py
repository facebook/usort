# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import sys
from pathlib import Path
from typing import Iterable, Optional, Tuple

from .config import Config
from .sorting import ImportSortingTransformer
from .types import Result
from .util import try_parse, timed, walk


def usort_bytes(
    data: bytes, config: Config, path: Optional[Path] = None
) -> Tuple[bytes, str]:
    """
    Returns (new_bytes, encoding_str) after sorting.
    """
    if path is None:
        path = Path("<data>")

    mod = try_parse(data=data, path=path)
    with timed(f"sorting {path}"):
        tr = ImportSortingTransformer(config)
        new_mod = mod.visit(tr)
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


def usort_path(path: Path, *, write: bool = False) -> Iterable[Result]:
    """
    For a given path, format it, or any .py files in it, and yield Result objects
    """
    files: Iterable[Path]
    if path.is_dir():
        files = walk(path, "*.py")
    else:
        files = [path]

    data: bytes = b""
    for f in files:
        try:
            config = Config.find(f.parent)
            data = f.read_bytes()
            output, encoding = usort_bytes(data, config, f)
            if write:
                f.write_bytes(output)
            yield Result(f, data, output, encoding)

        except Exception as e:
            yield Result(f, data, b"", None, e)


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
