PYTHON ?= python3
TEST_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

.PHONY: test
test:
	$(PYTHON) -B -m unittest discover -s "$(TEST_DIR)" -p 'test_*.py' -v
	$(MAKE) -C "$(TEST_DIR)../mylib/TEST" test PYTHON="$(PYTHON)"
