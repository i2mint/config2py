"""Utils for testing config2py functionality."""

from functools import partial


def user_input_patch(monkeypatch, user_input_string: str):
    monkeypatch.setattr("builtins.input", lambda _: user_input_string)
