
.. _versioning:

Versioning
==========

µsort tries to maintain the *spirit* of `SemVer <https://semver.org/>`_ while
focusing primarily on the sorting and formatting results than strictly on the
API contract.

In general, µsort will attempt to maintain consistent formatting results within
a major version, with a best-effort attempt to remain "backwards compatible"
with previous versions of µsort within that major release. Except for obvious
or egregious formatting errors, any file sorted by a newer release of µsort
should produce no changes if formatted by previous minor/patch versions
in that family.

Our goal is to enable a safe and predictable process for users to introduce
updates to their projects, especially in large monorepos. This policy allows
users to transparently and proactively format their codebase with new minor
or patch versions, and validate the resulting behavior, before upgrading CI
workflows or developer toolchains to the latest release.

For example, a file already sorted by µsort ``1.1.3`` may produce changes when
sorted by a newer µsort ``1.2.1`` release, but a file already sorted by ``1.2.1``
should remain unchanged if sorted again by ``1.1.3``. However, a file sorted by
a future µsort ``2.0.0`` release may not be stable if sorted again by version
``1.2.1``.


Details
-------

It is our intent to:

1. Bump the post version (and yank the original, depending on how severe) for:

    - documentation or packaging issues, such as missing files in the sdist
      or unintended classifiers

2. Bump the patch version for:

    - garden-variety bugs, such as those where the previous behavior was an exception
      (such as `#194 <https://github.com/facebook/usort/issues/194>`_)
    - any bug that produces output so mangled it would not have been accepted
      by human review (such as `#187 <https://github.com/facebook/usort/issues/187>`_
      fixed in `#188 <https://github.com/facebook/usort/issues/188>`_
      causing unnecessary reflow that disagreed with black)
    - performance optimizations that expect to have no impact on sorting behavior

    Additionally, if the bug causes data loss, we will also yank affected
    releases (best effort), but the timing of the yank is not defined here.
    The spirit of this is to prevent people from installing known-bad versions,
    but if people pin then yanking is a sign, not a cop.

3. Bump the minor version for:

    - new features that may change the output (at the byte level) for greenfield
      sorting, but produce output that can then be sorted with previous versions
      (see above) without producing additional changes
      (such as `#140 <https://github.com/facebook/usort/issues/140>`_)
    - anything that includes a new config option (although the defaults for
      those config options must keep previous behavior); if a consumer project
      relies on a certain config option, it is on them to constrain to `>=`
      the version where that was added
    - any new ``DeprecationWarning``
    - changing strings intended for humans (e.g. ``Result.warnings``) or exception
      classes (e.g. ``Result.exception``, or its specific values or hierarchy)
      which are not part of the :ref:`documented API <api>`.

4. Bump the major for:

    - any formatting change that breaks the ``backward-compatibility`` test
      on CI, i.e. any change to sorting behavior that would result in previous
      versions of µsort producing changes in code already sorted with the new
      version
    - any intentional change to picking ``pyproject.toml`` or inferring
      first-party names
    - any backwards-incompatible API change or removal

    Additionally, within reason we will yank releases that should have bumped
    the major but didn't, once informed.

5. Note that we assume our deps follow reasonable versioning practices
   (and since several of them are us with another hat on, this is believable).
   In particular:

    - We rely on ``trailrunner`` for discovery of ``pyproject.toml``, and will
      constrain to a major version, with the expectation that any intentional
      changes to discovery behavior will happen with a major version change.
      There may still be subtle edge cases when faced with complicated systems,
      like UNC paths on Windows or bind-mounted path loops on Linux.
    - We rely on ``stdlibs`` to classify top-level names in the stdlib section
      or not. This is date-versioned currently, and in general we *want* the
      updates like `stdlibs#25 <https://github.com/omnilib/stdlibs/pull/25>`_,
      even though that *can* cause formatting changes in uncommon cases.
    - If you are sensitive to behavior changes, we suggest pinning to specifc
      versions of the following packages:
      
        - ``black``
        - ``libcst``
        - ``stdlibs``
        - ``trailrunner``
        - ``usort``
