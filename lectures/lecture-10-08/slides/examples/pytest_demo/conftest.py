import pytest
from stack import Stack


@pytest.fixture
def stack():
    return Stack()


@pytest.fixture
def output_file(tmp_path):
    stream = (tmp_path / "out.txt").open("w+")
    yield stream
    stream.close()
