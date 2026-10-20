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
import errno
import os
import secrets
import time
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


def _secure_open(path, mode="w", *, follow_symlinks=True):
    """Open ``path`` for writing with owner-only (``0o600``) permissions.

    Local copy of ``config2py.util.secure_open`` -- this module deliberately has no
    intra-package imports (see note above). Avoids writing files that may hold secrets
    with the process's default (often world-readable) umask; see i2mint/config2py#15.

    Re-tightens via ``os.fchmod`` on the open fd (not just relying on ``os.open``'s
    ``mode`` argument, which POSIX only consults when a *new* file is created -- a
    pre-existing, already-loose file would otherwise keep its old permissions).

    With ``follow_symlinks=False`` a symlink at ``path`` (the last component only) and a
    file with several hard links are refused (``OSError``), the file left untouched;
    see i2mint/config2py#45 and #51.
    """
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if not follow_symlinks:
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        elif os.path.islink(path):  # Windows: no O_NOFOLLOW (check, then open)
            raise OSError(errno.ELOOP, "Refusing to follow a symlink", os.fspath(path))
        flags &= ~os.O_TRUNC  # truncate only after the hard link check
    fd = os.open(path, flags, 0o600)
    try:
        if not follow_symlinks:
            if os.fstat(fd).st_nlink > 1:
                raise OSError(
                    errno.EMLINK,
                    "Refusing a file with several hard links",
                    os.fspath(path),
                )
            os.ftruncate(fd, 0)
        if hasattr(os, "fchmod"):  # POSIX only -- Windows ACLs aren't unix mode bits
            os.fchmod(fd, 0o600)
        return os.fdopen(fd, mode)
    except BaseException:
        os.close(fd)
        raise


#: Hidden temp files older than this (seconds) are leftovers of a killed writer.
_STALE_TMP_SECONDS = 3600


def _sweep_stale_tmp(folder, name, *, max_age=_STALE_TMP_SECONDS):
    """Remove ``.<name>.<hex>.tmp`` leftovers (e.g. from a SIGKILL) older than ``max_age``."""
    prefix = f".{name}."
    try:
        entries = os.listdir(folder)
    except OSError:
        return
    for entry in entries:
        if not (entry.startswith(prefix) and entry.endswith(".tmp")):
            continue
        full = os.path.join(folder, entry)
        try:
            if time.time() - os.lstat(full).st_mtime > max_age:
                os.remove(full)
        except OSError:
            pass


def _atomic_write(path, content, *, follow_symlinks=True):
    """Replace ``path`` with ``content`` (``str`` or ``bytes``) atomically, ``0o600``.

    Writes a hidden ``0o600`` temp file next to ``path``, ``fsync``\ s it, then
    ``os.replace``\ s it over ``path``, so a crash never leaves the file empty or
    partial (see i2mint/config2py#52, #61). Local copy of
    ``config2py.util.atomic_write_bytes`` (this module has no intra-package imports).
    With ``follow_symlinks=False`` a symlink at ``path`` or a file with several hard
    links is refused (``OSError``) and left untouched.
    """
    path = os.fspath(path)
    data = content.encode("utf-8") if isinstance(content, str) else content
    if follow_symlinks:
        path = os.path.realpath(path)
    else:
        if os.path.islink(path):
            raise OSError(errno.ELOOP, "Refusing to replace a symlink", path)
        try:
            if os.stat(path).st_nlink > 1:
                raise OSError(
                    errno.EMLINK, "Refusing a file with several hard links", path
                )
        except FileNotFoundError:
            pass
    folder, name = os.path.split(path)
    _sweep_stale_tmp(folder or ".", name)
    tmp_path = os.path.join(folder, f".{name}.{secrets.token_hex(4)}.tmp")
    try:
        with _secure_open(tmp_path, "xb", follow_symlinks=False) as fp:
            fp.write(data)
            fp.flush()
            os.fsync(fp.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


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
        """See the class docstring for ``loader`` and ``dumper``."""
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
        follow_symlinks: If False, writing refuses (``OSError``) to go through a symlink
            at ``filepath`` (or a file with several hard links), instead of writing
            to its target (see i2mint/config2py#45). Default True, like ``open``.

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
        follow_symlinks: bool = True,
    ):
        """See the class docstring for each parameter."""
        self.filepath = Path(filepath).expanduser()
        self.follow_symlinks = follow_symlinks
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
            self.filepath.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            content = self._file_dumper(initial_data, **self.dump_kwargs)
            _atomic_write(
                self.filepath, content, follow_symlinks=self.follow_symlinks
            )
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
            _atomic_write(
                self.filepath, content, follow_symlinks=self.follow_symlinks
            )

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

        _atomic_write(
            self.filepath, content, follow_symlinks=self.follow_symlinks
        )

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
        follow_symlinks: See ``FileStore``.
        ensure_ascii: Whether to escape non-ASCII (default: False)
        follow_symlinks: See ``FileStore``.
        **dump_kwargs: Additional kwargs for json.dumps
    """

    def __init__(
        self,
        filepath: Union[str, Path],
        *,
        key_path: KeyPath = None,
        indent: int = 2,
        ensure_ascii: bool = False,
        follow_symlinks: bool = True,
        **dump_kwargs,
    ):
        """See the class docstring for each parameter."""
        dump_kwargs.setdefault("indent", indent)
        dump_kwargs.setdefault("ensure_ascii", ensure_ascii)

        super().__init__(
            filepath,
            loader=json.loads,
            dumper=json.dumps,
            key_path=key_path,
            mode="r",
            dump_kwargs=dump_kwargs,
            follow_symlinks=follow_symlinks,
        )
