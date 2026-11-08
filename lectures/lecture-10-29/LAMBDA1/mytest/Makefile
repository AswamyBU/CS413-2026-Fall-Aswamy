PYTHON ?= python3

.PHONY: check check-valid check-errors

check: check-valid check-errors

check-valid:
	@cd .. && PYTHONPATH=. $(PYTHON) -c 'from pathlib import Path; from lambda2 import d0cls_parse, d0cls_typecheck; files = sorted(p for p in Path("mytest").glob("*.lam") if not p.name.startswith("type_error_")); [d0cls_typecheck(d0cls_parse(p.read_text())) for p in files]; print("Type-checked:", ", ".join(p.name for p in files))'

check-errors:
	@set -eu; for file in type_error_*.lam; do \
		if (cd .. && PYTHONPATH=. $(PYTHON) -c 'import sys; from pathlib import Path; from lambda2 import d0cls_parse, d0cls_typecheck; d0cls_typecheck(d0cls_parse(Path(sys.argv[1]).read_text()))' "mytest/$$file") >/dev/null 2>&1; then \
			echo "Expected a type error in $$file"; exit 1; \
		fi; \
	done; echo "Rejected as expected: type_error_*.lam"
