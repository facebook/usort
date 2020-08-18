# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import sys
import time
from pathlib import Path
from typing import List

import click
from moreorless.click import echo_color_unified_diff

from . import __version__
from .config import Config
from .sorting import sortable_blocks, usort_string
from .util import try_parse, walk


@click.group()
@click.version_option(__version__)
def main() -> None:
    pass


@main.command()
@click.option("--multiples", is_flag=True, help="Only show files with multiple blocks")
@click.option("--debug", is_flag=True, help="Show internal information")
@click.argument("filenames", nargs=-1)
def list_imports(multiples: bool, debug: bool, filenames: List[str]) -> None:
    # This is used to debug the sort keys on the various lines, and understand
    # where the barriers are that produce different blocks.

    for f in filenames:
        config = Config.find(Path(f))
        mod = try_parse(Path(f))
        try:
            blocks = sortable_blocks(mod, config)
        except Exception as e:
            print("Exception", f, e)
            continue

        if multiples and len(blocks) < 2:
            continue

        click.secho(f"{f} {len(blocks)} blocks:", fg="yellow")
        for b in blocks:
            print(f"  body[{b.start_idx}:{b.end_idx}]")
            sorted_stmts = sorted(b.stmts)
            if debug:
                for s in b.stmts:
                    print(
                        f"    {sorted_stmts.index(s)} {s} ({s.config.category(s.first_module)})"
                    )
            else:
                print("Formatted:")
                print("[[[")
                for s in sorted_stmts:
                    print(mod.code_for_node(s.node), end="")
                print("]]]")


@main.command()
@click.option("--diff", is_flag=True)
@click.option("--check", is_flag=True)
@click.option("--show-time", is_flag=True)
@click.argument("filenames", nargs=-1)
def format(diff: bool, check: bool, show_time: bool, filenames: List[str]) -> None:
    """
    This is intended to sort nodes separated by barriers, and that's it.
    We don't format them (aside from moving comments).  Black does the rest.
    When in doubt leave lines alone.
    """
    if not filenames:
        raise click.ClickException("Provide some filenames")

    rc = 0
    for f in filenames:
        pf = Path(f)
        t0 = time.time()
        if pf.is_dir():
            files = list(walk(pf, "*.py"))
        else:
            files = [pf]
        if show_time:
            print(f"walk {f} {time.time() - t0}")

        for pf in files:
            t0 = time.time()
            config = Config.find(pf.parent)
            try:
                data = pf.read_text()
                result = usort_string(data, config)
            except Exception as e:
                print(repr(e))
                rc |= 1
                continue

            if show_time:
                print(f"sort {pf} {time.time() - t0}")

            if diff:
                echo_color_unified_diff(data, result, pf.as_posix())
            elif check:
                if data != result:
                    rc |= 2
                    print(f"Would sort {pf}")
            elif result != data:
                print(f"Sorted {pf}")
                pf.write_text(result)

    sys.exit(rc)


if __name__ == "__main__":
    main()
