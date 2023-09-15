"""Tools to read and write configurations from various sources and formats"""

from config2py.s_configparser import ConfigStore, ConfigReader
from config2py.tools import extract_exports, repl_config_getter
from config2py.base import get_config, user_gettable, sources_chainmap
from config2py.util import (
    ask_user_for_input,
    Configs,
    configs,  # deprecate in favor of local_configs?
    # or make configs be more of a default get_configs "chained Mapping"
    local_configs,
    get_configs_local_store,
    get_app_data_folder,
)
