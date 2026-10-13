"""Symlink and folder-ownership hardening for user-supplied folders.

See https://github.com/i2mint/config2py/issues/45: ``follow_symlinks=False`` refuses to
write through a symlink planted at a value file's path, and a store warns once about a
root folder that is owned by another user or writable by its group or by others.
"""

import os
import sys
import warnings

import pytest

from config2py import (
    ConfigStore,
    InsecureConfigFolderWarning,
    get_configs_local_store,
)
from config2py.tools import SecureTextFiles
from config2py.util import (
    check_folder_is_private,
    secure_open,
    unsafe_folder_reason,
)

posix_only = pytest.mark.skipif(sys.platform == "win32", reason="POSIX modes/symlinks")


@pytest.fixture
def private_dir(tmp_path):
    d = tmp_path / "store"
    d.mkdir(mode=0o700)
    d.chmod(0o700)
    return d


@pytest.fixture
def victim(tmp_path):
    path = tmp_path / "victim.txt"
    path.write_text("precious")
    return path


# secure_open ----------------------------------------------------------------------


@posix_only
def test_secure_open_follows_symlinks_by_default(tmp_path, victim):
    link = tmp_path / "link"
    link.symlink_to(victim)
    with secure_open(link, "w") as f:
        f.write("new")
    assert victim.read_text() == "new"


@posix_only
def test_secure_open_can_refuse_symlinks(tmp_path, victim):
    link = tmp_path / "link"
    link.symlink_to(victim)
    with pytest.raises(OSError):
        secure_open(link, "w", follow_symlinks=False)
    assert victim.read_text() == "precious"
    plain = tmp_path / "plain"
    with secure_open(plain, "w", follow_symlinks=False) as f:  # plain files still work
        f.write("x")
    assert plain.read_text() == "x"


# SecureTextFiles / ConfigStore ------------------------------------------------------


@posix_only
def test_secure_text_files_refuses_a_planted_symlink(private_dir, victim):
    (private_dir / "API_KEY").symlink_to(victim)
    store = SecureTextFiles(str(private_dir), follow_symlinks=False)
    with pytest.raises(KeyError):
        store["API_KEY"] = "sk-secret"
    assert victim.read_text() == "precious"
    store["OTHER"] = "fine"
    assert store["OTHER"] == "fine"


@posix_only
def test_secure_text_files_default_still_follows(private_dir, victim):
    (private_dir / "API_KEY").symlink_to(victim)
    SecureTextFiles(str(private_dir))["API_KEY"] = "sk-secret"
    assert victim.read_text() == "sk-secret"


@posix_only
def test_config_store_refuses_a_symlink(tmp_path):
    victim = tmp_path / "victim.ini"
    victim.write_text("[precious]\n")
    link = tmp_path / "config.ini"
    link.symlink_to(victim)
    store = ConfigStore(str(link), follow_symlinks=False)
    with pytest.raises(OSError):
        store["section"] = {"key": "value"}
    assert victim.read_text() == "[precious]\n"


@posix_only
def test_get_configs_local_store_passes_the_options_through(private_dir, victim):
    (private_dir / "K").symlink_to(victim)
    store = get_configs_local_store(str(private_dir) + os.sep, follow_symlinks=False)
    with pytest.raises(KeyError):
        store["K"] = "v"


# folder check ---------------------------------------------------------------------


@posix_only
def test_a_private_folder_does_not_warn(private_dir):
    assert unsafe_folder_reason(private_dir) is None
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        SecureTextFiles(str(private_dir))


@posix_only
@pytest.mark.parametrize("mode", [0o770, 0o707, 0o777])
def test_a_writable_by_others_folder_warns_once(tmp_path, mode):
    d = tmp_path / f"shared{mode:o}"
    d.mkdir()
    d.chmod(mode)
    with pytest.warns(InsecureConfigFolderWarning, match="writable by") as record:
        SecureTextFiles(str(d))
    assert record[0].filename == __file__  # points at the caller
    with warnings.catch_warnings():  # the same folder doesn't warn again
        warnings.simplefilter("error")
        SecureTextFiles(str(d))


@posix_only
def test_on_unsafe_folder_raise_and_ignore(tmp_path):
    d = tmp_path / "open"
    d.mkdir()
    d.chmod(0o777)
    with pytest.raises(PermissionError, match="writable by"):
        SecureTextFiles(str(d), on_unsafe_folder="raise")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        SecureTextFiles(str(d), on_unsafe_folder="ignore")
    with pytest.raises(ValueError):
        check_folder_is_private(d, on_unsafe="bogus")


@posix_only
def test_a_folder_owned_by_another_user_is_flagged(private_dir, monkeypatch):
    real_euid = os.geteuid()
    monkeypatch.setattr(os, "geteuid", lambda: real_euid + 1)  # we're "someone else"
    if real_euid == 0:  # root owns everything it is allowed to; only test non-root
        assert unsafe_folder_reason(private_dir) is None
    else:
        assert "owned by another user" in unsafe_folder_reason(private_dir)


def test_a_missing_folder_is_not_flagged(tmp_path):
    assert unsafe_folder_reason(tmp_path / "nope") is None
