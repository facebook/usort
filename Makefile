PYTHON?=python
SOURCES=usort

.PHONY: venv
venv:
	$(PYTHON) -m venv --clear .venv
	source .venv/bin/activate && make install
	@echo 'run `source .venv/bin/activate` to use virtualenv'

.PHONY: clean
clean:
	rm -rf build dist html

.PHONY: distclean
distclean:
	rm -rf .venv .mypy_cache .coverage

# The rest of these are intended to be run within the venv, where python points
# to whatever was used to set up the venv.

.PHONY: install
install:
	python -m pip install -U pip setuptools
	python -m pip install -e .[dev,docs]

.PHONY: test
test:
	python -m coverage run -m usort.tests $(TESTOPTS)
	python -m coverage report
	python -m mypy --strict usort --install-types --non-interactive

.PHONY: format
format:
	python -m ufmt format $(SOURCES)

.PHONY: lint
lint:
	python -m ufmt check $(SOURCES)
	python -m flake8 $(SOURCES)
	/bin/bash check_copyright.sh

.PHONY: deps
deps:
	python -m pessimist --requirements= -c "python -m usort --help" .

.PHONY: backcompat
backcompat:
	python check_backcompat.py

.PHONY: html
html:
	sphinx-build -ab html docs html

.PHONY: release
release:
	rm -rf dist
	hatch build
	hatch publish
