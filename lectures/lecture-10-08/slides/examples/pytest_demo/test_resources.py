import pytest
from stack import announce, greeting


def test_output_file(output_file):
    output_file.write("hello")
    output_file.seek(0)
    assert output_file.read() == "hello"


def test_save_names(tmp_path):
    path = tmp_path / "names.txt"
    path.write_text("Ada\nGrace\n", encoding="utf-8")
    names = path.read_text(encoding="utf-8").splitlines()
    assert names == ["Ada", "Grace"]


def test_announce(capsys):
    announce("Ada")
    captured = capsys.readouterr()
    assert captured.out == "Hello, Ada!\n"
    assert captured.err == ""


def test_greeting(monkeypatch):
    monkeypatch.setenv("USER_NAME", "Ada")
    assert greeting() == "Hello, Ada"


def test_greeting_default(monkeypatch):
    monkeypatch.delenv("USER_NAME", raising=False)
    assert greeting() == "Hello, guest"


def test_decimal_sum():
    assert 0.1 + 0.2 == pytest.approx(0.3, abs=1e-12, rel=0)
