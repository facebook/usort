User Guide
==========

Blocks
------

Code
^^^^

Comments
^^^^^^^^

Shadows
^^^^^^^

```py
import foo as os
import os
```

For this, we detect two sortable blocks because of the name shadowing.


Troubleshooting
---------------

To see the blocks and sort keys:

```sh
$ usort list-imports --debug <filename>
```


Tests
-----

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
