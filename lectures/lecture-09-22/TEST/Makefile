# Requires Python 3.12 or later. Override with: make PYTHON=python3.12
PYTHON ?= python3

.PHONY: test test-opt test-all

test:
	$(PYTHON) -B -m unittest discover -s . -p 'test*.py' -v

test-opt:
	$(PYTHON) -B -O -m unittest discover -s . -p 'test*.py' -v
	$(PYTHON) -B -OO -m unittest discover -s . -p 'test*.py' -v

test-all: test test-opt
