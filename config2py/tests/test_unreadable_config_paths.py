"""An unreadable file or a folder given as a config source is told apart from a missing one.

See https://github.com/i2mint/config2py/issues/43. ``ConfigReader`` used to read a file
it was not allowed to open as silently empty (``configparser`` swallows the ``OSError``).
Running as root, ``os.access`` always says yes, so those cases are also simulated.
"""

import os
import sys
import warnings

import pytest

from config2py import ConfigReader, extract_exports
from config2py.errors import MissingConfigFileWarning


@pytest.fixture
def ini_file(tmp_path):
    path = tmp_path / "config.ini"
    path.write_text("[section]\nkey = value\n")
    return path


@pytest.fixture
def pretend_unreadable(monkeypatch):
    """Make ``os.access(path, R_OK)`` say no for ``path`` (works as root too)."""

    def _pretend(path):
        real_access = os.access
        target = os.fspath(path)

        def access(p, mode, *args, **kwargs):
            if os.fspath(p) == target and mode == os.R_OK:
                return False
            return real_access(p, mode, *args, **kwargs)

        monkeypatch.setattr(os, "access", access)

    return _pretend


def test_config_reader_warns_on_an_unreadable_file(ini_file, pretend_unreadable):
    pretend_unreadable(ini_file)
    with pytest.warns(MissingConfigFileWarning, match="not readable") as record:
        ConfigReader(ini_file)
    assert record[0].filename == __file__  # points at the caller's line


def test_config_reader_can_raise_or_ignore_an_unreadable_file(
    ini_file, pretend_unreadable
):
    pretend_unreadable(ini_file)
    with pytest.raises(PermissionError, match="not readable"):
        ConfigReader(str(ini_file), on_missing="raise")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        ConfigReader(ini_file, on_missing="ignore")


@pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="needs a non-root POSIX user for chmod to deny reads",
)
def test_config_reader_really_unreadable_file(ini_file):
    ini_file.chmod(0)
    try:
        with pytest.warns(MissingConfigFileWarning, match="not readable"):
            reader = ConfigReader(ini_file)
        assert list(reader) == ["DEFAULT"]  # still reads as empty, as before
    finally:
        ini_file.chmod(0o600)


def test_config_reader_directory_is_called_a_directory(tmp_path):
    with pytest.warns(MissingConfigFileWarning, match="is a directory"):
        ConfigReader(tmp_path)
    with pytest.raises(IsADirectoryError, match="is a directory"):
        ConfigReader(tmp_path, on_missing="raise")


def test_extract_exports_directory_is_called_a_directory(tmp_path):
    with pytest.warns(MissingConfigFileWarning, match="is a directory"):
        assert extract_exports(str(tmp_path)) == {}


def test_a_readable_file_still_does_not_warn(ini_file):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        reader = ConfigReader(ini_file)
    assert dict(reader["section"]) == {"key": "value"}

