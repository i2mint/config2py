"""Various tools"""

from pathlib import Path
import re
import getpass
from dol import Pipe, resolve_path
import os
from config2py.util import local_configs
from config2py.base import get_config, user_gettable


repl_config_getter = get_config(
    sources=[
        os.environ,  # search in environment variables first
        local_configs,  # then search in local_configs
        user_gettable(
            local_configs
        ),  # if not found, ask the user and store in local_configs
    ]
)
repl_config_getter.local_configs = local_configs

export_line_p = re.compile('export .+')
export_p = re.compile(r'(\w+)\s?\=\s?"(.+)"')

_extract_name_and_value_from_export_line = Pipe(
    lambda x: x[len('export ') :],
    lambda x: export_p.match(x),
    lambda x: x.groups() if x else '',
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
    if '\n' not in exports and Path(resolve_path(exports)).is_file():
        exports = Path(resolve_path(exports)).read_text()
    return dict(
        filter(
            None,
            map(
                _extract_name_and_value_from_export_line, export_line_p.findall(exports)
            ),
        )
    )
