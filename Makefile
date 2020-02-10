PYTHON?=python
SOURCES=usort setup.py

.PHONY: venv
venv:
	$(PYTHON) -m venv .venv
	source .venv/bin/activate && make setup
	@echo 'run `source .venv/bin/activate` to use virtualenv'

# The rest of these are intended to be run within the venv, where python points
# to whatever was used to set up the venv.

.PHONY: setup
setup:
	python -m pip install -Ur requirements-dev.txt
	python -m pip install -Ur requirements.txt

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

.PHONY: release
release:
	rm -rf dist
	python setup.py sdist bdist_wheel
	twine upload dist/*
