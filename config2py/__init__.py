"""Tools to read and write configurations from various sources and formats"""

from importlib import import_module as _import_module
from typing import TYPE_CHECKING as _TYPE_CHECKING

# The public names are resolved on first access (PEP 562), so that ``import config2py``,
# or importing one of its submodules such as ``config2py.secret_text``, does not pull in
# ``dol`` and every other module (see https://github.com/i2mint/config2py/issues/69).
# ``config_getter``, ``local_configs`` and ``configs`` (the user-customized configs
# store instance, ``local_configs`` by default) are built on first access too, so that
# ``import config2py`` creates no folder (see https://github.com/i2mint/config2py/issues/26).
_names_by_module = {
    "s_configparser": ("ConfigStore", "ConfigReader"),
    "errors": (
        "Config2PyError",
        "Config2PyWarning",
        "ConfigNotFound",
        "InsecureConfigFolderWarning",
        "MissingConfigFileWarning",
    ),
    "tools": (
        "extract_exports",
        "get_configs_local_store",
        "simple_config_getter",
        "Configs",  # user-customized configs store class (default is TextFiles)
        "config_getter",
        "local_configs",
        "configs",
    ),
    "base": ("get_config", "user_gettable", "sources_chainmap"),
    "util": (
        "envvar",  # os.environ, but with dict display override to hide secrets
        "ask_user_for_input",
        "get_app_config_folder",
        "get_app_data_folder",
        "get_app_folder",
        "get_configs_folder_for_app",
        "is_repl",
        "parse_assignments_from_py_source",
        "process_path",
        "ensure_seeded",
        "AppData",
    ),
    "secret_text": ("has_secret", "SecretRule", "SECRET_RULES", "SECRET_TEXT_PATTERNS"),
    "sync_store": ("SyncStore", "FileStore", "JsonStore", "register_extension"),
}
_default_instances = ("config_getter", "local_configs", "configs")
_module_of = {
    name: module for module, names in _names_by_module.items() for name in names
}
# Submodules a star import (or ``config2py.codecs``) reaches by attribute.
_submodules = (*_names_by_module, "codecs")


def __getattr__(name):
    if name in _module_of:
        value = getattr(_import_module(f"config2py.{_module_of[name]}"), name)
    elif name in _submodules:
        value = _import_module(f"config2py.{name}")
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    globals()[name] = value  # resolved once; ``config_getter`` & co. are built just now
    return value


def __dir__():
    # Not the three default instances: ``dir()`` walkers (pydoc, doctest collection) would
    # build them, and importing must create no folder (#26).
    return sorted({*globals(), *_module_of, *_submodules} - set(_default_instances))


if _TYPE_CHECKING:  # for IDEs and type checkers; at run time the names are lazy
    from config2py import codecs
    from config2py.s_configparser import ConfigStore, ConfigReader
    from config2py.errors import (
        Config2PyError,
        Config2PyWarning,
        ConfigNotFound,
        InsecureConfigFolderWarning,
        MissingConfigFileWarning,
    )
    from config2py.tools import (
        extract_exports,
        get_configs_local_store,
        simple_config_getter,
        Configs,
        config_getter,
        local_configs,
        configs,
    )
    from config2py.base import get_config, user_gettable, sources_chainmap
    from config2py.util import (
        envvar,
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
    from config2py.secret_text import (
        has_secret,
        SecretRule,
        SECRET_RULES,
        SECRET_TEXT_PATTERNS,
    )
    from config2py.sync_store import SyncStore, FileStore, JsonStore, register_extension

# What ``from config2py import *`` exports: every public name, the submodules that were
# bound by the old eager imports, and the lazy instances (a star import builds them).
__all__ = [*_module_of, *_submodules]
