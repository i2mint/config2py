# config2py.tools

Various tools

### Functions

| [`extract_exports`](#config2py.tools.extract_exports)(exports, \*[, on_missing])   | Get a dict of `{name: value}` pairs from the `name="value" pairs of unix export lines (that is, lines of the ``export NAME="VALUE"` format        |
|-----------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| [`get_configs_local_store`](#config2py.tools.get_configs_local_store)([config_src, ...])   | Get the local store of configs.                                                                                                                   |
| [`simple_config_getter`](#config2py.tools.simple_config_getter)([configs_src, ...])     | Make a simple config getter from a "central" config source specification.                                                                         |
| [`source_config_params`](#config2py.tools.source_config_params)(\*config_params)        | A decorator factory that sources config params, based on their names, to a config getter that will be provided when calling the wrapped function. |

### Classes

| [`Configs`](#config2py.tools.Configs)                                |                                                                          |
|-----------------------------------------------------------------------------------------|--------------------------------------------------------------------------|
| [`SecureTextFiles`](#config2py.tools.SecureTextFiles)(\*args[, delete_func]) | A `dol.TextFiles` (one text file per key) whose value files are `0o600`. |

### config2py.tools.Configs

alias of [`SecureTextFiles`](#config2py.tools.SecureTextFiles)

### *class* config2py.tools.SecureTextFiles(\*args, delete_func=None, \*\*kwargs)

Bases: `TextFiles`

A `dol.TextFiles` (one text file per key) whose value files are `0o600`.

Config values are often secrets (API keys); plain `TextFiles` writes them with
the umask default (commonly world-readable `0o644`). Still an `isinstance`
of `TextFiles`, so it is a drop-in replacement
(see [https://github.com/i2mint/config2py/issues/33](https://github.com/i2mint/config2py/issues/33)).

Like `TextFiles`, values are UTF-8 on disk whatever the locale, and a failed
write raises `KeyError`. Unlike it, the value is encoded before the file is
opened, so an unencodable value doesn’t leave an emptied file behind
(see [https://github.com/i2mint/config2py/issues/35](https://github.com/i2mint/config2py/issues/35)).

Like `TextFiles` (and `open`), a value file that is a symlink is followed, and
its target is the file written (and tightened to `0o600`). That is deliberate:
it keeps value files symlinked from elsewhere (a dotfiles repo, say) working, and
in config2py’s own configs folder (`0o700`) only its owner can plant a link
(see [https://github.com/i2mint/config2py/issues/37](https://github.com/i2mint/config2py/issues/37)). A folder you pass in is not
checked: if others can write to it, they can plant a link that redirects your
secrets, so keep such stores in folders only you can write to
(see [https://github.com/i2mint/config2py/issues/45](https://github.com/i2mint/config2py/issues/45)).

`__setitem__` relies on three `dol` internals: `_id_of_key`,
`store.validate_key` and `_data_of_obj`. `dol` is unpinned, so
`test_secure_text_files_dol_contract` checks they still exist.

### config2py.tools.extract_exports(exports, , on_missing='warn')

Get a dict of `{name: value}` pairs from the `name="value" pairs of unix
export lines (that is, lines of the ``export NAME="VALUE"` format

* **Parameters:**
  * **exports** – Filepath (`str` or `os.PathLike`) or string contents thereof
  * **on_missing** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – What to do when `exports` looks like a filepath (a single,
    non-blank line with no `export` in it) that is not an existing file:
    `"warn"` (the default) issues a `MissingConfigFileWarning` and returns
    `{}`, `"raise"` raises `FileNotFoundError`, `"ignore"` returns `{}`
    (see [https://github.com/i2mint/config2py/issues/27](https://github.com/i2mint/config2py/issues/27)).
* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)
* **Returns:**
  A dict of extracted `{name: value}` pairs

```pycon
>>> extract_exports('export KEY="secret"\nexport TOKEN="arbitrary"')
{'KEY': 'secret', 'TOKEN': 'arbitrary'}
>>> extract_exports('export KEY="secret"')  # a single line of content works too
{'KEY': 'secret'}
```

A mistyped path is not silently read as empty content:

```pycon
>>> extract_exports('no/such/path/.env', on_missing='raise')
Traceback (most recent call last):
  ...
FileNotFoundError: [Errno 2] No such config file: 'no/such/path/.env'
```

## Use case:

You have access to environment variables through `os.environ`, but
if you want to extract exports from only a specific file (env vars are often
placed in different linked files), or the exports are defined in a string you hold,
then this simple parser can be useful.

### config2py.tools.get_configs_local_store(config_src='/home/runner/.config/config2py/configs', , configs_name='configs')

Get the local store of configs.

* **Parameters:**
  **config_src** – A specification of the local config store. By default:
  If it’s a directory, it’s assumed to be a folder of text files.
  If it’s a file, it’s assumed to be an ini or cfg file.
  If it’s a string, it’s assumed to be an app name, from which to create a folder

#### NOTE
a directory is only recognized as such if `config_src` contains
`os.path.sep`. A bare name (e.g. `"configs"`) is always treated as an app
name, even if a directory of that name exists in the current working directory;
pass `"./configs"` (or an absolute path) to use that directory
(see [https://github.com/i2mint/config2py/issues/28](https://github.com/i2mint/config2py/issues/28)).

The default, `DFLT_CONFIG_FOLDER`, is config2py’s own configs folder. It is
created here, on first use, rather than at import
(see [https://github.com/i2mint/config2py/issues/26](https://github.com/i2mint/config2py/issues/26)).

### config2py.tools.simple_config_getter(configs_src='/home/runner/.config/config2py/configs', \*, first_look_in_env_vars=True, ask_user_if_key_not_found=None, config_store_factory=<function get_configs_local_store>)

Make a simple config getter from a “central” config source specification.

The purpose of this function is to implement a common pattern of getting configs:
One that, by default (but optionally), looks in environment variables first,
then in a central config store, created via a simple `configs_src` specification
and then, if the key is not found in this “central” store, optionally (but not by
default) asks the user for the value and stores it in the central config store.

* **Parameters:**
  * **configs_src** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – A specification of the central config store. By default:
    If it’s a directory (with at least a slash), it’s assumed to be a folder of text files.
    If it’s a file, it’s assumed to be an ini or cfg file.
    If it’s a string, it’s assumed to be an app name, from which to create a folder
  * **first_look_in_env_vars** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether to look in environment variables first
  * **ask_user_if_key_not_found** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether to ask the user if the key is not found
    (and subsequently store the key in the central config store)
  * **config_store_factory** ([`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)) – A function that takes a config source specification
    and returns the central config store

### config2py.tools.source_config_params(\*config_params)

A decorator factory that sources config params, based on their names, to a config
getter that will be provided when calling the wrapped function.

* **Parameters:**
  **config_params** – The names of the config params to source
* **Returns:**
  A decorator that sources the config params to the config getter

```pycon
>>> @source_config_params('a', 'b')
... def foo(a, b, c):
...     return a, b, c
>>> config = {'a': 1, 'b': 2, 'c': 3}
>>> foo(a='a', b='b', c=3, _config_getter=config.get)
(1, 2, 3)
```

A common use case is when you need to partialize a function with configs but the
config source is not defined yet.

```pycon
>>> from functools import partial
>>> bar = partial(foo, a='a')
```

`a` is set, but you’ll be able to call `bar` with different config sources,

```pycon
>>> bar(b='b', c=3, _config_getter=config.get)
(1, 2, 3)
>>> other_config = {'a': 11, 'b': 22, 'c': 33}
>>> bar(b='b', c=3, _config_getter=other_config.get)
(11, 22, 3)
```

What if the function as kwargs? No problem, the decorator will handle it. Just
make sure to use the same names for the kwargs as the config params.

```pycon
>>> @source_config_params('a', 'b', 'd')
... def foo(a, b, c, **kwargs):
...     return a, b, c, kwargs
>>> config = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
>>> foo(a='a', b='b', c=3, d='d', _config_getter=config.get)
(1, 2, 3, {'d': 4})
```

As you can see, `d` is sourced as well.
