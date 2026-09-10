# config2py.sync_store

Synchronized key-value stores with automatic persistence.

Provides MutableMapping interfaces that automatically sync changes to their backing
storage. Supports deferred sync via context manager for batch operations.

```pycon
>>> import tempfile
>>> import json
>>>
>>> # Basic usage
>>> with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
...     _ = f.write('{"key": "value"}')
...     temp_file = f.name
>>>
>>> store = FileStore(temp_file)
>>> store['new_key'] = 'new_value'  # Auto-syncs immediately
>>> assert 'new_key' in store
>>>
>>> # Batch operations with context manager
>>> with store:
...     store['a'] = 1
...     store['b'] = 2
...     store['c'] = 3
...     # No sync until context exit
>>>
>>> import os
>>> os.unlink(temp_file)
```

### Functions

| [`register_extension`](#config2py.sync_store.register_extension)(ext, loader, dumper)   | Register loader/dumper for a file extension.     |
|--------------------------------------------------------------------------------------------|--------------------------------------------------|
| [`get_format_handlers`](#config2py.sync_store.get_format_handlers)(filepath)             | Get loader/dumper for a file based on extension. |

### Classes

| [`SyncStore`](#config2py.sync_store.SyncStore)(loader, dumper)                        | A MutableMapping that automatically syncs changes to backing storage.   |
|---------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| [`FileStore`](#config2py.sync_store.FileStore)(filepath, \*[, key_path, loader, ...]) | A SyncStore backed by a file with automatic format detection.           |
| [`JsonStore`](#config2py.sync_store.JsonStore)(filepath, \*[, key_path, indent, ...]) | A FileStore specialized for JSON files.                                 |

### *class* config2py.sync_store.FileStore(filepath, , key_path=None, loader=None, dumper=None, mode='r', dump_kwargs=None, create_file_content=None, create_key_path_content=None)

Bases: [`SyncStore`](#config2py.sync_store.SyncStore)

A SyncStore backed by a file with automatic format detection.

Supports nested key paths for working with specific sections.

* **Parameters:**
  * **filepath** (`Union`[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]) – Path to file (supports ~ expansion)
  * **key_path** (`Union`[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`Tuple`](https://docs.python.org/3/library/typing.html#typing.Tuple)[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`...`](https://docs.python.org/3/library/constants.html#Ellipsis)], [`None`](https://docs.python.org/3/library/constants.html#None)]) – Optional nested path to operate on
  * **loader** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`str`](https://docs.python.org/3/library/stdtypes.html#str)], [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)]]) – Optional custom loader (auto-detected from extension if not provided)
  * **dumper** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`dict`](https://docs.python.org/3/library/stdtypes.html#dict)], [`str`](https://docs.python.org/3/library/stdtypes.html#str)]]) – Optional custom dumper (auto-detected from extension if not provided)
  * **mode** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – File read mode (‘r’ for text, ‘rb’ for binary)
  * **dump_kwargs** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`dict`](https://docs.python.org/3/library/stdtypes.html#dict)]) – Additional kwargs for dumper
  * **create_file_content** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[], [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)]]) – Optional factory callable that returns initial dict content
    for missing files. If None, FileNotFoundError is raised for missing files.
  * **create_key_path_content** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[], [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]) – Optional factory callable that returns initial content
    for missing key_path. If None, KeyError is raised for missing key paths.

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

### *class* config2py.sync_store.JsonStore(filepath, , key_path=None, indent=2, ensure_ascii=False, \*\*dump_kwargs)

Bases: [`FileStore`](#config2py.sync_store.FileStore)

A FileStore specialized for JSON files.

Pre-configured with json.loads/dumps and sensible defaults.

* **Parameters:**
  * **filepath** (`Union`[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]) – Path to JSON file
  * **key_path** (`Union`[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`Tuple`](https://docs.python.org/3/library/typing.html#typing.Tuple)[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`...`](https://docs.python.org/3/library/constants.html#Ellipsis)], [`None`](https://docs.python.org/3/library/constants.html#None)]) – Optional nested path to operate on
  * **indent** ([`int`](https://docs.python.org/3/library/functions.html#int)) – JSON indentation (default: 2)
  * **ensure_ascii** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – Whether to escape non-ASCII (default: False)
  * **\*\*dump_kwargs** – Additional kwargs for json.dumps

### *class* config2py.sync_store.SyncStore(loader, dumper)

Bases: [`MutableMapping`](https://docs.python.org/3/library/collections.abc.html#collections.abc.MutableMapping)

A MutableMapping that automatically syncs changes to backing storage.

Supports deferred sync via context manager for efficient batch operations.

* **Parameters:**
  * **loader** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[], [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)]) – Function that returns the current data as a dict
  * **dumper** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`dict`](https://docs.python.org/3/library/stdtypes.html#dict)], [`None`](https://docs.python.org/3/library/constants.html#None)]) – Function that persists the data dict to storage

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

### config2py.sync_store.get_format_handlers(filepath)

Get loader/dumper for a file based on extension.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Tuple`](https://docs.python.org/3/library/typing.html#typing.Tuple)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable), [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)]]

### config2py.sync_store.register_extension(ext, loader, dumper)

Register loader/dumper for a file extension.

* **Return type:**
  [`None`](https://docs.python.org/3/library/constants.html#None)
