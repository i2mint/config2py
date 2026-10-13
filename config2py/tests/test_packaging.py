"""Packaging checks: the consumer skill must ship in the sdist (and so in the wheel).

``.claude/skills/<name>`` are relative symlinks to the real skill folders. hatchling
walks the project with ``followlinks=True`` and skips folders it has already seen, so
unless ``.claude/skills`` is pruned (see ``[tool.hatch.build.targets.sdist]`` in
``pyproject.toml``) the real folders are silently dropped from the sdist.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CONSUMER_SKILL = "config2py/data/skills/config2py-quickstart/SKILL.md"
DEV_SKILL = "skills/config2py-dev/SKILL.md"


def _require_source_checkout():
    if not (REPO_ROOT / "pyproject.toml").exists():
        pytest.skip("not running from a source checkout")


def test_claude_skill_links_resolve_to_the_real_skills():
    _require_source_checkout()
    links = {
        "config2py-quickstart": CONSUMER_SKILL,
        "config2py-dev": DEV_SKILL,
    }
    for name, target in links.items():
        link = REPO_ROOT / ".claude" / "skills" / name
        if not link.is_symlink():
            pytest.skip("symlinks not materialized (e.g. Windows checkout)")
        assert (link / "SKILL.md").resolve() == (REPO_ROOT / target).resolve()


def test_sdist_includes_the_skills():
    _require_source_checkout()
    sdist = pytest.importorskip("hatchling.builders.sdist")
    builder = sdist.SdistBuilder(str(REPO_ROOT))
    included = {f.relative_path.replace("\\", "/") for f in builder.recurse_included_files()}
    assert CONSUMER_SKILL in included
    assert DEV_SKILL in included
