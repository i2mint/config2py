# config2py

Tools to read and write configurations from various sources and formats

### Functions

| [`extract_exports`](#config2py.extract_exports)(exports, \*[, on_missing])        | Get a dict of `{name: value}` pairs from the `name="value" pairs of unix export lines (that is, lines of the ``export NAME="VALUE"` format   |
|----------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------|
| [`get_configs_local_store`](#config2py.get_configs_local_store)([config_src, ...])        | Get the local store of configs.                                                                                                              |
| [`simple_config_getter`](#config2py.simple_config_getter)([configs_src, ...])          | Make a simple config getter from a "central" config source specification.                                                                    |
| [`get_config`](#config2py.get_config)([key, sources, default, egress, ...])  | Get a config value from a list of sources                                                                                                    |
| [`user_gettable`](#config2py.user_gettable)([save_to, prompt_template, ...])    | Create a `GettableContainer` that asks the user for a value, optionally saving it.                                                           |
| [`sources_chainmap`](#config2py.sources_chainmap)(sources[, val_is_valid, ...])    | Create a `ChainMap` from a list of sources                                                                                                   |
| [`ask_user_for_input`](#config2py.ask_user_for_input)(prompt[, default, ...])        | Ask the user for input, optionally masking, validating and transforming the input.                                                           |
| [`get_app_config_folder`](#config2py.get_app_config_folder)([app_name, ...])            | Retrieve or create the app directory specific to the given app name and folder kind.                                                         |
| [`get_app_data_folder`](#config2py.get_app_data_folder)([app_name, ...])              | Retrieve or create the app directory specific to the given app name and folder kind.                                                         |
| [`get_app_folder`](#config2py.get_app_folder)([app_name, setup_callback, ...])   | Retrieve or create the app directory specific to the given app name and folder kind.                                                         |
| [`get_configs_folder_for_app`](#config2py.get_configs_folder_for_app)([app_name, ...])       | Retrieve or create the configs directory specific to the given app name.                                                                     |
| [`is_repl`](#config2py.is_repl)()                                         | Determines if the Python interpreter is running in REPL.                                                                                     |
| [`parse_assignments_from_py_source`](#config2py.parse_assignments_from_py_source)(source_code, \*) | Parse assignments from python source code.                                                                                                   |
| [`process_path`](#config2py.process_path)(\*path[, ensure_dir_exists, ...])    | Process a path string, ensuring it exists, and optionally expanding user.                                                                    |
| [`ensure_seeded`](#config2py.ensure_seeded)(target, package_name, ...[, ...])   | Copy a bundled seed file to *target* if it does not already exist.                                                                           |
| [`register_extension`](#config2py.register_extension)(ext, loader, dumper)           | Register loader/dumper for a file extension.                                                                                                 |
| `config_getter`([key, sources, default, ...])                                                      | Get a config value from a list of sources                                                                                                    |

### Classes

| [`ConfigStore`](#config2py.ConfigStore)(source, \*[, defaults, ...])         | Persister (read, write, delete) for ini configs.                      |
|---------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------|
| [`ConfigReader`](#config2py.ConfigReader)(source, \*[, on_missing])           | A KvReader to read config files                                       |
| [`Configs`](#config2py.Configs)                                          |                                                                       |
| [`AppData`](#config2py.AppData)(app_name, \*[, package_name, ...])       | Per-user data directory facade for a Python application.              |
| [`SyncStore`](#config2py.SyncStore)(loader, dumper)                        | A MutableMapping that automatically syncs changes to backing storage. |
| [`FileStore`](#config2py.FileStore)(filepath, \*[, key_path, loader, ...]) | A SyncStore backed by a file with automatic format detection.         |
| [`JsonStore`](#config2py.JsonStore)(filepath, \*[, key_path, indent, ...]) | A FileStore specialized for JSON files.                               |

### Exceptions

| [`Config2PyError`](#config2py.Config2PyError)              | Base class for config2py errors.                                                                                                                                                                                                                                                           |
|------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`Config2PyWarning`](#config2py.Config2PyWarning)            | Warnings issued by config2py (e.g. permissions it could not tighten).                                                                                                                                                                                                                      |
| [`ConfigNotFound`](#config2py.ConfigNotFound)              | Raised when a config file is not found.                                                                                                                                                                                                                                                    |
| [`InsecureConfigFolderWarning`](#config2py.InsecureConfigFolderWarning) | A folder used to store config values (which may be secrets) is owned by another user or writable by others, who could plant a symlink or file there to redirect or read those values (see [https://github.com/i2mint/config2py/issues/45](https://github.com/i2mint/config2py/issues/45)). |
| [`MissingConfigFileWarning`](#config2py.MissingConfigFileWarning)    | A path given as a config source is not an existing, readable file (it is missing, a folder, or unreadable), so it was read as empty (see [https://github.com/i2mint/config2py/issues/27](https://github.com/i2mint/config2py/issues/27) and /43).                                          |

### *class* config2py.AppData(app_name, , package_name=None, seed_data_dir='_seed_data')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Per-user data directory facade for a Python application.

Binds an application name (and optional Python package name) once and
provides convenient access to:

* **resources** — editable reference data seeded from the package on
  first access (`~/.local/share/<app>/resources/`).
* **config** — user preference files, also seeded on first access
  (`~/.config/<app>/`).
* **artifact directories** — runtime-generated data organised by kind
  (`~/.local/share/<app>/artifacts/<kind>/`).

Seed files are read via `importlib.resources` from
`<package_name>._seed_data.{resources,config}/`.

* **Parameters:**
  * **app_name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – The application name used for the directory under the
    XDG root (e.g. `"my_app"` → `~/.local/share/my_app`).
  * **package_name** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – The top-level Python package that contains the
    `_seed_data` directory.  Defaults to *app_name*.
  * **seed_data_dir** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Name of the seed-data sub-package inside the
    Python package (default `"_seed_data"`).

### Example

```pycon
>>> app = AppData("myapp", package_name="myapp")
>>> app.app_folder()
PosixPath('/Users/.../.local/share/myapp')
```

#### app_folder(, folder_kind='data')

Return the app directory for *folder_kind*, creating it if needed.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

#### get_artifact_dir(kind)

Return (and create) an artifact sub-directory for *kind*.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

#### get_config(name)

Return a config file path, seeding from package data if missing.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

#### get_resource(name)

Return a user resource path, seeding from package data if missing.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

### *exception* config2py.Config2PyError

Bases: [`Exception`](https://docs.python.org/3/builtins/exceptions.html#Exception)

Base class for config2py errors.

### *exception* config2py.Config2PyWarning

Bases: [`UserWarning`](https://docs.python.org/3/builtins/exceptions.html#UserWarning)

Warnings issued by config2py (e.g. permissions it could not tighten).

### *exception* config2py.ConfigNotFound

Bases: [`Config2PyError`](config2py.errors.html.md#config2py.errors.Config2PyError)

Raised when a config file is not found.

### *class* config2py.ConfigReader(source, , on_missing='warn', \*\*kwargs)

Bases: [`ConfigStore`](config2py.s_configparser.html.md#config2py.s_configparser.ConfigStore)

A KvReader to read config files

```pycon
>>> from config2py.s_configparser import ConfigReader
>>>
>>> # from a (pretend) file
>>> from io import BytesIO, StringIO
>>> file_content_bytes = b'''
... [Paths]
... home_dir: /Users
... my_dir: %(home_dir)s/lumberjack
... my_pictures: %(my_dir)s/Pictures
...
... [Escape]
... gain: 80%%  # use a %% to escape the % sign (% is the only character that needs to be escaped)'''
>>> c = ConfigReader(file_content_bytes)  # get configs from the bytes
>>> list(c)
['DEFAULT', 'Paths', 'Escape']
>>> ######## From a (pretend) file (pointer) ########
>>> # Usually, you write your configs in a file and give ConfigReader the filepath, or open file pointer...
>>> pretend_file_pointer = StringIO(file_content_bytes.decode())
>>> c = ConfigReader(pretend_file_pointer)
>>> list(c)
['DEFAULT', 'Paths', 'Escape']
>>> c['Paths']  # gives you a configparser.Section object
<Section: Paths>
>>> # A configparser.Section is a mapping. Let's see the keys
>>> list(c['Paths'])
['home_dir', 'my_dir', 'my_pictures']
```

# >>> # here’s a quick way to see both keys and values. Note how the home_dir interpolation was performed!
# >>> dict(c[‘Paths’])
# {‘home_dir’: ‘/Users’, ‘my_dir’: ‘/Users/lumberjack’, ‘my_pictures’: ‘/Users/lumberjack/Pictures’}

```pycon
>>>
>>> ######## Get configs from a dict ########
>>> config_dict = {'section1': {'key1': 'value1'},
...                'section2': {'keyA': 'valueA', 'keyB': 'valueB'},
...                'section3': {'foo': 'x', 'bar': 'y','baz': 'z'}}
>>> c = ConfigReader(config_dict)
>>>
>>> assert list(c) == ['DEFAULT', 'section1', 'section2', 'section3']
>>> assert list(c['section3']) == ['foo', 'bar', 'baz']
>>>
>>> ######## Get configs from a string ########
>>> from config2py.s_configparser import _test_config_str
>>> c = ConfigReader(_test_config_str, allow_no_value=True)
>>> list(c)
['DEFAULT', 'Simple Values', 'All Values Are Strings', 'Multiline Values', 'No Values', 'You can use comments', 'Sections Can Be Indented']
>>> list(c['Simple Values'])
['key', 'spaces in keys', 'spaces in values', 'spaces around the delimiter', 'you can also use']
```

######## A filepath that doesn’t exist ########

A filepath (a single-line `str`, an `os.PathLike`, or several of them in a list
or tuple) that is not an existing file reads as empty, as `configparser` does.
So does one that is a folder or can’t be read (permission denied).
`on_missing` says what else happens: `"warn"` (the default) issues a
`MissingConfigFileWarning`, `"raise"` raises `FileNotFoundError` (or
`IsADirectoryError` / `PermissionError`), and `"ignore"` does nothing
(see [https://github.com/i2mint/config2py/issues/27](https://github.com/i2mint/config2py/issues/27) and /43).

```pycon
>>> c = ConfigReader('no/such/file.ini', on_missing='ignore')
>>> list(c)
['DEFAULT']
>>> ConfigReader('no/such/file.ini', on_missing='raise')
Traceback (most recent call last):
  ...
FileNotFoundError: [Errno 2] No such config file: 'no/such/file.ini'
```

#### persist()

Disabled: `ConfigReader` is read-only.

### *class* config2py.ConfigStore(source, \*, defaults=None, dict_type=<class 'dict'>, allow_no_value=False, target_kind=None, follow_symlinks=True, \*\*more_config_parser_kwargs)

Bases: `Store`

Persister (read, write, delete) for ini configs.

You can read ini formated configurations with ConfigStore (though if you want to
just read, you should use ConfigReader instead – since ConfigReader disables
write and delete operations.

See ConfigReader for more examples of how to use ConfigStore.
We’ll mainly focus on write and delete operations here.

```pycon
>>> import os
>>> from config2py.s_configparser import ConfigStore, ConfigReader
>>> import tempfile
>>> temp_dir_path = tempfile.TemporaryDirectory().name
>>> if not os.path.exists(temp_dir_path):
...     os.makedirs(temp_dir_path)
>>> ini_filepath = os.path.join(temp_dir_path, 'config_store_test.ini')
>>> if os.path.isfile(ini_filepath):
...     os.remove(ini_filepath)
>>>
>>> os.path.isfile(ini_filepath)  # File doesn't exist
False
>>>
>>> s = ConfigStore(ini_filepath)
>>> list(s)  # There's always a default (by default empty)
['DEFAULT']
>>>
>>> os.path.isfile(ini_filepath)  # But the file still doesn't exist (the DEFAULT is virtual)
False
>>>
>>> # Now let's make a config
>>> s['nothing'] = {'special': 'about', 'number': 42}
>>> list(s)
['DEFAULT', 'nothing']
>>>
>>> os.path.isfile(ini_filepath)  # But NOW the file exists (ConfigStore will automatically write to file)
True
>>> s['add'] = {'more': 'sections'}
>>> list(s)
['DEFAULT', 'nothing', 'add']
```

```pycon
>>> # and yes, that config can now be read
>>> config_reader = ConfigReader(ini_filepath)
>>> list(config_reader)
['DEFAULT', 'nothing', 'add']
>>>
>>> config_reader['nothing']
<Section: nothing>
>>>
>>> dict(config_reader['nothing'])  # note that 42 is now a string (that's the ini format for you!)
{'special': 'about', 'number': '42'}
>>> dict(config_reader['DEFAULT'])  # and DEFAULT is empty
{}
```

You can delete sections

```pycon
>>> del s['add']
```

But you’ll need to refresh your reader to see the effect.

```pycon
>>> list(config_reader)
['DEFAULT', 'nothing', 'add']
>>> config_reader = ConfigReader(ini_filepath)
>>> list(config_reader)
['DEFAULT', 'nothing']
```

You can use `update` to write several sections at the same time.
Note that existing sections will be completely overwritten.

```pycon
>>> s.update({'nothing': {'like': 'you'}, 'new_section': {'a': 'b', 'c': 'd'}})
>>> ConfigReader(ini_filepath).to_dict()
{'DEFAULT': {}, 'nothing': {'like': 'you'}, 'new_section': {'a': 'b', 'c': 'd'}}
```

**Warning: On the other hand, updating a section will not persist the updates**

Updates are automatically persisted at the top level, as shown in the example above.
This means you can change a section entirely, but partial updates of a section
will not be persisted.

You’ll see the updated section in the store.

```pycon
>>> s['nothing'].update({'something': 'else'})
>>> dict(s['nothing'])
{'like': 'you', 'something': 'else'}
```

But it’s not automatically persisted

```pycon
>>> dict(ConfigReader(ini_filepath)['nothing'])
{'like': 'you'}
```

… unless you ask for it explicitly

```pycon
>>> s.persist()
>>> dict(ConfigReader(ini_filepath)['nothing'])
{'like': 'you', 'something': 'else'}
```

# TODO: Could make section updates auto-persistent by wrapping configparser.SectionProxy

For your convenience, the ConfigStore is also a context manager, that will,
you guessed, persist stuff when (and only when) you exit it.

```pycon
>>> ConfigReader(ini_filepath).to_dict()
{'DEFAULT': {}, 'nothing': {'like': 'you', 'something': 'else'}, 'new_section': {'a': 'b', 'c': 'd'}}
>>> with ConfigStore(ini_filepath) as s:
...     del s['new_section']  # that's usually immediately persisted. This time, it'll wait to be
...     del s['nothing']['something']  # delete the something field of nothing section
...     s['nothing'].update({'like': 'that', 'ever': 'happened'})  # update 'like' config and add an 'ever' one
>>> ConfigReader(ini_filepath).to_dict()
{'DEFAULT': {}, 'nothing': {'like': 'that', 'ever': 'happened'}}
```

#### *class* BasicInterpolation

Bases: `Interpolation`

Interpolation as implemented in the classic ConfigParser.

The option values can contain format strings which refer to other values in
the same section, or values in the special default section.

For example:

> something: %(dir)s/whatever

would resolve the “%(dir)s” to the value of dir.  All reference
expansions are done late, on demand. If a user needs to use a bare % in
a configuration file, she can escape it by writing %%. Other % usage
is considered a user error and raises `InterpolationSyntaxError`.

#### *class* ExtendedInterpolation

Bases: `Interpolation`

Advanced variant of interpolation, supports the syntax used by
`zc.buildout`. Enables interpolation between sections.

#### get(k, default=None)

Needed because the Store.get didn’t catch the NoSectionError

#### persist()

Persists the data (if not in a context manager).
Persists means to call

#### to_dict()

Return the whole config as a `{section: {key: value}}` dict.

### config2py.Configs

alias of [`SecureTextFiles`](config2py.tools.html.md#config2py.tools.SecureTextFiles)

### *class* config2py.FileStore(filepath, , key_path=None, loader=None, dumper=None, mode='r', dump_kwargs=None, create_file_content=None, create_key_path_content=None, follow_symlinks=True)

Bases: [`SyncStore`](config2py.sync_store.html.md#config2py.sync_store.SyncStore)

A SyncStore backed by a file with automatic format detection.

Supports nested key paths for working with specific sections.

* **Parameters:**
  * **filepath** (`Union`[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]) – Path to file (supports ~ expansion)
  * **key_path** (`Union`[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Tuple`](https://docs.python.org/3/library/typing.html#typing.Tuple)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`...`](https://docs.python.org/3/builtins/constants.html#Ellipsis)], [`None`](https://docs.python.org/3/builtins/constants.html#None)]) – Optional nested path to operate on
  * **loader** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)], [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]]) – Optional custom loader (auto-detected from extension if not provided)
  * **dumper** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)], [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]]) – Optional custom dumper (auto-detected from extension if not provided)
  * **mode** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – File read mode (‘r’ for text, ‘rb’ for binary)
  * **dump_kwargs** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]) – Additional kwargs for dumper
  * **create_file_content** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[], [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]]) – Optional factory callable that returns initial dict content
    for missing files. If None, FileNotFoundError is raised for missing files.
  * **create_key_path_content** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[], [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]) – Optional factory callable that returns initial content
    for missing key_path. If None, KeyError is raised for missing key paths.
  * **follow_symlinks** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – If False, writing refuses (`OSError`) to go through a symlink
    at `filepath` (or a file with several hard links), instead of writing
    to its target (see i2mint/config2py#45). Default True, like `open`.

### Example

```pycon
>>> import tempfile
>>> import os
>>>
>>> # Basic usage with existing file
>>> with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
...     _ = f.write('{"section": {"key": "value"}}')
...     temp_file = f.name
>>>
>>> section = FileStore(temp_file, key_path='section')
>>> section['key']
'value'
>>> section['new'] = 'data'
>>> os.unlink(temp_file)
>>>
>>> # Auto-create missing file and key_path
>>> with tempfile.TemporaryDirectory() as tmpdir:
...     new_file = os.path.join(tmpdir, 'config.json')
...     store = FileStore(
...         new_file,
...         key_path='servers',
...         create_file_content=lambda: {},
...         create_key_path_content=lambda: {}
...     )
...     store['myserver'] = {'command': 'python'}
...     'myserver' in store
True
```

### *exception* config2py.InsecureConfigFolderWarning

Bases: [`Config2PyWarning`](config2py.errors.html.md#config2py.errors.Config2PyWarning)

A folder used to store config values (which may be secrets) is owned by another
user or writable by others, who could plant a symlink or file there to redirect or
read those values (see [https://github.com/i2mint/config2py/issues/45](https://github.com/i2mint/config2py/issues/45)).

### *class* config2py.JsonStore(filepath, , key_path=None, indent=2, ensure_ascii=False, follow_symlinks=True, \*\*dump_kwargs)

Bases: [`FileStore`](config2py.sync_store.html.md#config2py.sync_store.FileStore)

A FileStore specialized for JSON files.

Pre-configured with json.loads/dumps and sensible defaults.

* **Parameters:**
  * **filepath** (`Union`[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]) – Path to JSON file
  * **key_path** (`Union`[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Tuple`](https://docs.python.org/3/library/typing.html#typing.Tuple)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`...`](https://docs.python.org/3/builtins/constants.html#Ellipsis)], [`None`](https://docs.python.org/3/builtins/constants.html#None)]) – Optional nested path to operate on
  * **indent** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – JSON indentation (default: 2)
  * **follow_symlinks** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – See `FileStore`.
  * **ensure_ascii** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether to escape non-ASCII (default: False)
  * **follow_symlinks** – See `FileStore`.
  * **\*\*dump_kwargs** – Additional kwargs for json.dumps

### *exception* config2py.MissingConfigFileWarning

Bases: [`Config2PyWarning`](config2py.errors.html.md#config2py.errors.Config2PyWarning)

A path given as a config source is not an existing, readable file (it is
missing, a folder, or unreadable), so it was read as empty
(see [https://github.com/i2mint/config2py/issues/27](https://github.com/i2mint/config2py/issues/27) and /43).

### *class* config2py.SyncStore(loader, dumper)

Bases: [`MutableMapping`](https://docs.python.org/3/library/collections.abc.html#collections.abc.MutableMapping)

A MutableMapping that automatically syncs changes to backing storage.

Supports deferred sync via context manager for efficient batch operations.

* **Parameters:**
  * **loader** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[], [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]) – Function that returns the current data as a dict
  * **dumper** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)], [`None`](https://docs.python.org/3/builtins/constants.html#None)]) – Function that persists the data dict to storage

### Example

```pycon
>>> def my_loader():
...     return {'x': 1}
>>>
>>> data_holder = []
>>> def my_dumper(data):
...     data_holder.clear()
...     data_holder.append(data.copy())
>>>
>>> store = SyncStore(my_loader, my_dumper)
>>> store['y'] = 2  # Auto-syncs
>>> data_holder[0]
{'x': 1, 'y': 2}
>>>
>>> # Batch with context manager
>>> with store:
...     store['a'] = 1
...     store['b'] = 2
...     # Not synced yet
>>> data_holder[0]  # Now synced
{'x': 1, 'y': 2, 'a': 1, 'b': 2}
```

#### flush()

Sync data to backing storage if changes exist.

### config2py.ask_user_for_input(prompt, default='', \*, mask_input=<function looks_like_secret>, masking_toggle_str=None, egress=<function identity>)

Ask the user for input, optionally masking, validating and transforming the input.

* **Parameters:**
  * **prompt** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Prompt to display to the user
  * **default** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Default value to return if the user enters nothing
  * **mask_input** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)], [`bool`](https://docs.python.org/3/builtins/functions.html#bool)]) – Whether to mask the user’s input: a bool, or a
    `prompt -> bool` predicate. The default, `looks_like_secret`, masks
    prompts that mention something secret-looking (`API_KEY`, `TOKEN`,
    `PASSWORD`, …) and echoes the others. When masking is decided by a
    predicate and stdin is piped (not a terminal), the response is read from
    stdin, as it was before this default existed. An explicit `True` always
    uses `getpass.getpass`, which reads the terminal even when stdin is piped.
  * **masking_toggle_str** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – String to toggle input masking. If `None`, no toggle
    is available. If not `None` (a common choice is the empty string)
    the user can enter this string to toggle input masking.
  * **egress** ([`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)) – Function to apply to the user’s response before returning it.
    This can be used to validate the response, for example.
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
* **Returns:**
  The user’s response (or the default value if the user entered nothing)

### config2py.ensure_seeded(target, package_name, seed_subpackage, filename, , seed_data_dir='_seed_data')

Copy a bundled seed file to *target* if it does not already exist.

Reads the seed from `importlib.resources.files(
"{package_name}.{seed_data_dir}.{seed_subpackage}") / filename`
and writes its bytes to *target*.  If *target* already exists, this is
a no-op (user edits are preserved).

* **Parameters:**
  * **target** (`Union`[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]) – Destination path for the seeded file.
  * **package_name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Top-level Python package that ships the seed data.
  * **seed_subpackage** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Subdirectory inside `_seed_data` (e.g. `"resources"`
    or `"config"`).
  * **filename** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Name of the seed file.
  * **seed_data_dir** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Name of the seed-data directory inside *package_name*
    (default `"_seed_data"`).
* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
* **Returns:**
  The resolved *target* as a `Path`.

### Example

```pycon
>>> from config2py import ensure_seeded
>>> # ensure_seeded("/tmp/myfile.txt", "mypkg", "resources", "myfile.txt")
```

### config2py.extract_exports(exports, , on_missing='warn')

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

### config2py.get_app_config_folder(app_name='config2py', \*, setup_callback=<function \_default_folder_setup>, ensure_exists=False, folder_kind='config')

Retrieve or create the app directory specific to the given app name and folder kind.

The folder kind determines where the app’s files are stored. Here are concise
explanations for each folder kind:

- **config**: User preferences and settings files (e.g., API keys, theme
  preferences, editor settings). Files users might edit manually or that
  define how the app behaves.
- **data**: Essential user-created content and application state (e.g.,
  databases, saved games, user documents, session files). Data that should
  be backed up and persists across updates.
- **cache**: Temporary, regeneratable files (e.g., downloaded images,
  compiled assets, web cache). Can be safely deleted to free space without
  losing user work.
- **state**: Application state and logs that persist between sessions but
  aren’t critical user data (e.g., command history, undo history, recently
  opened files, log files). Unlike cache, shouldn’t be auto-deleted.
- **runtime**: Temporary runtime files that only exist while the app runs
  (e.g., PID files, Unix sockets, lock files, named pipes). Typically
  cleared on logout/reboot.
- **TL;DR**: config = settings, data = user files, cache = disposable,
  state = logs/history, runtime = process files.

* **Parameters:**
  * **app_name** – Name of the app for which the directory is needed.
  * **setup_callback** – A callback function to initialize the directory.
    Default is \_default_folder_setup.
  * **ensure_exists** – Whether to ensure the directory exists.
  * **folder_kind** – Type of folder (‘config’, ‘data’, ‘cache’, ‘state’, or ‘runtime’).
    Default is ‘config’ for backward compatibility.
* **Returns:**
  Path to the app directory.
* **Return type:**
  [*str*](https://docs.python.org/3/builtins/stdtypes.html#str)

By default, the app will be “config2py” and folder_kind will be “config”.
The exact text of the path is platform-specific (`~/.config/config2py` under
the XDG standards, `%APPDATA%\config2py` on Windows), so we assert the
properties that hold everywhere: it is an absolute path named after the app,
sitting directly inside the ‘config’ root directory.

```pycon
>>> folder = get_app_folder()
>>> os.path.isabs(folder)
True
>>> os.path.basename(folder)
'config2py'
>>> os.path.dirname(folder) == get_app_rootdir('config')
True
```

You can specify a different app name and folder kind:

```pycon
>>> get_app_folder('my_app', folder_kind='data')
'/Users/.../.local/share/my_app'
>>> get_app_folder('my_app', folder_kind='cache')
'/Users/.../.cache/my_app'
```

You can also specify a path relative to the app root directory:

```pycon
>>> get_app_folder('another/app/subfolder', folder_kind='data')
'/Users/.../.local/share/another/app/subfolder'
```

If ensure_exists is True, the directory will be created and initialized
with the setup_callback:

```pycon
>>> path = get_app_folder('my_app', ensure_exists=True)
>>> os.path.exists(path)
True
```

### config2py.get_app_data_folder(app_name='config2py', \*, setup_callback=<function \_default_folder_setup>, ensure_exists=False, folder_kind='data')

Retrieve or create the app directory specific to the given app name and folder kind.

The folder kind determines where the app’s files are stored. Here are concise
explanations for each folder kind:

- **config**: User preferences and settings files (e.g., API keys, theme
  preferences, editor settings). Files users might edit manually or that
  define how the app behaves.
- **data**: Essential user-created content and application state (e.g.,
  databases, saved games, user documents, session files). Data that should
  be backed up and persists across updates.
- **cache**: Temporary, regeneratable files (e.g., downloaded images,
  compiled assets, web cache). Can be safely deleted to free space without
  losing user work.
- **state**: Application state and logs that persist between sessions but
  aren’t critical user data (e.g., command history, undo history, recently
  opened files, log files). Unlike cache, shouldn’t be auto-deleted.
- **runtime**: Temporary runtime files that only exist while the app runs
  (e.g., PID files, Unix sockets, lock files, named pipes). Typically
  cleared on logout/reboot.
- **TL;DR**: config = settings, data = user files, cache = disposable,
  state = logs/history, runtime = process files.

* **Parameters:**
  * **app_name** – Name of the app for which the directory is needed.
  * **setup_callback** – A callback function to initialize the directory.
    Default is \_default_folder_setup.
  * **ensure_exists** – Whether to ensure the directory exists.
  * **folder_kind** – Type of folder (‘config’, ‘data’, ‘cache’, ‘state’, or ‘runtime’).
    Default is ‘config’ for backward compatibility.
* **Returns:**
  Path to the app directory.
* **Return type:**
  [*str*](https://docs.python.org/3/builtins/stdtypes.html#str)

By default, the app will be “config2py” and folder_kind will be “config”.
The exact text of the path is platform-specific (`~/.config/config2py` under
the XDG standards, `%APPDATA%\config2py` on Windows), so we assert the
properties that hold everywhere: it is an absolute path named after the app,
sitting directly inside the ‘config’ root directory.

```pycon
>>> folder = get_app_folder()
>>> os.path.isabs(folder)
True
>>> os.path.basename(folder)
'config2py'
>>> os.path.dirname(folder) == get_app_rootdir('config')
True
```

You can specify a different app name and folder kind:

```pycon
>>> get_app_folder('my_app', folder_kind='data')
'/Users/.../.local/share/my_app'
>>> get_app_folder('my_app', folder_kind='cache')
'/Users/.../.cache/my_app'
```

You can also specify a path relative to the app root directory:

```pycon
>>> get_app_folder('another/app/subfolder', folder_kind='data')
'/Users/.../.local/share/another/app/subfolder'
```

If ensure_exists is True, the directory will be created and initialized
with the setup_callback:

```pycon
>>> path = get_app_folder('my_app', ensure_exists=True)
>>> os.path.exists(path)
True
```

### config2py.get_app_folder(app_name='config2py', \*, setup_callback=<function \_default_folder_setup>, ensure_exists=False, folder_kind='config')

Retrieve or create the app directory specific to the given app name and folder kind.

The folder kind determines where the app’s files are stored. Here are concise
explanations for each folder kind:

- **config**: User preferences and settings files (e.g., API keys, theme
  preferences, editor settings). Files users might edit manually or that
  define how the app behaves.
- **data**: Essential user-created content and application state (e.g.,
  databases, saved games, user documents, session files). Data that should
  be backed up and persists across updates.
- **cache**: Temporary, regeneratable files (e.g., downloaded images,
  compiled assets, web cache). Can be safely deleted to free space without
  losing user work.
- **state**: Application state and logs that persist between sessions but
  aren’t critical user data (e.g., command history, undo history, recently
  opened files, log files). Unlike cache, shouldn’t be auto-deleted.
- **runtime**: Temporary runtime files that only exist while the app runs
  (e.g., PID files, Unix sockets, lock files, named pipes). Typically
  cleared on logout/reboot.
- **TL;DR**: config = settings, data = user files, cache = disposable,
  state = logs/history, runtime = process files.

* **Parameters:**
  * **app_name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Name of the app for which the directory is needed.
  * **setup_callback** ([`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)], [`None`](https://docs.python.org/3/builtins/constants.html#None)]) – A callback function to initialize the directory.
    Default is \_default_folder_setup.
  * **ensure_exists** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether to ensure the directory exists.
  * **folder_kind** ([`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)[`'config'`, `'data'`, `'cache'`, `'state'`, `'runtime'`]) – Type of folder (‘config’, ‘data’, ‘cache’, ‘state’, or ‘runtime’).
    Default is ‘config’ for backward compatibility.
* **Returns:**
  Path to the app directory.
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

By default, the app will be “config2py” and folder_kind will be “config”.
The exact text of the path is platform-specific (`~/.config/config2py` under
the XDG standards, `%APPDATA%\config2py` on Windows), so we assert the
properties that hold everywhere: it is an absolute path named after the app,
sitting directly inside the ‘config’ root directory.

```pycon
>>> folder = get_app_folder()
>>> os.path.isabs(folder)
True
>>> os.path.basename(folder)
'config2py'
>>> os.path.dirname(folder) == get_app_rootdir('config')
True
```

You can specify a different app name and folder kind:

```pycon
>>> get_app_folder('my_app', folder_kind='data')
'/Users/.../.local/share/my_app'
>>> get_app_folder('my_app', folder_kind='cache')
'/Users/.../.cache/my_app'
```

You can also specify a path relative to the app root directory:

```pycon
>>> get_app_folder('another/app/subfolder', folder_kind='data')
'/Users/.../.local/share/another/app/subfolder'
```

If ensure_exists is True, the directory will be created and initialized
with the setup_callback:

```pycon
>>> path = get_app_folder('my_app', ensure_exists=True)
>>> os.path.exists(path)
True
```

### config2py.get_config(key=None, sources=None, \*, default=Sentinel('no_default'), egress=None, val_is_valid=<function always_true>, config_not_found_exceptions=(<class 'Exception'>, ))

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
`config_not_found_exceptions` argument, which defaults to `(Exception,)`.

Beware that this broad default treats *any* error raised by a callable source
(a network blip, a bug, a missing import, rejected credentials) as “not found”,
and silently moves on to the next, possibly less trusted, source. When the
sources are known, prefer passing something narrower, such as
`config_not_found_exceptions=(KeyError, LookupError, FileNotFoundError)`
(see [https://github.com/i2mint/config2py/issues/25](https://github.com/i2mint/config2py/issues/25)).

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
([https://pypi.org/project/dol/](https://pypi.org/project/dol/)) which will allow you to make `Mapping` objects
for all sorts of data sources.

For more info, see: [https://github.com/i2mint/config2py/issues/4](https://github.com/i2mint/config2py/issues/4)

### config2py.get_configs_folder_for_app(app_name='config2py', \*, configs_name='configs', app_dir_setup_callback=<function \_default_folder_setup>, config_dir_setup_callback=<function \_default_folder_setup>, ensure_exists=True)

Retrieve or create the configs directory specific to the given app name.

* **Parameters:**
  * **app_name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Name of the app for which the configs directory is needed.
  * **configs_name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Name of the configs directory.
  * **app_dir_setup_callback** ([`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)], [`None`](https://docs.python.org/3/builtins/constants.html#None)]) – A callback function to
    initialize the app directory. Default is \_default_folder_setup.
  * **config_dir_setup_callback** ([`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)], [`None`](https://docs.python.org/3/builtins/constants.html#None)]) – A callback function to
    initialize the configs directory. Default is \_default_folder_setup.
  * **ensure_exists** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether to create (and set up) the directory. With
    `False`, only the path is computed: nothing is created or chmod-ed.

### config2py.get_configs_local_store(config_src='/home/runner/.config/config2py/configs', , configs_name='configs', follow_symlinks=True, on_unsafe_folder='warn', kind='auto')

Get the local store of configs.

* **Parameters:**
  * **config_src** – A specification of the local config store. By default:
    If it’s a directory, it’s assumed to be a folder of text files.
    If it’s a file, it’s assumed to be an ini or cfg file.
    If it’s a string, it’s assumed to be an app name, from which to create a folder
    (a `pathlib.Path` is always a path).
  * **follow_symlinks** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether the store may write through a symlink at a value
    (or ini) file’s path. `False` refuses to
    (see [https://github.com/i2mint/config2py/issues/45](https://github.com/i2mint/config2py/issues/45)).
  * **on_unsafe_folder** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – `"warn"` (default), `"raise"` or `"ignore"` when
    a folder store’s root (or, for an ini file, its folder; a sticky one like
    `/tmp` is fine) is owned by another user or writable by its group or by
    others (see `SecureTextFiles`).
  * **kind** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – How to read `config_src`: `"auto"` (default), `"path"` or
    `"app"`. In `"auto"` mode, a `pathlib.Path`, an absolute path, or a
    string containing `os.sep` or `os.altsep` is a path, and any other string
    is an app name, even if a directory of that name exists in the current working
    directory (so as not to change where existing callers read and write; only an
    existing `.ini`/`.cfg` file of that name is used as a file).
    `kind="path"` makes a bare name such as `"configs"` mean that directory
    (or file); `kind="app"` makes any string an app name.
    See [https://github.com/i2mint/config2py/issues/28](https://github.com/i2mint/config2py/issues/28).

The default, `DFLT_CONFIG_FOLDER`, is config2py’s own configs folder. It is
created here, on first use, rather than at import
(see [https://github.com/i2mint/config2py/issues/26](https://github.com/i2mint/config2py/issues/26)).

### config2py.is_repl()

Determines if the Python interpreter is running in REPL.

To test: If you put it in a module.py, do a print of it in the module, and do
`python module.py` it should print False.
If you do `python -i module.py`, or call it from a python console or jupyter
notebook, it should return `True`.

* **Returns:**
  True if running in a REPL, False otherwise.
* **Return type:**
  [*bool*](https://docs.python.org/3/builtins/functions.html#bool)

`is_repl` returns `True` if any function in `is_repl.repl_conditions`
(a set of no-argument callables) returns `True`. By default that set checks
whether `get_ipython` is in globals, or whether `__main__` has no
`__file__` attribute. Mutate `is_repl.repl_conditions` in place (e.g.
`is_repl.repl_conditions.add(fn)`) to change the checks – rebinding the
attribute to a new set has no effect, since `is_repl` reads the original set.

### config2py.parse_assignments_from_py_source(source_code, \*, name_filt=None, value_filt=<function \_value_node_is_instance_of>)

Parse assignments from python source code.

```pycon
>>> source_code = '''a = 1
... b = 'hello'
... c = [1, 2, 3]
... def func():
...     d = 4
... '''
>>> dict(parse_assignments_from_py_source(source_code))
{'a': 1, 'b': 'hello', 'c': [1, 2, 3], 'd': 4}
```

### config2py.process_path(\*path, ensure_dir_exists=False, assert_exists=False, ensure_endswith_slash=False, ensure_does_not_end_with_slash=False, expanduser=True, expandvars=True, abspath=True, rootdir='')

Process a path string, ensuring it exists, and optionally expanding user.

* **Parameters:**
  * **path** ([`Iterable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterable)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – The path to process. Can be multiple components of a path.
  * **ensure_dir_exists** ([`int`](https://docs.python.org/3/builtins/functions.html#int) | [`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether to ensure the path exists.
  * **assert_exists** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether to assert that the path exists.
  * **ensure_endswith_slash** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether to ensure the path ends with a slash.
  * **ensure_does_not_end_with_slash** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether to ensure the path does not end with a slash.
  * **expanduser** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether to expand the user in the path.
  * **expandvars** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether to expand environment variables in the path.
  * **abspath** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether to convert the path to an absolute path.
  * **rootdir** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – The root directory to prepend to the path.
* **Returns:**
  The processed path.
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The result uses the running OS’s native separator, so these examples assert
OS-independently (the literal forward-slash form is what you get on POSIX):

```pycon
>>> import os
>>> process_path('a', 'b', 'c').endswith(os.path.join('a', 'b', 'c'))
True
>>> p = process_path(
...     'a', 'b', 'c', rootdir='root_dir',
...     ensure_endswith_slash=True, abspath=False, expanduser=False, expandvars=False,
... )
>>> p == os.path.join('root_dir', 'a', 'b', 'c') + os.sep
True
```

### config2py.register_extension(ext, loader, dumper)

Register loader/dumper for a file extension.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### config2py.simple_config_getter(configs_src='/home/runner/.config/config2py/configs', \*, first_look_in_env_vars=True, ask_user_if_key_not_found=None, config_store_factory=<function get_configs_local_store>)

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

### config2py.sources_chainmap(sources, val_is_valid=<function always_true>, config_not_found_exceptions=(<class 'Exception'>, ))

Create a `ChainMap` from a list of sources

* **Return type:**
  [`ChainMap`](https://docs.python.org/3/library/collections.html#collections.ChainMap)

### config2py.user_gettable(save_to=None, \*, prompt_template='Enter a value for {}: ', egress=None, user_asker=<function ask_user_for_input>, val_is_valid=<function is_not_empty>, config_not_found_exceptions=(<class 'Exception'>, ))

Create a `GettableContainer` that asks the user for a value, optionally saving it.

* **Parameters:**
  * **save_to** (`Union`[[`MutableMapping`](https://docs.python.org/3/library/collections.abc.html#collections.abc.MutableMapping), [`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`TypeVar`](https://docs.python.org/3/library/typing.html#typing.TypeVar)(`KT`), [`TypeVar`](https://docs.python.org/3/library/typing.html#typing.TypeVar)(`VT`)], [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)], [`None`](https://docs.python.org/3/builtins/constants.html#None)]) – Where to save the user’s response: a `MutableMapping` (or
    anything with a `__setitem__`), or a `(key, value)` saver function.
    If `None`, the user’s response is not saved.
  * **prompt_template** – A template string to prompt the user with. It should
    contain a placeholder for the key, e.g. `"Enter a value for {}: "`.
  * **egress** ([`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – A function to apply to the user’s response before returning it.
    This can be used to validate the response, for example.
  * **user_asker** – A function that asks the user for input. It should take a
    prompt string and return the user’s response.
  * **val_is_valid** ([`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`TypeVar`](https://docs.python.org/3/library/typing.html#typing.TypeVar)(`VT`)], [`bool`](https://docs.python.org/3/builtins/functions.html#bool)]) – A function that takes a value and returns a boolean. If it
    returns `False`, the user will be asked for a new value.
  * **config_not_found_exceptions** ([`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`type`](https://docs.python.org/3/builtins/functions.html#type)[[`Exception`](https://docs.python.org/3/builtins/exceptions.html#Exception)], [`...`](https://docs.python.org/3/builtins/constants.html#Ellipsis)]) – An iterable of exceptions that should be
    considered as “config not found” exceptions. If the user’s response
    raises one of these exceptions, the user will be asked for a new value.
* **Returns:**
  A `GettableContainer` that asks the user for a value, optionally saving it.

### Example

```pycon
>>> s = user_gettable()
>>> v = s['SOME_KEY']
'SOME_VAL'
```

This will trigger a prompt for the user to enter the value of `SOME_KEY`.
When they do (say they entered ‘SOME_VAL’) it will return that value.

And if you specify a save_to store (usually a persistent MutableMapping made
with the `dol` package) then it will save the value to that store for
future use.

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

### Modules

| [`util`](config2py.util.html.md#module-config2py.util)                     | Utility functions for config2py.                                 |
|-------------------------------------------------------------------------------------------------|------------------------------------------------------------------|
| [`errors`](config2py.errors.html.md#module-config2py.errors)                 | Error classes for config2py.                                     |
| [`s_configparser`](config2py.s_configparser.html.md#module-config2py.s_configparser) | Data Object Layer for configparser standard lib.                 |
| [`base`](config2py.base.html.md#module-config2py.base)                     | Base for getting configs from various sources and formats        |
| [`tools`](config2py.tools.html.md#module-config2py.tools)                   | Various tools                                                    |
| [`sync_store`](config2py.sync_store.html.md#module-config2py.sync_store)         | Synchronized key-value stores with automatic persistence.        |
| [`codecs`](config2py.codecs.html.md#module-config2py.codecs)                 | Extension-based codec registries for configuration file parsing. |
