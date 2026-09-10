# config2py.util

Utility functions for config2py.

### Module Attributes

| [`FolderSpec`](#config2py.util.FolderSpec)(env_var, default_path, subpath)   | Declarative description of where a given folder kind lives on a platform.   |
|-----------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------|

### Functions

| [`always_true`](#config2py.util.always_true)(x)                                    | Function that just returns True.                                                                                                                                                        |
|----------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`app_folder_standards`](#config2py.util.app_folder_standards)([os_name])                   | Return the `{folder_kind: FolderSpec}` table for the given `os.name`.                                                                                                                   |
| [`ask_user_for_input`](#config2py.util.ask_user_for_input)(prompt[, default, ...])        | Ask the user for input, optionally masking, validating and transforming the input.                                                                                                      |
| [`create_directories`](#config2py.util.create_directories)(dirpath[, max_dirs_to_make])   | Create directories up to a specified limit.                                                                                                                                             |
| [`ensure_seeded`](#config2py.util.ensure_seeded)(target, package_name, ...[, ...])   | Copy a bundled seed file to *target* if it does not already exist.                                                                                                                      |
| [`extract_variable_declarations`](#config2py.util.extract_variable_declarations)(string[, expand])   | Reads the contents of a config file, extracting Unix-style environment variable declarations of the form `export {NAME}={value}`, returning a dictionary of `{NAME: value, ...}` pairs. |
| [`get_app_folder`](#config2py.util.get_app_folder)([app_name, setup_callback, ...])   | Retrieve or create the app directory specific to the given app name and folder kind.                                                                                                    |
| [`get_app_rootdir`](#config2py.util.get_app_rootdir)([folder_kind, ensure_exists])     | Returns the root directory for a specific folder kind.                                                                                                                                  |
| [`get_configs_directory_for_app`](#config2py.util.get_configs_directory_for_app)([app_name, ...])    | Retrieve or create the configs directory specific to the given app name.                                                                                                                |
| [`get_configs_folder_for_app`](#config2py.util.get_configs_folder_for_app)([app_name, ...])       | Retrieve or create the configs directory specific to the given app name.                                                                                                                |
| [`identity`](#config2py.util.identity)(x)                                       | Function that just returns its argument.                                                                                                                                                |
| [`is_not_empty`](#config2py.util.is_not_empty)(x)                                   | Function that returns True if x is not empty.                                                                                                                                           |
| [`is_repl`](#config2py.util.is_repl)()                                         | Determines if the Python interpreter is running in REPL.                                                                                                                                |
| [`parse_assignments_from_py_source`](#config2py.util.parse_assignments_from_py_source)(source_code, \*) | Parse assignments from python source code.                                                                                                                                              |
| [`system_default_for_app_data_folder`](#config2py.util.system_default_for_app_data_folder)([...])         | Get the system default folder for `folder_kind`.                                                                                                                                        |

### Classes

| [`AppData`](#config2py.util.AppData)(app_name, \*[, package_name, ...])   | Per-user data directory facade for a Python application.                     |
|-----------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|
| [`EnvironmentVariables`](#config2py.util.EnvironmentVariables)()                       | Class to wrap environment variables without revealing sensitive information. |
| [`FolderSpec`](#config2py.util.FolderSpec)(env_var, default_path, subpath)   | Declarative description of where a given folder kind lives on a platform.    |

### *class* config2py.util.AppData(app_name, , package_name=None, seed_data_dir='_seed_data')

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

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
  * **app_name** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – The application name used for the directory under the
    XDG root (e.g. `"my_app"` → `~/.local/share/my_app`).
  * **package_name** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]) – The top-level Python package that contains the
    `_seed_data` directory.  Defaults to *app_name*.
  * **seed_data_dir** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – Name of the seed-data sub-package inside the
    Python package (default `"_seed_data"`).

Example:

```default
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

### *class* config2py.util.EnvironmentVariables

Bases: [`ChainMap`](https://docs.python.org/3/library/collections.html#collections.ChainMap)

Class to wrap environment variables without revealing sensitive information.

### *class* config2py.util.FolderSpec(env_var, default_path, subpath)

Bases: [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)

Declarative description of where a given folder kind lives on a platform.

`env_var` is the platform-standard environment variable that, when set,
names the *root* folder.  `default_path` is the root to use when that
variable is absent (`~` is expanded).  `subpath` is a relative path
appended to the root; it exists because some platform standards place a
folder kind *inside* another kind’s root rather than under its own variable
(e.g. Windows cache lives at `%LOCALAPPDATA%\\Temp`).

#### default_path

Alias for field number 1

#### env_var

Alias for field number 0

#### subpath

Alias for field number 2

### config2py.util.always_true(x)

Function that just returns True.

* **Return type:**
  [`bool`](https://docs.python.org/3/library/functions.html#bool)

### config2py.util.app_folder_standards(os_name='posix')

Return the `{folder_kind: FolderSpec}` table for the given `os.name`.

This is the *single* place where config2py branches on the operating
system: everything else consumes the returned table.  Exposing it as a
function (rather than an `if` at import time) keeps the branch testable
on any platform – callers can ask for the table of an OS they are not
running on.

* **Parameters:**
  **os_name** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – An `os.name` value; `"nt"` selects the Windows standards,
  anything else selects the XDG Base Directory standards.
* **Return type:**
  [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)

```pycon
>>> app_folder_standards("nt")["cache"]
FolderSpec(env_var='LOCALAPPDATA', default_path='~\\AppData\\Local', subpath='Temp')
>>> app_folder_standards("posix")["cache"]
FolderSpec(env_var='XDG_CACHE_HOME', default_path='~/.cache', subpath='')
```

### config2py.util.ask_user_for_input(prompt, default='', \*, mask_input=False, masking_toggle_str=None, egress=<function identity>)

Ask the user for input, optionally masking, validating and transforming the input.

* **Parameters:**
  * **prompt** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – Prompt to display to the user
  * **default** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – Default value to return if the user enters nothing
  * **mask_input** – Whether to mask the user’s input
  * **masking_toggle_str** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – String to toggle input masking. If `None`, no toggle
    is available. If not `None` (a common choice is the empty string)
    the user can enter this string to toggle input masking.
  * **egress** ([`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)) – Function to apply to the user’s response before returning it.
    This can be used to validate the response, for example.
* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)
* **Returns:**
  The user’s response (or the default value if the user entered nothing)

### config2py.util.create_directories(dirpath, max_dirs_to_make=None)

Create directories up to a specified limit.

### Parameters

dirpath (str): The directory path to create.
max_dirs_to_make (int, optional): The maximum number of directories to create. If None, there’s no limit.

### Returns

bool: True if the directory was created successfully, False otherwise.

### Raises

ValueError: If max_dirs_to_make is negative.

### Examples

```pycon
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
```

```pycon
>>> temp_dir = tempfile.mkdtemp()
>>> target_dir = os.path.join(temp_dir, 'a', 'b', 'c', 'd')
>>> create_directories(target_dir)
True
>>> os.path.isdir(target_dir)
True
>>> shutil.rmtree(temp_dir)  # Cleanup
```

### config2py.util.ensure_seeded(target, package_name, seed_subpackage, filename, , seed_data_dir='_seed_data')

Copy a bundled seed file to *target* if it does not already exist.

Reads the seed from `importlib.resources.files(
"{package_name}.{seed_data_dir}.{seed_subpackage}") / filename`
and writes its bytes to *target*.  If *target* already exists, this is
a no-op (user edits are preserved).

* **Parameters:**
  * **target** (`Union`[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]) – Destination path for the seeded file.
  * **package_name** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – Top-level Python package that ships the seed data.
  * **seed_subpackage** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – Subdirectory inside `_seed_data` (e.g. `"resources"`
    or `"config"`).
  * **filename** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – Name of the seed file.
  * **seed_data_dir** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – Name of the seed-data directory inside *package_name*
    (default `"_seed_data"`).
* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
* **Returns:**
  The resolved *target* as a `Path`.

Example:

```default
>>> from config2py import ensure_seeded
>>> # ensure_seeded("/tmp/myfile.txt", "mypkg", "resources", "myfile.txt")
```

### config2py.util.extract_variable_declarations(string, expand=None)

Reads the contents of a config file, extracting Unix-style environment variable
declarations of the form
`export {NAME}={value}`, returning a dictionary of `{NAME: value, ...}` pairs.

See issue for more info and applications:
[https://github.com/i2mint/config2py/issues/2](https://github.com/i2mint/config2py/issues/2)

* **Parameters:**
  * **string** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – String to extract variable declarations from
  * **expand** ([`dict`](https://docs.python.org/3/library/stdtypes.html#dict) | [`bool`](https://docs.python.org/3/library/functions.html#bool) | [`None`](https://docs.python.org/3/library/constants.html#None)) – An optional dictionary of variable names and values to use to
    expand variables that are referenced (i.e. `$NAME` is a reference to `NAME`
    variable) in the values of config variables.
    If `True`, `expand` is replaced with an empty dictionary, which means we
    want to expand variables recursively, but we have no references to seed the
    expansion with. If `False`, `expand` is replaced with `None`, indicating
    that we don’t want to expand any variables.
* **Return type:**
  [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)
* **Returns:**
  A dictionary of variable names and values.

```pycon
>>> config = 'export ENVIRONMENT="dev"\nexport PORT=8080\nexport DEBUG=true'
>>> extract_variable_declarations(config)
{'ENVIRONMENT': 'dev', 'PORT': '8080', 'DEBUG': 'true'}
```

```pycon
>>> config = 'export PATH="$PATH:/usr/local/bin"\nexport EDITOR="nano"'
>>> extract_variable_declarations(config)
{'PATH': '$PATH:/usr/local/bin', 'EDITOR': 'nano'}
```

The `expand` argument can be used to expand variables in the values of other.

Let’s add a reference to the `PATH` variable in the `EDITOR` variable:

```pycon
>>> config = 'export PATH="$PATH:/usr/local/bin"\nexport EDITOR="nano $PATH"'
```

If you specify a value for `PATH` in the `expand` argument, you’ll see it
reflected in the `PATH` variable (self reference) and the `EDITOR` variable.
(Note if you changed the order of `PATH` and `EDITOR` in the `config`,
you wouldn’t get the same thing though.)

```pycon
>>> extract_variable_declarations(config, expand={'PATH': '/root'})
{'PATH': '/root:/usr/local/bin', 'EDITOR': 'nano /root:/usr/local/bin'}
```

If you specify `expand={}`, the first `PATH` variable will not be expanded,
since PATH is not in the expand dictionary. But the second `PATH` variable,
referenced in the definition of `EDITOR` will be expanded, since it is in the
expand dictionary.

```pycon
>>> extract_variable_declarations(config, expand={})
{'PATH': '$PATH:/usr/local/bin', 'EDITOR': 'nano $PATH:/usr/local/bin'}
```

### config2py.util.get_app_config_folder(app_name='config2py', \*, setup_callback=<function \_default_folder_setup>, ensure_exists=False, folder_kind='config')

Retrieve or create the app directory specific to the given app name and folder kind.

The folder kind determines where the app’s files are stored:
Here are concise explanations for each folder kind:

```default
**config**: User preferences and settings files (e.g., API keys, theme preferences, editor settings). Files users might edit manually or that define how the app behaves.
**data**: Essential user-created content and application state (e.g., databases, saved games, user documents, session files). Data that should be backed up and persists across updates.
**cache**: Temporary, regeneratable files (e.g., downloaded images, compiled assets, web cache). Can be safely deleted to free space without losing user work.
**state**: Application state and logs that persist between sessions but aren't critical user data (e.g., command history, undo history, recently opened files, log files). Unlike cache, shouldn't be auto-deleted.
**runtime**: Temporary runtime files that only exist while the app runs (e.g., PID files, Unix sockets, lock files, named pipes). Typically cleared on logout/reboot.
**TL;DR**: config = settings, data = user files, cache = disposable, state = logs/history, runtime = process files.
```

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
  [*str*](https://docs.python.org/3/library/stdtypes.html#str)

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

### config2py.util.get_app_data_directory(app_name='config2py', \*, setup_callback=<function \_default_folder_setup>, ensure_exists=False, folder_kind='config')

Retrieve or create the app directory specific to the given app name and folder kind.

The folder kind determines where the app’s files are stored:
Here are concise explanations for each folder kind:

```default
**config**: User preferences and settings files (e.g., API keys, theme preferences, editor settings). Files users might edit manually or that define how the app behaves.
**data**: Essential user-created content and application state (e.g., databases, saved games, user documents, session files). Data that should be backed up and persists across updates.
**cache**: Temporary, regeneratable files (e.g., downloaded images, compiled assets, web cache). Can be safely deleted to free space without losing user work.
**state**: Application state and logs that persist between sessions but aren't critical user data (e.g., command history, undo history, recently opened files, log files). Unlike cache, shouldn't be auto-deleted.
**runtime**: Temporary runtime files that only exist while the app runs (e.g., PID files, Unix sockets, lock files, named pipes). Typically cleared on logout/reboot.
**TL;DR**: config = settings, data = user files, cache = disposable, state = logs/history, runtime = process files.
```

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
  [*str*](https://docs.python.org/3/library/stdtypes.html#str)

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

### config2py.util.get_app_data_folder(app_name='config2py', \*, setup_callback=<function \_default_folder_setup>, ensure_exists=False, folder_kind='data')

Retrieve or create the app directory specific to the given app name and folder kind.

The folder kind determines where the app’s files are stored:
Here are concise explanations for each folder kind:

```default
**config**: User preferences and settings files (e.g., API keys, theme preferences, editor settings). Files users might edit manually or that define how the app behaves.
**data**: Essential user-created content and application state (e.g., databases, saved games, user documents, session files). Data that should be backed up and persists across updates.
**cache**: Temporary, regeneratable files (e.g., downloaded images, compiled assets, web cache). Can be safely deleted to free space without losing user work.
**state**: Application state and logs that persist between sessions but aren't critical user data (e.g., command history, undo history, recently opened files, log files). Unlike cache, shouldn't be auto-deleted.
**runtime**: Temporary runtime files that only exist while the app runs (e.g., PID files, Unix sockets, lock files, named pipes). Typically cleared on logout/reboot.
**TL;DR**: config = settings, data = user files, cache = disposable, state = logs/history, runtime = process files.
```

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
  [*str*](https://docs.python.org/3/library/stdtypes.html#str)

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

### config2py.util.get_app_folder(app_name='config2py', \*, setup_callback=<function \_default_folder_setup>, ensure_exists=False, folder_kind='config')

Retrieve or create the app directory specific to the given app name and folder kind.

The folder kind determines where the app’s files are stored:
Here are concise explanations for each folder kind:

```default
**config**: User preferences and settings files (e.g., API keys, theme preferences, editor settings). Files users might edit manually or that define how the app behaves.
**data**: Essential user-created content and application state (e.g., databases, saved games, user documents, session files). Data that should be backed up and persists across updates.
**cache**: Temporary, regeneratable files (e.g., downloaded images, compiled assets, web cache). Can be safely deleted to free space without losing user work.
**state**: Application state and logs that persist between sessions but aren't critical user data (e.g., command history, undo history, recently opened files, log files). Unlike cache, shouldn't be auto-deleted.
**runtime**: Temporary runtime files that only exist while the app runs (e.g., PID files, Unix sockets, lock files, named pipes). Typically cleared on logout/reboot.
**TL;DR**: config = settings, data = user files, cache = disposable, state = logs/history, runtime = process files.
```

* **Parameters:**
  * **app_name** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – Name of the app for which the directory is needed.
  * **setup_callback** ([`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`str`](https://docs.python.org/3/library/stdtypes.html#str)], [`None`](https://docs.python.org/3/library/constants.html#None)]) – A callback function to initialize the directory.
    Default is \_default_folder_setup.
  * **ensure_exists** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Whether to ensure the directory exists.
  * **folder_kind** ([`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)[`'config'`, `'data'`, `'cache'`, `'state'`, `'runtime'`]) – Type of folder (‘config’, ‘data’, ‘cache’, ‘state’, or ‘runtime’).
    Default is ‘config’ for backward compatibility.
* **Returns:**
  Path to the app directory.
* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

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

### config2py.util.get_app_rootdir(folder_kind='config', , ensure_exists=True)

Returns the root directory for a specific folder kind.

The folder kind determines which standard directory is returned:

- ‘config’: Configuration files (XDG_CONFIG_HOME, default ~/.config)
- ‘data’: Application data (XDG_DATA_HOME, default ~/.local/share)
- ‘cache’: Temporary/cache files (XDG_CACHE_HOME, default ~/.cache)
- ‘state’: State data/logs (XDG_STATE_HOME, default ~/.local/state)
- ‘runtime’: Runtime files (XDG_RUNTIME_DIR, default /tmp)

On Windows:

- ‘config’: %APPDATA%
- ‘data’: %LOCALAPPDATA%
- ‘cache’: %LOCALAPPDATA%Temp
- ‘state’: %LOCALAPPDATA%
- ‘runtime’: %TEMP%

* **Parameters:**
  * **folder_kind** ([`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)[`'config'`, `'data'`, `'cache'`, `'state'`, `'runtime'`]) – The kind of folder to get. One of ‘config’, ‘data’, ‘cache’, ‘state’, ‘runtime’.
    Defaults to ‘config’.
    Here are concise explanations for each folder kind:
    **config**: User preferences and settings files (e.g., API keys, theme preferences, editor settings). Files users might edit manually or that define how the app behaves.
    **data**: Essential user-created content and application state (e.g., databases, saved games, user documents, session files). Data that should be backed up and persists across updates.
    **cache**: Temporary, regeneratable files (e.g., downloaded images, compiled assets, web cache). Can be safely deleted to free space without losing user work.
    **state**: Application state and logs that persist between sessions but aren’t critical user data (e.g., command history, undo history, recently opened files, log files). Unlike cache, shouldn’t be auto-deleted.
    **runtime**: Temporary runtime files that only exist while the app runs (e.g., PID files, Unix sockets, lock files, named pipes). Typically cleared on logout/reboot.
    **TL;DR**: config = settings, data = user files, cache = disposable, state = logs/history, runtime = process files.
  * **ensure_exists** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Whether to create the directory if it doesn’t exist
* **Returns:**
  The full path of the app root folder for the specified kind.
* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

#### NOTE
> The default root folder follows XDG Base Directory standards on Unix/Linux/macOS.
> You can override this by setting environment variables:

> - CONFIG2PY_CONFIG_DIR, CONFIG2PY_DATA_DIR, CONFIG2PY_CACHE_DIR, etc.

(highest priority, overrides everything, and works on **every** platform –
see `config2py_env_var` for the full list of names)

- The platform’s own standard variable: XDG_CONFIG_HOME, XDG_DATA_HOME,
  XDG_CACHE_HOME, etc. on Unix/Linux/macOS; APPDATA / LOCALAPPDATA / TEMP on
  Windows. The XDG variables are a POSIX standard and are **not** consulted on
  Windows – use the CONFIG2PY_\* variables above for platform-neutral overrides.
- If neither is set, uses platform defaults

### Examples

```pycon
>>> get_app_rootdir('config')
'/Users/.../.config'
>>> get_app_rootdir('data')
'/Users/.../.local/share'
>>> get_app_rootdir('cache')
'/Users/.../.cache'
```

### config2py.util.get_configs_directory_for_app(app_name='config2py', \*, configs_name='configs', app_dir_setup_callback=<function \_default_folder_setup>, config_dir_setup_callback=<function \_default_folder_setup>)

Retrieve or create the configs directory specific to the given app name.

### Args

- app_name (str): Name of the app for which the configs directory is needed.
- configs_name (str): Name of the configs directory.
- app_dir_setup_callback (Callable[[str], None]): A callback function to initialize the app directory.
  : Default is \_default_folder_setup.
- config_dir_setup_callback (Callable[[str], None]): A callback function to initialize the configs directory.
  : Default is \_default_folder_setup.

### config2py.util.get_configs_folder_for_app(app_name='config2py', \*, configs_name='configs', app_dir_setup_callback=<function \_default_folder_setup>, config_dir_setup_callback=<function \_default_folder_setup>)

Retrieve or create the configs directory specific to the given app name.

### Args

- app_name (str): Name of the app for which the configs directory is needed.
- configs_name (str): Name of the configs directory.
- app_dir_setup_callback (Callable[[str], None]): A callback function to initialize the app directory.
  : Default is \_default_folder_setup.
- config_dir_setup_callback (Callable[[str], None]): A callback function to initialize the configs directory.
  : Default is \_default_folder_setup.

### config2py.util.identity(x)

Function that just returns its argument.

* **Return type:**
  [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

### config2py.util.is_not_empty(x)

Function that returns True if x is not empty.

* **Return type:**
  [`bool`](https://docs.python.org/3/library/functions.html#bool)

### config2py.util.is_repl()

Determines if the Python interpreter is running in REPL.

To test: If you put it in a module.py, do a print of it in the module, and do
`python module.py` it should print False.
If you do `python -i module.py`, or call it from a python console or jupyter
notebook, it should return `True`.

* **Parameters:**
  **repl_conditions** ([*list*](https://docs.python.org/3/library/stdtypes.html#list)) – 

  A list of functions that return True if the interpreter
  is running in a REPL, False otherwise.
  By default, this is a list of two functions that check if:
  - `get_ipython` is in globals
  - `__main__` does not have a `__file__` attribute
* **Returns:**
  True if running in a REPL, False otherwise.
* **Return type:**
  [*bool*](https://docs.python.org/3/library/functions.html#bool)

is_repl.repl_conditions is a set of functions that return True if the interpreter.
This set can be modified to modify the behavior of `is_repl`.

### config2py.util.parse_assignments_from_py_source(source_code, \*, name_filt=None, value_filt=<function \_value_node_is_instance_of>)

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

### config2py.util.system_default_for_app_data_folder(folder_kind='config', , standards=None)

Get the system default folder for `folder_kind`.

The root is the value of the platform’s standard environment variable for
that kind, falling back to the spec’s `default_path`; the spec’s
`subpath` (usually empty) is then appended.

* **Parameters:**
  * **folder_kind** ([`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)[`'config'`, `'data'`, `'cache'`, `'state'`, `'runtime'`]) – One of ‘config’, ‘data’, ‘cache’, ‘state’, ‘runtime’.
  * **standards** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`dict`](https://docs.python.org/3/library/stdtypes.html#dict)]) – The `{folder_kind: FolderSpec}` table to resolve against.
    Defaults to the running platform’s (`APP_FOLDER_STANDARDS`);
    pass another platform’s table to resolve as that platform would.
* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)
