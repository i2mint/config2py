"""Fixes from the sprint review: a read error must not wipe an ini file, a blank or
relative XDG path must not root configs at the cwd, and an encoding error must not
quote the secret it failed on."""

import errno
import os

import pytest

import config2py.s_configparser as s_configparser
from config2py.s_configparser import ConfigStore
from config2py.tools import SecureTextFiles
from config2py.util import (
    APP_FOLDER_STANDARDS,
    check_folder_is_private,
    system_default_for_app_data_folder,
)


def test_a_read_error_other_than_missing_raises_and_keeps_the_file(
    tmp_path, monkeypatch
):
    ini = tmp_path / "secrets.ini"
    ini.write_text("[keep]\napi_key = SECRET\n")

    def too_many_open_files(*args, **kwargs):
        raise OSError(errno.EMFILE, "Too many open files")

    monkeypatch.setattr(s_configparser, "open", too_many_open_files, raising=False)
    with pytest.raises(OSError):
        ConfigStore(str(ini))
    monkeypatch.undo()
    assert "api_key = SECRET" in ini.read_text()


def test_a_missing_ini_file_is_still_an_empty_store(tmp_path):
    assert ConfigStore(str(tmp_path / "new.ini")).sections() == []


@pytest.mark.parametrize(
    "source",
    ["{tmp}", "{tmp}/file.ini/x.ini", "[s]a=1;" * 60],
    ids=["a folder", "through a file", "a long content string"],
)
def test_a_source_that_is_no_file_is_still_an_empty_store(tmp_path, source):
    (tmp_path / "file.ini").write_text("")
    assert ConfigStore(source.format(tmp=tmp_path)).sections() == []


@pytest.mark.parametrize("value", ["rel/cfg", "./x", "  ", ""])
def test_a_blank_or_relative_xdg_path_counts_as_unset(monkeypatch, value):
    env_var = APP_FOLDER_STANDARDS["config"].env_var
    monkeypatch.delenv(env_var, raising=False)
    default = system_default_for_app_data_folder("config")
    monkeypatch.setenv(env_var, value)
    if value.strip():  # a non-empty value that is ignored says so
        with pytest.warns(UserWarning, match="not an absolute path"):
            assert system_default_for_app_data_folder("config") == default
    else:
        assert system_default_for_app_data_folder("config") == default


def test_an_unencodable_ini_value_is_refused_without_quoting_it(tmp_path):
    ini = tmp_path / "s.ini"
    ini.write_text("[keep]\na = 1\n")
    store = ConfigStore(str(ini))
    with pytest.raises(ValueError) as exc:
        store["s"] = {"k": "sec\udcffret"}
    assert "\udcff" not in str(exc.value)
    assert "a = 1" in ini.read_text()


def test_an_absolute_xdg_path_is_honoured(monkeypatch, tmp_path):
    env_var = APP_FOLDER_STANDARDS["config"].env_var
    monkeypatch.setenv(env_var, str(tmp_path))
    assert system_default_for_app_data_folder("config") == str(tmp_path)


def test_an_unencodable_value_is_refused_without_quoting_it(tmp_path):
    store = SecureTextFiles(str(tmp_path))
    with pytest.raises(KeyError) as exc:
        store["k"] = "sec\udcffret"
    assert "\\udcff" not in str(exc.value) and "\udcff" not in str(exc.value)
    assert "position 3" in str(exc.value)
    assert not os.path.exists(tmp_path / "k")


def test_a_bad_on_unsafe_value_names_its_own_argument(tmp_path):
    with pytest.raises(ValueError, match="on_unsafe must be one of"):
        check_folder_is_private(tmp_path, on_unsafe="sometimes")
