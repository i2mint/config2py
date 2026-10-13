"""How ``get_configs_local_store`` tells a folder/file path from an app name
(https://github.com/i2mint/config2py/issues/28)."""

import os
from pathlib import Path

import pytest

from config2py import get_configs_local_store
from config2py.tools import SecureTextFiles
from config2py.util import looks_like_path


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """A cwd with a private ``configs`` folder, and app folders redirected to tmp."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    work = tmp_path / "work"
    (work / "configs").mkdir(parents=True)
    (work / "configs").chmod(0o700)
    monkeypatch.chdir(work)
    return work


def test_looks_like_path():
    assert not looks_like_path("configs")
    assert looks_like_path("./configs")
    assert looks_like_path("configs" + os.sep)
    assert looks_like_path(os.path.abspath("configs"))
    assert looks_like_path(Path("configs"))
    if os.path.altsep:  # Windows: "C:/work/configs" is a path too
        assert looks_like_path("C:/work/configs")


def test_a_path_object_is_a_folder(sandbox):
    store = get_configs_local_store(Path("configs"))
    assert isinstance(store, SecureTextFiles)
    store["K"] = "v"
    assert (sandbox / "configs" / "K").read_text() == "v"


def test_an_absolute_path_and_a_dotted_one_are_folders(sandbox):
    for spelling in (str(sandbox / "configs"), "./configs"):
        assert isinstance(get_configs_local_store(spelling), SecureTextFiles)


def test_a_bare_name_is_still_an_app_even_if_such_a_folder_exists(sandbox):
    """Unchanged default: no existing caller's store moves."""
    store = get_configs_local_store("configs")
    store["K"] = "v"
    assert not (sandbox / "configs" / "K").exists()


def test_kind_path_takes_a_bare_name_as_the_folder(sandbox):
    store = get_configs_local_store("configs", kind="path")
    store["K"] = "v"
    assert (sandbox / "configs" / "K").read_text() == "v"


def test_kind_path_on_a_missing_bare_name_does_not_make_an_app_folder(sandbox):
    with pytest.raises(ValueError):
        get_configs_local_store("nowhere", kind="path")


def test_kind_app_takes_a_path_looking_string_as_the_name(sandbox):
    # a bare name that is also an existing ini file in cwd is still an app name
    (sandbox / "cfg.ini").write_text("[a]\nb = 1\n")
    store = get_configs_local_store("cfg.ini", kind="app")
    assert isinstance(store, SecureTextFiles)


def test_kind_is_validated(sandbox):
    with pytest.raises(ValueError, match="kind"):
        get_configs_local_store("configs", kind="folder")
    with pytest.raises(ValueError, match="kind"):
        get_configs_local_store(Path("configs"), kind="app")


def test_a_path_object_to_an_ini_file(sandbox):
    from config2py.s_configparser import ConfigStore

    ini = sandbox / "cfg.ini"
    ini.write_text("[a]\nb = 1\n")
    ini.chmod(0o600)
    assert isinstance(get_configs_local_store(ini, on_unsafe_folder="ignore"), ConfigStore)
