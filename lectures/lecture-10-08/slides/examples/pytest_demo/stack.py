"""Small application used in the pytest lecture."""
import os


class Stack:
    def __init__(self):
        self._items = []

    def push(self, value):
        self._items.append(value)

    def pop(self):
        if not self._items:
            raise IndexError("empty stack")
        return self._items.pop()


def greeting():
    return "Hello, " + os.getenv("USER_NAME", "guest")


def announce(name):
    print(f"Hello, {name}!")
