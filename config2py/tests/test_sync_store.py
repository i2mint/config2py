"""Tests for sync_store module."""

import tempfile
import json
from pathlib import Path
from config2py.sync_store import SyncStore, FileStore, JsonStore, register_extension

try:
    import pytest

    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False


def test_sync_store_basic_operations():
    """Test basic MutableMapping operations."""
    data_holder = [{}]

    def loader():
        return data_holder[0].copy()

    def dumper(data):
        data_holder[0] = data.copy()

    store = SyncStore(loader, dumper)

    # Set
    store["key"] = "value"
    assert store["key"] == "value"
    assert data_holder[0]["key"] == "value"

    # Delete
    del store["key"]
    assert "key" not in store
    assert "key" not in data_holder[0]

    # Iteration
    store["a"] = 1
    store["b"] = 2
    assert set(store) == {"a", "b"}

    # Length
    assert len(store) == 2


def test_sync_store_auto_sync():
    """Test that changes auto-sync by default."""
    data_holder = [{}]
    sync_count = [0]

    def loader():
        return data_holder[0].copy()

    def dumper(data):
        data_holder[0] = data.copy()
        sync_count[0] += 1

    store = SyncStore(loader, dumper)

    store["a"] = 1
    assert sync_count[0] == 1

    store["b"] = 2
    assert sync_count[0] == 2

    del store["a"]
    assert sync_count[0] == 3


def test_sync_store_context_manager():
    """Test deferred sync with context manager."""
    data_holder = [{}]
    sync_count = [0]

    def loader():
        return data_holder[0].copy()

    def dumper(data):
        data_holder[0] = data.copy()
        sync_count[0] += 1

    store = SyncStore(loader, dumper)

    # Batch operations
    with store:
        store["a"] = 1
        store["b"] = 2
        store["c"] = 3
        assert sync_count[0] == 0  # Not synced yet

    assert sync_count[0] == 1  # Synced once on exit
    assert data_holder[0] == {"a": 1, "b": 2, "c": 3}


def test_sync_store_manual_flush():
    """Test manual flush() call."""
    data_holder = [{}]
    sync_count = [0]

    def loader():
        return data_holder[0].copy()

    def dumper(data):
        data_holder[0] = data.copy()
        sync_count[0] += 1

    store = SyncStore(loader, dumper)

    with store:
        store["a"] = 1
        assert sync_count[0] == 0

        store.flush()  # Manual flush
        assert sync_count[0] == 1

        store["b"] = 2
        assert sync_count[0] == 1  # Still in context, not auto-synced

    assert sync_count[0] == 2  # Final flush on exit


def test_file_store_json():
    """Test FileStore with JSON file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"key": "value"}')
        temp_file = f.name

    try:
        store = FileStore(temp_file)

        # Read
        assert store["key"] == "value"

        # Write
        store["new_key"] = "new_value"

        # Verify persistence
        with open(temp_file) as f:
            data = json.load(f)
        assert data["new_key"] == "new_value"

        # Delete
        del store["key"]
        assert "key" not in store

    finally:
        Path(temp_file).unlink()


def test_file_store_key_path():
    """Test FileStore with nested key_path."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"section1": {"a": 1}, "section2": {"b": 2}}')
        temp_file = f.name

    try:
        # Work with section1 only
        section1 = FileStore(temp_file, key_path="section1")

        assert section1["a"] == 1
        section1["c"] = 3
        assert "c" in section1

        # Verify section2 untouched
        with open(temp_file) as f:
            data = json.load(f)
        assert data["section2"] == {"b": 2}
        assert data["section1"]["c"] == 3

    finally:
        Path(temp_file).unlink()


def test_file_store_dotted_key_path():
    """Test FileStore with dotted key_path notation."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"a": {"b": {"c": {}}}}')
        temp_file = f.name

    try:
        nested = FileStore(temp_file, key_path="a.b.c")
        nested["key"] = "value"

        with open(temp_file) as f:
            data = json.load(f)
        assert data["a"]["b"]["c"]["key"] == "value"

    finally:
        Path(temp_file).unlink()


def test_json_store():
    """Test JsonStore with defaults."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"key": "value"}')
        temp_file = f.name

    try:
        store = JsonStore(temp_file)
        store["new"] = "data"

        # Check formatting (indent=2 by default)
        with open(temp_file) as f:
            content = f.read()
        assert "  " in content  # Should have indentation

    finally:
        Path(temp_file).unlink()


def test_file_store_batch_operations():
    """Test that batch operations work efficiently."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{}")
        temp_file = f.name

    try:
        store = FileStore(temp_file)

        # Batch mode - only one write
        with store:
            for i in range(100):
                store[f"key_{i}"] = i

        # Verify all written
        with open(temp_file) as f:
            data = json.load(f)
        assert len(data) == 100
        assert data["key_42"] == 42

    finally:
        Path(temp_file).unlink()


def test_extension_registry():
    """Test custom extension registration."""

    # Register custom format
    def custom_loader(content):
        return {"loaded": content}

    def custom_dumper(data):
        return str(data)

    register_extension(".custom", custom_loader, custom_dumper)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".custom", delete=False) as f:
        f.write("test content")
        temp_file = f.name

    try:
        store = FileStore(temp_file)
        assert store["loaded"] == "test content"

    finally:
        Path(temp_file).unlink()


def test_store_repr():
    """Test string representations."""
    data_holder = [{}]
    store = SyncStore(lambda: data_holder[0], lambda d: None)
    assert "SyncStore" in repr(store)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"section": {}}')  # Include section key
        temp_file = f.name

    try:
        file_store = FileStore(temp_file)
        assert "FileStore" in repr(file_store)
        assert temp_file in repr(file_store)

        file_store_with_path = FileStore(temp_file, key_path="section")
        assert "key_path" in repr(file_store_with_path)

    finally:
        Path(temp_file).unlink()


if __name__ == "__main__":
    if PYTEST_AVAILABLE:
        pytest.main([__file__, "-v"])
    else:
        # Run tests manually
        print("Running tests without pytest...")
        tests = [
            test_sync_store_basic_operations,
            test_sync_store_auto_sync,
            test_sync_store_context_manager,
            test_sync_store_manual_flush,
            test_file_store_json,
            test_file_store_key_path,
            test_file_store_dotted_key_path,
            test_json_store,
            test_file_store_batch_operations,
            test_extension_registry,
            test_store_repr,
        ]

        failed = []
        for test in tests:
            try:
                test()
                print(f"✓ {test.__name__}")
            except Exception as e:
                print(f"✗ {test.__name__}: {e}")
                failed.append((test.__name__, e))

        print(f"\n{len(tests) - len(failed)}/{len(tests)} tests passed")
        if failed:
            print("\nFailed tests:")
            for name, error in failed:
                print(f"  {name}: {error}")
            exit(1)
