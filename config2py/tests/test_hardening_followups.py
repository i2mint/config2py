"""Follow-ups to the symlink hardening (https://github.com/i2mint/config2py/issues/51):
the folders above a store, symlinked sub-folders of a key, ``sync_store.FileStore``,
and the folder of an ini file."""

import os
import sys
import warnings

import pytest

from config2py import InsecureConfigFolderWarning, get_configs_local_store
from config2py.sync_store import FileStore, JsonStore
from config2py.tools import SecureTextFiles
from config2py.util import secure_open, unsafe_folder_reason

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


# ancestors ------------------------------------------------------------------------


@posix_only
def test_a_private_folder_in_a_world_writable_parent_is_flagged(tmp_path):
    parent = tmp_path / "shared"
    parent.mkdir()
    parent.chmod(0o777)
    child = parent / "store"
    child.mkdir(mode=0o700)
    reason = unsafe_folder_reason(child)
    assert reason and str(parent) in reason and "writable" in reason
    assert unsafe_folder_reason(child, check_ancestors=False) is None
    with pytest.warns(InsecureConfigFolderWarning, match="under"):
        SecureTextFiles(str(child))
    with pytest.raises(PermissionError):
        SecureTextFiles(str(child), on_unsafe_folder="raise")
    SecureTextFiles(str(child), on_unsafe_folder="ignore")


@posix_only
@pytest.mark.skipif(
    not hasattr(os, "geteuid") or os.geteuid() != 0, reason="needs root to chown"
)
def test_an_ancestor_owned_by_another_user_is_flagged_unless_across_a_mount(
    tmp_path, monkeypatch
):
    """A host user's folder bind-mounted into a container, seen by root (#56)."""
    from config2py import util

    parent = tmp_path / "hostdir"
    parent.mkdir()
    parent.chmod(0o755)
    os.chown(parent, 65534, -1)
    child = parent / "store"
    child.mkdir(mode=0o700)
    assert "owned by another user" in unsafe_folder_reason(child)  # same filesystem

    real_stat = os.stat

    def stat_with_parent_on_another_device(path, *args, **kwargs):
        st = real_stat(path, *args, **kwargs)
        if os.fspath(path) == str(parent):
            fields = list(st)
            fields[2] = st.st_dev + 1  # st_dev
            return os.stat_result(fields)
        return st

    monkeypatch.setattr(util.os, "stat", stat_with_parent_on_another_device)
    assert unsafe_folder_reason(child) is None
    parent.chmod(0o777)  # ...but still flagged if others could write there
    assert "writable" in unsafe_folder_reason(child)


@posix_only
def test_a_sticky_parent_is_fine(tmp_path):
    parent = tmp_path / "tmpish"
    parent.mkdir()
    parent.chmod(0o1777)
    child = parent / "store"
    child.mkdir(mode=0o700)
    assert unsafe_folder_reason(child) is None


@posix_only
def test_a_deep_ancestor_is_flagged_and_symlinks_are_resolved(tmp_path):
    top = tmp_path / "top"
    (top / "a" / "b").mkdir(parents=True)
    store = top / "a" / "b" / "store"
    store.mkdir(mode=0o700)
    for d in (top, top / "a", top / "a" / "b"):
        d.chmod(0o755)
    top.chmod(0o777)
    link = tmp_path / "link"
    link.symlink_to(store)
    assert "top" in unsafe_folder_reason(link)  # found through the symlink


# sub-folders of a key -----------------------------------------------------------------


@posix_only
def test_a_symlinked_subfolder_of_a_key_is_refused_when_not_following(
    private_dir, tmp_path
):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (private_dir / "sub").symlink_to(elsewhere)
    store = SecureTextFiles(str(private_dir), follow_symlinks=False)
    with pytest.raises(KeyError):
        store["sub/KEY"] = "sk-secret"
    assert not (elsewhere / "KEY").exists()
    followed = SecureTextFiles(str(private_dir))  # the default is unchanged
    followed["sub/KEY"] = "sk-secret"
    assert (elsewhere / "KEY").read_text() == "sk-secret"


@posix_only
def test_a_real_subfolder_still_works_when_not_following(private_dir):
    (private_dir / "sub" / "deeper").mkdir(parents=True)
    store = SecureTextFiles(str(private_dir), follow_symlinks=False)
    store["sub/deeper/KEY"] = "v"
    assert store["sub/deeper/KEY"] == "v"
    assert (
        oct((private_dir / "sub" / "deeper" / "KEY").stat().st_mode & 0o777) == "0o600"
    )


@posix_only
def test_a_symlinked_root_is_the_users_choice(private_dir, tmp_path):
    link = tmp_path / "rootlink"
    link.symlink_to(private_dir)
    store = SecureTextFiles(str(link), follow_symlinks=False)
    store["KEY"] = "v"
    assert (private_dir / "KEY").read_text() == "v"


def test_secure_open_beneath_rejects_a_path_outside(tmp_path):
    with pytest.raises(ValueError):
        secure_open(
            tmp_path / "a", "w", follow_symlinks=False, beneath=tmp_path / "other"
        )


# sync_store.FileStore -----------------------------------------------------------------


@posix_only
@pytest.mark.parametrize("make", [FileStore, JsonStore])
def test_file_store_refuses_a_symlink_when_not_following(tmp_path, victim, make):
    path = tmp_path / "config.json"
    path.symlink_to(victim)
    victim.write_text("{}")
    store = make(path, follow_symlinks=False)
    with pytest.raises(OSError):
        store["k"] = "v"
    assert victim.read_text() == "{}"


@posix_only
def test_file_store_follows_symlinks_by_default_and_refuses_hardlinks(tmp_path, victim):
    victim.write_text("{}")
    link = tmp_path / "config.json"
    link.symlink_to(victim)
    JsonStore(link)["k"] = "v"
    assert '"k"' in victim.read_text()
    other = tmp_path / "other.json"
    other.write_text('{"keep": 1}')
    hard = tmp_path / "hard.json"
    os.link(other, hard)
    with pytest.raises(OSError):
        JsonStore(hard, follow_symlinks=False)["k"] = "v"
    assert other.read_text() == '{"keep": 1}'


# ini files ------------------------------------------------------------------------


@posix_only
def test_an_ini_file_in_an_unsafe_folder_warns(tmp_path):
    shared = tmp_path / "shared"
    shared.mkdir()
    shared.chmod(0o777)
    ini = shared / "c.ini"
    ini.write_text("[s]\nk = v\n")
    with pytest.warns(InsecureConfigFolderWarning):
        get_configs_local_store(str(ini))
    with pytest.raises(PermissionError):
        get_configs_local_store(str(ini), on_unsafe_folder="raise")
    get_configs_local_store(str(ini), on_unsafe_folder="ignore")


@posix_only
def test_an_ini_file_in_a_sticky_folder_does_not_warn(tmp_path):
    sticky = tmp_path / "sticky"
    sticky.mkdir()
    sticky.chmod(0o1777)
    ini = sticky / "c.ini"
    ini.write_text("[s]\nk = v\n")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        get_configs_local_store(str(ini))


@posix_only
def test_a_key_ending_in_a_separator_is_refused_when_not_following(private_dir):
    store = SecureTextFiles(str(private_dir), follow_symlinks=False)
    with pytest.raises(KeyError):
        store["new/"] = "v"
    assert not (private_dir / "new").exists()


@posix_only
def test_a_traverse_only_subfolder_works_when_not_following(private_dir):
    sub = private_dir / "sub"
    sub.mkdir()
    store = SecureTextFiles(str(private_dir), follow_symlinks=False)
    store["sub/KEY"] = "v"
    sub.chmod(0o300)  # search + write, no read
    try:
        if os.access(sub, os.R_OK):  # e.g. running as root: can't test this
            pytest.skip("permissions are not enforced for this user")
        store["sub/KEY"] = "w"
    finally:
        sub.chmod(0o700)
    assert (sub / "KEY").read_text() == "w"
