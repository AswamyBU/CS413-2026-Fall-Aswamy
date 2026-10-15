NODE ?= node
PYTHON ?= python3

.PHONY:: test
.PHONY:: test-py

test:: test-py

test-py:
	$(PYTHON) -m unittest discover -s . -p 'test_*.py' -v

