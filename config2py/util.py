"""Utility functions for config2py."""

import re
import os
import ast
from pathlib import Path
from typing import Optional, Union, Any, Callable, Set
import getpass

DFLT_APP_NAME = 'config2py'
DFLT_MASKING_INPUT = False


def always_true(x: Any) -> bool:
    """Function that just returns True."""
    return True


def identity(x: Any) -> Any:
    """Function that just returns its argument."""
    return x


# TODO: Make this into an open-closed mini-framework
def ask_user_for_input(
    prompt: str,
    default: str = None,
    *,
    mask_input=DFLT_MASKING_INPUT,
    masking_toggle_str: str = None,
    egress: Callable = identity,
) -> str:
    """
    Ask the user for input, optionally masking, validating and transforming the input.

    :param prompt: Prompt to display to the user
    :param default: Default value to return if the user enters nothing
    :param mask_input: Whether to mask the user's input
    :param masking_toggle_str: String to toggle input masking. If ``None``, no toggle
        is available. If not ``None`` (a common choice is the empty string)
        the user can enter this string to toggle input masking.
    :param egress: Function to apply to the user's response before returning it.
        This can be used to validate the response, for example.
    :return: The user's response (or the default value if the user entered nothing)
    """
    _original_prompt = prompt
    if prompt[-1] != ' ':  # pragma: no cover
        prompt = prompt + ' '
    if masking_toggle_str is not None:
        prompt = (
            f'{prompt}\n'
            f"    (Input masking is {'ENABLED' if mask_input else 'DISABLED'}. "
            f"Enter '{masking_toggle_str}' (without quotes) to toggle input masking)\n"
        )
    if default:
        prompt = prompt + f' [{default}]: '
    if mask_input:
        response = getpass.getpass(prompt)
    else:
        response = input(prompt)
    if masking_toggle_str is not None and response == masking_toggle_str:
        return ask_user_for_input(
            _original_prompt,
            default,
            mask_input=not mask_input,
            masking_toggle_str=masking_toggle_str,
        )

    return egress(response or default)


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
    lines = string.split('\n')
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


def _system_default_for_app_data_folder():
    """Get the system default for the app data folder."""
    if os.name == 'nt':
        # Windows
        app_data_folder = os.getenv('APPDATA')
    else:
        # macOS and Linux/Unix
        app_data_folder = os.path.expanduser('~/.config')
    return app_data_folder


DFLT_APP_DATA_FOLDER = os.getenv(
    'CONFIG2PY_APP_DATA_FOLDER', _system_default_for_app_data_folder()
)


def process_path(
    path: str,
    *,
    ensure_dir_exists=False,
    assert_exists=False,
    ensure_endswith_slash=False,
    ensure_does_not_end_with_slash=False,
    expanduser=True,
) -> str:
    """
    Process a path string, ensuring it exists, and optionally expanding user.

    Args:
        path (str): The path to process.
        ensure_dir_exists (bool): Whether to ensure the path exists.
        assert_exists (bool): Whether to assert that the path exists.
        ensure_endswith_slash (bool): Whether to ensure the path ends with a slash.
        ensure_does_not_end_with_slash (bool): Whether to ensure the path does not end with a slash.
        expanduser (bool): Whether to expand the user in the path.

    Returns:
        str: The processed path.

    """
    if ensure_endswith_slash and ensure_does_not_end_with_slash:
        raise ValueError(
            'Cannot ensure both ends with slash and does not end with slash.'
        )
    if expanduser:
        path = os.path.expanduser(path)
    if ensure_endswith_slash:
        if not path.endswith('/'):
            path = path + '/'
    if ensure_does_not_end_with_slash:
        if path.endswith('/'):
            path = path[:-1]
    if ensure_dir_exists:
        os.makedirs(path, exist_ok=True)
    if assert_exists:
        assert os.path.exists(path), f'Path does not exist: {path}'
    return path


# Note: First possible i2 dependency -- vendoring for now
def get_app_data_rootdir(*, ensure_exists=False) -> str:
    """
    Returns the full path of a directory suitable for storing application-specific data.

    On Windows, this is typically %APPDATA%.
    On macOS, this is typically ~/.config.
    On Linux, this is typically ~/.config.

    Returns:
        str: The full path of the app data folder.

    See https://github.com/i2mint/i2mint/issues/1.

    >>> get_app_data_rootdir()  # doctest: +SKIP
    '/Users/.../.config'

    If ``ensure_exists`` is ``True``, the folder will be created if it doesn't exist.

    >>> get_app_data_rootdir(ensure_exists=True)  # doctest: +SKIP
    '/Users/.../.config'

    Note: The default app data folder is the system default for the current operating
    system. If you want to override this, you can do so by setting the
    CONFIG2PY_APP_DATA_FOLDER environment variable to the path of the folder you want
    to use.

    """
    return process_path(DFLT_APP_DATA_FOLDER, ensure_dir_exists=True)


def _default_folder_setup(directory_path: str) -> None:
    """
    Create the given directory if it doesn't exist and initialize it
    with a hidden file for identification.

    Args:
    - directory_path (str): Path to the directory to be initialized.

    Note:
    This is the default setup callback for directories managed by config2py.
    """
    if not os.path.isdir(directory_path):
        os.mkdir(directory_path)
        # Add a hidden file to annotate the directory as one managed by config2py.
        # This helps distinguish it from directories created by other programs
        # (this can be useful to avoid conflicts).
        (Path(directory_path) / '.config2py').write_text('Created by config2py.')


def get_app_data_folder(
    app_name: str = DFLT_APP_NAME,
    *,
    setup_callback: Callable[[str], None] = _default_folder_setup,
    ensure_exists: bool = False,
) -> str:
    """
    Retrieve or create the app data directory specific to the given app name.

    Args:
    - app_name (str): Name of the app for which the data directory is needed.
    - setup_callback (Callable[[str], None]): A callback function to initialize the directory.
                                              Default is _default_folder_setup.
    - ensure_exists (bool): Whether to ensure the directory exists.

    Returns:
    - str: Path to the app data directory.

    By default, the app will be "config2py":

    >>> get_app_data_folder()  # doctest: +ELLIPSIS
    '.../.config/config2py'

    You can specify a different app name though. 
    And if you want, you can also specify a callback function to initialize the 
    directory.

    >>> path = get_app_data_folder('my_app', ensure_exists=True)  # doctest: +SKIP
    >>> path  # doctest: +SKIP
    '/Users/.../.config/my_app'
    >>> os.path.exists(path)  # doctest: +SKIP

    You can also specify a path relative to the app data root directory
    (on linux/mac systems, this is typically ~/.config)

    >>> get_app_data_folder('another/app/and/subfolder')  # doctest: +SKIP
    '/Users/.../.config/another/app/and/subfolder'

    """
    app_data_path = os.path.join(
        get_app_data_rootdir(ensure_exists=ensure_exists), app_name
    )
    app_data_folder_did_not_exist = not os.path.isdir(app_data_path)
    app_data_folder = process_path(app_data_path, ensure_dir_exists=True)

    if app_data_folder_did_not_exist:
        setup_callback(app_data_path)
    return app_data_path


DFLT_CONFIGS_NAME = 'configs'


# TODO: is "get" the right word, since it makes the folder too?
def get_configs_folder_for_app(
    app_name: str = DFLT_APP_NAME,
    *,
    configs_name: str = DFLT_CONFIGS_NAME,
    app_dir_setup_callback: Callable[[str], None] = _default_folder_setup,
    config_dir_setup_callback: Callable[[str], None] = _default_folder_setup,
):
    """
    Retrieve or create the configs directory specific to the given app name.

    Args:
    - app_name (str): Name of the app for which the configs directory is needed.
    - configs_name (str): Name of the configs directory.
    - app_dir_setup_callback (Callable[[str], None]): A callback function to initialize the app directory.
                                                       Default is _default_folder_setup.
    - config_dir_setup_callback (Callable[[str], None]): A callback function to initialize the configs directory.
                                                         Default is _default_folder_setup.
    """
    app_dir = get_app_data_folder(app_name, setup_callback=app_dir_setup_callback)
    configs_dir = os.path.join(app_dir, configs_name)
    config_dir_setup_callback(configs_dir)
    return configs_dir


get_app_data_directory = get_app_data_folder  # backwards compatibility alias
get_configs_directory_for_app = (
    get_configs_folder_for_app  # backwards compatibility alias
)

DFLT_CONFIG_FOLDER = get_configs_folder_for_app()


import sys


def _get_ipython_in_globals():
    return 'get_ipython' in globals()


def _main_does_not_have_file_attribute():
    return not hasattr(sys.modules['__main__'], '__file__')


_repl_conditions = {_get_ipython_in_globals, _main_does_not_have_file_attribute}


def is_repl():
    """
    Determines if the Python interpreter is running in REPL.

    To test: If you put it in a module.py, do a print of it in the module, and do
    ``python module.py`` it should print False.
    If you do ``python -i module.py``, or call it from a python console or jupyter
    notebook, it should return ``True``.

    Args:
        repl_conditions (list): A list of functions that return True if the interpreter
            is running in a REPL, False otherwise.
            By default, this is a list of two functions that check if:
            - ``get_ipython`` is in globals
            - ``__main__`` does not have a ``__file__`` attribute
    Returns:
        bool: True if running in a REPL, False otherwise.

    is_repl.repl_conditions is a set of functions that return True if the interpreter.
    This set can be modified to modify the behavior of ``is_repl``.
    """
    if any(condition() for condition in _repl_conditions):
        return True
    return False


is_repl.repl_conditions: Set[Callable] = _repl_conditions


def _value_node_is_instance_of(
    node_value, classes=(ast.Constant, ast.List, ast.Tuple, ast.Dict)
):
    return isinstance(node_value, classes)


def parse_assignments_from_py_source(
    source_code: str, *, name_filt=None, value_filt=_value_node_is_instance_of
):
    """Parse assignments from python source code.

    >>> source_code = '''a = 1
    ... b = 'hello'
    ... c = [1, 2, 3]
    ... def func():
    ...     d = 4
    ... '''
    >>> dict(parse_assignments_from_py_source(source_code))
    {'a': 1, 'b': 'hello', 'c': [1, 2, 3], 'd': 4}

    """
    name_filt = name_filt or (lambda x: True)
    value_filt = value_filt or (lambda x: True)

    # Parse the source code to create an AST
    tree = ast.parse(source_code)

    # Walk through all nodes in the AST
    for node in ast.walk(tree):
        # If the node is an assignment, it may be assigning a value to a variable
        if isinstance(node, ast.Assign):
            # Go through each target in the assignment
            for target in node.targets:
                # If the target is a Name node, it's a variable being assigned a value
                if isinstance(target, ast.Name):
                    if name_filt(target.id) and value_filt(node.value):
                        yield target.id, ast.literal_eval(node.value)
