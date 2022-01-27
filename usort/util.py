# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import re
from contextlib import contextmanager
from pathlib import Path
from time import monotonic
from typing import Callable, Generator, List, Optional, Sequence, Tuple

import libcst as cst

Timing = Tuple[str, float]

INLINE_COMMENT_RE = re.compile(r"#+[^#]*")
TIMINGS: List[Timing] = []


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


def get_timings() -> Sequence[Tuple[str, float]]:
    try:
        return list(TIMINGS)
    finally:
        TIMINGS.clear()


def print_timings(
    fn: Callable[[str], None] = print, *, timings: Sequence[Timing]
) -> None:
    """
    Print all stored timing values in microseconds.
    """
    for msg, duration in timings:
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


def parse_import(code: str) -> cst.SimpleStatementLine:
    """
    Parse a single import statement. For testing and debugging purposes only.
    """
    node = cst.parse_statement(code)
    if not isinstance(node, cst.SimpleStatementLine):
        raise ValueError("not a statement")
    if not isinstance(node.body[0], (cst.Import, cst.ImportFrom)):
        raise ValueError("not an import statement")
    return node


def split_inline_comment(text: str) -> Sequence[str]:
    return [part.rstrip() for part in INLINE_COMMENT_RE.findall(text)]


def split_relative(name: str) -> Tuple[str, int]:
    ndots = len(name) - len(name.lstrip("."))
    return name[ndots:], ndots


def stem_join(stem: Optional[str], name: str) -> str:
    if stem is None:
        return name
    elif stem.endswith("."):
        return stem + name
    else:
        return f"{stem}.{name}"


def top_level_name(name: str) -> str:
    return name.split(".", 1)[0]


def with_dots(x: cst.CSTNode) -> str:
    """
    Helper to make it easier to use an Attribute or Name.
    """
    if isinstance(x, cst.Attribute):
        return ".".join([with_dots(x.value), with_dots(x.attr)])
    elif isinstance(x, cst.Name):
        return x.value
    else:
        raise TypeError(f"Can't with_dots on {type(x)}")
