# Contributing to µsort
We want to make contributing to this project as easy and transparent as
possible.

## Getting Started

µsort requires Python 3.6 or newer. [pyenv][] can help install and manage
multiple versions of Python.

Clone the repository and set up your local workspace:

```shell-session
$ make venv
...

$ source .venv/bin/activate
(usort) $
```

This will create a virtualenv, install dependencies, and set up µsort as
an editable package in the virtualenv. This enables running the `usort` command
from your workspace while activated.

## Testing

You can run tests and linters manually against your virtualenv:

```shell-session
(usort) $ make test lint
```

You can also run the test suite against all supported versions of Python
at once using Tox:

```shell-session
$ tox -p all
```

## Documentation

µsort uses [Sphinx][] for building documentation, and all documentation is
stored in the `docs/` directory at the root of the repository. If you are not
familiar with writing reStructuredText, there is a good
[reStructuredText primer][rst] in the Sphinx documentation.

After making changes, build the documentation and open the resulting HTML
in your browser of choice to make sure your changes have rendered correctly:

```shell-session
(usort) $ make html
...

(usort) $ python -m webbrowser "file://$PWD/html/index.html"
```


## Pull Requests
We actively welcome your pull requests.

1. Fork the repo and push your changes to a separate branch.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. If you haven't already, complete the Contributor License Agreement ("CLA").

## Contributor License Agreement ("CLA")
In order to accept your pull request, we need you to submit a CLA. You only need
to do this once to work on any of Facebook's open source projects.

Complete your CLA here: <https://code.facebook.com/cla>

## Issues
We use GitHub issues to track public bugs. Please ensure your description is
clear and has sufficient instructions to be able to reproduce the issue.

Facebook has a [bounty program](https://www.facebook.com/whitehat/) for the safe
disclosure of security bugs. In those cases, please go through the process
outlined on that page and do not file a public issue.

## License
By contributing to µsort, you agree that your contributions will be licensed
under the [LICENSE][] file in the root directory of this source tree.


[license]: https://github.com/facebook/usort/tree/main/LICENSE
[pyenv]: https://github.com/pyenv/pyenv
[rst]: https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html
[sphinx]: https://www.sphinx-doc.org/
