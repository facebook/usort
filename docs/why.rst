Why µsort?
==========

µsort was originally designed with safety as the top priority—"first, do no harm".
Sorting imports should never result in breaking functionality of the module.

µsort is designed to be as safe as possible when running on enterprise scale codebases
with tens or hundreds of thousands of Python source files, and can be used either as a
standalone formatting tool or linter, or as part of automated codemod toolchains and
CI/CD pipelines. It is currently used in production at Meta for sorting all formatted
Python sources, with daily codemods enforcing sorting on all covered files.

µsort achieves this by making a best effort at understanding common patterns in the
structure of modules, and splitting the code into smaller blocks of sortable imports.
By sorting imports only within these blocks, µsort preserves the locations any
intermediary code that could affect the context or behavior of subsequent imports,
and sorts modules safely with a minimal number of comment directives (ideally none).
When in doubt, µsort will prefer to leave imports in place, rather than risk breaking
functionality of the module being sorted.

See the :doc:`User Guide <guide>` for details.


Design Goals
------------

µsort prefers the simplest code necessary, with predictable and understandable logic,
to sort imports while maintaining safety of the output with minimal directives from
developers writing code:

- Simple dataclasses and sorting methods, optimizing for readable and maintainable
  code rather than absolute performance.

- A single primary code path, to reduce the amount of code and number of test cases
  needed to guarantee safety.

- Stable sorting methods that should always result in the same final output, even
  after multiple passes. This is enforced as part of the functional test suite.

- `LibCST`_ for parsing files and modifying syntax trees.
  µsort transforms CST nodes into dataclasses, then back to CST nodes after sorting.
  This guarantees grammatical correctness of both the input file and the generated
  output. Support for future grammar or syntax changes is the responsibility of LibCST.

- No support for configuring output style. µsort works best when run before a
  dedicated code formatter like `Black`_ for enforcing style choices. µsort does use
  the configured line length for Black when rendering imports on one or more lines.
  We use `µfmt`_ to combine µsort and Black into a single, atomic formatting step.

- No vendored code. All dependencies are satisfied from PyPI, with unbound version
  constraints, and validated in CI pipelines by `pessimist`_.


Non-Goals
---------

There are some features of alternative import sorters that µsort will not offer:

- Broad behavioral changes when sorting files, like moving imports from below a function
  to the top of the file during development. Guaranteeing safety and stability while
  also moving imports between blocks is difficult and hard to reason about in code.

- Removing unused imports. This would require µsort to also consume and understand the
  functionality of each file to accurately know which imports are unused, which would
  increase the amount of code and testing needed to guarantee safety. Furthemore, the
  possibility for import-time side effects in removed imports makes this operation
  potentially dangerous in subtle ways.

- Configurable output style. More options means more code paths to follow, and more
  test cases needed to cover all possible outputs. This is better left for dedicated
  code formatters like `Black`_. We recommend using `µfmt`_ to combine µsort and Black
  into a single, atomic formatting step for CI and linting.

- Python 2 support. µsort's use of strict parsing and manipulation of syntax trees
  makes supporting Python 2 dependent on support in `LibCST`_. Given the incompatible
  grammar elements like print statements, upstream support for Python 2 is unlikely.


Comparison to isort
-------------------

Unlike `isort`_, µsort only sorts imports within individual "blocks" of imports,
inferred based on a number of heuristics (see :ref:`Import Blocks <import-blocks>`
for details). µsort will not attempt to move imports outside of these blocks, or
across any blocks of code that aren't import statements.

For example, µsort detects two distinct blocks of imports in the following code::

    import sys
    sys.path.append("/path/to/libs")

    import foo

Appending to :data:`sys.path`, by definition, changes the behavior of future imports.
µsort treats this snippet of code as correctly sorted, while isort will attempt to move
the ``import foo`` statement to the top, breaking the module if ``foo`` isn't available
in the default search path, and requiring addition of ``isort: skip`` directives to
maintain functionality.

This also extends to common debugging, testing, or performance techniques::

    import a
    print("after a")
    import b

Or::

    import lazy_import
    module = lazy_import.lazy_module("module")

    import sys

Again, µsort will maintain these constructs as-is, without any need for skip directives.

------

µsort uses case-insensitive, lexicographical sorting for both module names and imported
items within each statement. This means uppercase or titlecase names are mixed with
lowercase names, but this also provides a more consistent ordering of names, and
ensures that ``frog``, ``Frog``, and ``FROG`` will always sort next to each other::

    from unittest.mock import (
        ANY,
        AsyncMock,
        call,
        DEFAULT,
        Mock,
        patch,
    )

------

µsort operates on a strictly-parsed syntax tree of each file as a whole, rather than
reading and parsing individual lines of text at a time. This guarantees that µsort is
modifying the actual Python syntax elements, along with any associated comments, and
generating grammatically correct results after sorting.

This prevents an entire class of bugs that can result in generating syntax errors at
best, and causing subtle runtime failures at worst:

- `"Can't handle backslash and bracket"`__
- `"Changes the content of multiline strings after a yield statement"`__
- `"Introduces syntax error by removing closing paren"`__
- `"Line break and tab indentation makes wrong fix"`__

.. __: https://github.com/PyCQA/isort/issues/575
.. __: https://github.com/PyCQA/isort/issues/1507
.. __: https://github.com/PyCQA/isort/issues/1539
.. __: https://github.com/PyCQA/isort/issues/1714

Many of these issues are due to parsing individual lines without the context of the
grammar surrounding it. By parsing the entire file and modifying grammar objects,
there is no chance of mistaking string contents for imports, or of modifying any
elements of the source file that aren't import statements.

No project is free of bugs, including µsort, but design decisions have been made with
the expectation that µsort bugs will tend towards non-destructive failure modes.

.. _LibCST: https://libcst.readthedocs.io
.. _Black: https://black.readthedocs.io
.. _isort: https://pycqa.github.io/isort/
.. _µfmt: https://ufmt.readthedocs.io
.. _pessimist: https://pypi.org/project/pessimist/
