# config2py.base

Base for getting configs from various sources and formats

### Functions

| [`ask_user_for_key`](#config2py.base.ask_user_for_key)([key, prompt_template, ...])     | Ask the user for the value of `key`, optionally saving it.                         |
|----------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| [`get_config`](#config2py.base.get_config)([key, sources, default, egress, ...])  | Get a config value from a list of sources                                          |
| [`gettable_containers`](#config2py.base.gettable_containers)(sources[, val_is_valid, ...]) | Convert an iterable of sources into `GettableContainers`                           |
| `is_not_empty`(val)                                                                                |                                                                                    |
| `is_not_none_nor_empty`(x)                                                                         |                                                                                    |
| [`sources_chainmap`](#config2py.base.sources_chainmap)(sources[, val_is_valid, ...])    | Create a `ChainMap` from a list of sources                                         |
| [`user_gettable`](#config2py.base.user_gettable)([save_to, prompt_template, ...])    | Create a `GettableContainer` that asks the user for a value, optionally saving it. |

### Classes

| [`FuncBasedGettableContainer`](#config2py.base.FuncBasedGettableContainer)(getter[, ...])   | A class that wraps a `Callable[[KT], VT]` function so it has a (partial) Mapping[KT, TT] interface.   |
|----------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| [`GettableContainer`](#config2py.base.GettableContainer)(\*args, \*\*kwargs)       | `Containers` that are "gettable"".                                                                    |

### *class* config2py.base.FuncBasedGettableContainer(getter, val_is_valid=<function always_true>, config_not_found_exceptions=(<class 'Exception'>, ))

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

A class that wraps a `Callable[[KT], VT]` function so it has a (partial)
Mapping[KT, TT] interface. It is “partial” in the sense that it only implements
`__getitem__`, raise a `KeyError` when a key can’t be computed.
This is the standard for `Mapping` types, which enables us to use the
`FuncBasedGettable` in a `collections.ChainMap` to catch the error and move on
to the next source.

```pycon
>>> def getter(k):
...     if k == 'foo':
...         return 'quux'
...     elif k == 'green':
...         return 'eggs'
...     else:
...         raise RuntimeError(f"I don't handle that: {k}")
>>> gc = FuncBasedGettableContainer(getter)
>>> gc['foo']
'quux'
>>> gc['green']
'eggs'
```

Observe below that though the `getter` function raises a `RuntimeError`, the
`FuncBasedGettableContainer` raises a `KeyError`, to conform to the
`Mapping` protocol.

```pycon
>>> gc['no_a_key']
Traceback (most recent call last):
...
KeyError: 'no_a_key'
```

The `KeyError` message is just the key: neither the upstream exception text nor
the rejected value is interpolated into it, since getters commonly wrap credential
checks and these errors commonly end up in logs. The upstream exception is still
available, through the standard exception chain:

```pycon
>>> try:
...     gc['no_a_key']
... except KeyError as e:
...     print(type(e.__cause__).__name__, e.__cause__, sep=': ')
RuntimeError: I don't handle that: no_a_key
```

Note that by default, `FuncBasedGettableContainer` will catch all `Exception`
exceptions, but you can specify a different set of exceptions to catch.

Note as well that you can specify a `val_is_valid` function that will be used to
check the value returned by the `getter` function. If the value is not valid, a
`KeyError` will also be raised.
This is useful, for example, when you have a function that returns a sentinel like
`None` instead of raising an exception, but you want to treat that as a
`KeyError`.

```pycon
>>> def getter(k):
...     if k == 'foo':
...         return 'quux'
...     elif k == 'green':
...         return 'eggs'
...     else:
...         return None
>>> gc = FuncBasedGettableContainer(getter, val_is_valid=lambda x: x is not None)
>>> gc['foo']
'quux'
>>> gc['no_a_key']
Traceback (most recent call last):
...
KeyError: 'no_a_key'
```

#### val_is_valid()

Function that just returns True.

* **Return type:**
  [`bool`](https://docs.python.org/3/library/functions.html#bool)

### *class* config2py.base.GettableContainer(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

`Containers` that are “gettable””.

By “gettable”, we mean that we can fetch an element from `obj` with brackets:
`obj[k]`. That is, `obj` has a `__getitem__` method.
A `Container` means that `obj` has a `__contains__` method, i.e. the
expression `k in obj` is valid.

```pycon
>>> isinstance(3, GettableContainer)  # 3 is not Gettable (can't do 3[...])
False
```

But `dict`, `list`, and `str` are GettableContainer:

```pycon
>>> isinstance([1, 2, 3], GettableContainer)
True
>>> isinstance({'foo': 'bar'}, GettableContainer)
True
>>> isinstance('foo', GettableContainer)
True
```

Note that so are their types:

```pycon
>>> all(isinstance(c, GettableContainer) for c in (list, dict, str))
True
```

But `set` is not a `GettableContainer`.

```pycon
>>> myset = {1, 2, 3}
>>> isinstance(myset, GettableContainer)
False
```

This is because a `set` is a `Container`, but it is not gettable:

```pycon
>>> 4 in myset  # set is a container
False
>>> myset[4]  # ... but not gettable
Traceback (most recent call last):
...
TypeError: 'set' object is not subscriptable
```

### config2py.base.ask_user_for_key(key=None, \*, prompt_template='Enter a value for {}: ', save_to=None, save_condition=<function is_not_empty>, user_asker=<function ask_user_for_input>, egress=None)

Ask the user for the value of `key`, optionally saving it.

* **Parameters:**
  * **key** – The key to ask the user for. If `None`, a “curried” version of
    `ask_user_for_key` is returned, so you can specify the key later.
  * **prompt_template** – A template string to prompt the user with. It should
    contain a placeholder for the key, e.g. `"Enter a value for {}: "`.
  * **save_to** (`Union`[[`MutableMapping`](https://docs.python.org/3/library/collections.abc.html#collections.abc.MutableMapping), [`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`TypeVar`](https://docs.python.org/3/library/typing.html#typing.TypeVar)(`KT`), [`TypeVar`](https://docs.python.org/3/library/typing.html#typing.TypeVar)(`VT`)], [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)], [`None`](https://docs.python.org/3/library/constants.html#None)]) – Where to save the user’s response: a `MutableMapping` (or
    anything with a `__setitem__`), or a `(key, value)` saver function.
    If `None`, the response is not saved. See `_resolve_saver`.
  * **save_condition** – A function of the value, deciding whether to save it.
  * **user_asker** – A function that takes a prompt string and returns the user’s
    response.
  * **egress** ([`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable) | [`None`](https://docs.python.org/3/library/constants.html#None)) – A `(key, value)` function to apply to the user’s response before
    returning (and saving) it.

The value can be saved to any `MutableMapping`:

```pycon
>>> store = {}
>>> ask_user_for_key('some_key', save_to=store, user_asker=lambda prompt: 'val')
'val'
>>> store
{'some_key': 'val'}
```

… or to a `(key, value)` function, when saving isn’t a simple write:

```pycon
>>> saved = []
>>> ask_user_for_key(
...     'some_key',
...     save_to=lambda k, v: saved.append((k, v)),
...     user_asker=lambda prompt: 'val',
... )
'val'
>>> saved
[('some_key', 'val')]
```

### config2py.base.get_config(key=None, sources=None, \*, default=Sentinel('no_default'), egress=None, val_is_valid=<function always_true>, config_not_found_exceptions=(<class 'Exception'>, ))

Get a config value from a list of sources

A source can be a function or a `GettableContainer`.
(A `GettableContainer` is anything that can be indexed with brackets: `obj[k]`,
like `dict`, `list`, `str`, etc..).

Let’s take two sources: a `dict` and a `Callable`.

```pycon
>>> def func(k):
...     if k == 'foo':
...         return 'quux'
...     elif k == 'green':
...         return 'eggs'
...     else:
...         raise RuntimeError(f"I don't handle that: {k}")
>>> dict_ = {'foo': 'bar', 'baz': 'qux'}
>>> sources = [func, dict_]
```

See that `get_config` go through the sources in the order they were listed,
and returns the first value it finds (or manages to compute) for the key:

`get_config` finds `'foo'` in the very first source (`func`):

```pycon
>>> get_config('foo', sources)
'quux'
```

But `baz` makes `func` raise an error, so it goes to the next source: `dict_`.
There, it finds `'baz'` and returns its value:

```pycon
>>> get_config('baz', sources)
'qux'
```

On the other hand, no one manages to find a config value for `'no_a_key'`, so
`get_config` raises an error:

```pycon
>>> get_config('no_a_key', sources)
Traceback (most recent call last):
...
config2py.errors.ConfigNotFound: Could not find config for key: no_a_key
```

But if you provide a default value, it will return that instead:

```pycon
>>> get_config('no_a_key', sources, default='default')
'default'
```

You can also provide a function that will be called on the value before it is
returned. This is useful if you want to do some post-processing on the value,
or if you want to make sure that the value is of a certain type:

This “search the next source if the previous one fails” behavior may not be what
you want in some situations, since you’d be hiding some errors that you might
want to be aware of. This is why allow you to specify what exceptions should
actually be considered as “config not found” exceptions, through the
`config_not_found_exceptions` argument, which defaults to `Exception`.

Further, your sources may return a value, but not one that you consider valid:
For example, a sentinel like `None`. In this case you may want the search to
continue. This is what the `val_is_valid` argument is for. It is a function
that takes a value and returns a boolean. If it returns `False`, the search
will continue. If it returns `True`, the search will stop and the value will
be returned.

Finally, we have `egress : Callable[[KT, TT], VT]`.
This is a function that takes a key and a value, and
returns a value. It is called after the value has been found, and its return
value is the one that is returned by `get_config`. This is useful if you want
to do some post-processing on the value, or before you return the value, or if you
want to do some caching.

```pycon
>>> config_store = dict()
>>> def store_before_returning(k, v):
...    config_store[k] = v
...    return v
>>> get_config('foo', sources, egress=store_before_returning)
'quux'
>>> config_store
{'foo': 'quux'}
```

Note that a source can be a callable or a `GettableContainer` (most of the
time, a `Mapping` (e.g. `dict`)).
Here, you should be compelled to use the resources of `dol`
([https://pypi.org/project/dol/](https://pypi.org/project/dol/)) which will allow you to make 

```
``
```

Mapping\`\`s for all
sorts of data sources.

For more info, see: [https://github.com/i2mint/config2py/issues/4](https://github.com/i2mint/config2py/issues/4)

### config2py.base.gettable_containers(sources, val_is_valid=<function always_true>, config_not_found_exceptions=(<class 'Exception'>, ))

Convert an iterable of sources into `GettableContainers`

* **Return type:**
  [`Iterable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterable)[[`GettableContainer`](#config2py.base.GettableContainer)]

### config2py.base.sources_chainmap(sources, val_is_valid=<function always_true>, config_not_found_exceptions=(<class 'Exception'>, ))

Create a `ChainMap` from a list of sources

* **Return type:**
  [`ChainMap`](https://docs.python.org/3/library/collections.html#collections.ChainMap)

### config2py.base.user_gettable(save_to=None, \*, prompt_template='Enter a value for {}: ', egress=None, user_asker=<function ask_user_for_input>, val_is_valid=<function is_not_empty>, config_not_found_exceptions=(<class 'Exception'>, ))

Create a `GettableContainer` that asks the user for a value, optionally saving it.

* **Parameters:**
  * **save_to** (`Union`[[`MutableMapping`](https://docs.python.org/3/library/collections.abc.html#collections.abc.MutableMapping), [`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`TypeVar`](https://docs.python.org/3/library/typing.html#typing.TypeVar)(`KT`), [`TypeVar`](https://docs.python.org/3/library/typing.html#typing.TypeVar)(`VT`)], [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)], [`None`](https://docs.python.org/3/library/constants.html#None)]) – Where to save the user’s response: a `MutableMapping` (or
    anything with a `__setitem__`), or a `(key, value)` saver function.
    If `None`, the user’s response is not saved.
  * **prompt_template** – A template string to prompt the user with. It should
    contain a placeholder for the key, e.g. `"Enter a value for {}: "`.
  * **egress** ([`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable) | [`None`](https://docs.python.org/3/library/constants.html#None)) – A function to apply to the user’s response before returning it.
    This can be used to validate the response, for example.
  * **user_asker** – A function that asks the user for input. It should take a
    prompt string and return the user’s response.
  * **val_is_valid** ([`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`TypeVar`](https://docs.python.org/3/library/typing.html#typing.TypeVar)(`VT`)], [`bool`](https://docs.python.org/3/library/functions.html#bool)]) – A function that takes a value and returns a boolean. If it
    returns `False`, the user will be asked for a new value.
  * **config_not_found_exceptions** ([`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)[[`type`](https://docs.python.org/3/library/functions.html#type)[[`Exception`](https://docs.python.org/3/library/exceptions.html#Exception)], [`...`](https://docs.python.org/3/library/constants.html#Ellipsis)]) – An iterable of exceptions that should be
    considered as “config not found” exceptions. If the user’s response raises
    one of these exceptions, the user will be asked for a new value.
* **Returns:**
  A `GettableContainer` that asks the user for a value, optionally saving
  it.

### Example

```pycon
>>> s = user_gettable()
>>> v = s['SOME_KEY']
'SOME_VAL'
```

This will trigger a prompt for the user to enter the value of `SOME_KEY`.
When they do (say they entered ‘SOME_VAL’) it will return that value.

And if you specify a save_to store (usually a persistent MutableMapping made with
the `dol` package) then it will save the value to that store for future use.

```pycon
>>> d = dict(some='store')
>>> s = user_gettable(save_to=d)
>>> s['SOME_KEY']
'SOME_VAL'
>>> d
{'some': 'store', 'SOME_KEY': 'SOME_VAL'}
```

When saving isn’t a simple write (say you need to encrypt, or write to two
places), `save_to` can be a `(key, value)` function instead:

```pycon
>>> saved = []
>>> s = user_gettable(
...     save_to=lambda k, v: saved.append((k, v)),
...     user_asker=lambda prompt: 'SOME_VAL',
... )
>>> s['SOME_KEY']
'SOME_VAL'
>>> saved
[('SOME_KEY', 'SOME_VAL')]
```
