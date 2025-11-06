"""
Synchronized key-value stores with automatic persistence.

Provides MutableMapping interfaces that automatically sync changes to their backing
storage. Supports deferred sync via context manager for batch operations.

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
"""

from typing import Callable, Any, Iterator, Union, Tuple, Optional, Dict
from collections.abc import MutableMapping
from pathlib import Path
import json
from functools import reduce

__all__ = [
    "SyncStore",
    "FileStore",
    "JsonStore",
    "register_extension",
    "get_format_handlers",
]

# Note: Independent module. No imports from config2py, dol etc.
# TODO: Do we want to use more stuff from config2py, dol, etc.?

# Type aliases
KeyPath = Union[str, Tuple[str, ...], None]
Loader = Callable[[], dict]
Dumper = Callable[[dict], None]


# --------------------------------------------------------------------------------------
# Extension Registry

_extension_registry: Dict[str, Tuple[Callable, Callable]] = {}


def register_extension(ext: str, loader: Callable, dumper: Callable) -> None:
    """Register loader/dumper for a file extension."""
    _extension_registry[ext.lower()] = (loader, dumper)


def get_format_handlers(
    filepath: Union[str, Path],
) -> Optional[Tuple[Callable, Callable]]:
    """Get loader/dumper for a file based on extension."""
    ext = Path(filepath).suffix.lower()
    return _extension_registry.get(ext)


# Register standard formats
register_extension(".json", json.loads, json.dumps)

# TODO: Use register-if-available pattern (with context managers.. implemented somewhere...)

# ConfigParser for .ini and .cfg
try:
    from configparser import ConfigParser
    import io

    def _ini_loader(content: str) -> dict:
        parser = ConfigParser()
        parser.read_string(content)
        return {section: dict(parser[section]) for section in parser.sections()}

    def _ini_dumper(data: dict) -> str:
        parser = ConfigParser()
        for section, values in data.items():
            parser[section] = values
        output = io.StringIO()
        parser.write(output)
        return output.getvalue()

    register_extension(".ini", _ini_loader, _ini_dumper)
    register_extension(".cfg", _ini_loader, _ini_dumper)
except ImportError:
    pass

# YAML support (optional)
try:
    import yaml

    register_extension(".yaml", yaml.safe_load, yaml.dump)
    register_extension(".yml", yaml.safe_load, yaml.dump)
except ImportError:
    pass

# TOML support (optional)
try:
    import tomllib  # Python 3.11+
    import tomli_w

    register_extension(".toml", tomllib.loads, tomli_w.dumps)
except ImportError:
    try:
        import tomli
        import tomli_w

        register_extension(".toml", tomli.loads, tomli_w.dumps)
    except ImportError:
        pass


# --------------------------------------------------------------------------------------
# Helper functions for nested key paths

# TODO: Consider using dol.paths


def _normalize_key_path(key_path: KeyPath) -> Tuple[str, ...]:
    """Normalize key_path to tuple of strings."""
    if key_path is None or key_path == ():
        return ()
    if isinstance(key_path, str):
        return tuple(key_path.split(".")) if "." in key_path else (key_path,)
    return tuple(key_path)


def _get_nested(data: dict, path: Tuple[str, ...]) -> Any:
    """Get value from nested dict using path."""
    if not path:
        return data
    return reduce(lambda d, key: d[key], path, data)


def _set_nested(data: dict, path: Tuple[str, ...], value: Any) -> dict:
    """Set value in nested dict, creating intermediate dicts as needed."""
    if not path:
        return value

    result = data.copy() if isinstance(data, dict) else {}
    current = result

    for key in path[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]

    current[path[-1]] = value
    return result


# --------------------------------------------------------------------------------------
# Core Classes


class SyncStore(MutableMapping):
    """
    A MutableMapping that automatically syncs changes to backing storage.

    Supports deferred sync via context manager for efficient batch operations.

    Args:
        loader: Function that returns the current data as a dict
        dumper: Function that persists the data dict to storage

    Example:
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
    """

    def __init__(self, loader: Loader, dumper: Dumper):
        self._loader = loader
        self._dumper = dumper
        self._data = None
        self._auto_sync = True
        self._needs_flush = False
        self._load()

    def _load(self):
        """Load data from backing storage."""
        self._data = self._loader()

    def _mark_dirty(self):
        """Mark data as changed and sync if auto_sync is enabled."""
        self._needs_flush = True
        if self._auto_sync:
            self.flush()

    def flush(self):
        """Sync data to backing storage if changes exist."""
        if self._needs_flush:
            self._dumper(self._data)
            self._needs_flush = False

    def __enter__(self):
        """Enter deferred sync mode."""
        self._auto_sync = False
        return self

    def __exit__(self, *args):
        """Exit deferred sync mode and flush changes."""
        self.flush()
        self._auto_sync = True

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value
        self._mark_dirty()

    def __delitem__(self, key):
        del self._data[key]
        self._mark_dirty()

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return f"{self.__class__.__name__}({len(self._data)} items)"


class FileStore(SyncStore):
    """
    A SyncStore backed by a file with automatic format detection.

    Supports nested key paths for working with specific sections.

    Args:
        filepath: Path to file (supports ~ expansion)
        key_path: Optional nested path to operate on
        loader: Optional custom loader (auto-detected from extension if not provided)
        dumper: Optional custom dumper (auto-detected from extension if not provided)
        mode: File read mode ('r' for text, 'rb' for binary)
        dump_kwargs: Additional kwargs for dumper
        create_file_content: Optional factory callable that returns initial dict content
            for missing files. If None, FileNotFoundError is raised for missing files.
        create_key_path_content: Optional factory callable that returns initial content
            for missing key_path. If None, KeyError is raised for missing key paths.

    Example:
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
    """

    def __init__(
        self,
        filepath: Union[str, Path],
        *,
        key_path: KeyPath = None,
        loader: Optional[Callable[[str], dict]] = None,
        dumper: Optional[Callable[[dict], str]] = None,
        mode: str = "r",
        dump_kwargs: Optional[dict] = None,
        create_file_content: Optional[Callable[[], dict]] = None,
        create_key_path_content: Optional[Callable[[], Any]] = None,
    ):
        self.filepath = Path(filepath).expanduser()
        self.key_path = _normalize_key_path(key_path)
        self.mode = mode
        self.dump_kwargs = dump_kwargs or {}
        self.create_file_content = create_file_content
        self.create_key_path_content = create_key_path_content

        # Auto-detect format if not provided
        if loader is None or dumper is None:
            handlers = get_format_handlers(self.filepath)
            if handlers is None:
                raise ValueError(
                    f"No format handler registered for {self.filepath.suffix}. "
                    f"Provide explicit loader/dumper or register the extension."
                )
            auto_loader, auto_dumper = handlers
            loader = loader or auto_loader
            dumper = dumper or auto_dumper

        self._file_loader = loader
        self._file_dumper = dumper

        # Create loader/dumper closures for SyncStore
        super().__init__(loader=self._load_from_file, dumper=self._dump_to_file)

    def _load_from_file(self) -> dict:
        """Read and parse file, returning the section specified by key_path."""
        # Handle missing file
        if not self.filepath.exists():
            if self.create_file_content is None:
                raise FileNotFoundError(f"File not found: {self.filepath}")

            # Create file with initial content
            initial_data = self.create_file_content()
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            content = self._file_dumper(initial_data, **self.dump_kwargs)
            write_mode = "w" if "b" not in self.mode else "wb"
            with open(self.filepath, write_mode) as f:
                f.write(content)
            data = initial_data
        else:
            # Load existing file
            with open(self.filepath, self.mode) as f:
                content = f.read()
            data = self._file_loader(content)

        # Handle missing key_path
        try:
            return _get_nested(data, self.key_path)
        except (KeyError, TypeError):
            if self.create_key_path_content is None:
                raise KeyError(f"Key path not found: {self.key_path}")

            # Create key_path with initial content
            initial_content = self.create_key_path_content()
            full_data = _set_nested(data, self.key_path, initial_content)

            # Write back to file
            content = self._file_dumper(full_data, **self.dump_kwargs)
            write_mode = "w" if "b" not in self.mode else "wb"
            with open(self.filepath, write_mode) as f:
                f.write(content)

            return initial_content

    def _dump_to_file(self, section_data: dict) -> None:
        """Write data to file, updating only the section specified by key_path."""
        if not self.key_path:
            # No key_path, write entire data
            content = self._file_dumper(section_data, **self.dump_kwargs)
        else:
            # Have key_path, need to merge with full file content
            with open(self.filepath, self.mode) as f:
                full_data = self._file_loader(f.read())
            full_data = _set_nested(full_data, self.key_path, section_data)
            content = self._file_dumper(full_data, **self.dump_kwargs)

        write_mode = "w" if "b" not in self.mode else "wb"
        with open(self.filepath, write_mode) as f:
            f.write(content)

    def __repr__(self):
        key_path_str = f", key_path={self.key_path!r}" if self.key_path else ""
        return f"{self.__class__.__name__}({self.filepath!r}{key_path_str})"


class JsonStore(FileStore):
    """
    A FileStore specialized for JSON files.

    Pre-configured with json.loads/dumps and sensible defaults.

    Args:
        filepath: Path to JSON file
        key_path: Optional nested path to operate on
        indent: JSON indentation (default: 2)
        ensure_ascii: Whether to escape non-ASCII (default: False)
        **dump_kwargs: Additional kwargs for json.dumps
    """

    def __init__(
        self,
        filepath: Union[str, Path],
        *,
        key_path: KeyPath = None,
        indent: int = 2,
        ensure_ascii: bool = False,
        **dump_kwargs,
    ):
        dump_kwargs.setdefault("indent", indent)
        dump_kwargs.setdefault("ensure_ascii", ensure_ascii)

        super().__init__(
            filepath,
            loader=json.loads,
            dumper=json.dumps,
            key_path=key_path,
            mode="r",
            dump_kwargs=dump_kwargs,
        )
