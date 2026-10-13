"""Error classes for config2py."""


class Config2PyError(Exception):
    """Base class for config2py errors."""


class ConfigNotFound(Config2PyError):
    """Raised when a config file is not found."""


class Config2PyWarning(UserWarning):
    """Warnings issued by config2py (e.g. permissions it could not tighten)."""


class MissingConfigFileWarning(Config2PyWarning):
    """A path given as a config source is not an existing file, so it was read as
    empty (see https://github.com/i2mint/config2py/issues/27)."""


ON_MISSING_OPTIONS = ("warn", "raise", "ignore")


def validate_on_missing(on_missing: str) -> str:
    """Check that ``on_missing`` is one of ``ON_MISSING_OPTIONS`` and return it."""
    if on_missing not in ON_MISSING_OPTIONS:
        raise ValueError(
            f"on_missing must be one of {ON_MISSING_OPTIONS}. Was: {on_missing!r}"
        )
    return on_missing


def report_missing_config_file(path, *, on_missing: str = "warn", stacklevel: int = 2):
    """Act on a config source ``path`` that is not an existing file.

    :param on_missing: ``"warn"`` issues a ``MissingConfigFileWarning``,
        ``"raise"`` raises ``FileNotFoundError``, ``"ignore"`` does nothing.
    :param stacklevel: Passed to ``warnings.warn``, so the warning points at the
        caller's code (``2`` is the caller of this function).
    """
    import errno
    import os
    import warnings

    validate_on_missing(on_missing)
    if on_missing == "ignore":
        return
    msg = (
        f"No such config file: {os.fspath(path)!r}, so it reads as empty. Pass "
        "on_missing='ignore' if an absent file is expected, or 'raise' to fail."
    )
    if on_missing == "raise":  # str(error): "[Errno 2] No such config file: 'path'"
        raise FileNotFoundError(errno.ENOENT, "No such config file", os.fspath(path))
    warnings.warn(msg, MissingConfigFileWarning, stacklevel=stacklevel + 1)
