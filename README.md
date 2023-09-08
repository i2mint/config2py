# `config2py`

Simplified reading and writing configurations from various sources and formats

To install:	```pip install config2py```

[Documentation](https://i2mint.github.io/config2py/)


# Best of

## `get_config`

Get a config value from a list of sources.

This function acts as a mini-framework to construct config accessors including defining multiple sources of where to find these configs, 
including asking the user for a config value (and optionally saving it for them).

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
