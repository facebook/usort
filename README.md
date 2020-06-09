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
statement.


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

usort is MIT licensed, as found in the LICENSE file.
