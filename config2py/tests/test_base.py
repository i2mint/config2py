"""Tests for ``config2py.base``: ``save_to`` dispatch and leak-free ``KeyError``s."""

import pytest

from config2py.base import (
    LEGACY_CONFIG_NOT_FOUND_EXCEPTIONS,
    FuncBasedGettableContainer,
    ask_user_for_key,
    user_gettable,
)

# A stand-in for a credential. Used to assert that a rejected value (or the upstream
# exception text that echoes it) never reaches an error message.
SECRET = "sk-secret-1234"


def _constant_asker(value):
    """Make a ``user_asker`` that answers ``value`` without touching stdin."""
    return lambda prompt: value


class _SetItemOnlyStore:
    """A write target that has ``__setitem__`` but is not a ``MutableMapping``.

    Stands in for the write-only stores that ``dol`` (and friends) hand out.
    """

    def __init__(self):
        self.written = {}

    def __setitem__(self, k, v):
        self.written[k] = v


# --------------------------------------------------------------------------------
# save_to dispatch


def test_ask_user_for_key_saves_to_mapping():
    store = {}
    val = ask_user_for_key("K", save_to=store, user_asker=_constant_asker("V"))
    assert val == "V"
    assert store == {"K": "V"}


def test_ask_user_for_key_saves_to_setitem_only_store():
    store = _SetItemOnlyStore()
    val = ask_user_for_key("K", save_to=store, user_asker=_constant_asker("V"))
    assert val == "V"
    assert store.written == {"K": "V"}


def test_ask_user_for_key_saves_to_callable_saver():
    saved = []
    val = ask_user_for_key(
        "K",
        save_to=lambda k, v: saved.append((k, v)),
        user_asker=_constant_asker("V"),
    )
    assert val == "V"
    assert saved == [("K", "V")]


def test_ask_user_for_key_rejects_unusable_save_to():
    with pytest.raises(TypeError) as excinfo:
        ask_user_for_key("K", save_to=42, user_asker=_constant_asker("V"))
    # The error names the offending type, but never the value being saved
    assert "int" in str(excinfo.value)


def test_ask_user_for_key_rejects_unusable_save_to_before_prompting():
    """An unusable ``save_to`` is reported at wiring time, not after the user typed."""
    asked = []

    def recording_asker(prompt):
        asked.append(prompt)
        return "V"

    with pytest.raises(TypeError):
        ask_user_for_key("K", save_to=object(), user_asker=recording_asker)
    assert asked == [], "the user should not be prompted for a value we cannot save"


def test_ask_user_for_key_does_not_save_when_condition_is_false():
    saved = []
    val = ask_user_for_key(
        "K",
        save_to=lambda k, v: saved.append((k, v)),
        user_asker=_constant_asker(""),
    )
    assert val == ""
    assert saved == []


def test_user_gettable_with_mapping_saver():
    store = {}
    s = user_gettable(save_to=store, user_asker=_constant_asker("SOME_VAL"))
    assert s["SOME_KEY"] == "SOME_VAL"
    assert store == {"SOME_KEY": "SOME_VAL"}


def test_user_gettable_with_callable_saver():
    saved = {}
    s = user_gettable(
        save_to=lambda k, v: saved.update({k: v}),
        user_asker=_constant_asker("SOME_VAL"),
    )
    assert s["SOME_KEY"] == "SOME_VAL"
    assert saved == {"SOME_KEY": "SOME_VAL"}


def test_user_gettable_rejects_unusable_save_to():
    with pytest.raises(TypeError):
        user_gettable(save_to=42)


# --------------------------------------------------------------------------------
# KeyError messages must not leak secrets (issue #14)


def test_getter_exception_keyerror_does_not_leak_secret():
    def getter(k):
        raise RuntimeError(f"authentication failed for token {SECRET}")

    gc = FuncBasedGettableContainer(
        getter, config_not_found_exceptions=LEGACY_CONFIG_NOT_FOUND_EXCEPTIONS
    )
    with pytest.raises(KeyError) as excinfo:
        gc["API_KEY"]
    assert SECRET not in str(excinfo.value)
    assert SECRET not in repr(excinfo.value)
    assert excinfo.value.args[0] == "API_KEY"


def test_getter_exception_keyerror_keeps_cause():
    """The upstream exception stays reachable -- just not embedded in the message."""

    def getter(k):
        raise RuntimeError(f"authentication failed for token {SECRET}")

    gc = FuncBasedGettableContainer(
        getter, config_not_found_exceptions=LEGACY_CONFIG_NOT_FOUND_EXCEPTIONS
    )
    with pytest.raises(KeyError) as excinfo:
        gc["API_KEY"]
    cause = excinfo.value.__cause__
    assert isinstance(cause, RuntimeError)
    assert SECRET in str(cause)


def test_invalid_value_keyerror_does_not_leak_rejected_value():
    gc = FuncBasedGettableContainer(lambda k: SECRET, val_is_valid=lambda v: False)
    with pytest.raises(KeyError) as excinfo:
        gc["API_KEY"]
    assert SECRET not in str(excinfo.value)
    assert SECRET not in repr(excinfo.value)
    assert excinfo.value.args[0] == "API_KEY"


def test_contains_still_works_with_leak_free_errors():
    """``__contains__`` relies on the ``KeyError``, so it must survive the change."""
    gc = FuncBasedGettableContainer(
        lambda k: k if k == "there" else None, val_is_valid=lambda v: v is not None
    )
    assert "there" in gc
    assert "not_there" not in gc


# --------------------------------------------------------------------------------------
# config_not_found_exceptions: only lookup errors fall through by default (issue #25)


def _flaky_source(k):
    raise RuntimeError("network blip")


def _lookup_source(k):
    raise KeyError(k)


def test_default_lets_real_errors_propagate():
    import pytest

    from config2py.base import get_config

    with pytest.raises(RuntimeError, match="network blip"):
        get_config("k", [_flaky_source, {"k": "v"}])


def test_default_falls_through_on_lookup_errors_silently():
    import warnings

    from config2py.base import get_config

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert get_config("k", [_lookup_source, {"k": "v"}]) == "v"


def test_default_still_returns_default_when_nothing_found():
    from config2py.base import get_config

    assert get_config("k", [_lookup_source], default="d") == "d"


def test_legacy_exceptions_fall_through_silently():
    import warnings

    from config2py.base import LEGACY_CONFIG_NOT_FOUND_EXCEPTIONS, get_config

    assert LEGACY_CONFIG_NOT_FOUND_EXCEPTIONS == (Exception,)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        got = get_config(
            "k",
            [_flaky_source, {"k": "v"}],
            config_not_found_exceptions=LEGACY_CONFIG_NOT_FOUND_EXCEPTIONS,
        )
    assert got == "v"


def test_func_based_container_hides_the_cause_text():
    import pytest

    from config2py.base import FuncBasedGettableContainer

    def leaky(k):
        raise KeyError("token sk-SECRET rejected")

    gc = FuncBasedGettableContainer(leaky)
    with pytest.raises(KeyError) as info:
        gc["k"]
    assert "sk-SECRET" not in str(info.value)


def test_user_prompt_with_nobody_to_ask_falls_back_to_default():
    """A closed stdin (EOFError) is "not found", so ``default=`` still applies."""
    from config2py.base import get_config

    def no_stdin(prompt):
        raise EOFError

    src = user_gettable(user_asker=no_stdin)
    assert get_config("k", [{}, src], default="d") == "d"


@pytest.mark.parametrize(
    "error",
    [
        OSError("pytest: reading from stdin while output is captured!"),
        __import__("io").UnsupportedOperation("not readable"),
    ],
)
def test_user_prompt_unreadable_stdin_falls_back_to_default(error):
    """An asker that cannot read stdin (pytest capture, a non-readable stream) is
    "not found", so ``default=`` still applies (issue #83)."""
    from config2py.base import get_config

    def unreadable(prompt):
        raise error

    src = user_gettable(user_asker=unreadable)
    assert get_config("k", [{}, src], default="d") == "d"


def test_user_prompt_lost_stdin_falls_back_to_default(monkeypatch):
    """With stdin closed, ``input()`` raises ``RuntimeError: lost sys.stdin``: that is
    "not found" too (issue #83)."""
    import sys

    from config2py.base import get_config

    def lost_stdin(prompt):
        raise RuntimeError("lost sys.stdin")

    monkeypatch.setattr(sys, "stdin", None)
    src = user_gettable(user_asker=lost_stdin)
    assert get_config("k", [{}, src], default="d") == "d"


def test_user_prompt_runtime_error_with_stdin_present_propagates():
    """A ``RuntimeError`` from the asker while stdin exists is a real error."""
    from config2py.base import get_config

    def broken(prompt):
        raise RuntimeError("bug in the asker")

    src = user_gettable(user_asker=broken)
    with pytest.raises(RuntimeError, match="bug in the asker"):
        get_config("k", [{}, src], default="d")


def test_user_prompt_in_pytest_capture_falls_back_to_default():
    """The real ``input()`` under pytest's capture (issue #83)."""
    from config2py.base import get_config

    src = user_gettable(user_asker=input)
    assert get_config("k", [{}, src], default="d") == "d"


def test_user_prompt_validation_errors_propagate():
    from config2py.base import get_config

    def egress(k, v):
        raise ValueError("bad value")

    src = user_gettable(user_asker=_constant_asker("x"), egress=egress)
    with pytest.raises(ValueError, match="bad value"):
        get_config("k", [{}, src], default="d")
