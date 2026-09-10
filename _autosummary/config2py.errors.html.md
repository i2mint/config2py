# config2py.errors

Error classes for config2py.

### Exceptions

| [`Config2PyError`](#config2py.errors.Config2PyError)   | Base class for config2py errors.        |
|-------------------------------------------------------------------|-----------------------------------------|
| [`ConfigNotFound`](#config2py.errors.ConfigNotFound)   | Raised when a config file is not found. |

### *exception* config2py.errors.Config2PyError

Bases: [`Exception`](https://docs.python.org/3/library/exceptions.html#Exception)

Base class for config2py errors.

### *exception* config2py.errors.ConfigNotFound

Bases: [`Config2PyError`](#config2py.errors.Config2PyError)

Raised when a config file is not found.
