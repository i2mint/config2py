"""Tests for ``config2py.base``: ``save_to`` dispatch and leak-free ``KeyError``s."""

import pytest

from config2py.base import (
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

    gc = FuncBasedGettableContainer(getter)
    with pytest.raises(KeyError) as excinfo:
        gc["API_KEY"]
    assert SECRET not in str(excinfo.value)
    assert SECRET not in repr(excinfo.value)
    assert excinfo.value.args[0] == "API_KEY"


def test_getter_exception_keyerror_keeps_cause():
    """The upstream exception stays reachable -- just not embedded in the message."""

    def getter(k):
        raise RuntimeError(f"authentication failed for token {SECRET}")

    gc = FuncBasedGettableContainer(getter)
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
