## 1.0.7

Maintenance release

* Added pre-commit hook for usort (#261, #260)
* Fixed tests for LibCST 1.0 release and native parser

```shell-session
$ git shortlog -sn v1.0.6...
     3  Amethyst Reese
```

## 1.0.6

Bugfix release

* Fix dropped inline comments on last import item without trailing comma (#251, #249)

```shell-session
$ git shortlog -sn v1.0.5...
     4  Amethyst Reese
```

## 1.0.5

Bugfix release

* Fix AssertionError when sorting multiple statements on one line (#203, #204)
* Deprecated: Python 3.6 support will be dropped in v1.1.0 (#154)

```shell-session
$ git shortlog -sn v1.0.4...
     4  Amethyst Reese
```

## 1.0.4

Bugfix release

* Make sure indentation is tracked (#188)

```shell-session
$ git shortlog -sn v1.0.3...
     1  Amethyst Reese
```

## 1.0.3

Bugfix release

* Skip visiting CST nodes that cannot have import statements (#187)
* Skip deep copying CST after parsing (#167)
* Optimize passing multiple paths to usort CLI (#161)
* Don't use trailrunner to format exactly one file (#160)

```shell-session
$ git shortlog -sn v1.0.2...
     2  Amethyst Reese
     2  Zsolt Dollenstein
     1  Arseny Boykov
```

## 1.0.2

Bugfix release

* Fix unstable sorting from basic imports with mixed categories (#145, #146)
* Fix documentation examples (#142)
* Updated stdlibs for Python 3.10 (#138)

```shell-session
$ git shortlog -sn v1.0.1...
     7  dependabot[bot]
     5  Amethyst Reese
     2  Tim Hatch
```

## 1.0.1

Bugfix release

* Handle single line from-imports with parens (#128)
* Significant speedup when sorting files that don't produce warnings (#126)
* Documentation for the "Why µsort" topic (#130)
* Updated copyright, attribution, and logos to Meta Platforms, Inc (#131)
* Dependency updates

```shell-session
$ git shortlog -sn v1.0.0...
    14  Amethyst Reese
    12  dependabot[bot]
     3  Zsolt Dollenstein
```

## 1.0.0

Feature release

* New feature: sorting items in a single import statement (#81)
* New feature: merging imports from the same module (#81)
* Supports usort:skip directives on first and last line of multi-line imports (#108)
* Supports usort:skip directives that aren't the first comment directive on a line (#108)
* Deprecation: `usort_bytes()` and `usort_string()` replaced by `usort()` (#88)
* Fix reading the configured black line length from pyproject.toml (#110)
* Improved performance by sorting multiple files in parallel (#70)
* Officially support Python 3.10 (#74)
* Documentation improvements (#91, #108, #109)

```shell-session
$ git shortlog -sn v0.6.4...
   104  Amethyst Reese
    18  dependabot[bot]
     7  Tim Hatch
     3  Jason Fried
```

## 1.0.0rc1

Release Candidate:

* Supports usort:skip directives on first and last line of multi-line imports (#108)
* Supports usort:skip directives that aren't the first comment directive on a line (#108)
* Fix reading the configured black line length from pyproject.toml (#110)
* Documentation improvements (#108, #109)

```shell-session
git shortlog -sn v1.0.0b1...
    10  Amethyst Reese
```

## 1.0.0b1

Beta release

* Deprecation: `usort_bytes()` and `usort_string()` replaced by `usort()` (#88)
* Improved documentation in user guide for sorting, merging, comments, and associations (#91)
* Fixed bug when merging imports and subsequent blocks (#86)
* Fixed output of basic imports that exceed line length (#87)

```shell-session
$ git shortlog -sn v1.0.0a1...
    28  Amethyst Reese
    13  dependabot[bot]
     3  Jason Fried
```

## 1.0.0a1

Alpha release

* New feature: sorting items in a single import statement (#81)
* New feature: merging imports from the same module (#81)
* Improved performance by sorting multiple files in parallel (#70)
* Officially support Python 3.10 (#74)

```shell-session
$ git shortlog -sn v0.6.4...
    62  Amethyst Reese
     7  Tim Hatch
     5  dependabot[bot]
```

## 0.6.4

Bugfix release

* Fix incomplete stdlib detection by using "stdlibs" from pypi (#56)

```shell-session
$ git shortlog -sn v0.6.3...
     1  Amethyst Reese
     1  Tim Hatch
```

## 0.6.3

Bugfix release

* Enforce blank lines before comments within a category (#50)
* Fix config finding with relative paths (#43, #53)
* Correctly handle encodings in LibCST (#46, #54)
* Sort usort with usort (#51)
* Officially support Python 3.9 (#50)

```shell-session
$ git shortlog -sn v0.6.2...
    11  Tim Hatch
     3  Amethyst Reese
```

## 0.6.2

Minor release

* Option to disable first-party heuristic (#47)

```shell-session
$ git shortlog -sn v0.6.1...
     1  Amethyst Reese
     1  Tim Hatch
```

## 0.6.1

Minor release

* Improve error messages, especially for parsing errors (#45)

```shell-session
$ git shortlog -sn v0.6.0...
     7  Amethyst Reese
     1  Tim Hatch
```

## 0.6.0

* Add support for configurable side-effect modules as block separators (#39)
* Rename `default_section` option to `default_category` (#41)

```shell-session
$ git shortlog -sn v0.5.0...
    11  Amethyst Reese
     2  Tim Hatch
```

## 0.5.0

Initial public release

* Fixes case insensitive handling for stdlib modules like cProfile (#37)
* Added timing metrics for walking file trees, parsing files, and sorting (#35)
* Added a maintainer's guide (#36)
* Documentation fixes

```shell-session
$ git shortlog -sn
    34  Tim Hatch
    28  Amethyst Reese
     2  Facebook Community Bot
```

## 0.5.0a3

* Improved detection of shadowed imports (#24)
* Normalizes to one blank line between categories (#22)
* Ensure case-insensitive sorting order (#19)
* Fixed import sorting outside of global scope (#15)
* Added support for formatting stdin with `usort format -` (#12)
* Moved diff/check functionality into separate `diff` and `check` commands (#12)
* Replaced `usort format --show-time` with `usort --benchmark` framework (#12)
* Added custom section names (#13)
* Includes sphinx docs (#7)
* Corrects missing `toml` dep (#11)

## 0.5.0a2

* Automatic finding of first-party dirs
* Skip entries marked `# usort:skip` or `#isort:skip`
* Uses `.with_changes` on the libcst module object

## 0.5.0a1

* Minimum viable product with configuration

## 0.0.0

* Reserving name on pypi.
