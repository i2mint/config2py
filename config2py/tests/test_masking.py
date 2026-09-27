"""Tests for input masking in ``ask_user_for_input`` (i2mint/config2py#13).

Two prompt functions are faked throughout:

- a *stdlib-like* ``getpass`` (its ``__module__`` is ``"getpass"``), which, like the
  real one, reads the controlling terminal rather than ``sys.stdin``;
- ``builtins.input``, which reads ``sys.stdin``.

Whether ``sys.stdin`` is a terminal is controlled by swapping in stand-ins.
"""

import builtins
import getpass
import io
import sys

import pytest

from config2py.util import ask_user_for_input, looks_like_secret
from config2py.tools import simple_config_getter


class _TtyStdin(io.StringIO):
    """A stdin stand-in that claims to be an interactive terminal."""

    def isatty(self):
        return True


def _fake_getpass(returns, module="getpass"):
    calls = []

    def fake(prompt="", stream=None):
        calls.append(prompt)
        if isinstance(returns, BaseException):
            raise returns
        return returns

    fake.__module__ = module
    fake.calls = calls
    return fake


def _fake_input(returns):
    calls = []

    def fake(prompt=""):
        calls.append(prompt)
        if isinstance(returns, BaseException):
            raise returns
        return returns

    fake.calls = calls
    return fake


@pytest.fixture
def interactive_terminal(monkeypatch):
    """Make ``sys.stdin`` look like a terminal; return the prompt fakes to configure."""
    monkeypatch.setattr(sys, "stdin", _TtyStdin())

    def install(*, getpass_returns="masked value", input_returns="echoed value"):
        fake_getpass = _fake_getpass(getpass_returns)
        fake_input = _fake_input(input_returns)
        monkeypatch.setattr(getpass, "getpass", fake_getpass)
        monkeypatch.setattr(builtins, "input", fake_input)
        return fake_getpass, fake_input

    return install


@pytest.mark.parametrize(
    "key",
    ["OPENAI_API_KEY", "github_token", "DB_PASSWORD", "client_secret", "MY_PWD"],
)
def test_secret_looking_keys_are_masked_by_default(interactive_terminal, key):
    fake_getpass, fake_input = interactive_terminal()
    assert ask_user_for_input(f"Enter a value for {key}: ") == "masked value"
    assert len(fake_getpass.calls) == 1
    assert fake_input.calls == []


@pytest.mark.parametrize("key", ["DATA_DIR", "display_name", "OA_DFLT_MODEL"])
def test_other_keys_are_echoed_by_default(interactive_terminal, key):
    fake_getpass, fake_input = interactive_terminal()
    assert ask_user_for_input(f"Enter a value for {key}: ") == "echoed value"
    assert fake_getpass.calls == []
    assert len(fake_input.calls) == 1


def test_default_value_does_not_decide_masking(interactive_terminal):
    """Only the caller's prompt is inspected, not the ``[default]`` decoration."""
    fake_getpass, fake_input = interactive_terminal(input_returns="")
    assert ask_user_for_input("Enter DATA_DIR", default="~/my_keys") == "~/my_keys"
    assert fake_getpass.calls == []


def test_explicit_mask_input_overrides_the_heuristic(interactive_terminal):
    fake_getpass, fake_input = interactive_terminal()
    assert ask_user_for_input("Enter API_KEY", mask_input=False) == "echoed value"
    assert ask_user_for_input("Enter DATA_DIR", mask_input=True) == "masked value"
    assert len(fake_getpass.calls) == len(fake_input.calls) == 1


def test_mask_input_can_be_a_custom_predicate(interactive_terminal):
    fake_getpass, _ = interactive_terminal()
    always = ask_user_for_input("Enter DATA_DIR", mask_input=lambda prompt: True)
    assert always == "masked value"
    assert len(fake_getpass.calls) == 1


def test_masking_toggle_starts_from_the_resolved_default(interactive_terminal, monkeypatch):
    """With the toggle, the user sees (and flips) the state the heuristic chose."""
    answers = iter(["", "typed"])  # "" toggles masking, then the real value
    prompts = []

    def respond(prompt=""):
        prompts.append(prompt)
        return next(answers)

    respond.__module__ = "getpass"
    monkeypatch.setattr(getpass, "getpass", respond)
    monkeypatch.setattr(builtins, "input", _fake_input(AssertionError("not masked")))
    with pytest.raises(AssertionError, match="not masked"):
        # secret-looking: starts ENABLED, toggling switches to (the failing) input
        ask_user_for_input("Enter API_KEY", masking_toggle_str="")
    assert "Input masking is ENABLED" in prompts[0]


@pytest.mark.parametrize("mask_input", [looks_like_secret, lambda prompt: True])
def test_piped_stdin_is_read_when_masking_is_inferred(monkeypatch, mask_input):
    """When masking was *inferred* (the default predicate), piped input keeps being
    read from stdin, as it was before masking became the default for secret-looking
    prompts: stdlib ``getpass`` would read the terminal instead (or block on it).
    """
    monkeypatch.setattr(sys, "stdin", io.StringIO("piped value\n"))
    monkeypatch.setattr(
        getpass, "getpass", _fake_getpass(AssertionError("read the terminal"))
    )
    # Note: the real builtins.input is used here, reading the replaced sys.stdin
    assert ask_user_for_input("Enter API_KEY", mask_input=mask_input) == "piped value"


def test_explicit_mask_input_true_keeps_reading_the_terminal(monkeypatch):
    """An explicit ``mask_input=True`` keeps its pre-#13 meaning: stdlib ``getpass``,
    which deliberately reads the terminal even when stdin is piped (like ``sudo``), so
    piped data is never mistaken for the secret.
    """
    monkeypatch.setattr(sys, "stdin", io.StringIO("piped data, not the secret\n"))
    fake_getpass = _fake_getpass("typed at the terminal")
    monkeypatch.setattr(getpass, "getpass", fake_getpass)
    monkeypatch.setattr(builtins, "input", _fake_input(AssertionError("read stdin")))
    assert ask_user_for_input("Enter API_KEY", mask_input=True) == (
        "typed at the terminal"
    )
    assert len(fake_getpass.calls) == 1


def test_frontend_getpass_is_used_without_a_terminal(monkeypatch):
    """Frontends such as Jupyter replace ``getpass.getpass`` with their own masked
    widget while ``sys.stdin`` is not a terminal. That replacement must be used.
    """
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    frontend_getpass = _fake_getpass("from widget", module="ipykernel.kernelbase")
    monkeypatch.setattr(getpass, "getpass", frontend_getpass)
    monkeypatch.setattr(builtins, "input", _fake_input(AssertionError("echoed")))
    assert ask_user_for_input("Enter API_KEY") == "from widget"


def test_no_stdin_at_all_does_not_crash(monkeypatch):
    """``sys.stdin`` is ``None`` under pythonw and some embedded interpreters."""
    monkeypatch.setattr(sys, "stdin", None)
    monkeypatch.setattr(getpass, "getpass", _fake_getpass(AssertionError("tty")))
    monkeypatch.setattr(builtins, "input", _fake_input("fallback"))
    assert ask_user_for_input("Enter API_KEY") == "fallback"


def test_simple_config_getter_masks_secret_keys_end_to_end(
    interactive_terminal, tmp_path
):
    fake_getpass, fake_input = interactive_terminal(
        getpass_returns="sk-not-shown", input_returns="/some/dir"
    )
    get = simple_config_getter(
        str(tmp_path) + "/", first_look_in_env_vars=False, ask_user_if_key_not_found=True
    )
    assert get("_C2P_TEST_API_TOKEN_") == "sk-not-shown"
    assert get("_C2P_TEST_DATA_DIR_") == "/some/dir"
    assert len(fake_getpass.calls) == len(fake_input.calls) == 1
    assert (tmp_path / "_C2P_TEST_API_TOKEN_").read_text() == "sk-not-shown"
