"""Tests for the file/dir permission hardening added for i2mint/config2py#15.

Covers the pieces the fix touches that ``test_app_data.py`` doesn't already exercise
through ``AppData``/``ensure_seeded``: ``secure_makedirs``'s re-tightening behaviour,
the ``create_directories`` alternate (``max_dirs_to_make``) code path, and the two
concrete file-writing call sites (``ConfigStore.persist`` / ``s_configparser.py`` and
``FileStore`` / ``sync_store.py``) that were updated to use ``secure_open``.

All permission assertions are POSIX-only (``os.name == "posix"``): file mode bits are
not meaningful on Windows.
"""

import json
import os
import tempfile

import pytest

from config2py.util import create_directories, secure_makedirs
from config2py.s_configparser import ConfigStore
from config2py.sync_store import FileStore

posix_only = pytest.mark.skipif(os.name != "posix", reason="file mode bits are POSIX-only")


@posix_only
def test_secure_makedirs_retightens_existing_dir(tmp_path):
    """A pre-existing, loosely-permissioned dir must be re-tightened to 0o700."""
    target = tmp_path / "already_here"
    target.mkdir(mode=0o755)
    os.chmod(target, 0o755)  # mkdir's mode is subject to umask; force it to stick
    assert oct(target.stat().st_mode & 0o777) == "0o755"

    secure_makedirs(target)

    assert oct(target.stat().st_mode & 0o777) == "0o700"


@posix_only
def test_create_directories_max_dirs_to_make_branch_is_owner_only(tmp_path):
    """The ``max_dirs_to_make``-bounded branch of create_directories must also be 0o700."""
    target = tmp_path / "a" / "b" / "c"
    assert create_directories(str(target), max_dirs_to_make=5) is True
    for p in (target, target.parent, target.parent.parent):
        assert oct(p.stat().st_mode & 0o777) == "0o700"


@posix_only
def test_config_store_persist_writes_owner_only_file(tmp_path):
    """ConfigStore.persist() (s_configparser.py) must not leave a world-readable file."""
    ini_path = tmp_path / "config_store_test.ini"
    store = ConfigStore(str(ini_path))
    store["a_section"] = {"key": "value"}  # triggers persist()

    assert ini_path.is_file()
    assert oct(ini_path.stat().st_mode & 0o777) == "0o600"


@posix_only
def test_file_store_write_is_owner_only(tmp_path):
    """FileStore (sync_store.py) must not leave a world-readable file after a write."""
    path = tmp_path / "store.json"
    path.write_text('{"key": "value"}')
    os.chmod(path, 0o644)  # start world-readable, like a plain `open(..., "w")` would

    store = FileStore(str(path))
    store["new_key"] = "new_value"  # triggers a write via _secure_open

    with open(path) as f:
        assert json.load(f)["new_key"] == "new_value"
    assert oct(path.stat().st_mode & 0o777) == "0o600"
