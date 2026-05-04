"""Validate that .claude/skills/ files reference real CLI commands and
real Python modules.

External audit round 7 (2026-05-03) found 7 broken references across
4 skill files: ``divineos aria``, ``divineos opinions``,
``divineos council``, ``divineos knowledge`` (none of which exist),
plus three skills with broken Python heredoc imports
(``from family.entity`` instead of ``from divineos.core.family.entity``).

The skills are user-invokable workflows shipped via ``.claude/skills/``.
A broken reference means a user invoking ``/file-opinion`` or ``/summon``
hits ``Error: No such command 'X'`` mid-flow. These tests parse each
SKILL.md, extract divineos command references and Python import
statements, and assert each one resolves against the live CLI surface
and importable module space.

Audit's own suggestion: a 50-line test would have caught all 7 issues
at once and prevent future drift. This is that test.
"""

from __future__ import annotations

import importlib
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"


def _real_top_level_commands() -> set[str]:
    """Return the set of top-level commands ``divineos --help`` lists."""
    out = subprocess.run(["divineos", "--help"], capture_output=True, text=True, check=False)
    # Click prints commands as "  <name>  <description>" in the Commands
    # block. Match lines starting with two spaces + a lowercase word.
    return set(re.findall(r"^  ([a-z][a-z0-9_-]+)\b", out.stdout, re.MULTILINE))


def _skill_files() -> list[Path]:
    if not SKILLS_DIR.exists():
        return []
    return sorted(SKILLS_DIR.rglob("SKILL.md"))


def test_skills_directory_exists():
    """Sanity check: the skills directory exists. If this fails, the test
    suite needs to be re-pointed at the right location."""
    assert SKILLS_DIR.exists(), f"Expected skills at {SKILLS_DIR}"
    assert _skill_files(), "No SKILL.md files found"


def test_every_divineos_command_referenced_in_skills_exists():
    """Every ``divineos <cmd>`` reference in a skill file must resolve
    against the live CLI surface. Catches stale references from CLI
    renames (``emit SESSION_END`` -> ``extract``, ``council`` ->
    ``mansion council``, etc.)."""
    real = _real_top_level_commands()
    # Allowed even if not in --help output (e.g. external docs convention).
    # ``extract`` is the renamed SESSION_END pipeline.
    real |= {"extract"}

    broken: list[tuple[str, str]] = []
    for skill_md in _skill_files():
        text = skill_md.read_text(encoding="utf-8")
        # Match `divineos <cmd>` where <cmd> is the next word.
        # Skip lines inside `allowed-tools:` since those are glob patterns
        # like `divineos opinion:*` — extract the command name only.
        for cmd in re.findall(r"divineos\s+([a-z][a-z0-9_-]+)", text):
            if cmd not in real:
                broken.append((skill_md.name, cmd))

    if broken:
        # Group by skill for readable output
        by_skill: dict[str, set[str]] = {}
        for name, cmd in broken:
            by_skill.setdefault(name, set()).add(cmd)
        msg_lines = ["Skill files reference CLI commands that don't exist:"]
        for skill_name, cmds in sorted(by_skill.items()):
            msg_lines.append(f"  {skill_name}: {sorted(cmds)}")
        pytest.fail("\n".join(msg_lines))


def test_every_python_import_in_skill_heredocs_resolves():
    """Every ``from <module> import ...`` line in a SKILL.md must resolve
    against the importable module space.

    Catches stale module paths from refactors (``from family.entity``
    rather than ``from divineos.core.family.entity``).

    Skips imports of standard-library modules and known stub names that
    appear in pseudocode examples (``"my_module"``, ``"some_module"``).
    """
    skip_prefixes = (
        "sys",
        "os",
        "json",
        "hashlib",
        "subprocess",
        "pathlib",
        "datetime",
        "typing",
        "collections",
        "functools",
        "itertools",
        "re",
        "time",
        "uuid",
        "pytest",
        "abc",
        "dataclasses",
        "enum",
    )
    skip_exact = {"my_module", "some_module", "your_module"}

    broken: list[tuple[str, str, str]] = []
    for skill_md in _skill_files():
        text = skill_md.read_text(encoding="utf-8")
        for match in re.finditer(r"^\s*from\s+([\w.]+)\s+import", text, re.MULTILINE):
            module = match.group(1)
            top = module.split(".")[0]
            if top in skip_prefixes or module in skip_exact:
                continue
            try:
                importlib.import_module(module)
            except ImportError as e:
                broken.append((skill_md.name, module, str(e)))

    if broken:
        msg_lines = ["Skill files reference Python modules that can't be imported:"]
        for skill_name, mod, err in broken:
            msg_lines.append(f"  {skill_name}: {mod!r}  ({err})")
        pytest.fail("\n".join(msg_lines))
