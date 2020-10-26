## 0.6.0

* Add support for configurable side-effect modules as block separators (#39)
* Rename `default_section` option to `default_category` (#41)

```shell-session
$ git shortlog -sn v0.5.0...
    11  John Reese
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
    28  John Reese
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
