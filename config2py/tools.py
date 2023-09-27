"""Various tools"""

from typing import Callable
from pathlib import Path
import re
from dol import Pipe, TextFiles, resolve_path
import os
from config2py.util import get_configs_folder_for_app, DFLT_CONFIG_FOLDER, is_repl

from config2py.base import get_config, user_gettable


# TODO: Make it into an open-closed plug-in using routing
def get_configs_local_store(config_src=DFLT_CONFIG_FOLDER):
    """Get the local store of configs.
    
    :param config_src: A specification of the local config store. By default:
        If it's a directory, it's assumed to be a folder of text files.
        If it's a file, it's assumed to be an ini or cfg file.
        If it's a string, it's assumed to be an app name, from which to create a folder
    """
    if os.path.isdir(config_src):
        return TextFiles(config_src)
    elif os.path.isfile(config_src):
        # TODO: Not tested
        # TODO: Make this open-closed plug-in via routing argument
        _, extension = os.path.splitext(config_src)
        if extension in {".ini", ".cfg"}:
            from config2py.s_configparser import ConfigStore

            return ConfigStore(config_src)
    elif os.path.sep not in config_src:  # it's just a string
        # TODO: is "get" the right word, since it makes the folder too
        path = get_configs_folder_for_app(config_src)
        return TextFiles(path)
    else:
        raise ValueError(
            f"config_src must be a directory, ini or cfg file, or app name. "
            f"Was: {config_src}"
        )


# TODO: Need tests and demo
def simple_config_getter(
    configs_src: str = DFLT_CONFIG_FOLDER,
    *,
    first_look_in_env_vars: bool = True,
    ask_user_if_key_not_found: bool = None,
    config_store_factory: Callable = get_configs_local_store,
):
    """Make a simple config getter from a "central" config source specification.

    The purpose of this function is to implement a common pattern of getting configs:
    One that, by default (but optionally), looks in environment variables first,
    then in a central config store, created via a simple ``configs_src`` specification
    and then, if the key is not found in this "central" store, optionally (but not by
    default) asks the user for the value and stores it in the central config store.

    :param configs_src: A specification of the central config store. By default:
        If it's a directory, it's assumed to be a folder of text files.
        If it's a file, it's assumed to be an ini or cfg file.
        If it's a string, it's assumed to be an app name, from which to create a folder
    :param first_look_in_env_vars: Whether to look in environment variables first
    :param ask_user_if_key_not_found: Whether to ask the user if the key is not found
        (and subsequently store the key in the central config store)
    :param config_store_factory: A function that takes a config source specification
        and returns the central config store
    """
    # TODO: Resource validation block. Refactor! And add tool to config2py if not there
    central_configs = config_store_factory(configs_src)
    sources = []
    if first_look_in_env_vars:
        sources.append(os.environ)
    sources.append(central_configs)
    if ask_user_if_key_not_found is None:
        # if the user didn't ask for anythin explicit (True or False), then
        # add this option if the user is in a REPL (interactive mode)
        ask_user_if_key_not_found = is_repl()
    if ask_user_if_key_not_found:
        sources.append(user_gettable(central_configs))
    config_getter = get_config(sources=sources)
    config_getter.configs = central_configs
    return config_getter


# Make a ready-to-use config getter, using the defaults
config_getter = simple_config_getter()

# --------------------------------------------------------------------
# Ready to import instances
#
# TODO: Is destined to be a class that makes a store (MutableMapping) to access configs
#   (properties, etc.). The default is TextFiles, but the user should be able to specify
#   a different store (e.g. ConfigStore, or a custom store) to use.
#   Make the Configs class with use outside config2py in mind.
#   Note: Perhaps there's no need for a class.
#   Maybe just a function that returns a store
Configs = TextFiles  # TODO: deprecate

# A default persistent store for configs
local_configs = get_configs_local_store()

# TODO: This is the real purpose of the Configs class (not even used here)
#    To provide a default (but customizable) `MutableMapping` interface to configs
configs = local_configs  # TODO: backwards compatibility alias

# --------------------------------------------------------------------

export_line_p = re.compile("export .+")
export_p = re.compile(r'(\w+)\s?\=\s?"(.+)"')

_extract_name_and_value_from_export_line = Pipe(
    lambda x: x[len("export ") :],
    lambda x: export_p.match(x),
    lambda x: x.groups() if x else "",
)


def extract_exports(exports: str) -> dict:
    r"""Get a dict of ``{name: value}`` pairs from the ``name="value" pairs of unix
    export lines (that is, lines of the ``export NAME="VALUE"`` format

    :param exports: Filepath or string contents thereof
    :return: A dict of extracted ``{name: value}`` pairs

    >>> extract_exports('export KEY="secret"\nexport TOKEN="arbitrary"')
    {'KEY': 'secret', 'TOKEN': 'arbitrary'}

    Use case:
    ---------

    You have access to environment variables through ``os.environ``, but
    if you want to extract exports from only a specific file (env vars are often
    placed in different linked files), or the exports are defined in a string you hold,
    then this simple parser can be useful.

    """
    if "\n" not in exports and Path(resolve_path(exports)).is_file():
        exports = Path(resolve_path(exports)).read_text()
    return dict(
        filter(
            None,
            map(
                _extract_name_and_value_from_export_line, export_line_p.findall(exports)
            ),
        )
    )
