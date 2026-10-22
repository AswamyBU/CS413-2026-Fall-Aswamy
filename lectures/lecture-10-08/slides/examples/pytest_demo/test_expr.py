import pytest
from expr import free_vars


@pytest.mark.parametrize("expr, expected", [
    (("var", "x"), {"x"}),
    (("lam", "x", ("var", "x")), set()),
    (("app", ("var", "x"), ("var", "y")), {"x", "y"}),
    (("lam", "x", ("var", "y")), {"y"}),
    (("lam", "x", ("app", ("var", "x"),
       ("lam", "y", ("var", "x")))), set()),
], ids=["variable", "bound", "application", "free", "nested"])
def test_free_vars(expr, expected):
    assert free_vars(expr) == expected
