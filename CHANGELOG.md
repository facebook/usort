## 0.5.0a3

* Added support for formatting stdin with `usort format -`
* Moved diff/check functionality into separate `diff` and `check` commands
* Replaced `usort format --show-time` with `usort --benchmark` framework
* Added custom section names
* Normalize whitespace between sections
* Improves detection of shadowed names with dotted imports
* Case-normalizes names when sorting
* Includes sphinx docs
* Corrects missing `toml` dep

## 0.5.0a2

* Automatic finding of first-party dirs
* Skip entries marked `# usort:skip` or `#isort:skip`
* Uses `.with_changes` on the libcst module object

## 0.5.0a1

* Minimum viable product with configuration

## 0.0.0

* Reserving name on pypi.
