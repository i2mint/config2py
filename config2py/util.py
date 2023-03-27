"""Utility functions for config2py."""


# def extract_variable_declarations(string):
#     """
#     Reads the contents of a config file, extracting Unix-style environment variable
#     declarations of the form
#     `export {NAME}={value}`, returning a dictionary of `{NAME: value, ...}` pairs.
#
#     # >>> config = (
#     # ...   'export ENVIRONMENT="development"\\n'
#     # ...   'export PORT=8080\\n'
#     # ...   'alias = "just to make it harder"\\n'
#     # ...   '\\n'
#     # ...   'export DEBUG=true'
#     # ...)
#     # >>> extract_variable_declarations(config)
#     # {'ENVIRONMENT': '"development"', 'PORT': '8080', 'DEBUG': 'true'}
#
#     >>> config = 'export PATH="$PATH:/usr/local/bin"\\nexport EDITOR="nano"'
#     >>> extract_variable_declarations(config)
#     {'PATH': '$PATH:/usr/local/bin', 'EDITOR': 'nano'}
#
#     """
#     env_vars = {}
#     lines = string.split("\n")
#     for line in lines:
#         line = line.strip()
#         if line.startswith("export"):
#             parts = line.split("=")
#             name = parts[0].split(" ")[1]
#             value = parts[1]
#             env_vars[name] = value
#     return env_vars


import re
from typing import Optional, Union, Any


def always_true(x: Any) -> bool:
    return True


# Note: Could be made more efficient, but this is good enough (for now)
def extract_variable_declarations(
        string: str, expand: Optional[Union[dict, bool]] = None
) -> dict:
    """
    Reads the contents of a config file, extracting Unix-style environment variable
    declarations of the form
    `export {NAME}={value}`, returning a dictionary of `{NAME: value, ...}` pairs.

    See issue for more info and applications:
    https://github.com/i2mint/config2py/issues/2

    :param string: String to extract variable declarations from
    :param expand: An optional dictionary of variable names and values to use to
        expand variables that are referenced (i.e. ``$NAME`` is a reference to ``NAME``
        variable) in the values of config variables.
        If ``True``, ``expand`` is replaced with an empty dictionary, which means we
        want to expand variables recursively, but we have no references to seed the
        expansion with. If ``False``, ``expand`` is replaced with ``None``, indicating
        that we don't want to expand any variables.

    :return: A dictionary of variable names and values.

    >>> config = 'export ENVIRONMENT="dev"\\nexport PORT=8080\\nexport DEBUG=true'
    >>> extract_variable_declarations(config)
    {'ENVIRONMENT': 'dev', 'PORT': '8080', 'DEBUG': 'true'}

    >>> config = 'export PATH="$PATH:/usr/local/bin"\\nexport EDITOR="nano"'
    >>> extract_variable_declarations(config)
    {'PATH': '$PATH:/usr/local/bin', 'EDITOR': 'nano'}

    The ``expand`` argument can be used to expand variables in the values of other.

    Let's add a reference to the ``PATH`` variable in the ``EDITOR`` variable:

    >>> config = 'export PATH="$PATH:/usr/local/bin"\\nexport EDITOR="nano $PATH"'

    If you specify a value for ``PATH`` in the ``expand`` argument, you'll see it
    reflected in the ``PATH`` variable (self reference) and the ``EDITOR`` variable.
    (Note if you changed the order of ``PATH`` and ``EDITOR`` in the ``config``,
    you wouldn't get the same thing though.)

    >>> extract_variable_declarations(config, expand={'PATH': '/root'})
    {'PATH': '/root:/usr/local/bin', 'EDITOR': 'nano /root:/usr/local/bin'}

    If you specify ``expand={}``, the first ``PATH`` variable will not be expanded,
    since PATH is not in the expand dictionary. But the second ``PATH`` variable,
    referenced in the definition of ``EDITOR`` will be expanded, since it is in the
    expand dictionary.

    >>> extract_variable_declarations(config, expand={})
    {'PATH': '$PATH:/usr/local/bin', 'EDITOR': 'nano $PATH:/usr/local/bin'}

    """
    if expand is True:
        # If expand is True, we'll use an empty dictionary as the expand dictionary
        # This means we want variables to be expanded recursively, but we have no
        # references to seed the expansion with.
        expand = {}
    elif expand is False:
        # If expand is False, we don't want to expand any variables.
        expand = None

    env_vars = {}
    pattern = re.compile(r'^export\s+([A-Za-z0-9_]+)=(.*)$')
    lines = string.split("\n")
    for line in lines:
        line = line.strip()
        match = pattern.match(line)
        if match:
            name = match.group(1)
            value = match.group(2).strip('"')
            if expand is not None:
                for key, val in expand.items():
                    value = value.replace(f'${key}', val)
                env_vars[name] = value
                expand = dict(expand, **env_vars)
            else:
                env_vars[name] = value
    return env_vars