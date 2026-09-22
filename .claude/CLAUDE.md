# config2py

Tools to read and write configurations from various sources and formats: layered
lookup (env vars, files, user prompt), a `ConfigStore`/`ConfigReader` data-object
layer over `configparser`, extension-based codecs, and synchronized key-value
stores with automatic persistence.

## Module map (`config2py/`)

- `base.py` — `get_config`, `user_gettable`, `sources_chainmap`: the layered
  lookup chain a config value is resolved through.
- `tools.py` — `config_getter`/`simple_config_getter` (the headline "ask user for
  missing key -> save to disk" flow), `get_configs_local_store`, `local_configs`,
  `configs`, `Configs`, `extract_exports`.
- `util.py` — `envvar` (like `os.environ` but hides secrets on display),
  `ask_user_for_input`, `get_app_config_folder`/`get_app_data_folder`/`get_app_folder`.
- `s_configparser.py` — `ConfigStore`/`ConfigReader`: a data-object layer over
  stdlib `configparser`.
- `codecs.py` — extension-based codec registry (bytes <-> JSON-friendly Python
  types), keyed by file extension.
- `sync_store.py` — `MutableMapping`s that auto-sync changes to a backing store.
- `errors.py` — `Config2PyError` and subclasses.

## Tests & lint (verified)

```bash
uv venv .venv && uv pip install -e . pytest ruff
.venv/bin/pytest config2py --doctest-modules \
  -o doctest_optionflags='ELLIPSIS IGNORE_EXCEPTION_DETAIL' -q   # 132 passed, 4 skipped
.venv/bin/ruff check .
```
Or `wads ci-local`. **Gotchas already documented in `pyproject.toml` comments:**
`testpaths = ["config2py"]`, not `"tests"` — there is no top-level `tests/` dir,
only `config2py/tests/`. `doctest_optionflags` here is kept in sync with what CI's
`run-tests-uv` action passes on the command line (which *overrides* this
setting) — notably CI does **not** set `NORMALIZE_WHITESPACE`, so a doctest that
passes locally with the bare `pytest` config can still fail in CI; use the
command above (matching CI) to catch that before pushing.

## Invariants / known gaps (see open issues before "fixing" these)

- **`DFLT_MASKING_INPUT = False`** in `util.py` — `simple_config_getter`'s
  prompt-for-missing-key flow echoes typed input (including secrets) to the
  terminal by default; masking (`getpass`) is wired in but off by default.
  Flipping the default is blocked on 3 fleet dependents not present on every
  box (see [i2mint/config2py#13](https://github.com/i2mint/config2py/issues/13)) —
  don't change it without re-running the dependents check.
- [i2mint/config2py#16](https://github.com/i2mint/config2py/issues/16) — an
  omnibus of smaller audit findings (docstring overclaims, a broad fallback,
  the pickle codec, import-time side effects) — read before touching those areas.
- [i2mint/config2py#22](https://github.com/i2mint/config2py/pull/22) (open) —
  removes the vestigial `setup.cfg`, adds `[tool.wads.ci]`, migrates CI to the
  reusable-workflow stub; currently blocked on a hosted-CI `action_required`
  anomaly (see [#23](https://github.com/i2mint/config2py/issues/23)). Until it
  lands, CI here is the inline uv workflow using discrete `i2mint/wads` actions.

## Dependents

`accompy`, `aix`, `arioso`, `aw`, `brand`, `mood`, `py2store`, `tonal`, and 25
others (see `fleet_dependents.json`) import this package — check their tests
before changing `get_config`, `simple_config_getter`, or any default.
