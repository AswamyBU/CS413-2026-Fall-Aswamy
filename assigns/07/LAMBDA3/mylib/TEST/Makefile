PYTHON ?= python3

.PHONY: test
test:
	$(PYTHON) -B -m unittest discover -s "$(dir $(abspath $(lastword $(MAKEFILE_LIST))))" -p 'test_*.py' -v
