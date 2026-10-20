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


def _orphan(folder, name, age):
    orphan = folder / f".{name}.deadbeef.tmp"
    orphan.write_bytes(b"x")
    old = os.stat(orphan).st_mtime - age
    os.utime(orphan, (old, old))
    return orphan


def test_stale_temp_leftovers_are_swept_fresh_ones_kept(tmp_path):
    stale, fresh = _orphan(tmp_path, "k", 7200), tmp_path / ".k.cafe0000.tmp"
    fresh.write_bytes(b"x")
    atomic_write_bytes(tmp_path / "k", b"v")
    assert not stale.exists() and fresh.exists()


def test_sync_store_writes_are_atomic_and_sweep_leftovers(tmp_path, monkeypatch):
    from config2py.sync_store import JsonStore

    path = tmp_path / "c.json"
    path.write_text('{"a": 1}')
    stale = _orphan(tmp_path, "c.json", 7200)
    store = JsonStore(path)
    monkeypatch.setattr(os, "replace", lambda *a: (_ for _ in ()).throw(OSError("x")))
    with pytest.raises(OSError):
        store["b"] = 2
    monkeypatch.undo()
    assert path.read_text() == '{"a": 1}'  # old content intact, not truncated
    store["b"] = 2
    assert JsonStore(path)["b"] == 2
    assert not stale.exists()
    assert sorted(os.listdir(tmp_path)) == ["c.json"]


def test_sweep_leaves_lookalike_files_alone(tmp_path):
    keep = _orphan(tmp_path, "k.notes", 7200)  # ".k.notes.deadbeef.tmp" is another name's
    other = tmp_path / ".k.mine.tmp"
    other.write_bytes(b"x")
    os.utime(other, (1, 1))
    atomic_write_bytes(tmp_path / "k", b"v")
    assert keep.exists() and other.exists()
