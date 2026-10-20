"""Secret and ini writes are atomic: a failed write keeps the old value (#52)."""

import os

import pytest

from config2py.tools import SecureTextFiles
from config2py.util import atomic_write_bytes


def test_failed_write_keeps_old_content_and_leaves_no_temp(tmp_path, monkeypatch):
    target = tmp_path / "k"
    atomic_write_bytes(target, b"old")

    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        atomic_write_bytes(target, b"new")
    assert target.read_bytes() == b"old"
    assert os.listdir(tmp_path) == ["k"]


def test_store_write_failure_keeps_old_value(tmp_path, monkeypatch):
    store = SecureTextFiles(str(tmp_path))
    store["KEY"] = "old"
    monkeypatch.setattr(os, "fsync", lambda fd: (_ for _ in ()).throw(OSError("x")))
    with pytest.raises(KeyError):
        store["KEY"] = "new"
    monkeypatch.undo()
    assert store["KEY"] == "old"
    assert os.listdir(tmp_path) == ["KEY"]


@pytest.mark.skipif(os.name != "posix", reason="POSIX modes")
def test_result_is_owner_only(tmp_path):
    target = tmp_path / "k"
    atomic_write_bytes(target, b"x")
    assert target.stat().st_mode & 0o777 == 0o600


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="needs symlinks")
def test_symlink_is_never_replaced_when_not_following(tmp_path):
    real = tmp_path / "real"
    real.write_text("keep")
    link = tmp_path / "link"
    link.symlink_to(real)
    with pytest.raises(OSError):
        atomic_write_bytes(link, b"new", follow_symlinks=False)
    assert link.is_symlink() and real.read_text() == "keep"
    atomic_write_bytes(link, b"new")  # following: the target is replaced
    assert link.is_symlink() and real.read_bytes() == b"new"


def test_orphan_temp_file_is_not_listed_as_a_key(tmp_path):
    store = SecureTextFiles(str(tmp_path))
    store["A"] = "1"
    (tmp_path / ".A.deadbeef.tmp").write_text("x")
    assert list(store) == ["A"]
