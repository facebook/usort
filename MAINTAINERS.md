# Maintaining µsort

This documents the processes for maintaining and releasing µsort.

## Reviewing Pull Requests

When developers submit pull requests, the following points should be considered
when deciding to accept, request changes, or reject them:

For new features:

* Is the feature appropriate for µsort?
* Does this feature uphold existing safety guarantees?
* Do we want to take responsibility for maintaining and fixing this feature?
* Is this implemented in a way that matches existing µsort patterns and use cases?
* Is this a complete implementation, or is there a clear path to completion?
* Is the feature documented appropriately?

For all code changes:

* Does CI (test, lint, formatting) pass on all supported platforms?
* Does this include appropriate test case coverage?
* Is documentation updated as necessary?

When a PR has been accepted:

* Update PR title if necessary to clarify purpose.
* Prefer using merge commits from Github to record PR name and number.
* For automated PR's (like dependabot), prefer using rebase from Github UI.

## Releasing New Versions

1. Decide on the next version number, based on what has been added to the `main`
   branch since the previous release. See the
   [Versioning Guide](https://usort.rtfd.io/en/latest/versioning.html).

2. Update `CHANGELOG.md` with the new version, following the same pattern as
   previous versions. Entries should reference both the PR number and any
   associated issue numbers related to the feature or change described.

   Contributers to this release should be acknowledged by including the output
   of `git shortlog -sn <previous tag>...`.

3. If releasing a new major version, ensure the ``check_backcompat.py`` test
   script has been updated to match the intended backward compatibility
   version target for future releases.

4. Commit the updated content with a message following the pattern
   "(Feature | bugfix) release v<version>".

5. Push this commit to upstream main branch and wait for CI to run/pass.

6. Tag this commit with the version number (including the preceding "v")
   using `git tag -s v<version>`, and paste the contents of the changelog
   for this version as the tag's message.  Be sure to make a signed tag (`-s`)
   using a GPG key attached to your Github profile.

7. Push this tag to upstream using `git push --tags` and wait for CI to pass.

8. Publish this release to PyPI using `make release` to build and upload
   the source distribution and wheels.
