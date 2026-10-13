"""Various tools"""

from collections.abc import Callable
from pathlib import Path
import re
import threading
from dol import Pipe, TextFiles, resolve_path
import os
from i2 import Sig

from config2py.util import (
    envvar,
    get_configs_folder_for_app,
    _DFLT_CONFIGS_FOLDER_PATH,  # the path of DFLT_CONFIG_FOLDER, not created (#26)
    ensure_default_configs_folder,
    is_default_configs_folder,
    is_repl,
    DFLT_CONFIGS_NAME,
    secure_open,
    check_folder_is_private,
    setup_configs_folder,
)
from config2py.base import get_config, user_gettable
from config2py.errors import report_missing_config_file, validate_on_missing


class SecureTextFiles(TextFiles):
    """A ``dol.TextFiles`` (one text file per key) whose value files are ``0o600``.

    Config values are often secrets (API keys); plain ``TextFiles`` writes them with
    the umask default (commonly world-readable ``0o644``). Still an ``isinstance``
    of ``TextFiles``, so it is a drop-in replacement
    (see https://github.com/i2mint/config2py/issues/33).

    Like ``TextFiles``, values are UTF-8 on disk whatever the locale, and a failed
    write raises ``KeyError``. Unlike it, the value is encoded before the file is
    opened, so an unencodable value doesn't leave an emptied file behind
    (see https://github.com/i2mint/config2py/issues/35).

    Like ``TextFiles`` (and ``open``), a value file that is a symlink is followed, and
    its target is the file written (and tightened to ``0o600``). That is deliberate:
    it keeps value files symlinked from elsewhere (a dotfiles repo, say) working, and
    in config2py's own configs folder (``0o700``) only its owner can plant a link
    (see https://github.com/i2mint/config2py/issues/37). If others can write to a
    folder you pass in, they can plant a link that redirects your secrets: the store
    warns about such a folder (``on_unsafe_folder``), and ``follow_symlinks=False``
    refuses to write through a link (see
    https://github.com/i2mint/config2py/issues/45).

    ``__setitem__`` relies on three ``dol`` internals: ``_id_of_key``,
    ``store.validate_key`` and ``_data_of_obj``. ``dol`` is unpinned, so
    ``test_secure_text_files_dol_contract`` checks they still exist.
    """

    encoding = "utf-8"  # what dol's TextFiles reads with
    _follow_symlinks = True  # per-instance via ``__init__``; see ``__getstate__``

    def __init__(
        self,
        *args,
        follow_symlinks: bool = True,
        on_unsafe_folder: str = "warn",
        **kwargs,
    ):
        """
        :param follow_symlinks: ``False`` refuses (``KeyError``) to write through a
            symlink at a value file's path (``O_NOFOLLOW``: only the last path
            component is checked). ``True`` (the default) keeps ``open``'s behavior.
        :param on_unsafe_folder: What to do if the root folder is owned by another
            user or writable by its group or by others (as ssh's ``StrictModes``
            checks): ``"warn"`` (the default, once per folder), ``"raise"``
            (``PermissionError``) or ``"ignore"``.
        """
        super().__init__(*args, **kwargs)
        self._follow_symlinks = follow_symlinks
        rootdir = args[0] if args else kwargs.get("rootdir")
        if rootdir is not None:
            check_folder_is_private(rootdir, on_unsafe=on_unsafe_folder, stacklevel=2)

    # dol's ``Store.__getstate__`` (used by ``copy`` and ``pickle``) keeps only its own
    # attributes, so carry ours along (a copy must not quietly start following links).
    def __getstate__(self) -> dict:
        return {**super().__getstate__(), "_follow_symlinks": self._follow_symlinks}

    def __setstate__(self, state: dict):
        state = dict(state)
        self._follow_symlinks = state.pop("_follow_symlinks", True)
        super().__setstate__(state)

    def __setitem__(self, k, v):
        # dol's TextFiles wraps an inner persister, so write via the full path here,
        # keeping that persister's key validation and its KeyError contract.
        path = self._id_of_key(k)
        self.store.validate_key(path)
        try:
            data = self._data_of_obj(v).encode(self.encoding)
            with secure_open(path, "wb", follow_symlinks=self._follow_symlinks) as fp:
                fp.write(data)
        except UnicodeError as error:
            # Its text quotes the offending character of the (possibly secret) value.
            raise KeyError(
                f"{k!r}: the value can't be encoded as {self.encoding} "
                f"({type(error).__name__} at position {getattr(error, 'start', '?')})"
            ) from None
        except Exception as error:
            raise KeyError(str(error)) from error


def _ensure_if_default_configs_folder(src):
    """Create config2py's own configs folder if ``src`` is it (#26)."""
    if is_default_configs_folder(src):
        ensure_default_configs_folder()
    elif isinstance(src, str) and src == _DFLT_CONFIGS_FOLDER_PATH:
        # the default bound at import, if ``config2py.util`` was reloaded since
        setup_configs_folder(src)


# TODO: Make it into an open-closed plug-in using routing
def get_configs_local_store(
    config_src=_DFLT_CONFIGS_FOLDER_PATH,
    *,
    configs_name=DFLT_CONFIGS_NAME,
    follow_symlinks: bool = True,
    on_unsafe_folder: str = "warn",
):
    """Get the local store of configs.

    :param config_src: A specification of the local config store. By default:
        If it's a directory, it's assumed to be a folder of text files.
        If it's a file, it's assumed to be an ini or cfg file.
        If it's a string, it's assumed to be an app name, from which to create a folder
    :param follow_symlinks: Whether the store may write through a symlink at a value
        (or ini) file's path. ``False`` refuses to
        (see https://github.com/i2mint/config2py/issues/45).
    :param on_unsafe_folder: ``"warn"`` (default), ``"raise"`` or ``"ignore"`` when
        a folder store's root is owned by another user or writable by its group or by
        others (see ``SecureTextFiles``).

    Note: a directory is only recognized as such if ``config_src`` contains
    ``os.path.sep``. A bare name (e.g. ``"configs"``) is always treated as an app
    name, even if a directory of that name exists in the current working directory;
    pass ``"./configs"`` (or an absolute path) to use that directory
    (see https://github.com/i2mint/config2py/issues/28).

    The default, ``DFLT_CONFIG_FOLDER``, is config2py's own configs folder. It is
    created here, on first use, rather than at import
    (see https://github.com/i2mint/config2py/issues/26).
    """
    _ensure_if_default_configs_folder(config_src)
    if os.path.sep in config_src and os.path.isdir(config_src):
        # TODO: This was a quick fix to avoid unknowingly making directories in the
        #   wrong place. Broke stuff so leaving this for later.
        # if os.path.sep not in config_src:
        #     raise ValueError(
        #         f"There's a directory named {config_src}, so I'm not sure if you want "
        #         f" me to make an 'app' folder or not. Please specify "
        #         f"{config_src + os.path.sep} if you want to use it as a folder. "
        #         f"If you want to make an 'app' folder for {config_src}, then call the "
        #         f"get_configs_local_store function from a directory that doesn't "
        #         "contain a {config_src} folder."
        #     )
        return SecureTextFiles(
            config_src,
            follow_symlinks=follow_symlinks,
            on_unsafe_folder=on_unsafe_folder,
        )
    elif os.path.isfile(config_src):
        # TODO: Not tested
        # TODO: Make this open-closed plug-in via routing argument
        _, extension = os.path.splitext(config_src)
        if extension in {".ini", ".cfg"}:
            from config2py.s_configparser import ConfigStore

            return ConfigStore(config_src, follow_symlinks=follow_symlinks)
    elif os.path.sep not in config_src:  # it's just a string
        # TODO: is "get" the right word, since it makes the folder too
        path = get_configs_folder_for_app(config_src, configs_name=configs_name)
        return SecureTextFiles(
            path, follow_symlinks=follow_symlinks, on_unsafe_folder=on_unsafe_folder
        )
    else:
        raise ValueError(
            f"config_src must be a directory, ini or cfg file, or app name. "
            f"Was: {config_src}"
        )


# TODO: Need tests and demo
def simple_config_getter(
    configs_src: str = _DFLT_CONFIGS_FOLDER_PATH,
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
        If it's a directory (with at least a slash), it's assumed to be a folder of text files.
        If it's a file, it's assumed to be an ini or cfg file.
        If it's a string, it's assumed to be an app name, from which to create a folder
    :param first_look_in_env_vars: Whether to look in environment variables first
    :param ask_user_if_key_not_found: Whether to ask the user if the key is not found
        (and subsequently store the key in the central config store)
    :param config_store_factory: A function that takes a config source specification
        and returns the central config store
    """
    # TODO: Resource validation block. Refactor! And add tool to config2py if not there
    _ensure_if_default_configs_folder(configs_src)  # not created at import (#26)
    central_configs = config_store_factory(configs_src)
    sources = []
    if first_look_in_env_vars:
        sources.append(envvar)
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


# --------------------------------------------------------------------
# Ready to import instances
#
# ``config_getter`` (a ready-to-use config getter, using the defaults), ``local_configs``
# (a default persistent store for configs) and ``configs`` (an alias of
# ``local_configs``) are built on first access, by the module ``__getattr__`` below,
# then cached as ordinary module attributes. Building them creates the default configs
# folder (``~/.config/config2py/configs`` on Linux), so doing it lazily keeps
# ``import config2py`` free of disk writes
# (see https://github.com/i2mint/config2py/issues/26).
#
# TODO: Is destined to be a class that makes a store (MutableMapping) to access configs
#   (properties, etc.). The default is TextFiles, but the user should be able to specify
#   a different store (e.g. ConfigStore, or a custom store) to use.
#   Make the Configs class with use outside config2py in mind.
#   Note: Perhaps there's no need for a class.
#   Maybe just a function that returns a store
Configs = SecureTextFiles  # TODO: deprecate

# TODO: ``configs`` is the real purpose of the Configs class (not even used here)
#    To provide a default (but customizable) `MutableMapping` interface to configs
_lazy_instance_factories = {
    "config_getter": lambda: simple_config_getter(),
    "local_configs": lambda: get_configs_local_store(),
    # backwards compatibility alias: the same object as ``local_configs``
    "configs": lambda: _lazy_instance("local_configs"),
}
_lazy_instances = {}  # the built instances, unaffected by patching the attributes
_lazy_instances_lock = threading.RLock()


def _lazy_instance(name):
    with _lazy_instances_lock:  # so concurrent first accesses get the same object
        if name not in _lazy_instances:
            _lazy_instances[name] = _lazy_instance_factories[name]()
        return _lazy_instances[name]


def __getattr__(name):
    """Build, cache and return the lazy instances ``config_getter``,
    ``local_configs`` and ``configs`` (PEP 562).

    Building them creates the default configs folder, so an ``OSError`` (say, a
    read-only HOME) surfaces on first access, which ``import config2py`` used to raise.
    They are deliberately left out of ``dir()``, so that tools that ``getattr`` every
    listed name (``pydoc``, doctest collection) don't create the folder.
    """
    if name == "DFLT_CONFIG_FOLDER":  # re-exported from util, which creates it
        return ensure_default_configs_folder()
    if name not in _lazy_instance_factories:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = _lazy_instance(name)
    globals()[name] = value  # later accesses are ordinary attribute lookups
    return value


# --------------------------------------------------------------------

export_line_p = re.compile("export .+")
export_p = re.compile(r'(\w+)\s?\=\s?"(.+)"')

_extract_name_and_value_from_export_line = Pipe(
    lambda x: x[len("export ") :],
    lambda x: export_p.match(x),
    lambda x: x.groups() if x else "",
)


def _is_file(path: Path) -> bool:
    try:
        return path.is_file()
    except OSError:  # e.g. "File name too long"
        return False


def extract_exports(exports, *, on_missing: str = "warn") -> dict:
    r"""Get a dict of ``{name: value}`` pairs from the ``name="value" pairs of unix
    export lines (that is, lines of the ``export NAME="VALUE"`` format

    :param exports: Filepath (``str`` or ``os.PathLike``) or string contents thereof
    :param on_missing: What to do when ``exports`` looks like a filepath (a single,
        non-blank line with no ``export`` in it) that is not an existing file:
        ``"warn"`` (the default) issues a ``MissingConfigFileWarning`` and returns
        ``{}``, ``"raise"`` raises ``FileNotFoundError``, ``"ignore"`` returns ``{}``
        (see https://github.com/i2mint/config2py/issues/27).
    :return: A dict of extracted ``{name: value}`` pairs

    >>> extract_exports('export KEY="secret"\nexport TOKEN="arbitrary"')
    {'KEY': 'secret', 'TOKEN': 'arbitrary'}
    >>> extract_exports('export KEY="secret"')  # a single line of content works too
    {'KEY': 'secret'}

    A mistyped path is not silently read as empty content:

    >>> extract_exports('no/such/path/.env', on_missing='raise')
    Traceback (most recent call last):
      ...
    FileNotFoundError: [Errno 2] No such config file: 'no/such/path/.env'

    Use case:
    ---------

    You have access to environment variables through ``os.environ``, but
    if you want to extract exports from only a specific file (env vars are often
    placed in different linked files), or the exports are defined in a string you hold,
    then this simple parser can be useful.

    """
    validate_on_missing(on_missing)
    if isinstance(exports, os.PathLike):
        exports = os.fspath(exports)
    if "\n" not in exports and not export_line_p.search(exports):  # a filepath
        filepath = Path(resolve_path(exports))
        if _is_file(filepath):
            exports = filepath.read_text()
        elif exports.strip():
            report_missing_config_file(
                exports, on_missing=on_missing, stacklevel=2, resolved_path=filepath
            )
    return dict(
        filter(
            None,
            map(
                _extract_name_and_value_from_export_line, export_line_p.findall(exports)
            ),
        )
    )


def source_config_params(*config_params):
    """A decorator factory that sources config params, based on their names, to a config
    getter that will be provided when calling the wrapped function.

    :param config_params: The names of the config params to source
    :return: A decorator that sources the config params to the config getter

    >>> @source_config_params('a', 'b')
    ... def foo(a, b, c):
    ...     return a, b, c
    >>> config = {'a': 1, 'b': 2, 'c': 3}
    >>> foo(a='a', b='b', c=3, _config_getter=config.get)
    (1, 2, 3)

    A common use case is when you need to partialize a function with configs but the
    config source is not defined yet.

    >>> from functools import partial
    >>> bar = partial(foo, a='a')

    `a` is set, but you'll be able to call `bar` with different config sources,

    >>> bar(b='b', c=3, _config_getter=config.get)
    (1, 2, 3)
    >>> other_config = {'a': 11, 'b': 22, 'c': 33}
    >>> bar(b='b', c=3, _config_getter=other_config.get)
    (11, 22, 3)

    What if the function as kwargs? No problem, the decorator will handle it. Just
    make sure to use the same names for the kwargs as the config params.

    >>> @source_config_params('a', 'b', 'd')
    ... def foo(a, b, c, **kwargs):
    ...     return a, b, c, kwargs
    >>> config = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
    >>> foo(a='a', b='b', c=3, d='d', _config_getter=config.get)
    (1, 2, 3, {'d': 4})

    As you can see, `d` is sourced as well.
    """

    def wrapper(func):
        sig = Sig(func)

        @sig.add_params(["_config_getter"])
        def wrapped_func(*args, _config_getter, **kwargs):
            def source(k, v):
                if k == sig.var_keyword_name:
                    return {
                        kk: _config_getter(vv) if kk in config_params else vv
                        for kk, vv in v.items()
                    }
                else:
                    return _config_getter(v) if k in config_params else v

            arguments = sig.map_arguments_from_variadics(*args, **kwargs)
            arguments = {k: source(k, v) for k, v in arguments.items()}

            _args, _kwargs = sig.mk_args_and_kwargs(arguments)

            return func(*_args, **_kwargs)

        return wrapped_func

    return wrapper
