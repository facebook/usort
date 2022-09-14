PYTHON?=python
SOURCES=usort setup.py

.PHONY: venv
venv:
	$(PYTHON) -m venv .venv
	source .venv/bin/activate && make setup
	@echo 'run `source .venv/bin/activate` to use virtualenv'

.PHONY: clean
clean:
	rm -rf build dist html

.PHONY: distclean
distclean:
	rm -rf .venv .mypy_cache .coverage

# The rest of these are intended to be run within the venv, where python points
# to whatever was used to set up the venv.

.PHONY: setup
setup:
	python -m pip install -Ur requirements-dev.txt
	python -m pip install -Ur requirements.txt
	python -m pip install -e .

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
	sphinx-build -b html docs html

.PHONY: release
release:
	rm -rf dist
	python setup.py sdist bdist_wheel
	twine upload dist/*
