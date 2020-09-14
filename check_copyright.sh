#!/bin/bash

set -eu

die() { echo "$1"; exit 1; }

while read filename; do \
  grep -q "Copyright (c) Facebook" "$filename" ||
    die "Missing copyright in $filename"
done < <( git ls-tree -r --name-only HEAD | grep ".py$" )

