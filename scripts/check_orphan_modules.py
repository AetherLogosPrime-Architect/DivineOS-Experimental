"""Detect orphan modules — code that exists, has tests, is re-exported,
but has no production callers.

Audit finding 2026-05-03 round 2: 10+ modules in ``src/divineos/`` had
no production callers but were tested and importable. Each successive
maintenance commit (broad-except tightening, type-check pass, etc.)
paid the tax for code that did nothing. The audit suggested:

    For each src/divineos/**/*.py (excluding __init__.py):
      1. Find imports from {module} or from {parent}.{name} in src/
      2. Find imports in .claude/hooks/*.sh
      3. If both empty AND tests/ has importers → flag as orphan

This script implements that detector, plus respects the project's
``# AGENT_RUNTIME`` marker convention. A module marked AGENT_RUNTIME
is INTENTIONALLY unwired into the CLI/import graph but invoked from
a separate runtime context (e.g., Claude Code hooks). Marked modules
are excluded from the orphan list.

Output format mirrors ``check_doc_counts.py``: prints findings to
stdout, exits 0 on clean tree, non-zero if orphans found (so it can
be wired into pre-commit / CI when ready).

Note: this script is NOT yet wired into the gate. It's a tool for
running periodically to catch accumulation. Wiring it as a hard
gate would block any PR that introduces a new module before its
caller lands, which is too strict.

Known limitations:

* Modules reached only through ``from <package> import <symbol>``
  re-export shapes are flagged as orphans because the dotted path
  doesn't appear in any source file. The 39 council expert modules
  are an example: each is imported by ``council/experts/__init__.py``
  as ``from divineos.core.council.experts.feynman import
  create_feynman_wisdom``, then re-exported, then used elsewhere as
  ``from divineos.core.council.experts import create_feynman_wisdom``.
  The static check sees the second pattern but doesn't follow the
  re-export back to ``feynman.py``.
* CLI commands registered dynamically via ``register(cli)`` (the
  pattern in ``cli/__init__.py``) won't show up as imports from
  the command module's full dotted path.

Treat the output as a triage starting point, not ground truth.
For each finding, manually verify whether it's a real orphan
(audit round 2's list of 10 modules is the canonical confirmed
set) or one of the above false-positive shapes.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "divineos"
TESTS = ROOT / "tests"
HOOKS = ROOT / ".claude" / "hooks"


def _collect_module_paths() -> list[Path]:
    """Return every non-init Python module under src/divineos/ as a path."""
    out: list[Path] = []
    for p in SRC.rglob("*.py"):
        if p.name == "__init__.py":
            continue
        if "__pycache__" in p.parts:
            continue
        out.append(p)
    return out


def _module_dotted_name(path: Path) -> str:
    """Convert ``src/divineos/core/foo/bar.py`` to ``divineos.core.foo.bar``."""
    rel = path.relative_to(SRC.parent)
    parts = list(rel.with_suffix("").parts)
    return ".".join(parts)


def _is_agent_runtime(path: Path) -> bool:
    """Modules marked AGENT_RUNTIME are intentionally unwired into the
    CLI/import graph but invoked from a separate runtime context."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    # Match "AGENT_RUNTIME" near the top of the file (in a docstring/comment)
    return bool(re.search(r"AGENT_RUNTIME", text[:2000]))


def _has_caller_in(needle_module: str, search_root: Path, exclude: Path | None = None) -> bool:
    """Return True if any file under ``search_root`` imports ``needle_module``.

    Matches both ``from <needle_module> import ...`` and
    ``import <needle_module>`` patterns. Excludes the module's own
    ``__init__.py`` (since a package re-export isn't a caller) and
    the file at ``exclude`` (the module itself).
    """
    # Pattern: bare module-name reference or sub-module reference
    pat = re.compile(
        rf"\b(?:from\s+{re.escape(needle_module)}\b|import\s+{re.escape(needle_module)}\b)"
    )
    for p in search_root.rglob("*.py"):
        if exclude and p.resolve() == exclude.resolve():
            continue
        if "__pycache__" in p.parts:
            continue
        # Skip the module's package __init__.py — re-exports aren't real callers
        if p.name == "__init__.py":
            parent = p.parent
            # If this __init__.py is the parent of the module we're checking,
            # treat its imports as re-exports, not callers.
            try:
                parent_dotted = _module_dotted_name(parent / "_dummy.py").rsplit(".", 1)[0]
                if needle_module.startswith(parent_dotted + "."):
                    continue
            except ValueError:
                # Path isn't under SRC (e.g., a test conftest); fall through.
                pass
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if pat.search(text):
            return True
    return False


def _has_caller_in_shell(needle: str) -> bool:
    """Return True if any .sh hook references ``divineos.<needle>``
    (e.g., via ``python -m divineos.<needle>``)."""
    if not HOOKS.exists():
        return False
    pat = re.compile(rf"\bdivineos\.{re.escape(needle)}\b")
    for p in HOOKS.rglob("*.sh"):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if pat.search(text):
            return True
    return False


def find_orphans() -> list[tuple[Path, str]]:
    """Return a list of (path, reason) for every orphan module.

    A module is an orphan if:
      1. It has NO production caller (nothing in src/divineos/ imports
         it, except its own __init__.py re-export)
      2. It has NO hook caller (nothing in .claude/hooks/ runs it)
      3. It DOES have a test importer (otherwise it's just unused code,
         not an orphan — covered by vulture/dead-code scan)
      4. It is NOT marked ``AGENT_RUNTIME``
    """
    orphans: list[tuple[Path, str]] = []
    for path in _collect_module_paths():
        if _is_agent_runtime(path):
            continue
        dotted = _module_dotted_name(path)

        # Check production callers in src/
        if _has_caller_in(dotted, SRC, exclude=path):
            continue
        # Check hook callers
        if _has_caller_in_shell(dotted.removeprefix("divineos.")):
            continue
        # Confirm there IS a test importer (otherwise it's not an
        # "orphan-with-tests" but plain dead code).
        if not _has_caller_in(dotted, TESTS):
            continue

        orphans.append((path, "no production callers, has tests"))

    return orphans


def main() -> int:
    orphans = find_orphans()
    if not orphans:
        print("Orphan check OK (no modules found that have tests but no production callers)")
        return 0

    print(f"Found {len(orphans)} orphan module(s):")
    for path, reason in orphans:
        rel = path.relative_to(ROOT)
        print(f"  {rel}: {reason}")
    print()
    print("For each: decide one of —")
    print("  (a) Wire it into a production code path")
    print("  (b) Add `# AGENT_RUNTIME` marker if invoked from outside the CLI graph")
    print("  (c) Delete the module + its tests (audit Tier 2 dead-chain pattern)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
