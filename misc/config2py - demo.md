```python

```

# The cherry on top: `config_getter`


```python
from config2py import config_getter
```

Let's start with an extremely convenient, no questions asked, object.

What `config2py.config_getter(key)` will do is:
* search for `key` in your environment variables, and if not found...
* ... search for it in a `config2py` directory (automatically made) of the standard config folder of your system (following XDG standards on Unix/Linux/macOS: `~/.config`, `%APPDATA%` on Windows), and if not found...
* ... ask the user to enter the value that key should have, and then put it in the `config2py` directory so it's persisted.

<img width="341" alt="image" src="https://github.com/i2mint/config2py/assets/1906276/09f287a8-05f9-4590-8664-10feda9ad617">


```python
config_getter('HOME')  # if you are using Linux/MacOS
# config_getter('USERPROFILE')  # if you are using Windows
```




    '/Users/thorwhalen'



Now, normally all systems come with a `HOME` environment variable (or a `USERPROFILE` on windows), so the above should always work fine. 
But see what happens if you ask for a key that is not an environment variable:


```python
my_config_val = config_getter('_TEST_NON_EXISTING_KEY_')  # triggers a user input dialog
# ... I enter 'my config value' in the dialog, and then...
```


```python
my_config_val
```




    'my config value'



But if I do that again (even on a different day, somewhere else (on my same computer), in a different session), it will get me the value I entered in the user input dialog.


```python
my_config_val = config_getter('_TEST_NON_EXISTING_KEY_')  # does not trigger input dialog
my_config_val
```




    'my config value'



And of course, we give you a means to delete that value, since `config_getter` has a `local_configs` mapping (think `dict`) to the local files where it has been stored. 
You can do all the usual stuff you do with a `dict` (except the effects will be on local files), 
like list the keys (with `list(.)`), get values for a key (with `.[key]`), ask for the number of keys (`len(.)`), and, well, delete stuff:


```python
if '_TEST_NON_EXISTING_KEY_' in config_getter.configs:
    del config_getter.configs['_TEST_NON_EXISTING_KEY_']

```

Where **is** this configs store actually stored? 
Well, you will get to chose, but by default it's in a `config2py` directory (automatically made) of the standard config folder of your system (following XDG standards on Unix/Linux/macOS: `~/.config`, `%APPDATA%` on Windows).

This tool allows you to:
* not have to set up any special configs stuff (unless you want/need to)
* enables you to share your notebooks (CLIs etc.) with others without having to polute the code with configs-setup gunk...
* ... including when you put local file/folder paths (or worse, secrets) in your notebook or code, which others then have to edit (instead, here, just enter a probably-unique name for the needed resource, then enter your filepath in the user input dialog instead)

This is very convenient situation where user input (via things like `__builtins__.input` or `getpass.getpass` etc) is available. But you should use this only in iteractive situations, **anywhere where there's not a user to see and respond to the builtin user input dialog**

Don't fret though, this `config_getter` is just our no-BS entry point to much more. 
Let's have a slight look under its hood to see what else we can do with it. 

And of course, if you're that type, you can already have a look at [the documentation](https://i2mint.github.io/config2py/)

# Setting the config key search path

If you check out the code for `config_getter`, you'll find that all it is is:

```python
config_getter = get_config(sources=[
    os.environ,  # search in environment variables first
    local_configs,  # then search in local_configs
    user_gettable(local_configs)  # if not found, ask the user and store in local_configs
])
config_getter.configs = local_configs
```

So you see that you can easily define your own sources for configs, and in what order they should be searched. If you don't want that "ask the user for the value" thing, you can just remove the `user_gettable(local_configs)` part. If you wanted instead to add a place to look before the environment variables -- say, you want to look in to local variables of the scope the config getter is **defined** (not called), you can stick `locals()` in front of the `os.environ`.

Let's work through a custom-made `config_getter`.

```python
from config2py import get_config, user_gettable
from dol import TextFiles
import os

my_configs = TextFiles('~/.my_configs/')  # Note, to run this, you'd need to have such a directory!
# (But you can also use my_configs = dict() if you want.)
config_getter = get_config(sources=[locals(), os.environ, my_configs, user_gettable(my_configs)])
```

Now let's see what happens when we do:

```python
config_getter('SOME_CONFIG_KEY')
```

Well, it will first look in `locals()`, which is a dictionary containing local variables
where the `config_getter` was **defined** (careful -- not called!!). 
This is desirable sometimes when you define your `config_getter` in a module that has other python variables you'd like to use. 

Assuming it doesn't find such a key in `locals()` it goes on to try to find it in 
`os.environ`, which is a dict containing system environment variables. 

Assuming it doesn't find it there either (that is, doesn't find a file with that name in 
the directory `~/.my_configs/`), it will prompt the user to enter the value of that key.
The function finally returns with the value that the user entered.

But there's more!

Now look at what's in `my_configs`! 
If you've used `TextFiles`, look in the folder to see that there's a new file.
Either way, if you do:

```python
my_configs['SOME_CONFIG_KEY']
```

You'll now see the value the user entered.

This means what? This means that the next time you try to get the config:

```python
config_getter('SOME_CONFIG_KEY')
```

It will return the value that the user entered last time, without prompting the 
user again.


# A few notable tools you can import from config2py

* `get_config`: Get a config value from a list of sources. See more below.
* `user_gettable`: Create a ``GettableContainer`` that asks the user for a value, optionally saving it.
* `ask_user_for_input`: Ask the user for input, optionally masking, validating and transforming the input.
* `get_app_folder`: Returns the full path of a directory suitable for storing application-specific data for a given app name and folder kind (config, data, cache, state, runtime).
* `get_app_config_folder`: Specialized version of `get_app_folder` for configuration files.
* `get_app_data_folder`: Specialized version of `get_app_folder` for application data.
* `get_configs_local_store`: Get a local store (mapping interface of local files) of configs for a given app or package name
* `configs`: A default local store (mapping interface of local files) for configs.

## get_config

Get a config value from a list of sources.

This function acts as a mini-framework to construct config accessors including defining 
multiple sources of where to find these configs, 

A source can be a function or a ``GettableContainer``.
(A ``GettableContainer`` is anything that can be indexed with brackets: ``obj[k]``,
like ``dict``, ``list``, ``str``, etc..).

Let's take two sources: a ``dict`` and a ``Callable``.

    >>> def func(k):
    ...     if k == 'foo':
    ...         return 'quux'
    ...     elif k == 'green':
    ...         return 'eggs'
    ...     else:
    ...         raise RuntimeError(f"I don't handle that: {k}")
    >>> dict_ = {'foo': 'bar', 'baz': 'qux'}
    >>> sources = [func, dict_]


See that ``get_config`` go through the sources in the order they were listed,
and returns the first value it finds (or manages to compute) for the key:

``get_config`` finds ``'foo'`` in the very first source (``func``):

    >>> get_config('foo', sources)
    'quux'

But ``baz`` makes ``func`` raise an error, so it goes to the next source: ``dict_``.
There, it finds ``'baz'`` and returns its value:

    >>> get_config('baz', sources)
    'qux'

On the other hand, no one manages to find a config value for ``'no_a_key'``, so
``get_config`` raises an error:

    >>> get_config('no_a_key', sources)
    Traceback (most recent call last):
    ...
    config2py.errors.ConfigNotFound: Could not find config for key: no_a_key

But if you provide a default value, it will return that instead:

    >>> get_config('no_a_key', sources, default='default')
    'default'

You can also provide a function that will be called on the value before it is
returned. This is useful if you want to do some post-processing on the value,
or if you want to make sure that the value is of a certain type:

This "search the next source if the previous one fails" behavior may not be what
you want in some situations, since you'd be hiding some errors that you might
want to be aware of. This is why allow you to specify what exceptions should
actually be considered as "config not found" exceptions, through the
``config_not_found_exceptions`` argument, which defaults to ``Exception``.

Further, your sources may return a value, but not one that you consider valid:
For example, a sentinel like ``None``. In this case you may want the search to
continue. This is what the ``val_is_valid`` argument is for. It is a function
that takes a value and returns a boolean. If it returns ``False``, the search
will continue. If it returns ``True``, the search will stop and the value will
be returned.

Finally, we have ``egress : Callable[[KT, TT], VT]``.
This is a function that takes a key and a value, and
returns a value. It is called after the value has been found, and its return
value is the one that is returned by ``get_config``. This is useful if you want
to do some post-processing on the value, or before you return the value, or if you
want to do some caching.

    >>> config_store = dict()
    >>> def store_before_returning(k, v):
    ...    config_store[k] = v
    ...    return v
    >>> get_config('foo', sources, egress=store_before_returning)
    'quux'
    >>> config_store
    {'foo': 'quux'}

    Note that a source can be a callable or a ``GettableContainer`` (most of the
    time, a ``Mapping`` (e.g. ``dict``)).
    Here, you should be compelled to use the resources of ``dol``
    (https://pypi.org/project/dol/) which will allow you to make ``Mapping``s for all
    sorts of data sources.

For more info, see: https://github.com/i2mint/config2py/issues/4




# user_gettable

So, what's that `user_gettable`? 

It's a way for you to specify that the system should ask the user for a key, and optionally save it somewhere, plus many other parameters (like what to ask the user, etc.)


```python
from config2py.base import user_gettable

s = user_gettable()
s['SOME_KEY'] 
# will trigger a prompt for the user to enter the value of SOME_KEY
# ... and when they do (say they entered 'SOME_VAL') it will return that value

# And if you specify a save_to store (usually a persistent MutableMapping made with the dol package)
# then it will save the value to that store for future use
d = dict(some='store')
s = user_gettable(save_to=d)
s['SOME_KEY'] 
```

More on that another day...


```python

```
