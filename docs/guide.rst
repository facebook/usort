User Guide
==========

Configuration
-------------


Import Blocks
-------------

µsort uses a set of simple heuristics to detect "blocks" of imports, and will
only rearrange imports within these distinct blocks.

Comment Directives
^^^^^^^^^^^^^^^^^^

Comments with special directives create explicit blocks, separated by the line
containing the directives::

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
