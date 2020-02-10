# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import difflib
from pathlib import Path
from typing import List

import click

from .sorting import sortable_blocks, try_parse, usort_string
from .stdlibs.all import stdlib as all_stdlib


@click.group()
def main():
    pass


@main.command()
@click.option("--multiples", is_flag=True, help="Only show files with multiple blocks")
@click.option("--debug", is_flag=True, help="Show internal information")
@click.argument("filenames", nargs=-1)
def list_imports(multiples: bool, debug: bool, filenames: List[str]):
    # This is intended to sort nodes separated by barriers, and that's it.
    # We don't format them (aside from moving comments).  Black does the rest.
    # When in doubt leave lines alone.

    for f in filenames:
        mod = try_parse(Path(f))
        try:
            blocks = sortable_blocks(mod)
        except Exception as e:
            print("Exception", f, e)
            continue

        if multiples and len(blocks) < 2:
            continue

        print(f"{f} {len(blocks)} blocks:")
        for b in blocks:
            print(f"  body[{b.start_idx}:{b.end_idx}]")
            sorted_stmts = sorted(b.stmts)
            if debug:
                for s in b.stmts:
                    print(f"    {sorted_stmts.index(s)} {s}")
            else:
                print("Formatted:")
                print("[[[")
                for s in sorted_stmts:
                    print(mod.code_for_node(s.node), end="")
                print("]]]")


@main.command()
@click.option("--diff", is_flag=True)
@click.argument("filenames", nargs=-1)
def format(diff, filenames):
    if not filenames:
        raise click.ClickException("Provide some filenames")
    for f in filenames:
        data = Path(f).read_text()
        result = usort_string(data)
        if diff:
            print(f)
            print(
                "".join(
                    difflib.unified_diff(data.splitlines(True), result.splitlines(True))
                )
            )
        else:
            Path(f).write_text(data)


if __name__ == "__main__":
    main()
