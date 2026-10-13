"""Tools to read and write configurations from various sources and formats"""

from config2py.s_configparser import ConfigStore, ConfigReader
from config2py.tools import (
    extract_exports,
    get_configs_local_store,
    simple_config_getter,
    Configs,  # user-customized configs store class (default is TextFiles)
)
from config2py.base import get_config, user_gettable, sources_chainmap
from config2py.util import (
    envvar,  # os.environ, but with dict display override to hide secrets
    ask_user_for_input,
    get_app_config_folder,
    get_app_data_folder,
    get_app_folder,
    get_configs_folder_for_app,
    is_repl,
    parse_assignments_from_py_source,
    process_path,
    ensure_seeded,
    AppData,
)
from config2py.sync_store import SyncStore, FileStore, JsonStore, register_extension
from config2py import codecs  # noqa - Make codecs module available

# ``config_getter``, ``local_configs`` and ``configs`` (the user-customized configs
# store instance, ``local_configs`` by default) are built on first access, so that
# ``import config2py`` creates no folder (see https://github.com/i2mint/config2py/issues/26).
_lazy_tools_attrs = ("config_getter", "local_configs", "configs")


def __getattr__(name):
    if name in _lazy_tools_attrs:
        from config2py import tools

        return getattr(tools, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(_lazy_tools_attrs))
