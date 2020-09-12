# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import sys
from pathlib import Path
from typing import List

import click
from moreorless.click import echo_color_unified_diff

from . import __version__
from .config import Config
from .sorting import sortable_blocks, usort_path, usort_stdin
from .util import try_parse


@click.group()
@click.version_option(__version__, "--version", "-V")
@click.option("--benchmark", is_flag=True, help="Output benchmark timing info")
def main(benchmark: bool) -> None:
    pass


@main.command()
@click.option("--multiples", is_flag=True, help="Only show files with multiple blocks")
@click.option("--debug", is_flag=True, help="Show internal information")
@click.argument("filenames", nargs=-1)
def list_imports(multiples: bool, debug: bool, filenames: List[str]) -> None:
    """
    Troubleshoot sorting behavior and show import blocks
    """
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
                        f"    {sorted_stmts.index(s)} {s} "
                        f"({s.config.category(s.first_module)})"
                    )
            else:
                print("Formatted:")
                print("[[[")
                for s in sorted_stmts:
                    print(mod.code_for_node(s.node), end="")
                print("]]]")


@main.command()
@click.argument("filenames", nargs=-1)
def check(filenames: List[str]) -> None:
    """
    Check imports for one or more path
    """
    if not filenames:
        raise click.ClickException("Provide some filenames")

    return_code = 0
    for f in filenames:
        path = Path(f)
        for result in usort_path(path, write=False):
            if result.error:
                click.echo(f"Error on {result.path}: {result.error!r}")
                return_code |= 1

            if result.content != result.output:
                click.echo(f"Would sort {result.path}")
                return_code |= 2

    sys.exit(return_code)


@main.command()
@click.argument("filenames", nargs=-1)
def diff(filenames: List[str]) -> None:
    """
    Output diff of changes for one or more path
    """
    if not filenames:
        raise click.ClickException("Provide some filenames")

    return_code = 0
    for f in filenames:
        path = Path(f)
        for result in usort_path(path, write=False):
            if result.error:
                click.echo(f"Error on {result.path}: {result.error!r}")
                return_code |= 1

            if result.content != result.output:
                echo_color_unified_diff(
                    result.content, result.output, result.path.as_posix()
                )

    sys.exit(return_code)


@main.command()
@click.argument("filenames", nargs=-1)
def format(filenames: List[str]) -> None:
    """
    Format one or more paths

    This is intended to sort nodes separated by barriers, and that's it.
    We don't format them (aside from moving comments).  Black does the rest.
    When in doubt leave lines alone.
    """
    if not filenames:
        raise click.ClickException("Provide some filenames")

    if filenames[0].strip() == "-":
        success = usort_stdin()
        sys.exit(0 if success else 1)

    return_code = 0
    for f in filenames:
        path = Path(f)
        for result in usort_path(path, write=True):
            if result.error:
                click.echo(f"Error on {result.path}: {result.error!r}")
                return_code |= 1
                continue

            if result.content != result.output:
                click.echo(f"Sorted {result.path}")

    sys.exit(return_code)


if __name__ == "__main__":
    main()
