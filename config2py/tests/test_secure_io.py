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


@posix_only
def test_configs_store_writes_owner_only_files(tmp_path):
    """#33: values saved through the configs store are 0o600, even in a 0o755 folder."""
    from dol import TextFiles
    from config2py.tools import get_configs_local_store

    folder = tmp_path / "configs"
    folder.mkdir(mode=0o755)
    store = get_configs_local_store(str(folder))
    assert isinstance(store, TextFiles)
    store["API_KEY"] = "sk-demo"
    assert store["API_KEY"] == "sk-demo"
    assert oct((folder / "API_KEY").stat().st_mode & 0o777) == "0o600"
    (folder / "API_KEY").chmod(0o644)  # overwrite re-tightens too
    store["API_KEY"] = "sk-new"
    assert oct((folder / "API_KEY").stat().st_mode & 0o777) == "0o600"


@posix_only
def test_existing_managed_configs_folder_is_retightened(tmp_path, monkeypatch):
    """#33: an older config2py-managed 0o755 configs folder becomes 0o700."""
    from config2py.util import get_configs_folder_for_app

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    path = get_configs_folder_for_app("app33_test")
    os.chmod(path, 0o755)
    assert get_configs_folder_for_app("app33_test") == path
    assert oct(os.stat(path).st_mode & 0o777) == "0o700"


# --------------------------------------------------------------------------------------
# Regressions and gaps from #34 (see https://github.com/i2mint/config2py/issues/35)


def _sandboxed_env(home, **extra):
    """An env whose HOME and XDG folders all point into ``home``, plus ``extra``."""
    env = dict(os.environ, HOME=str(home), **extra)
    for name in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"):
        env.pop(name, None)
    return env


def _run_python(code, env):
    import subprocess
    import sys

    return subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=120,
    )


@posix_only
def test_import_survives_a_folder_it_cannot_chmod(tmp_path):
    """#35.1: using config2py's default configs store must not crash when its folder
    can't be chmod-ed (read-only file system, folder owned by someone else).

    Since #26 the folder is created on first access to the default instances, not by
    ``import config2py``, so the code below accesses ``config_getter``."""
    env = _sandboxed_env(tmp_path)
    first = _run_python("import config2py; config2py.config_getter", env)  # creates it
    assert first.returncode == 0, first.stderr
    configs_dir = tmp_path / ".config" / "config2py" / "configs"
    assert (configs_dir / ".config2py").is_file()
    os.chmod(configs_dir, 0o755)  # an older, looser folder that "needs" re-tightening
    code = (
        "import errno, os\n"
        "def _chmod(*a, **k):\n"
        "    raise OSError(errno.EROFS, 'Read-only file system')\n"
        "os.chmod = _chmod\n"
        "import warnings\n"
        "with warnings.catch_warnings(record=True) as w:\n"
        "    warnings.simplefilter('always')\n"
        "    import config2py\n"
        "    config2py.config_getter\n"
        "print(len(w))\n"
    )
    result = _run_python(code, env)
    assert result.returncode == 0, result.stderr
    assert int(result.stdout.strip()) >= 1  # it warns instead


@posix_only
def test_already_tight_folder_is_not_chmod_ed(tmp_path, monkeypatch):
    """#35.1: no chmod at all when the mode is already right."""
    from config2py.util import get_configs_folder_for_app

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    path = get_configs_folder_for_app("app35_test")
    assert oct(os.stat(path).st_mode & 0o777) == "0o700"

    def _no_chmod(*args, **kwargs):
        raise AssertionError(f"unexpected chmod: {args}")

    monkeypatch.setattr(os, "chmod", _no_chmod)
    assert get_configs_folder_for_app("app35_test") == path


def test_values_are_written_as_utf8_whatever_the_locale(tmp_path):
    """#35.2: values are UTF-8 on disk even under a non-UTF-8 locale (``LC_ALL=C``),
    and a failed write never leaves a truncated (empty) file behind."""
    folder = tmp_path / "configs"
    folder.mkdir()
    (folder / "NAME").write_bytes(b"old")
    code = (
        "import sys\n"
        "from config2py.tools import get_configs_local_store\n"
        f"store = get_configs_local_store({str(folder) + os.sep!r})\n"
        "store['NAME'] = 'caf\\u00e9'\n"
        "assert store['NAME'] == 'caf\\u00e9', store['NAME']\n"
        "try:\n"
        "    store['NAME'] = 'bad \\udc80'\n"  # a lone surrogate: not encodable
        "except KeyError:\n"
        "    pass\n"
        "else:\n"
        "    sys.exit('expected a KeyError')\n"
        "assert store['NAME'] == 'caf\\u00e9', store['NAME']\n"
    )
    env = _sandboxed_env(
        tmp_path, LC_ALL="C", LANG="C", PYTHONUTF8="0", PYTHONCOERCECLOCALE="0"
    )
    result = _run_python(code, env)
    assert result.returncode == 0, result.stderr
    assert (folder / "NAME").read_bytes() == "café".encode("utf-8")


@posix_only
def test_existing_loose_files_in_managed_folder_are_tightened(tmp_path, monkeypatch):
    """#35.3: secrets saved before #34 (0o644) are tightened, not only on overwrite.
    Symlinks are not followed, and unmanaged folders are left alone."""
    from config2py.util import get_configs_folder_for_app

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    path = get_configs_folder_for_app("app35_files")
    secret = os.path.join(path, "API_KEY")
    nested = os.path.join(path, "sub", "TOKEN")
    os.makedirs(os.path.dirname(nested))
    outside = tmp_path / "outside.txt"
    outside.write_text("not ours")
    for p in (secret, nested, outside):
        with open(p, "w") as f:
            f.write("x")
        os.chmod(p, 0o644)
    os.symlink(outside, os.path.join(path, "LINK"))

    get_configs_folder_for_app("app35_files")

    assert oct(os.stat(secret).st_mode & 0o777) == "0o600"
    assert oct(os.stat(nested).st_mode & 0o777) == "0o600"
    assert oct(outside.stat().st_mode & 0o777) == "0o644"  # symlink target untouched

    unmanaged = tmp_path / ".config" / "unmanaged" / "configs"
    unmanaged.mkdir(parents=True)
    loose = unmanaged / "KEY"
    loose.write_text("x")
    loose.chmod(0o644)
    get_configs_folder_for_app("unmanaged")
    assert oct(loose.stat().st_mode & 0o777) == "0o644"


@posix_only
def test_configs_alias_is_the_secure_store(tmp_path):
    """#35.4: the public ``Configs`` alias writes owner-only files too."""
    from config2py.tools import Configs, SecureTextFiles

    assert Configs is SecureTextFiles
    store = Configs(str(tmp_path))
    store["API_KEY"] = "sk-demo"
    assert oct((tmp_path / "API_KEY").stat().st_mode & 0o777) == "0o600"


def test_failed_writes_raise_key_error_like_text_files(tmp_path):
    """#35.5: a failed write raises ``KeyError``, as dol's ``TextFiles`` does."""
    from dol import TextFiles
    from config2py.tools import SecureTextFiles

    for store_cls in (TextFiles, SecureTextFiles):
        folder = tmp_path / store_cls.__name__
        folder.mkdir()
        store = store_cls(str(folder))
        with pytest.raises(KeyError):
            store["missing_dir/KEY"] = "value"  # parent folder doesn't exist
        with pytest.raises(KeyError):
            store["KEY"] = 3  # not a str
    # ...and, unlike TextFiles, it doesn't leave a truncated file behind
    assert not (tmp_path / "SecureTextFiles" / "KEY").exists()


@posix_only
def test_untightenable_files_give_one_warning(tmp_path, monkeypatch):
    """#35 review: files that can't be tightened give one warning, not one each."""
    from config2py.errors import Config2PyWarning
    from config2py.util import get_configs_folder_for_app

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    path = get_configs_folder_for_app("app35_warn")
    for name in ("A", "B", "C"):
        p = os.path.join(path, name)
        with open(p, "w") as f:
            f.write("x")
        os.chmod(p, 0o644)

    def _eperm(*args, **kwargs):
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(os, "fchmod", _eperm)
    with pytest.warns(Config2PyWarning) as record:
        get_configs_folder_for_app("app35_warn")
    assert len(record) == 1
    assert "3 file(s)" in str(record[0].message)
