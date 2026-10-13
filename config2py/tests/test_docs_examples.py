"""Run the Python examples in ``README.md`` and the bundled skills, so they can't rot.

Each document's ```` ```python ```` blocks run top to bottom in one namespace (like a
notebook), in a subprocess whose HOME, XDG and CONFIG2PY_* folders all point into a
temporary directory: importing config2py creates its default configs folder, so the
examples must never touch the real user's home. stdin is closed, so a block that would
prompt the user fails loudly instead of hanging.

``>>>`` examples in the document are also run, as a doctest (with the same flags
as CI).

A block that can't run unattended (it prompts, or needs a placeholder filled in) is
excluded by putting ``<!-- no-test -->`` on the line right before its fence.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

PKG_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PKG_ROOT.parent

DOCUMENTS = {
    "README.md": REPO_ROOT / "README.md",
    "config2py-quickstart": PKG_ROOT
    / "data"
    / "skills"
    / "config2py-quickstart"
    / "SKILL.md",
}

SKIP_MARKER = "<!-- no-test -->"
_FENCE_OPEN = re.compile(r"^```python\s*$")
_FENCE_CLOSE = re.compile(r"^```\s*$")

_RUNNER = """
import sys, traceback
blocks = {blocks!r}
namespace = {{"__name__": "__main__"}}
for line, code in blocks:
    try:
        exec(compile(code, f"<{doc} block at line {{line}}>", "exec"), namespace)
    except BaseException:
        traceback.print_exc()
        print(f"FAILED: {doc} block starting at line {{line}}", file=sys.stderr)
        sys.exit(1)
print(f"ran {{len(blocks)}} blocks")
if {has_doctests!r}:
    import doctest
    flags = doctest.ELLIPSIS | doctest.IGNORE_EXCEPTION_DETAIL
    failed, attempted = doctest.testfile(
        {path!r}, module_relative=False, optionflags=flags, encoding="utf-8"
    )
    print(f"doctests: {{attempted - failed}}/{{attempted}} passed")
    sys.exit(1 if failed else 0)
"""


def python_blocks(text: str) -> list[tuple[int, str]]:
    """Return ``(line_number, code)`` for each runnable ```python block of ``text``.

    >>> doc = "x\\n```python\\na = 1\\n```\\n<!-- no-test -->\\n```python\\ninput()\\n```\\n"
    >>> python_blocks(doc)
    [(3, 'a = 1')]
    """
    lines = text.splitlines()
    blocks, i = [], 0
    while i < len(lines):
        if _FENCE_OPEN.match(lines[i]):
            skip = i > 0 and lines[i - 1].strip() == SKIP_MARKER
            start = i + 1
            j = start
            while j < len(lines) and not _FENCE_CLOSE.match(lines[j]):
                j += 1
            if not skip:
                blocks.append((start + 1, "\n".join(lines[start:j])))
            i = j + 1
        else:
            i += 1
    return blocks


def _sandboxed_env(root: Path) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("CONFIG2PY_")}
    home = root / "home"
    home.mkdir()
    env.update(
        HOME=str(home),
        USERPROFILE=str(home),
        XDG_CONFIG_HOME=str(home / ".config"),
        XDG_DATA_HOME=str(home / ".local" / "share"),
        XDG_CACHE_HOME=str(home / ".cache"),
        XDG_STATE_HOME=str(home / ".local" / "state"),
        APPDATA=str(home / "AppData" / "Roaming"),
        LOCALAPPDATA=str(home / "AppData" / "Local"),
    )
    return env


@pytest.mark.parametrize("doc", sorted(DOCUMENTS))
def test_document_examples_run(doc, tmp_path):
    path = DOCUMENTS[doc]
    if not path.exists():
        pytest.skip(f"{path} not present (not running from a source checkout)")
    text = path.read_text(encoding="utf-8")
    blocks = python_blocks(text)
    assert blocks, f"no runnable python blocks found in {path}"
    workdir = tmp_path / "cwd"
    workdir.mkdir()
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            _RUNNER.format(
                blocks=blocks, doc=doc, path=str(path), has_doctests=">>> " in text
            ),
        ],
        cwd=workdir,
        env=_sandboxed_env(tmp_path),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
