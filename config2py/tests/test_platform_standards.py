"""Cross-platform tests for the app-folder standards table.

``config2py.util.app_folder_standards`` is the single place where config2py
branches on the operating system.  Because it takes the ``os.name`` to resolve
for as an argument, these tests exercise *both* platforms' tables from whatever
platform happens to be running -- Windows behaviour is verified on Linux/macOS
and vice versa.
"""

import os
from typing import get_args

import pytest

from config2py.util import (
    APP_FOLDER_STANDARDS,
    AppFolderKind,
    FolderSpec,
    app_folder_standards,
    config2py_env_var,
    get_app_rootdir,
    system_default_for_app_data_folder,
)

#: The ``os.name`` values config2py distinguishes between.
OS_NAMES = ("nt", "posix")

#: Every folder kind config2py knows about.
FOLDER_KINDS = tuple(APP_FOLDER_STANDARDS)

#: Environment values standing in for a real Windows user profile.
WINDOWS_ENV = {
    "APPDATA": r"C:\Users\someone\AppData\Roaming",
    "LOCALAPPDATA": r"C:\Users\someone\AppData\Local",
    "TEMP": r"C:\Users\someone\AppData\Local\Temp",
}

#: The two platform tables, spelled out exactly as ``get_app_rootdir``'s docstring
#: promises them, as ``{os_name: {folder_kind: (env_var, default_path, subpath)}}``.
#:
#: Every other test here checks *structural* properties -- non-empty, no
#: collisions, right variable family -- which a silently-retargeted default would
#: still satisfy. This is the one place the literals themselves are pinned, so
#: that changing where config2py puts a user's files is necessarily a deliberate,
#: visible edit to both the table and this expectation.
DOCUMENTED_STANDARDS = {
    "posix": {
        "config": ("XDG_CONFIG_HOME", "~/.config", ""),
        "data": ("XDG_DATA_HOME", "~/.local/share", ""),
        "cache": ("XDG_CACHE_HOME", "~/.cache", ""),
        "state": ("XDG_STATE_HOME", "~/.local/state", ""),
        "runtime": ("XDG_RUNTIME_DIR", "/tmp", ""),
    },
    "nt": {
        "config": ("APPDATA", r"~\AppData\Roaming", ""),
        "data": ("LOCALAPPDATA", r"~\AppData\Local", ""),
        "cache": ("LOCALAPPDATA", r"~\AppData\Local", "Temp"),
        "state": ("LOCALAPPDATA", r"~\AppData\Local", ""),
        "runtime": ("TEMP", r"~\AppData\Local\Temp", ""),
    },
}


@pytest.mark.parametrize("os_name", OS_NAMES)
def test_every_kind_is_specified_on_every_platform(os_name):
    """Both platform tables cover exactly the kinds the type allows."""
    standards = app_folder_standards(os_name)
    assert set(standards) == set(get_args(AppFolderKind))


@pytest.mark.parametrize("os_name", OS_NAMES)
def test_tables_match_the_documented_standards(os_name):
    """The tables hold the exact roots the documentation advertises.

    Where a user's config, data, cache, state and runtime files land is public
    API: dependents and end users rely on those paths. Pinning the literals
    means a change of location cannot slip in as a side effect of an unrelated
    edit -- it has to be written down here too.
    """
    expected = {
        kind: FolderSpec(*spec) for kind, spec in DOCUMENTED_STANDARDS[os_name].items()
    }
    assert app_folder_standards(os_name) == expected


@pytest.mark.parametrize("os_name", OS_NAMES)
@pytest.mark.parametrize("folder_kind", FOLDER_KINDS)
def test_defaults_are_nonempty(os_name, folder_kind, monkeypatch):
    """A missing platform env var must still yield a usable root, never ''.

    An empty root silently degrades ``os.path.join(root, app_name)`` into a
    *relative* path, which would scatter app folders into the CWD.
    """
    standards = app_folder_standards(os_name)
    for spec in standards.values():
        monkeypatch.delenv(spec.env_var, raising=False)
    resolved = system_default_for_app_data_folder(folder_kind, standards=standards)
    assert resolved
    assert not resolved.endswith(("/", "\\"))


def test_windows_cache_is_not_the_data_folder(monkeypatch):
    """Regression: on Windows 'cache' must not collide with 'data'/'state'.

    Both are rooted at %LOCALAPPDATA%, so 'cache' has to live in a sub-folder.
    When they collided, clearing an app's cache would delete the user's data.
    """
    standards = app_folder_standards("nt")
    for name, value in WINDOWS_ENV.items():
        monkeypatch.setenv(name, value)
    resolved = {
        kind: system_default_for_app_data_folder(kind, standards=standards)
        for kind in standards
    }
    assert resolved["cache"] != resolved["data"]
    assert resolved["cache"] != resolved["state"]
    # ... and it is the documented %LOCALAPPDATA%\Temp, i.e. *inside* the root
    assert os.path.basename(resolved["cache"]) == "Temp"
    assert os.path.dirname(resolved["cache"]) == resolved["data"]


@pytest.mark.parametrize("os_name", OS_NAMES)
def test_posix_only_xdg_vars_are_absent_from_the_windows_table(os_name):
    """XDG_* is a POSIX standard; the Windows table must not name those vars."""
    standards = app_folder_standards(os_name)
    env_vars = {spec.env_var for spec in standards.values()}
    if os_name == "nt":
        assert not any(v.startswith("XDG_") for v in env_vars)
    else:
        assert all(v.startswith("XDG_") for v in env_vars)


@pytest.mark.parametrize("folder_kind", FOLDER_KINDS)
def test_config2py_override_wins_on_every_platform(folder_kind, tmp_path, monkeypatch):
    """``CONFIG2PY_<KIND>_DIR`` is the platform-neutral override.

    Unlike XDG_*, it is honoured on Windows too -- which is what makes it the
    right knob for tests and for users who need to relocate app folders.
    """
    target = tmp_path / folder_kind
    monkeypatch.setenv(getattr(config2py_env_var, folder_kind), str(target))
    rootdir = get_app_rootdir(folder_kind, ensure_exists=True)
    assert os.path.realpath(rootdir) == os.path.realpath(str(target))
