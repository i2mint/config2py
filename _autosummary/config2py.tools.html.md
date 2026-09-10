# config2py.tools

Various tools

### Functions

| [`extract_exports`](#config2py.tools.extract_exports)(exports)                   | Get a dict of `{name: value}` pairs from the `name="value" pairs of unix export lines (that is, lines of the ``export NAME="VALUE"` format        |
|---------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| [`get_configs_local_store`](#config2py.tools.get_configs_local_store)([config_src, ...]) | Get the local store of configs.                                                                                                                   |
| [`simple_config_getter`](#config2py.tools.simple_config_getter)([configs_src, ...])   | Make a simple config getter from a "central" config source specification.                                                                         |
| [`source_config_params`](#config2py.tools.source_config_params)(\*config_params)      | A decorator factory that sources config params, based on their names, to a config getter that will be provided when calling the wrapped function. |

### config2py.tools.extract_exports(exports)

Get a dict of `{name: value}` pairs from the `name="value" pairs of unix
export lines (that is, lines of the ``export NAME="VALUE"` format

* **Parameters:**
  **exports** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – Filepath or string contents thereof
* **Return type:**
  [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)
* **Returns:**
  A dict of extracted `{name: value}` pairs

```pycon
>>> extract_exports('export KEY="secret"\nexport TOKEN="arbitrary"')
{'KEY': 'secret', 'TOKEN': 'arbitrary'}
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

### config2py.tools.simple_config_getter(configs_src='/home/runner/.config/config2py/configs', \*, first_look_in_env_vars=True, ask_user_if_key_not_found=None, config_store_factory=<function get_configs_local_store>)

Make a simple config getter from a “central” config source specification.

The purpose of this function is to implement a common pattern of getting configs:
One that, by default (but optionally), looks in environment variables first,
then in a central config store, created via a simple `configs_src` specification
and then, if the key is not found in this “central” store, optionally (but not by
default) asks the user for the value and stores it in the central config store.

* **Parameters:**
  * **configs_src** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – A specification of the central config store. By default:
    If it’s a directory (with at least a slash), it’s assumed to be a folder of text files.
    If it’s a file, it’s assumed to be an ini or cfg file.
    If it’s a string, it’s assumed to be an app name, from which to create a folder
  * **first_look_in_env_vars** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Whether to look in environment variables first
  * **ask_user_if_key_not_found** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Whether to ask the user if the key is not found
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
