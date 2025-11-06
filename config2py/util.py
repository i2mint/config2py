"""
Utility functions for config2py.

"""

import re
import os
import ast
from collections import ChainMap, namedtuple
from pathlib import Path
from functools import partial
from typing import Optional, Union, Any, Set, Literal, get_args
from collections.abc import Callable
from types import SimpleNamespace
import getpass

from dol import process_path

from i2 import mk_sentinel  # TODO: Only i2 dependency. Consider replacing.

# def mk_sentinel(name):  # TODO: Only i2 dependency. Here's replacement, but not picklable
#     return type(name, (), {'__repr__': lambda self: name})()

DFLT_APP_NAME = "config2py"
DFLT_MASKING_INPUT = False

not_found = mk_sentinel("not_found")
no_default = mk_sentinel("no_default")


def always_true(x: Any) -> bool:
    """Function that just returns True."""
    return True


def identity(x: Any) -> Any:
    """Function that just returns its argument."""
    return x


def is_not_empty(x: Any) -> bool:
    """Function that returns True if x is not empty."""
    return bool(x)


# Note: Why subclassing ChainMap works, but subclassing dict doesn't.
# The `EnvironmentVariables` class inherits from `collections.ChainMap` and wraps
# `os.environ`, providing a dynamic view of the environment variables without exposing
# sensitive data. Unlike a regular `dict` copy, which creates a static snapshot,
# `ChainMap` maintains a live reference to `os.environ`, so any changes to the
# environment—whether through `os.environ['KEY'] = 'value'` or external updates—are
# immediately reflected in `EnvironmentVariables`. Overriding `__repr__` ensures that
# printing the object (e.g., in a REPL or log) hides the actual contents,
# preserving confidentiality while retaining full read/write functionality.
class EnvironmentVariables(ChainMap):
    """
    Class to wrap environment variables without revealing sensitive information.
    """

    def __init__(self):
        super().__init__(os.environ)

    def __repr__(self):
        return "EnvironmentVariables"


envvar = EnvironmentVariables()


# TODO: Make this into an open-closed mini-framework
def ask_user_for_input(
    prompt: str,
    default: str = "",
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
    if prompt[-1] != " ":  # pragma: no cover
        prompt = prompt + " "
    if masking_toggle_str is not None:
        prompt = (
            f"{prompt}\n"
            f"    (Input masking is {'ENABLED' if mask_input else 'DISABLED'}. "
            f"Enter '{masking_toggle_str}' (without quotes) to toggle input masking)\n"
        )
    if default not in {""}:
        prompt = prompt + f" [{default}]: "
    if mask_input:
        _prompt_func = getpass.getpass
    else:
        _prompt_func = input

    response = _prompt_func(prompt)

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
    string: str, expand: dict | bool | None = None
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
    pattern = re.compile(r"^export\s+([A-Za-z0-9_]+)=(.*)$")
    lines = string.split("\n")
    for line in lines:
        line = line.strip()
        match = pattern.match(line)
        if match:
            name = match.group(1)
            value = match.group(2).strip('"')
            if expand is not None:
                for key, val in expand.items():
                    value = value.replace(f"${key}", val)
                env_vars[name] = value
                expand = dict(expand, **env_vars)
            else:
                env_vars[name] = value
    return env_vars


def create_directories(dirpath, max_dirs_to_make=None):
    """
    Create directories up to a specified limit.

    Parameters:
    dirpath (str): The directory path to create.
    max_dirs_to_make (int, optional): The maximum number of directories to create. If None, there's no limit.

    Returns:
    bool: True if the directory was created successfully, False otherwise.

    Raises:
    ValueError: If max_dirs_to_make is negative.

    Examples:
    >>> import tempfile, shutil
    >>> temp_dir = tempfile.mkdtemp()
    >>> target_dir = os.path.join(temp_dir, 'a', 'b', 'c')
    >>> create_directories(target_dir, max_dirs_to_make=2)
    False
    >>> create_directories(target_dir, max_dirs_to_make=3)
    True
    >>> os.path.isdir(target_dir)
    True
    >>> shutil.rmtree(temp_dir)  # Cleanup

    >>> temp_dir = tempfile.mkdtemp()
    >>> target_dir = os.path.join(temp_dir, 'a', 'b', 'c', 'd')
    >>> create_directories(target_dir)
    True
    >>> os.path.isdir(target_dir)
    True
    >>> shutil.rmtree(temp_dir)  # Cleanup
    """
    if max_dirs_to_make is not None and max_dirs_to_make < 0:
        raise ValueError("max_dirs_to_make must be non-negative or None")

    if os.path.exists(dirpath):
        return True

    if max_dirs_to_make is None:
        os.makedirs(dirpath, exist_ok=True)
        return True

    # Calculate the number of directories to create
    dirs_to_make = []
    current_path = dirpath

    while not os.path.exists(current_path):
        dirs_to_make.append(current_path)
        current_path, _ = os.path.split(current_path)

    if len(dirs_to_make) > max_dirs_to_make:
        return False

    # Create directories from the top level down
    for dir_to_make in reversed(dirs_to_make):
        os.mkdir(dir_to_make)

    return True


FolderSpec = namedtuple("FolderSpec", ["env_var", "default_path"])

if os.name == "nt":
    APP_FOLDER_STANDARDS = dict(
        config=FolderSpec("APPDATA", os.getenv("APPDATA", "")),
        data=FolderSpec("LOCALAPPDATA", os.getenv("LOCALAPPDATA", "")),
        cache=FolderSpec(
            "LOCALAPPDATA", os.path.join(os.getenv("LOCALAPPDATA", ""), "Temp")
        ),
        state=FolderSpec("LOCALAPPDATA", os.getenv("LOCALAPPDATA", "")),
        runtime=FolderSpec("TEMP", os.getenv("TEMP", "")),
    )
else:
    APP_FOLDER_STANDARDS = dict(
        config=FolderSpec("XDG_CONFIG_HOME", "~/.config"),
        data=FolderSpec("XDG_DATA_HOME", "~/.local/share"),
        cache=FolderSpec("XDG_CACHE_HOME", "~/.cache"),
        state=FolderSpec("XDG_STATE_HOME", "~/.local/state"),
        runtime=FolderSpec("XDG_RUNTIME_DIR", "/tmp"),
    )


AppFolderKind = Literal["config", "data", "cache", "state", "runtime"]

# Verify AppFolderKind matches _APP_FOLDER_STANDARDS_DICT keys
# Note: This is due to the fact that static type checkers can't verify
# that the keys of _APP_FOLDER_STANDARDS_DICT match the Literal values.
# This breaks SSOT, but here we at least validate alignment at runtime.
_literal_kinds = get_args(AppFolderKind)
assert set(_literal_kinds) == set(APP_FOLDER_STANDARDS.keys()), (
    f"AppFolderKind Literal {_literal_kinds} doesn't match "
    f"APP_FOLDER_STANDARDS keys {tuple(APP_FOLDER_STANDARDS.keys())}"
)

config2py_env_var = SimpleNamespace(
    **{k: f"CONFIG2PY_{k.upper()}_DIR" for k in APP_FOLDER_STANDARDS}
)


DFLT_APP_FOLDER_KIND: AppFolderKind = "config"  # type: ignore (for <3.11)


def system_default_for_app_data_folder(
    folder_kind: AppFolderKind = DFLT_APP_FOLDER_KIND,  # type: ignore (for <3.11)
) -> str:
    """Get the system default for the app data folder."""
    # Platform-specific specs: (env_var, default_path)

    # Same logic for both platforms: check env var, then use default
    env_var, default = APP_FOLDER_STANDARDS[folder_kind]
    return os.path.expanduser(os.getenv(env_var, default))


DFLT_CONFIG_FOLDER = system_default_for_app_data_folder("config")
DFLT_DATA_FOLDER = system_default_for_app_data_folder("data")
DFLT_CACHE_FOLDER = system_default_for_app_data_folder("cache")
DFLT_STATE_FOLDER = system_default_for_app_data_folder("state")
DFLT_RUNTIME_FOLDER = system_default_for_app_data_folder("runtime")


def get_app_rootdir(
    folder_kind: AppFolderKind = DFLT_APP_FOLDER_KIND,  # type: ignore (for <3.11)
    *,
    ensure_exists: bool = True,
) -> str:
    """
    Returns the root directory for a specific folder kind.

    The folder kind determines which standard directory is returned:
    - 'config': Configuration files (XDG_CONFIG_HOME, default ~/.config)
    - 'data': Application data (XDG_DATA_HOME, default ~/.local/share)
    - 'cache': Temporary/cache files (XDG_CACHE_HOME, default ~/.cache)
    - 'state': State data/logs (XDG_STATE_HOME, default ~/.local/state)
    - 'runtime': Runtime files (XDG_RUNTIME_DIR, default /tmp)

    On Windows:
    - 'config': %APPDATA%
    - 'data': %LOCALAPPDATA%
    - 'cache': %LOCALAPPDATA%\\Temp
    - 'state': %LOCALAPPDATA%
    - 'runtime': %TEMP%

    Args:
        folder_kind (str): The kind of folder to get. One of 'config', 'data', 'cache', 'state', 'runtime'.
            Defaults to 'config'.
            Here are concise explanations for each folder kind:
            **config**: User preferences and settings files (e.g., API keys, theme preferences, editor settings). Files users might edit manually or that define how the app behaves.
            **data**: Essential user-created content and application state (e.g., databases, saved games, user documents, session files). Data that should be backed up and persists across updates.
            **cache**: Temporary, regeneratable files (e.g., downloaded images, compiled assets, web cache). Can be safely deleted to free space without losing user work.
            **state**: Application state and logs that persist between sessions but aren't critical user data (e.g., command history, undo history, recently opened files, log files). Unlike cache, shouldn't be auto-deleted.
            **runtime**: Temporary runtime files that only exist while the app runs (e.g., PID files, Unix sockets, lock files, named pipes). Typically cleared on logout/reboot.
            **TL;DR**: config = settings, data = user files, cache = disposable, state = logs/history, runtime = process files.

        ensure_exists: Whether to create the directory if it doesn't exist

    Returns:
        str: The full path of the app root folder for the specified kind.

    Note: The default root folder follows XDG Base Directory standards on Unix/Linux/macOS.
    You can override this by setting environment variables:
    - CONFIG2PY_CONFIG_FOLDER, CONFIG2PY_DATA_FOLDER, CONFIG2PY_CACHE_FOLDER, etc.
      (highest priority, overrides everything)
    - XDG_CONFIG_HOME, XDG_DATA_HOME, XDG_CACHE_HOME, etc.
      (standard XDG override)
    - If neither is set, uses platform defaults

    Examples:

        >>> get_app_rootdir('config')  # doctest: +SKIP
        '/Users/.../.config'
        >>> get_app_rootdir('data')  # doctest: +SKIP
        '/Users/.../.local/share'
        >>> get_app_rootdir('cache')  # doctest: +SKIP
        '/Users/.../.cache'
    """
    folderpath = os.getenv(
        getattr(config2py_env_var, folder_kind),  # Check config2py custom env var first
        system_default_for_app_data_folder(
            folder_kind
        ),  # ... if not, use system default
    )

    return process_path(folderpath, ensure_dir_exists=ensure_exists)


# renaming get_app_data_rootdir to get_app_rootdir
_legacy_app_data_rootdir = get_app_rootdir  # backwards compatibility alias


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
        os.makedirs(directory_path, exist_ok=True)
        # Add a hidden file to annotate the directory as one managed by config2py.
        # This helps distinguish it from directories created by other programs
        # (this can be useful to avoid conflicts).
        (Path(directory_path) / ".config2py").write_text("Created by config2py.")


def get_app_folder(
    app_name: str = DFLT_APP_NAME,
    *,
    setup_callback: Callable[[str], None] = _default_folder_setup,
    ensure_exists: bool = False,
    folder_kind: AppFolderKind = DFLT_APP_FOLDER_KIND,
) -> str:
    """
    Retrieve or create the app directory specific to the given app name and folder kind.

    The folder kind determines where the app's files are stored:
    Here are concise explanations for each folder kind:
        **config**: User preferences and settings files (e.g., API keys, theme preferences, editor settings). Files users might edit manually or that define how the app behaves.
        **data**: Essential user-created content and application state (e.g., databases, saved games, user documents, session files). Data that should be backed up and persists across updates.
        **cache**: Temporary, regeneratable files (e.g., downloaded images, compiled assets, web cache). Can be safely deleted to free space without losing user work.
        **state**: Application state and logs that persist between sessions but aren't critical user data (e.g., command history, undo history, recently opened files, log files). Unlike cache, shouldn't be auto-deleted.
        **runtime**: Temporary runtime files that only exist while the app runs (e.g., PID files, Unix sockets, lock files, named pipes). Typically cleared on logout/reboot.
        **TL;DR**: config = settings, data = user files, cache = disposable, state = logs/history, runtime = process files.

    Args:
        app_name: Name of the app for which the directory is needed.
        setup_callback: A callback function to initialize the directory.
                       Default is _default_folder_setup.
        ensure_exists: Whether to ensure the directory exists.
        folder_kind: Type of folder ('config', 'data', 'cache', 'state', or 'runtime').
                    Default is 'config' for backward compatibility.

    Returns:
        str: Path to the app directory.

    By default, the app will be "config2py" and folder_kind will be "config":

    >>> get_app_folder()  # doctest: +ELLIPSIS
    '.../.config/config2py'

    You can specify a different app name and folder kind:

    >>> get_app_folder('my_app', folder_kind='data')  # doctest: +SKIP
    '/Users/.../.local/share/my_app'
    >>> get_app_folder('my_app', folder_kind='cache')  # doctest: +SKIP
    '/Users/.../.cache/my_app'

    You can also specify a path relative to the app root directory:

    >>> get_app_folder('another/app/subfolder', folder_kind='data')  # doctest: +SKIP
    '/Users/.../.local/share/another/app/subfolder'

    If ensure_exists is True, the directory will be created and initialized
    with the setup_callback:

    >>> path = get_app_folder('my_app', ensure_exists=True)  # doctest: +SKIP
    >>> os.path.exists(path)  # doctest: +SKIP
    True
    """
    app_data_path = os.path.join(
        get_app_rootdir(folder_kind, ensure_exists=ensure_exists), app_name
    )
    app_data_folder_does_not_exist = not os.path.isdir(app_data_path)

    if app_data_folder_does_not_exist and ensure_exists:
        setup_callback(app_data_path, ensure_exists=ensure_exists)
    return app_data_path


get_app_config_folder = partial(get_app_folder, folder_kind="config")
get_app_data_folder = partial(get_app_folder, folder_kind="data")

DFLT_CONFIGS_NAME = "configs"


# TODO: is "get" the right word, since it makes the folder too?
# TODO: Merge get_configs_folder_for_app and get_app_config_folder
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
    app_dir = get_app_config_folder(app_name, setup_callback=app_dir_setup_callback)
    configs_dir = os.path.join(app_dir, configs_name)
    config_dir_setup_callback(configs_dir)
    return configs_dir


get_app_data_directory = get_app_config_folder  # backwards compatibility alias
get_configs_directory_for_app = (
    get_configs_folder_for_app  # backwards compatibility alias
)

DFLT_CONFIG_FOLDER = get_configs_folder_for_app()


import sys


def _get_ipython_in_globals():
    return "get_ipython" in globals()


def _main_does_not_have_file_attribute():
    return not hasattr(sys.modules["__main__"], "__file__")


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


is_repl.repl_conditions: set[Callable] = _repl_conditions  # type: ignore


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
