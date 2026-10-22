import pytest
from stack import Stack


def test_pop_returns_last_pushed():
    stack = Stack()
    stack.push("x")
    stack.push("y")
    result = stack.pop()
    assert result == "y"


def test_pop_removes_an_item():
    stack = Stack()
    stack.push("x")
    stack.push("y")
    assert stack.pop() == "y"
    assert stack.pop() == "x"


def test_empty_pop():
    stack = Stack()
    with pytest.raises(IndexError, match="empty stack"):
        stack.pop()


@pytest.mark.parametrize("values", [[], [7], [2, 5, 2]],
                         ids=["empty", "singleton", "duplicates"])
def test_lifo(values):
    stack = Stack()
    for value in values:
        stack.push(value)
    actual = [stack.pop() for _ in values]
    assert actual == list(reversed(values))


def test_fixture_stack(stack):
    stack.push(7)
    assert stack.pop() == 7


def test_pop_after_draining(stack):
    stack.push(7)
    stack.pop()
    with pytest.raises(IndexError, match="empty stack"):
        stack.pop()
