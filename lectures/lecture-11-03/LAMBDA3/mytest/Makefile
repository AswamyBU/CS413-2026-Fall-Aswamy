PYTHON ?= python3
NODE ?= node

.PHONY: check check-js show-factorial show-eight-queens show-js-factorial show-js-eight-queens

check:
	PYTHONPATH=.. $(PYTHON) check_examples.py

show-factorial:
	PYTHONPATH=.. $(PYTHON) -c 'from pathlib import Path; import lambda3 as L; source = Path("factorial.lam").read_text(); print(L.d0exp_compile(L.d0exp_parse(source)))'

show-eight-queens:
	PYTHONPATH=.. $(PYTHON) -c 'from pathlib import Path; import lambda3 as L; source = Path("eight_queens.lam").read_text(); print(L.d0exp_compile(L.d0exp_parse(source)))'

show-js-factorial:
	PYTHONPATH=.. $(PYTHON) -c 'from pathlib import Path; import lambda3 as L; source = Path("factorial.lam").read_text(); print(L.d0exp_compile_js(L.d0exp_parse(source)), end="")'

show-js-eight-queens:
	PYTHONPATH=.. $(PYTHON) -c 'from pathlib import Path; import lambda3 as L; source = Path("eight_queens.lam").read_text(); print(L.d0exp_compile_js(L.d0exp_parse(source)), end="")'

check-js:
	PYTHONPATH=.. $(PYTHON) check_javascript.py $(NODE)
