TEST ?= test*.py
PYTHON ?= python3

.PHONY: test
# Run all tests: make
# Run one file:  make TEST=test01_lambda0.py
test:
	$(PYTHON) -m unittest discover -s . -p '$(TEST)' -v
