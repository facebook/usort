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
4. Merge sequential import statements from the same module (See `Merging`_ for details)
5. Reorder imported names within each statement
6. Normalize whitespace between imports as needed

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

And lastly, imports of the same style are sorted lexicographically, and case-
insensitively, by source module name, and then by name of element being imported.

Altogether, this will result each block of imports sorted roughly according
to this example, for a module in the namespace :mod:`something`::

    # future imports
    from __future__ import annotations

    # standard library
    import re
    import sys
    from datetime import date, datetime, timedelta
    from pathlib import Path
    from unittest import expectedFailure, TestCase, skip

    # third-party
    import requests
    from attr import dataclasses
    from honesty.api import download_many

    # first-party
    from something import other_function, some_function
    from . import some_module
    from .other_module import SomeClass, some_thing, TestFixture


Merging
-------

After sorting import statements within a block, µsort will look for sequential imports
of the same style from the same module, and merge them into a single statement.

For a simple example, starting with the following imports::

    from unittest import expectedFailure, skip
    from typing import List, Dict
    from unittest import TestCase
    from typing import Set, Mapping

After running µsort, these imports would be merged together::

    from typing import Dict, List, Mapping, Set
    from unittest import expectedFailure, TestCase, skip

Individual names imported from that module will be deduplicated, and any associated
inline comments will be merged at best effort (see `Merging Comments`_ below).
µsort will ensure that it keeps one and only one of each unique imported name,
including any aliases. Given the following import statements::

    from foo import alpha, beta, gamma
    from foo import alpha as a
    from foo import alpha as egg
    from foo import alpha as a
    from foo import beta, gamma, delta

µsort will merge all of the import statements above into a single statement, preserving
all three aliases of `alpha` (expanded here for clarity)::

    from foo import (
        alpha,
        alpha as a,
        alpha as egg,
        beta,
        delta,
        gamma,
    )

If desired, merging behavior can be disabled in your project `configuration`_.

Merging Comments
^^^^^^^^^^^^^^^^

µsort will attempt to preserve any comments associated with an import statement, or any
imported names, and merge them with comments from the same name or same part from the
the other statement. See `Associations`_ for details on comment association rules.

For sake of simplicity in the implementation, comments are not deduplicated, and will
be reproduced in their entirety, including the comment prefix. Their final order is
arbitrary, and based on the order of statements they originate from after an initial
round of sorting.

An example showing some, but not all, possible ways comments will be moved or merged::

    # alpha
    from foo import (  # beta
        # gamma
        bar,  # delta
        baz,
        # epsilon
    )  # zeta

    # eta
    from foo import (  # theta
        # iota
        bar,  # kappa
        # lambda
        buzz,
        # mu
    )  # nu

Both statements will be merged, and comments will follow their respective elements::

    # alpha
    # eta
    from foo import (  # beta  # theta
        # gamma
        # iota
        bar,  # delta  # kappa
        baz,
        # lambda
        buzz,
        # epsilon
        # mu
    )  # zeta  # nu


Comments
--------

Directives
^^^^^^^^^^

µsort will obey simple ``#usort:skip`` directives to prevent moving import statements,
including moving any other statements across the skipped statement::

    import math

    import important_thing  # usort: skip

    import difflib

Comment directives must be on the first or last line of multi-line imports::

    from side_effect import (  # usort:skip  # here
        thing_one,
        thing_two,
    )  # usort:skip  # or here

Directives are also allowed anywhere in a comment, but must include another ``#``
character if they are not the first element::

    import side_effect  # noqa: F401  # usort:skip

See `Import Blocks`_ for details on how skip directives affect sorting behavior.

.. note:: 
    For compatibility with existing codebases previously using isort, the
    ``#isort:skip`` directive is also supported, with the same behavior as
    ``#usort:skip``.
    
    However, the ``#isort:skip_file`` directive **is ignored** by µsort, and there
    is no supported equivalent. We believe that µsort's behavior is safe enough that
    all files can be safely sortable, given an appropriate `configuration`_ that
    includes any known modules with import-time side effects.

    If there are files you absolutely don't want sorted; don't run µsort on them.

Associations
^^^^^^^^^^^^

When moving or merging imports, µsort will attempt to associate and preserve comments
based on simple heuristics for ownership:

* Whole-line, or block, comments:

  * outside of a multi-line statement are associated with the statement that follows
    the comment.
  * inside a multi-line statement, that precede an imported name, will be associated
    with the imported name.
  * inside a multi-line statement, that precede the closing braces for the statement,
    will be associated with the end of the statement.
  * inside a multi-line statement, that precede a comma, will be associated with the
    imported name preceding the comma.

* Inline, or trailing, comments:

  * immediately following the opening brace of a multi-line statement are associated
    with the statement.
  * following an imported name, or comma, will be associated with the imported name
    that precedes the comment.

Given the number of possible places for comments in the Python grammar for a single
import statement, it may be easier to follow this example::

    # IMPORT
    from foo import (  # IMPORT
        # BETA
        beta,  # BETA

        # ALPHA
        alpha  # ALPHA
        # ALPHA
        , # ALPHA

        # IMPORT
    )  # IMPORT

Be aware that blank lines do not impact association rules, and the blank lines in the
example above are purely for clarity.

.. note:: Block comments at the beginning of a source file will not be associated with
    any statement, due to behavior in LibCST [#libcst405]_.

    This means the `# alpha` comment below will not move with the import statement
    it would otherwise be associated with::

        #!/usr/bin/env python

        # alpha
        import foo
        import bar

    This would unexpectedly result in the following file after sorting::

        #!/usr/bin/env python

        # alpha
        import bar
        import foo

    To guarantee the expected behavior, a simple docstring can be added at the top of
    the file, and any comments after the docstring will be associated with the
    appropriate statements::

        #!/usr/bin/env python
        """ This is a module """

        # alpha
        import foo
        import bar

    This would then allow µsort to correctly move the comment as expected::

        #!/usr/bin/env python
        """ This is a module """

        import bar
        # alpha
        import foo

    .. [#libcst405] https://github.com/Instagram/LibCST/issues/405

.. _import-blocks:

Import Blocks
-------------

µsort groups imports into one or more "blocks" of imports. µsort will only move imports
within the distinct block they were originally located. The boundaries of blocks are
treated as "barriers", and imports will never move across these boundaries from one
block to another.

µsort uses a set of simple heuristics to define blocks of imports, based on common
idioms and special behaviors that ensure a reasonable level of "safety" when sorting.

Comment Directives
^^^^^^^^^^^^^^^^^^

Comments with special directives create explicit blocks, separated by the line
containing the directives, which will remain unchanged::

    import math

    import important_thing  # usort: skip

    import difflib

Both ``#usort:skip`` and ``#isort:skip`` (with any amount of whitespace),
will trigger this behavior, so existing comments intended for isort will still
work with µsort.

See `directives`_ for details on supported comment directives.

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

Similarly, any line with multiple statements separated by semicolons will also
create an implicit block separator. µsort will defer to a dedicated formatter
for correctly splitting those statements onto separate lines::

    import zipfile
    import sys; import re  # <-- implicit block separator
    import ast

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

.. _side-effect-imports:

Side Effect Imports
^^^^^^^^^^^^^^^^^^^

Writing modules with import-time side effects is a bad practice; any side
effects should ideally wait for a function in that module to be called, like
with :func:`warnings.filterwarnings()`. In these cases, µsort will correctly
find and create a block separator, preventing accidental changes in execution
order when sorting.

However, it's common for testing libraries and entry points to have well-known
side effects when imported, and this can cause trouble with import sorting.
Rather than adding ``# usort:skip`` comments to every occurence, these modules
can be added to the :attr:`side_effect_modules` configuration option:

.. code-block:: toml
    :name: pyproject.toml

    [tool.usort]
    side_effect_modules = ["sir_kibble"]

µsort will then treat any import of these modules as implicit block separators::

    import foo

    from sir_kibble import leash  # <-- implicit block separator

    import dog

This may result in less-obvious sorting results for users unaware of the
context, so it is recommended to use this sparingly. The ``list-imports``
command may be useful for understanding how this affects your source files.


Configuration
-------------

µsort shouldn't require configuration for most projects, but offers some basic
options to customize sorting and categorization behaviors.

:file:`pyproject.toml`
^^^^^^^^^^^^^^^^^^^^^^

The preferred method of configuring µsort is in your project's
:file:`pyproject.toml`, in the ``tool.usort`` table.
When sorting each file, µsort will look for the "nearest" :file:`pyproject.toml`
to the file being sorted, looking upwards until the project root is found, or
until the root of the filesystem is reached.

``[tool.usort]``
%%%%%%%%%%%%%%%%

The following options are valid for the main ``tool.usort`` table:

.. attribute:: categories
    :type: List[str]
    :value: ["future", "standard_library", "third_party", "first_party"]

    If given, this list of categories overrides the default list of categories
    that µsort provides. New categories may be added, but any of the default
    categories *not* listed here will be removed.

.. attribute:: default_category
    :type: str
    :value: "third_party"

    The default category to classify any modules that aren't already known by
    µsort as part of the standard library or otherwise listed in the
    ``tool.usort.known`` table.

.. attribute:: side_effect_modules
    :type: List[str]

    An optional list of known modules that have dangerous import-time side
    effects. Any module in this list will create implicit block separators from
    any import statement matching one of these modules.

    See :ref:`side-effect-imports`.

.. attribute:: first_party_detection
    :type: bool
    :value: true

    Whether to run a heuristic to detect the top-level name of the file being sorted,
    and consider that name as first-party.  This heuristic happens after other options
    are loaded, so such names cannot be overridden to another category if this is
    enabled.

.. attribute:: merge_imports
    :type: bool
    :value: true

    Whether to merge sequential imports from the same base module.
    See `Merging`_ for details on how this works.

.. attribute:: excludes
    :type: List[str]

    List of "gitignore" style filename patterns to exclude when sorting paths.
    This will supplement any ignored paths from the project root's ``.gitignore`` file,
    and any file or directory that matches these patterns will not be sorted.

    Example:

    .. code-block:: toml

        [tool.usort]
        excludes = [
            "test/fixtures/",
            "*_generated.py",
        ]

    This configuration would match and exclude the following files:

    * ``test/fixtures/something_good.py``
    * ``foo/test/fixtures/something_bad.py``
    * ``foo/client/robot_generated.py``

    See the :std:doc:`pathspec <pathspec:index>` and
    :py:class:`GitWildPatchPattern <pathspec.patterns.gitwildmatch.GitWildMatchPattern>`
    documentation for details of what patterns are allowed and how they are applied.

``[tool.usort.known]``
%%%%%%%%%%%%%%%%%%%%%%

The ``tool.usort.known`` table allows for providing a custom list of known
modules for each category defined by :attr:`categories` above. These modules
should be a list of module names assigned to a property named matching the
category they should be assigned to. If a module is listed under multiple
catergories, the last category it appears in will take precedence.

As an example, this creates a fifth category "numpy", and adds both :mod:`numpy`
and :mod:`pandas` to the known modules list for the "numpy" category, as well
as adding the :mod:`example` module to the "first_party" category:

.. code-block:: toml

    [tool.usort]
    categories = ["future", "standard_library", "numpy", "third_party", "first_party"]
    default_category = "third_party"

    [tool.usort.known]
    numpy = ["numpy", "pandas"]
    first_party = ["example"]


``[tool.black]``
%%%%%%%%%%%%%%%%

µsort will also recognize the following options for `Black`_:

.. attribute:: line-length
    :type: int
    :value: 88

    The target line length configured for Black will also be used by µsort when
    rendering imports after merging and sorting. Imports that fit within this length,
    including indentation and comments, will be rendered on a single line. Otherwise,
    imports will be rendered as multi-line imports, with a single name per line.

.. _Black: https://black.readthedocs.io


Troubleshooting
---------------

If µsort behavior is unexpected, or you would like to see how µsort detects
blocks in your code, the ``list-imports`` command may help.

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
