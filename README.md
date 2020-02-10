# μsort

μsort is a minimal import sorter.  It should not make "dangerous" changes to your
files, by detecting blocks which can be internally sorted.  This simple
heuristic works surprisingly well on real-world code:

```
import foo as os
import os
```

For this, we detect two sortable blocks because of the name shadowing.

```
import disable_network
disable_network.disable()

import b
```

For this, we detect two sortable blocks because of an intervening non-import
statement.

# Usage

To run on itself:

```
$ usort format --diff $(find usort -name '*.py')
```

or to apply the changes remove `--diff`.


# Tests

Run

```
$ make venv
$ . .venv/bin/activate
$ make test
```

# License

usort is MIT licensed, as found in the LICENSE file.
