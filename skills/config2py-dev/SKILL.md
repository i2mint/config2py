---
name: config2py-dev
description: >-
  Work on the config2py codebase itself: module map, how to run the tests the
  way CI does (doctests included), the dependents gate before changing a
  default, the docs-examples test that runs README and skill snippets, the
  release flow (merging to master publishes to PyPI), and the invariants and
  open design issues to read before "fixing" something. Use when contributing
  to, reviewing, debugging or releasing config2py (i2mint/config2py), or when
  a change touches get_config, simple_config_getter, ask_user_for_input,
  app folders or any public default.
metadata:
  audience: developers
---

# Working on config2py

## Module map (`config2py/`)

| Module | What lives there |
|---|---|
| `base.py` | `get_config` (the layered lookup), `sources_chainmap`, `FuncBasedGettableContainer` (callable to `KeyError`-raising mapping), `user_gettable` and `ask_user_for_key` (prompt, then save) |
| `tools.py` | `simple_config_getter`, `get_configs_local_store`, the import-time instances `config_getter`, `local_configs` and `configs`, plus `extract_exports` and `source_config_params` |
| `util.py` | `ask_user_for_input` (masking), `looks_like_secret`, `envvar`, app folders (`app_folder_standards`, `get_app_rootdir`, `get_app_folder`, `AppData`, `ensure_seeded`), `secure_open`/`secure_makedirs`, `is_repl` |
| `s_configparser.py` | `ConfigStore`/`ConfigReader`, mapping views over `configparser` |
| `sync_store.py` | `SyncStore`, `FileStore`, `JsonStore`, `register_extension`. It deliberately imports nothing from the package |
| `codecs.py` | Extension-keyed encoder and decoder registries (`encode_by_extension`, `decode_by_extension`, `register_codec`) |
| `errors.py` | `ConfigNotFound` and friends |
| `data/skills/` | Consumer skills shipped in the wheel. Dev skills like this one live in the top-level `skills/` |

All OS branching for folders is in `app_folder_standards(os_name)`, which takes the OS as an argument so both platforms are testable anywhere.

## Run the tests like CI

```bash
uv venv .venv && . .venv/bin/activate
uv pip install -e . pytest ruff
python -m pytest config2py --doctest-modules -o doctest_optionflags='ELLIPSIS IGNORE_EXCEPTION_DETAIL' -q
ruff check . && ruff format --check .
```

- Doctests are a large part of the suite. CI passes `doctest_optionflags` on the command line, which overrides `pyproject.toml`, and it does not set `NORMALIZE_WHITESPACE`, so always use the flags above.
- `testpaths = ["config2py"]`: the tests live in `config2py/tests/`, and there is no top-level `tests/`.
- `config2py/tests/test_docs_examples.py` runs every ```` ```python ```` block of `README.md` and of `config2py/data/skills/config2py-quickstart/SKILL.md` in a subprocess with a sandboxed HOME and closed stdin. When you edit either document, keep its blocks runnable, or put `<!-- no-test -->` on the line before a fence that has to prompt or needs placeholders.
- `wads ci-local` (from `pip install wads`) replays the whole CI job: ruff, pytest on each configured Python, then `uv build`. It is the pre-merge gate while hosted CI on the stub workflow is blocked (#23).

## Test isolation

`import config2py` creates `~/.config/config2py/configs/`, and folder defaults such as `DFLT_CONFIG_FOLDER` are computed at import. A test that needs a clean home must point `HOME` and the `XDG_*` variables (or `CONFIG2PY_*_DIR`) at a temp dir in a subprocess, as `test_docs_examples.py` does. Setting them after import has no effect on the module-level defaults. Prompt tests patch both `builtins.input` and `getpass.getpass`; `config2py/tests/utils_for_testing.py` has `user_input_patch` for that.

## Before changing a default or public behaviour

About 30 packages depend on config2py (for example `py2store`, `xdol`, `oa`, `aix`, `tonal`). A merge to master publishes to PyPI, so:

1. Grep the dependents for the symbol you are changing.
2. Run their test suites against your working tree (`uv pip install -e <dependent> && uv pip install -e <this repo>` in a scratch venv), before and after your change, and compare pass counts. Known pre-existing failures: `xdol` has 2 doctest-format failures and `oa` has 3 tests that need a real OpenAI key.
3. Prefer additive, keyword-only parameters. For example, `mask_input` accepts a bool or a `prompt -> bool` predicate, and explicit booleans keep their old meaning, including `True` reading the terminal when stdin is piped.

Read these open issues before touching the matching area: #25 (the broad `(Exception,)` fallback), #26 (import-time folder creation), #27 (typo'd paths give silent empty configs), #28 (`os.path.sep` path sniffing), #29 (the pickle decoder), #30 (the masking toggle drops `egress`), #33 (file modes of the configs store), #12 and #17 (folder layout and platformdirs).

## Release flow

- Never edit `version`. CI's publish job on master bumps it, builds, uploads to PyPI, then commits the bump back and tags it.
- Packaging is `pyproject.toml` with hatchling (`>=1.27`, for the PEP 639 SPDX `license`). The vestigial `setup.cfg` and the move to the reusable wads CI stub are in #22.
- Commit messages and PR text must not contain CI marker strings (the skip-CI and publish markers), because squash merges can carry them into master.
