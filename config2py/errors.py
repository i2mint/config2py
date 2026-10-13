"""Error classes for config2py."""


class Config2PyError(Exception):
    """Base class for config2py errors."""


class ConfigNotFound(Config2PyError):
    """Raised when a config file is not found."""


class Config2PyWarning(UserWarning):
    """Warnings issued by config2py (e.g. permissions it could not tighten)."""


class MissingConfigFileWarning(Config2PyWarning):
    """A path given as a config source is not an existing, readable file (it is
    missing, a folder, or unreadable), so it was read as empty
    (see https://github.com/i2mint/config2py/issues/27 and /43)."""


ON_MISSING_OPTIONS = ("warn", "raise", "ignore")


def validate_on_missing(on_missing: str) -> str:
    """Check that ``on_missing`` is one of ``ON_MISSING_OPTIONS`` and return it."""
    if on_missing not in ON_MISSING_OPTIONS:
        raise ValueError(
            f"on_missing must be one of {ON_MISSING_OPTIONS}. Was: {on_missing!r}"
        )
    return on_missing


def unusable_config_file_problem(path):
    """Why ``path`` can't be read as a config file, as ``(error_class, errno, reason)``,
    or ``None`` if it is an existing, readable, non-folder path."""
    import errno
    import os

    if not os.path.exists(path):
        return FileNotFoundError, errno.ENOENT, "No such config file"
    if os.path.isdir(path):
        return IsADirectoryError, errno.EISDIR, "Config file is a directory"
    if not os.access(path, os.R_OK):
        return PermissionError, errno.EACCES, "Config file is not readable"
    return None


def report_missing_config_file(path, *, on_missing: str = "warn", stacklevel: int = 2):
    """Act on a config source ``path`` that is not an existing, readable file.

    The problem is told apart: missing, a directory, or unreadable (permission
    denied). A path with no problem is left alone.

    :param on_missing: ``"warn"`` issues a ``MissingConfigFileWarning``,
        ``"raise"`` raises ``FileNotFoundError`` (``IsADirectoryError`` for a folder,
        ``PermissionError`` for an unreadable file), ``"ignore"`` does nothing.
    :param stacklevel: Passed to ``warnings.warn``, so the warning points at the
        caller's code (``2`` is the caller of this function).
    """
    import os
    import warnings

    validate_on_missing(on_missing)
    if on_missing == "ignore":
        return
    problem = unusable_config_file_problem(path)
    if problem is None:
        return
    error_class, code, reason = problem
    if on_missing == "raise":  # str(error): "[Errno 2] No such config file: 'path'"
        raise error_class(code, reason, os.fspath(path))
    warnings.warn(
        f"{reason}: {os.fspath(path)!r}, so it reads as empty. Pass "
        "on_missing='ignore' if this is expected, or 'raise' to fail.",
        MissingConfigFileWarning,
        stacklevel=stacklevel + 1,
    )
