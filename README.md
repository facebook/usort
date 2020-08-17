# μsort

μsort is a minimal import sorter.  It should not make "dangerous" changes to your
files, by detecting blocks which can be internally sorted.  This simple
heuristic works surprisingly well on real-world code:

```py
import foo as os
import os
```

For this, we detect two sortable blocks because of the name shadowing.

```py
import disable_network
disable_network.disable()

import b
```

For this, we detect two sortable blocks because of an intervening non-import
statement.  Lines with `# usort:skip` or `# isort:skip` will also split blocks.


# Usage

To run on itself:

```sh
$ usort format --diff .
```

or to apply the changes remove `--diff`.


# Debugging

To see the blocks and sort keys:

```sh
$ usort list-imports --debug <filename>
```


# Tests

Run

```
$ make venv
$ . .venv/bin/activate
$ make test
```

or

```
$ tox -p all
```

# License

μsort is copyright [Tim Hatch, Facebook](), and licensed under
the MIT license.  I am providing code in this repository to you under an open
source license.  This is my personal repository; the license you receive to
my code is from me and not from my employer. See the `LICENSE` file for details.
