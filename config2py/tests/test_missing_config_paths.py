"""Typo'd paths don't silently read as empty configs.

See https://github.com/i2mint/config2py/issues/27: ``ConfigReader`` and
``extract_exports`` warn by default (``on_missing="warn"``), can raise or stay quiet,
and keep reading content (strings, bytes, dicts, streams) and existing files as before.
"""

import io
import warnings
from pathlib import Path

import pytest

from config2py import ConfigReader, ConfigStore, extract_exports
from config2py.errors import Config2PyWarning, MissingConfigFileWarning


@pytest.fixture
def ini_file(tmp_path):
    path = tmp_path / "config.ini"
    path.write_text("[section]\nkey = value\n")
    return path


def _no_warnings(func, *args, **kwargs):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        return func(*args, **kwargs)


def test_the_warning_is_a_config2py_user_warning():
    assert issubclass(MissingConfigFileWarning, Config2PyWarning)
    assert issubclass(MissingConfigFileWarning, UserWarning)


# ConfigReader -------------------------------------------------------------------------


@pytest.mark.parametrize("source", ["no/such/file.ini", Path("no/such/file.ini")])
def test_config_reader_warns_on_a_missing_file(source):
    with pytest.warns(MissingConfigFileWarning, match="no/such/file.ini") as record:
        reader = ConfigReader(source)
    assert list(reader) == ["DEFAULT"]  # still reads as empty, as before
    assert record[0].filename == __file__  # points at the caller's line


def test_config_reader_can_raise_or_ignore():
    with pytest.raises(FileNotFoundError, match="no/such/file.ini"):
        ConfigReader("no/such/file.ini", on_missing="raise")
    assert list(_no_warnings(ConfigReader, "no/such/file.ini", on_missing="ignore")) == [
        "DEFAULT"
    ]


def test_config_reader_reports_only_the_missing_files_of_a_list(ini_file):
    with pytest.warns(MissingConfigFileWarning) as record:
        reader = ConfigReader([str(ini_file), "missing.ini"])
    assert [str(w.message).count("missing.ini") for w in record] == [1]
    assert dict(reader["section"]) == {"key": "value"}


def test_config_reader_sources_that_are_not_missing_paths_do_not_warn(ini_file):
    content = ini_file.read_text()
    for source in (
        str(ini_file),
        ini_file,
        content,
        content.encode(),
        {"section": {"key": "value"}},
        io.StringIO(content),
        "",  # blank: empty content, not a path
    ):
        _no_warnings(ConfigReader, source)


def test_config_reader_rejects_an_unknown_on_missing(ini_file):
    with pytest.raises(ValueError, match="on_missing"):
        ConfigReader(str(ini_file), on_missing="explode")


def test_config_store_still_creates_a_new_file(tmp_path):
    """The writable ``ConfigStore`` is unchanged: a new path is a new file."""
    path = tmp_path / "new.ini"
    store = _no_warnings(ConfigStore, str(path))
    store["section"] = {"key": "value"}
    assert dict(ConfigReader(str(path))["section"]) == {"key": "value"}


# extract_exports ----------------------------------------------------------------------


def test_extract_exports_warns_on_a_missing_file():
    with pytest.warns(MissingConfigFileWarning, match="no/such/.env") as record:
        assert extract_exports("no/such/.env") == {}
    assert record[0].filename == __file__


def test_extract_exports_can_raise_or_ignore():
    with pytest.raises(FileNotFoundError, match="no/such/.env"):
        extract_exports("no/such/.env", on_missing="raise")
    assert _no_warnings(extract_exports, "no/such/.env", on_missing="ignore") == {}
    with pytest.raises(ValueError, match="on_missing"):
        extract_exports('export A="1"', on_missing="explode")


def test_extract_exports_content_and_existing_files_do_not_warn(tmp_path):
    env = tmp_path / ".env"
    env.write_text('export A="1"\nexport B="2"\n')
    expected = {"A": "1", "B": "2"}
    assert _no_warnings(extract_exports, str(env)) == expected
    assert _no_warnings(extract_exports, env) == expected  # os.PathLike works too
    assert _no_warnings(extract_exports, env.read_text()) == expected
    assert _no_warnings(extract_exports, 'export A="1"') == {"A": "1"}
    assert _no_warnings(extract_exports, "") == {}
    empty = tmp_path / "empty.env"
    empty.write_text("")
    assert _no_warnings(extract_exports, str(empty)) == {}  # exists, so no warning
