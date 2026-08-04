"""Tests for ensure_seeded and AppData (user data folder management)."""

import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from config2py.util import ensure_seeded, AppData, config2py_env_var


def _redirect_app_root(folder_kind: str, target):
    """Redirect a config2py app-root folder kind at *target* for the test.

    Uses config2py's own ``CONFIG2PY_<KIND>_DIR`` override, which is honoured on
    every platform.  The XDG_* variables must NOT be used here: they are a POSIX
    standard and are ignored on Windows, so tests keyed on them silently write
    into the real user profile instead of the temp dir.
    """
    env_var = getattr(config2py_env_var, folder_kind)
    return patch.dict(os.environ, {env_var: str(target)})


def _same_path(a, b) -> bool:
    """Compare two paths by identity-on-disk, not by their string spelling.

    ``resolve()`` on both sides normalises the differences that make naive
    string comparison fail per-platform: macOS ``/var`` -> ``/private/var``
    symlinks, and Windows 8.3 short names (``RUNNER~1`` -> ``runneradmin``).
    """
    return Path(a).resolve() == Path(b).resolve()


# ---------------------------------------------------------------------------
# Helpers — mock importlib.resources for isolated testing
# ---------------------------------------------------------------------------


def _mock_importlib_files(seed_store: dict):
    """Return a mock for importlib.resources.files that reads from *seed_store*.

    *seed_store* maps ``(subpackage, filename)`` to ``bytes`` content.
    """

    def fake_files(package_path: str):
        # Extract subpackage from e.g. "mypkg._seed_data.resources"
        parts = package_path.split(".")
        subpkg = parts[-1]  # "resources" or "config"

        class FakeTraversable:
            def __truediv__(self, filename):
                key = (subpkg, filename)
                if key not in seed_store:
                    raise FileNotFoundError(
                        f"Seed file not found: {package_path}/{filename}"
                    )
                mock_ref = MagicMock()
                mock_ref.read_bytes.return_value = seed_store[key]
                return mock_ref

        return FakeTraversable()

    return fake_files


SEED_STORE = {
    ("resources", "hello.txt"): b"hello world\nline two\n",
    ("resources", "data.json"): json.dumps({"key": "value"}).encode(),
    ("config", "defaults.json"): json.dumps({"tempo": 120}).encode(),
}


@pytest.fixture
def mock_seeds():
    """Patch importlib.resources.files with a mock seed store."""
    with patch(
        "config2py.util.importlib.resources.files",
        side_effect=_mock_importlib_files(SEED_STORE),
    ) as m:
        yield m


# We need to ensure the patch target exists. ensure_seeded does
# `from importlib.resources import files` locally, so we patch
# at the importlib.resources level.
@pytest.fixture
def mock_seeds_for_ensure():
    """Patch importlib.resources.files for ensure_seeded's local import."""
    with patch(
        "importlib.resources.files",
        side_effect=_mock_importlib_files(SEED_STORE),
    ):
        yield


# =============================================================================
# ensure_seeded
# =============================================================================


class TestEnsureSeeded:

    def test_creates_file_when_missing(self, tmp_path, mock_seeds_for_ensure):
        target = tmp_path / "resources" / "hello.txt"
        result = ensure_seeded(target, "mypkg", "resources", "hello.txt")
        assert result == target
        assert target.exists()
        assert target.read_bytes() == b"hello world\nline two\n"

    def test_preserves_existing_file(self, tmp_path, mock_seeds_for_ensure):
        target = tmp_path / "hello.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("user content")

        result = ensure_seeded(target, "mypkg", "resources", "hello.txt")
        assert result == target
        assert target.read_text() == "user content"

    def test_creates_parent_dirs(self, tmp_path, mock_seeds_for_ensure):
        target = tmp_path / "deep" / "nested" / "dir" / "hello.txt"
        ensure_seeded(target, "mypkg", "resources", "hello.txt")
        assert target.exists()

    def test_missing_seed_raises(self, tmp_path, mock_seeds_for_ensure):
        target = tmp_path / "nope.txt"
        with pytest.raises(FileNotFoundError):
            ensure_seeded(target, "mypkg", "resources", "nope.txt")

    def test_returns_path_object(self, tmp_path, mock_seeds_for_ensure):
        target = tmp_path / "hello.txt"
        result = ensure_seeded(str(target), "mypkg", "resources", "hello.txt")
        assert isinstance(result, Path)

    def test_custom_seed_data_dir(self, tmp_path):
        """Ensure the seed_data_dir parameter is used in the package path."""
        calls = []

        def fake_files(pkg_path):
            calls.append(pkg_path)
            mock = MagicMock()
            ref = MagicMock()
            ref.read_bytes.return_value = b"data"
            mock.__truediv__ = lambda self, name: ref
            return mock

        target = tmp_path / "file.txt"
        with patch("importlib.resources.files", side_effect=fake_files):
            ensure_seeded(
                target,
                "mypkg",
                "resources",
                "file.txt",
                seed_data_dir="my_seeds",
            )
        assert calls[0] == "mypkg.my_seeds.resources"


# =============================================================================
# AppData
# =============================================================================


class TestAppData:

    def test_defaults_package_name_to_app_name(self):
        app = AppData("myapp")
        assert app.app_name == "myapp"
        assert app.package_name == "myapp"

    def test_custom_package_name(self):
        app = AppData("my-app", package_name="my_app")
        assert app.app_name == "my-app"
        assert app.package_name == "my_app"

    def test_app_folder_creates_directory(self, tmp_path):
        with _redirect_app_root("data", tmp_path):
            app = AppData("testapp")
            folder = app.app_folder(folder_kind="data")
            assert folder.is_dir()
            assert folder.name == "testapp"
            assert _same_path(folder, tmp_path / "testapp")

    def test_app_folder_config(self, tmp_path):
        with _redirect_app_root("config", tmp_path):
            app = AppData("testapp")
            folder = app.app_folder(folder_kind="config")
            assert folder.is_dir()
            assert _same_path(folder, tmp_path / "testapp")

    def test_get_resource_seeds_when_missing(self, tmp_path):
        with _redirect_app_root("data", tmp_path):
            with patch(
                "importlib.resources.files",
                side_effect=_mock_importlib_files(SEED_STORE),
            ):
                app = AppData("testapp")
                path = app.get_resource("hello.txt")
                assert path.exists()
                assert path.read_bytes() == b"hello world\nline two\n"
                assert _same_path(
                    path, tmp_path / "testapp" / "resources" / "hello.txt"
                )

    def test_get_resource_preserves_user_edits(self, tmp_path):
        with _redirect_app_root("data", tmp_path):
            with patch(
                "importlib.resources.files",
                side_effect=_mock_importlib_files(SEED_STORE),
            ):
                app = AppData("testapp")
                path = app.get_resource("hello.txt")
                path.write_text("edited by user")

                path2 = app.get_resource("hello.txt")
                assert path2.read_text() == "edited by user"

    def test_get_config_seeds_when_missing(self, tmp_path):
        with _redirect_app_root("config", tmp_path):
            with patch(
                "importlib.resources.files",
                side_effect=_mock_importlib_files(SEED_STORE),
            ):
                app = AppData("testapp")
                path = app.get_config("defaults.json")
                assert path.exists()
                data = json.loads(path.read_text())
                assert data["tempo"] == 120
                assert _same_path(path, tmp_path / "testapp" / "defaults.json")

    def test_get_artifact_dir_creates_subdir(self, tmp_path):
        with _redirect_app_root("data", tmp_path):
            app = AppData("testapp")
            midi_dir = app.get_artifact_dir("midi")
            assert midi_dir.is_dir()
            assert _same_path(midi_dir, tmp_path / "testapp" / "artifacts" / "midi")

    def test_get_artifact_dir_multiple_kinds(self, tmp_path):
        with _redirect_app_root("data", tmp_path):
            app = AppData("testapp")
            for kind in ("midi", "audio", "exports"):
                d = app.get_artifact_dir(kind)
                assert d.is_dir()
                assert d.name == kind
