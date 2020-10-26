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
	rm -rf .venv

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

.PHONY: format
format:
	python -m isort --recursive -y $(SOURCES)
	python -m black $(SOURCES)

.PHONY: lint
lint:
	python -m isort --recursive --diff $(SOURCES)
	python -m black --check $(SOURCES)
	python -m flake8 $(SOURCES)
	mypy --strict usort
	/bin/bash check_copyright.sh


.PHONY: html
html:
	sphinx-build -b html docs html

.PHONY: release
release:
	rm -rf dist
	python setup.py sdist bdist_wheel
	twine upload dist/*
