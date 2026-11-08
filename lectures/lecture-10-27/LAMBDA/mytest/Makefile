PYTHON ?= python3

ERROR_EXAMPLES := $(wildcard type_error_*.lam)
VALID_EXAMPLES := $(filter-out type_error_%.lam, $(wildcard *.lam))

.PHONY:: test
.PHONY:: test-valid
.PHONY:: test-errors

test: test-valid test-errors

test-valid:
	PYTHONPATH=.. $(PYTHON) -c 'import pathlib, sys; from lambda2 import d0cls_parse, d0cls_typecheck; [d0cls_typecheck(d0cls_parse(pathlib.Path(name).read_text())) for name in sys.argv[1:]]; print("Valid examples passed:", ", ".join(sys.argv[1:]))' $(VALID_EXAMPLES)

test-errors:
	PYTHONPATH=.. $(PYTHON) -c 'import pathlib, sys; from lambda2 import TypeCheckError, d0cls_parse, d0cls_typecheck; names = sys.argv[1:]; exec("def check(name):\n try: d0cls_typecheck(d0cls_parse(pathlib.Path(name).read_text()))\n except TypeCheckError: return True\n return False"); failed = [name for name in names if not check(name)]; sys.exit("Expected type errors were not raised: " + ", ".join(failed)) if failed else print("Expected type errors confirmed:", ", ".join(names))' $(ERROR_EXAMPLES)
