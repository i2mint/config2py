---
name: config2py-quickstart
description: >-
  Use config2py to get configuration values and secrets into Python code:
  layered lookup (environment variables, then a local config folder, then an
  interactive prompt whose answer is saved), per-app config/data/cache/state
  folders that follow XDG and Windows conventions, JSON/INI/YAML/TOML files
  exposed as dicts that save on write, and extension-based codecs. Use when
  code needs an API key or setting "from the environment or a config file",
  when prompting a user once for a value and remembering it, when deciding
  where an app should store its files, or when reading and writing config
  files as mappings. Triggers: config2py, config_getter, simple_config_getter,
  get_config, user_gettable, ask_user_for_input, get_app_folder, AppData,
  FileStore, JsonStore, ConfigStore, ConfigReader, decode_by_extension.
metadata:
  audience: users
---

# config2py quickstart

`pip install config2py`. Optional format extras: `config2py[yaml]`, `[toml]`, `[env]`, `[json5]`, `[properties]`, or `[all-codecs]`.

## Pick the entry point

| You need | Use |
|---|---|
| A value from an env var, else a saved local config, else ask once and save | `config_getter`, or your own via `simple_config_getter(...)` |
| Your own ordered sources (dicts, callables, stores) | `get_config(key, sources, default=...)` |
| Ask the user for a value and store the answer | `user_gettable(save_to=store)` |
| Where app `X` should keep config, data, cache or state files | `get_app_folder("X", folder_kind=...)`, or the `AppData("X")` facade |
| A JSON/INI/YAML/TOML file as a dict that is saved on every write | `FileStore`, `JsonStore` |
| An `.ini` file as a mapping of sections | `ConfigStore` (read-write), `ConfigReader` |
| Bytes to Python objects (and back) chosen by file extension | `config2py.codecs` |

## Layered lookup: `get_config`

Sources are tried in order and the first one that has the key wins. A source is any mapping, or any callable `key -> value` that raises when it doesn't have the key. Pass `sources` alone to get a reusable getter.

```python
import os
from config2py import get_config

defaults = {"MODEL": "small", "TIMEOUT": "30"}
get = get_config(sources=[{"MODEL": "large"}, defaults])
assert get("MODEL") == "large"
assert get("TIMEOUT") == "30"
assert get("NOT_SET", default=None) is None


def from_vault(key):  # any callable works as a source
    raise KeyError(key)  # "not here": move on to the next source


get = get_config(
    sources=[from_vault, os.environ, defaults],
    config_not_found_exceptions=(KeyError, LookupError),  # see the gotchas
)
assert get("TIMEOUT") == "30"
```

`get_config` also takes `egress=lambda key, value: ...` to post-process (or cache) what it found, and `val_is_valid=` to skip values such as `None` or `""`.

## The ready-made getter: `simple_config_getter`

`simple_config_getter(src)` looks in environment variables, then in a local store, and optionally asks the user and saves the answer in that store. `src` is an app name (store in `~/.config/<app>/configs/`), a directory path containing a separator (a folder of one text file per key), or an `.ini`/`.cfg` file. The package-level `config_getter` is `simple_config_getter()` with the defaults (app name `config2py`).

```python
import os
import tempfile
from config2py import simple_config_getter

folder = tempfile.mkdtemp() + os.sep  # a trailing separator marks a folder path
get = simple_config_getter(folder, ask_user_if_key_not_found=False)
get.configs["DB_URL"] = "sqlite:///app.db"  # writes the file <folder>/DB_URL
assert get("DB_URL") == "sqlite:///app.db"

os.environ["DB_URL"] = "postgres://prod"  # env vars are consulted first
assert get("DB_URL") == "postgres://prod"
del os.environ["DB_URL"]
```

## Ask the user once, remember the answer

`user_gettable(save_to=...)` is a mapping that prompts for any key and saves non-empty answers into `save_to` (any `MutableMapping`, or a `(key, value)` function). Put it last in a source list, after the store it saves to. `user_asker` is swapped here so the example runs unattended.

```python
from config2py import get_config, user_gettable

saved = {}
ask = user_gettable(save_to=saved, user_asker=lambda prompt: "typed value")
get = get_config(sources=[saved, ask])
assert get("API_TOKEN") == "typed value"  # asked, then saved
assert saved == {"API_TOKEN": "typed value"}
assert get("API_TOKEN") == "typed value"  # now found in `saved`, not asked again
```

The default asker is `ask_user_for_input`. It masks what the user types when the prompt looks secret (it mentions `key`, `token`, `pass`, `pwd`, `secret`, `api`, `auth`, `credential` or `private`) and echoes it otherwise. Force a choice with `ask_user_for_input(prompt, mask_input=True)` (or `False`), or pass your own `prompt -> bool` predicate. The match is a plain substring test on the prompt, so `KEYS_DIR` is masked too. When masking comes from the predicate and stdin is piped, the answer is read from stdin; an explicit `mask_input=True` always reads the terminal, like `sudo`.

## App folders

```python
import os
from config2py import get_app_folder

config_dir = get_app_folder("myapp", folder_kind="config")
data_dir = get_app_folder("myapp", folder_kind="data", ensure_exists=True)
assert os.path.basename(config_dir) == "myapp" and os.path.isdir(data_dir)
```

- Kinds are `config` (settings, API keys), `data` (files users would miss), `cache` (disposable), `state` (logs, history) and `runtime` (sockets, PID files).
- On Linux and macOS: `~/.config`, `~/.local/share`, `~/.cache`, `~/.local/state`, then `$XDG_RUNTIME_DIR` or `/tmp`. macOS uses these XDG paths, not `~/Library`. On Windows: `%APPDATA%`, `%LOCALAPPDATA%`, `%LOCALAPPDATA%\Temp`, `%LOCALAPPDATA%`, `%TEMP%`.
- Precedence: `CONFIG2PY_<KIND>_DIR` (for example `CONFIG2PY_DATA_DIR`), then the platform variable (`XDG_DATA_HOME`, `LOCALAPPDATA`, ...), then the default. These name the *root*; the app name is appended.
- Folders config2py creates are owner-only (`0o700`). `FileStore`, `ConfigStore` and `AppData` write files as `0o600`.

`AppData("myapp")` wraps this: `.app_folder(folder_kind=...)`, `.get_artifact_dir("runs")`, and `.get_resource(name)` / `.get_config(name)`, which copy a default file shipped in `myapp/_seed_data/{resources,config}/` on first access and never overwrite user edits.

## Files as dicts: `FileStore`, `JsonStore`

The format comes from the extension: `.json`, `.ini`/`.cfg`, `.yaml`/`.yml` (needs `pyyaml`) and `.toml` (needs `tomli-w` to write). Every write saves the file, and a `with` block batches the writes into one save.

```python
import json
import os
import tempfile
from config2py import FileStore

path = os.path.join(tempfile.mkdtemp(), "settings.json")
# create_file_content makes a missing file (without it, a missing file raises)
settings = FileStore(path, create_file_content=dict)
settings["theme"] = "dark"  # saved immediately
with settings:  # one save, on exit
    settings["a"] = 1
    settings["b"] = 2

db = FileStore(path, key_path="database", create_key_path_content=dict)
db["host"] = "localhost"  # only touches the "database" section
assert json.load(open(path)) == {
    "theme": "dark",
    "a": 1,
    "b": 2,
    "database": {"host": "localhost"},
}
```

`key_path` also takes a dotted path (`"app.settings"`) or a tuple. Use `register_extension(".ext", loader, dumper)` to add a format, and `SyncStore(loader, dumper)` to back the mapping with anything else.

## INI files: `ConfigStore`

```python
import os
import tempfile
from config2py import ConfigStore

path = os.path.join(tempfile.mkdtemp(), "app.ini")
with open(path, "w") as f:
    f.write("[db]\nhost = localhost\n")

store = ConfigStore(path)
store["cache"] = {"ttl": "60"}  # assigning a section saves the file
with store:  # edits *inside* a section are saved when the block exits
    store["db"]["port"] = "5432"
assert "port = 5432" in open(path).read()
```

## Codecs by extension

```python
from config2py.codecs import decode_by_extension, encode_by_extension, register_codec

data = encode_by_extension("settings.json", {"a": 1})
assert decode_by_extension("settings.json", data) == {"a": 1}
register_codec(".upper", encoder=lambda s: s.upper().encode(), decoder=bytes.decode)
assert decode_by_extension("x.upper", encode_by_extension("x.upper", "hi")) == "HI"
```

## Gotchas

- **Prompts in production.** `ask_user_if_key_not_found=None` (the default) prompts whenever `is_repl()` is true, and that includes `python -c` and notebooks. Pass `ask_user_if_key_not_found=False` in services, CI and libraries.
- **Import-time side effect.** `import config2py` creates `~/.config/config2py/configs/`, and default folders are resolved at import. In tests, point `HOME`/`XDG_CONFIG_HOME` (or `CONFIG2PY_CONFIG_DIR`) at a temp dir *before* the first import.
- **Broad fallback.** `config_not_found_exceptions` defaults to `(Exception,)`, so a bug or network error in a callable source silently falls through to the next source. Narrow it when you can.
- **Plain text, not a vault.** Values saved by the prompt flow are plain one-file-per-key text files, currently written with the umask default and protected only by their `0o700` folder when config2py created it (i2mint/config2py#33). `envvar` hides values from `repr()` only, not from iteration or pickling.
- **Silent empties.** `ConfigReader("typo.ini")` and `extract_exports("typo/.env")` return empty results instead of raising, so check that the path exists first.
- **Pickle.** `.pkl`/`.pickle` decode with `pickle.loads`, so never decode untrusted bytes under those extensions.
- **Bare names are app names.** `get_configs_local_store("configs")` means the app `configs`, even if `./configs` exists. Pass `"./configs"` to use the directory.
