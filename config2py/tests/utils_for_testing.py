"""Utils for testing config2py functionality."""

from functools import partial


def user_input_patch(monkeypatch, user_input_string: str):
    """Patch both prompt functions ``ask_user_for_input`` can dispatch to.

    Which one is actually called depends on ``mask_input`` (currently defaults to
    ``DFLT_MASKING_INPUT = False``, i.e. ``input`` -- but see the still-open
    i2mint/config2py#13, which proposes flipping that default), so tests that don't
    care about masking specifically should patch both rather than assume one.
    """
    monkeypatch.setattr("builtins.input", lambda _: user_input_string)
    monkeypatch.setattr("getpass.getpass", lambda _: user_input_string)
