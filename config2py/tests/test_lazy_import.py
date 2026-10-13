"""``import config2py`` writes nothing to disk; the default instances are lazy.

See https://github.com/i2mint/config2py/issues/26. Each test runs Python in a
subprocess whose HOME (and XDG/CONFIG2PY folder variables) point into a temp dir, so
the first import really is a first import, and the user's real folders are untouched.
"""

import os
import subprocess
import sys

import pytest

posix_only = pytest.mark.skipif(os.name != "posix", reason="HOME-based folders")


def _sandboxed_env(home):
    env = {
        k: v
        for k, v in os.environ.items()
        if not (k.startswith("XDG_") or k.startswith("CONFIG2PY_"))
    }
    env["HOME"] = str(home)
    return env


def _run_python(code, home):
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=_sandboxed_env(home),
        cwd=str(home),
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def _files_under(root):
    return sorted(
        os.path.relpath(os.path.join(dirpath, name), root)
        for dirpath, dirnames, filenames in os.walk(root)
        for name in dirnames + filenames
    )


@posix_only
def test_importing_config2py_creates_nothing(tmp_path):
    _run_python(
        "import config2py\n"
        "from config2py import codecs, s_configparser, sync_store, tools, util, base\n"
        "from config2py import ConfigStore, get_config, simple_config_getter, Configs\n"
        "import inspect, pydoc\n"
        "for module in (config2py, tools, util):\n"
        "    inspect.getmembers(module)  # as pydoc and doctest collection do\n"
        "pydoc.render_doc(config2py)\n",
        tmp_path,
    )
    assert _files_under(tmp_path) == []


@posix_only
def test_first_access_creates_the_default_configs_folder(tmp_path):
    out = _run_python(
        "import config2py\n"
        "from config2py import config_getter\n"
        "print(config_getter.configs.rootdir)\n",
        tmp_path,
    )
    configs_dir = tmp_path / ".config" / "config2py" / "configs"
    assert (configs_dir / ".config2py").is_file()
    assert oct(configs_dir.stat().st_mode & 0o777) == "0o700"
    assert out.strip().rstrip(os.sep) == str(configs_dir)


@posix_only
def test_lazy_instances_keep_their_identities(tmp_path):
    out = _run_python(
        "import config2py, config2py.tools as tools\n"
        "from config2py import config_getter, local_configs, configs\n"
        "from config2py.tools import SecureTextFiles\n"
        "checks = [\n"
        "    config_getter is config2py.config_getter is tools.config_getter,\n"
        "    local_configs is config2py.local_configs is tools.local_configs,\n"
        "    configs is local_configs,  # the backwards compatibility alias\n"
        "    config_getter.configs is not local_configs,  # as before #26\n"
        "    isinstance(local_configs, SecureTextFiles),\n"
        "    'config_getter' in vars(tools),  # cached as an ordinary attribute\n"
        "]\n"
        "print(checks)\n",
        tmp_path,
    )
    assert out.strip() == str([True] * 6)


@posix_only
def test_star_import_still_exports_the_lazy_instances(tmp_path):
    out = _run_python(
        "from config2py import *\n"
        "print(configs is local_configs, callable(config_getter))\n",
        tmp_path,
    )
    assert out.strip() == "True True"


@posix_only
@pytest.mark.parametrize("module", ["config2py.util", "config2py.tools"])
def test_reading_dflt_config_folder_creates_it(tmp_path, module):
    """As importing did before #26, so code that lists or writes into it works."""
    _run_python(
        "import os\n"
        f"from {module} import DFLT_CONFIG_FOLDER\n"
        "assert os.path.isdir(DFLT_CONFIG_FOLDER), DFLT_CONFIG_FOLDER\n"
        "with open(os.path.join(DFLT_CONFIG_FOLDER, 'KEY'), 'w') as f:\n"
        "    f.write('v')\n",
        tmp_path,
    )


@posix_only
def test_patching_local_configs_does_not_leak_into_configs(tmp_path):
    out = _run_python(
        "from unittest import mock\n"
        "import config2py\n"
        "with mock.patch('config2py.tools.local_configs', {'MOCK': 1}):\n"
        "    pass\n"
        "print(config2py.configs is config2py.local_configs, "
        "'MOCK' in config2py.configs)\n",
        tmp_path,
    )
    assert out.strip() == "True False"


@posix_only
def test_default_store_works_when_its_folder_is_missing(tmp_path):
    """The default store is created on use, also via explicit calls."""
    _run_python(
        "from config2py import get_configs_local_store, simple_config_getter\n"
        "from config2py.util import DFLT_CONFIG_FOLDER\n"
        "store = get_configs_local_store()\n"
        "store['KEY'] = 'value'\n"
        "assert get_configs_local_store(DFLT_CONFIG_FOLDER)['KEY'] == 'value'\n"
        "get = simple_config_getter(ask_user_if_key_not_found=False)\n"
        "assert get('KEY') == 'value'\n",
        tmp_path,
    )


@posix_only
def test_other_spellings_of_the_default_folder_create_it(tmp_path):
    _run_python(
        "import os, shutil\n"
        "from dol import TextFiles\n"
        "from config2py import get_configs_local_store, simple_config_getter\n"
        "from config2py.util import _DFLT_CONFIGS_FOLDER_PATH as path\n"
        "for spelling in (path + os.sep, os.path.join(path, '.')):\n"
        "    shutil.rmtree(path, ignore_errors=True)\n"
        "    get_configs_local_store(spelling)['KEY'] = 'v'\n"
        "shutil.rmtree(path, ignore_errors=True)\n"
        "# a custom store factory also gets an existing folder\n"
        "get = simple_config_getter(config_store_factory=TextFiles,\n"
        "                           ask_user_if_key_not_found=False)\n"
        "get.configs['KEY'] = 'v'\n",
        tmp_path,
    )


def test_unknown_attributes_still_raise_attribute_error():
    import config2py
    import config2py.tools

    for module in (config2py, config2py.tools):
        with pytest.raises(AttributeError):
            module.no_such_attribute
        assert not hasattr(module, "no_such_attribute")


@posix_only
def test_configs_folder_path_without_creating_it(tmp_path, monkeypatch):
    from config2py.util import get_configs_folder_for_app

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("CONFIG2PY_CONFIG_DIR", raising=False)
    path = get_configs_folder_for_app("app26_test", ensure_exists=False)
    assert path.startswith(str(tmp_path))
    assert _files_under(tmp_path) == []


@posix_only
def test_app_names_work_without_a_current_directory(tmp_path):
    """Recognizing the default folder must not need ``os.getcwd()``."""
    _run_python(
        "import os, tempfile\n"
        "from config2py import get_configs_local_store, simple_config_getter\n"
        "from config2py.util import is_default_configs_folder\n"
        "gone = tempfile.mkdtemp(dir=os.environ['HOME'])\n"
        "os.chdir(gone); os.rmdir(gone)\n"
        "get_configs_local_store('app26_test')\n"
        "simple_config_getter('app26_test', ask_user_if_key_not_found=False)\n"
        "assert not is_default_configs_folder('configs')\n"
        "assert not is_default_configs_folder(None)\n",
        tmp_path,
    )
