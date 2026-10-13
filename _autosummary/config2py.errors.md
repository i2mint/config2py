# config2py.errors

Error classes for config2py.

### Functions

| [`report_missing_config_file`](#config2py.errors.report_missing_config_file)(path, \*[, ...])   | Act on a config source `path` that is not an existing file.           |
|------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------|
| [`validate_on_missing`](#config2py.errors.validate_on_missing)(on_missing)               | Check that `on_missing` is one of `ON_MISSING_OPTIONS` and return it. |

### Exceptions

| [`Config2PyError`](#config2py.errors.Config2PyError)           | Base class for config2py errors.                                                                                                                                                       |
|---------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`Config2PyWarning`](#config2py.errors.Config2PyWarning)         | Warnings issued by config2py (e.g. permissions it could not tighten).                                                                                                                  |
| [`ConfigNotFound`](#config2py.errors.ConfigNotFound)           | Raised when a config file is not found.                                                                                                                                                |
| [`MissingConfigFileWarning`](#config2py.errors.MissingConfigFileWarning) | A path given as a config source is not an existing file, so it was read as empty (see [https://github.com/i2mint/config2py/issues/27](https://github.com/i2mint/config2py/issues/27)). |

### *exception* config2py.errors.Config2PyError

Bases: [`Exception`](https://docs.python.org/3/builtins/exceptions.html#Exception)

Base class for config2py errors.

### *exception* config2py.errors.Config2PyWarning

Bases: [`UserWarning`](https://docs.python.org/3/builtins/exceptions.html#UserWarning)

Warnings issued by config2py (e.g. permissions it could not tighten).

### *exception* config2py.errors.ConfigNotFound

Bases: [`Config2PyError`](#config2py.errors.Config2PyError)

Raised when a config file is not found.

### *exception* config2py.errors.MissingConfigFileWarning

Bases: [`Config2PyWarning`](#config2py.errors.Config2PyWarning)

A path given as a config source is not an existing file, so it was read as
empty (see [https://github.com/i2mint/config2py/issues/27](https://github.com/i2mint/config2py/issues/27)).

### config2py.errors.report_missing_config_file(path, , on_missing='warn', stacklevel=2)

Act on a config source `path` that is not an existing file.

* **Parameters:**
  * **on_missing** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – `"warn"` issues a `MissingConfigFileWarning`,
    `"raise"` raises `FileNotFoundError`, `"ignore"` does nothing.
  * **stacklevel** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – Passed to `warnings.warn`, so the warning points at the
    caller’s code (`2` is the caller of this function).

### config2py.errors.validate_on_missing(on_missing)

Check that `on_missing` is one of `ON_MISSING_OPTIONS` and return it.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
