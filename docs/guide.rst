User Guide
==========

The µsort command line interface is the primary method for sorting imports
in your Python modules. Installing µsort can be done via ``pip``:

.. code-block:: shell-session

    $ pip install usort

To format one or more files or directories in-place:

.. code-block:: shell-session

    $ usort format <path> [<path> ...]

To generate a diff of changes without modifying files:

.. code-block:: shell-session

    $ usort diff <path> [<path> ...]

µsort can also be used to validate formatting as part of CI:

.. code-block:: shell-session

    $ usort check <path> [<path> ...]


Sorting
-------

µsort follows a few simple steps when sorting imports in a module:

1. Look for all import statements in the module
2. Group these statements into "blocks" of sortable imports
   (See `Import Blocks`_ for details)
3. Reorder import statements within each block
4. Normalize whitespace between imports as needed

When ordering imports within a block, µsort categorizes the imports by source
into four major categories for imports, prioritized following common community
standards:

* :mod:`__future__` imports:
* Standard library modules (from CPython):
* Third-party modules (external imports)
* First-party modules (internal, local, or relative imports)

Within each category, imports are sorted first by "style" of import statement:

* "basic" imports (``import foo``)
* "from" imports (``from foo import bar``)

And lastly, imports of the same style are sorted lexicographically by source
module name, and then by name of element being imported.

Altogether, this will result each block of imports sorted roughly according
to this example, for a module in the namespace :mod:`something`::

    # future imports
    from __future__ import annotations

    # standard library
    import re
    import sys
    from datetime import date, datetime, timedelta
    from pathlib import Path

    # third-party
    import requests
    from attr import dataclasses
    from honesty.api import download_many

    # first-party
    from something import other_function, some_function
    from . import some_module
    from .other_module import some_name, that_thing


Configuration
-------------

µsort shouldn't require configuration for most projects, but offers some basic
options to customize sorting behaviors.  When using flags, only a few are
available:

* :attr:`known_standard_library: Set[str]`: A set of module names to treat
  as part of the standard library. This is added to the set of modules listed
  in the `stdlib_list <https://python-stdlib-list.readthedocs.io/en/latest/index.html>`_ package.

* :attr:`known_third_party: Set[str]`: A set of module names to treat as
  third-party modules.

* :attr:`known_first_party: Set[str]`: A set of module names to treat as
  first-party modules.

* :attr:`default_section: str`: Which category should be used for unrecognized
  module names. Valid values include ``"future"``, ``"standard_library"``,
  ``"third_party"``, and ``"first_party"``. Defaults to ``"third_party"``.

:file:`pyproject.toml`
^^^^^^^^^^^^^^^^^^^^^^

The preferred method of configuring µsort is in your project's
:file:`pyproject.toml`, in the ``tool.usort`` section.  When you use this
configuration, you may also come up with new category names:

.. code-block:: toml

    [tool.usort]
    categories = ["future", "standard_library", numpy", "third_party", "first_party"]
    default_section = "third_party"

    [tool.usort.known]
    numpy = ["numpy", "pandas"]
    first_party = ["something"]

When run, µsort will look for the "nearest" :file:`pyproject.toml` to the
current working directory, looking upwards until the project root is found,
or until the root of the filesystem is reached.


Import Blocks
-------------

µsort uses a set of simple heuristics to detect "blocks" of imports, and will
only rearrange imports within these distinct blocks.

Comment Directives
^^^^^^^^^^^^^^^^^^

Comments with special directives create explicit blocks, separated by the line
containing the directives, which will remain unchanged::

    import math

    import important_thing  # usort: skip

    import difflib

Both ``# usort:skip`` and ``# isort:skip`` (with any amount of whitespace),
will trigger this behavior, so existing comments intended for isort will still
work with µsort.

Statements
^^^^^^^^^^

Any non-import statement positioned between imports will create an implicit
block separator. This allows µsort to automatically preserve use of modules
that must happen before other imports, such as filtering warnings or debug
logging::

    import warnings
    warnings.filterwarnings(...)  # <-- implicit block separator

    import noisy_module

    print("in between imports")  # <-- implicit block separator

    import other_module

Shadowed Imports
^^^^^^^^^^^^^^^^

Any import that shadows a previous import will create an implicit block
separator::

    import foo as os
    import os  # <-- implicit block separator

Star Imports
^^^^^^^^^^^^

Star imports, which can potentially shadow or be shadowed by any other import,
will also create implicit block separators::

    import foo

    from bar import *  # <-- implicit block separator

    import dog


Troubleshooting
---------------

If µsort behavior is unexpected, or you would like to see how µsort detects
blocks in your code, the `list-imports` command may help.

Given the file ``test.py``::

    import warnings
    warnings.filterwarnings(...)

    import foo
    from bar import bar  # usort:skip

    import sys

Running ``list-imports`` will generate the following output:

.. code-block:: shell-session

    $ usort list-imports test.py
    test.py 3 blocks:
    body[0:1]
    Formatted:
    [[[
    import warnings
    ]]]
    body[2:3]
    Formatted:
    [[[

    import foo
    ]]]
    body[4:5]
    Formatted:
    [[[

    import sys
    ]]]

Note that imports that are also block separators (like star imports or imports
with ``skip`` directives) will not be listed in the output, because they are
not within the sortable blocks that µsort operates on.

If more details are desired, the ``--debug`` flag will also provide categories
and sorting information for each import:

.. code-block:: shell-session

    $ usort list-imports --debug test.py
    test.py 3 blocks:
    body[0:1]
        0 SortableImport(sort_key=SortKey(category_index=1, is_from_import=False, ndots=0), first_module='warnings', first_dotted_import='warnings', imported_names={'warnings'}) (Category.STANDARD_LIBRARY)
    body[2:3]
        0 SortableImport(sort_key=SortKey(category_index=2, is_from_import=False, ndots=0), first_module='foo', first_dotted_import='foo', imported_names={'foo'}) (Category.THIRD_PARTY)
    body[4:5]
        0 SortableImport(sort_key=SortKey(category_index=1, is_from_import=False, ndots=0), first_module='sys', first_dotted_import='sys', imported_names={'sys'}) (Category.STANDARD_LIBRARY)
