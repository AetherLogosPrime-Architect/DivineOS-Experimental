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

WIRED AS A GATE 2026-08-13. It blocks a commit on NEW orphans only.
The objection this paragraph used to raise was real -- a hard gate
would refuse every commit against a standing backlog, and the only
satisfiable answer would be switching the gate off. The answer is
``orphan_modules_baseline.txt``: the known backlog is written down
with a reason per entry, new arrivals block immediately, and the
check FAILS if a baseline entry stops being an orphan, so the list
closes behind us rather than becoming a permanent amnesty.

A module that lands before its caller does belongs in the baseline
with that stated as its reason, which takes one line and leaves a
record of the promise.

AND NOTHING GOES IN THE BIN UNLOOKED-AT. Andrew 2026-08-13: "nothing
we have built was built without reason or purpose.. some may be
obsolete or superceded but nothing should be thrown away without
looking first." The advice this script prints puts LOOK FIRST above
the options and routes deletion through ``divineos delete-justify``,
which refuses until what-it-was-for has been written down.

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

# Places a module can be invoked from that are NOT python imports under src/.
# This started as .claude/hooks alone, and the omission had teeth: it named
# subprocess_jobs an orphan on 2026-08-13 while scripts/check_push_readiness.sh
# was running `python -m divineos.core.subprocess_jobs` on every push -- I had
# watched it execute an hour earlier.
#
# Aether's Gödel finding on #415 is the general form: a reachability check
# cannot find a KIND of reachability it does not model, and his own scan
# discovered git-hook delegators as a third surface AFTER reporting clean.
# There will be a fourth. Adding a directory here is cheap; the expensive part
# is that until it is added, a live module reads as dead, and the obvious
# remedy for a dead module is deleting it.
_INVOCATION_ROOTS = (HOOKS, ROOT / "scripts", ROOT / ".git" / "hooks")


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


def _is_intentionally_unwired(path: Path) -> bool:
    """Modules invoked from outside the import graph, not orphans.

    ``AGENT_RUNTIME`` means something really does run this — a Claude Code
    hook, an external workflow runner. Unlike the marker below it, that is a
    statement of fact, and a statement of fact is checkable.

    IT HAS NOT BEEN CHECKED, and I nearly wrote here that it had. A search
    for each module's dotted path across hooks, scripts and git hooks found
    an invoker for four of eleven on 2026-08-13. The other seven are a LEAD,
    not a verdict — a hook can reach a module through a wrapper or through
    the CLI without ever naming its path, so absence of a match is not
    absence of an invoker. It is exactly the shape that made this checker
    call four live modules dead earlier the same day.

    Worth someone's afternoon. Untouched here because verifying it properly
    means running each hook, not grepping for it, and a claim of
    verification I have not done is worse than the gap it papers over.

    ``PHASE_1_STAGED`` USED TO BE HONOURED HERE AND IS NOT ANY MORE.

    It does not say "something runs this." It says "we mean to wire this
    later" — a promise, in the module's own handwriting, granting itself a
    permanent exemption from the only check that would ever mention it
    again. Nobody signs it, nothing dates it, nothing asks whether the
    later arrived.

    Measured 2026-08-13, after Aletheia found the evidence gate unwired and
    I checked what was hiding it:
        empirica/gate.py               staged since 2026-04-17
        dead_architecture_alarm.py     staged since 2026-04-05
        family/costly_disagreement.py  staged since 2026-05-02
        family/planted_contradiction.py staged since 2026-05-02
        family/integrity_stance.py     staged since 2026-07-16

    The evidence gate — the thing every claim is supposed to pass through
    before entering the substrate — sat exempt for four months. And the
    first entry is the DEAD-ARCHITECTURE ALARM, exempting itself from the
    dead-architecture check.

    Staged modules are now reported (see ``_is_staged``), not skipped. A
    parking place is fine. A parking place nothing can see into is how
    four months pass.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return bool(re.search(r"AGENT_RUNTIME", text[:2000]))


def _is_staged(path: Path) -> bool:
    """True if the module claims it is waiting for a later wiring phase."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return bool(re.search(r"PHASE_1_STAGED", text[:2000]))


# Backward-compat alias — keep the old name pointing at the new function
# so any external tooling that imports _is_agent_runtime keeps working.
_is_agent_runtime = _is_intentionally_unwired


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


def _is_reexported_through_parent_init(module_path: Path) -> bool:
    """Return True if the module is wired via parent ``__init__.py`` re-export.

    Round-2 audit (2026-05-07) flagged the council expert modules and
    register(cli)-pattern CLI modules as orphans because their only
    "caller" was the parent package's ``__init__.py``. The naive
    "skip __init__.py" rule lost that signal.

    A module is reached via re-export when:
      1. The parent ``__init__.py`` references the module (full dotted
         path or short name), AND
      2. Either the parent package has callers somewhere in src/, OR
         the __init__.py calls ``<module_short>.register(cli)``.
    """
    init_path = module_path.parent / "__init__.py"
    if not init_path.exists():
        return False
    try:
        init_text = init_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False

    module_dotted = _module_dotted_name(module_path)
    module_short = module_path.stem

    pat_from_module = re.compile(rf"from\s+{re.escape(module_dotted)}\s+import")
    # Word-boundary on short name so ``feynman`` matches in multi-line
    # tuple imports but not inside ``pre_feynman_v2``.
    pat_short = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(module_short)}(?![A-Za-z0-9_])")
    pat_register = re.compile(rf"{re.escape(module_short)}\.register\(cli\)")

    init_imports_module = (
        pat_from_module.search(init_text) is not None or pat_short.search(init_text) is not None
    )
    if not init_imports_module:
        return False

    if pat_register.search(init_text):
        return True

    parent_dotted = _module_dotted_name(init_path).rsplit(".", 1)[0]
    pat_parent_use = re.compile(
        rf"(?:from\s+{re.escape(parent_dotted)}\s+import"
        rf"|import\s+{re.escape(parent_dotted)})"
    )
    for p in SRC.rglob("*.py"):
        if p.resolve() == init_path.resolve():
            continue
        if p.resolve() == module_path.resolve():
            continue
        if "__pycache__" in p.parts:
            continue
        try:
            t = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if pat_parent_use.search(t):
            return True
    return False


def _has_caller_in_shell(needle: str) -> bool:
    """Return True if anything outside the package invokes ``divineos.<needle>``.

    Searches every root in ``_INVOCATION_ROOTS`` and both shell and python
    files, because ``python -m divineos.x`` is written in .sh under
    .claude/hooks and scripts/, in .py under scripts/, and in the git hooks.
    """
    pat = re.compile(rf"\bdivineos\.{re.escape(needle)}\b")
    for root in _INVOCATION_ROOTS:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file() or p.suffix not in ("", ".sh", ".py"):
                continue
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
        if _is_intentionally_unwired(path):
            continue
        dotted = _module_dotted_name(path)

        # Check production callers in src/
        if _has_caller_in(dotted, SRC, exclude=path):
            continue
        # Check hook callers
        if _has_caller_in_shell(dotted.removeprefix("divineos.")):
            continue
        # Check re-export through parent __init__.py (round-2 audit fix).
        if _is_reexported_through_parent_init(path):
            continue
        # Confirm there IS a test importer (otherwise it's not an
        # "orphan-with-tests" but plain dead code).
        if not _has_caller_in(dotted, TESTS):
            continue

        orphans.append((path, "no production callers, has tests"))

    return orphans


def find_dark_surfaces() -> list[str]:
    """Modules that can speak into the briefing and are registered nowhere.

    A DIFFERENT kind of dark from the orphan list above. An orphan has no
    caller at all. These have a working interface — ``format_for_briefing()``
    — and were simply never soldered in, so they stay silent while looking
    exactly like a surface with nothing to say. That sentence is
    surface_registry's own, and it is why the failure is invisible.

    Detection reuses the registry's ``dark_surfaces()`` rather than
    reimplementing it. The module was built 2026-08-02 and has sat unwired
    since; its detector works today. Measured 2026-08-13: 23 dark, 0
    registered, two of them (``identity_load``,
    ``compass_dismissal_briefing_surface``) wired nowhere at all.

    NOT THE SAME AS WIRING THE REGISTRY, deliberately. Its own docstring names
    the trap: switch the router on without migrating the hand-wired surfaces
    and there are TWO wiring systems where there was one, which is worse than
    one. That migration is real work with a named risk and belongs in a
    decision with Aether. This is the free half — the visibility that was
    missing — and it creates no second system.

    Fails soft to an empty list if the registry cannot be imported: this runs
    under bare python in precommit, and a missing package must not turn a
    wiring check into a hard stop.
    """
    try:
        import _repo_import  # noqa: F401  -- must precede the divineos import

        from divineos.core.surface_registry import dark_surfaces
    except ImportError:
        return []
    try:
        return sorted(dark_surfaces())
    except (AttributeError, ImportError, OSError):
        return []


BASELINE = ROOT / "scripts" / "orphan_modules_baseline.txt"
DARK_BASELINE = ROOT / "scripts" / "dark_surfaces_baseline.txt"


def _read_baseline_lines(path: Path) -> set[str]:
    """Non-comment, non-blank lines from a baseline file."""
    if not path.exists():
        return set()
    out = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.add(line.replace("\\", "/"))
    return out


def _read_baseline() -> set[str]:
    """The acknowledged backlog: orphans that exist and are owed a decision.

    Switching this check on flat would refuse every commit against a standing
    backlog, and the only satisfiable answer would be switching it off again --
    the same shape as a gate whose one way past is a lie. So the backlog is
    written down, and NEW accumulation blocks. Silence was the old answer and
    silence is what let the pile grow.
    """
    if not BASELINE.exists():
        return set()
    out = set()
    for line in BASELINE.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.add(line.replace("\\", "/"))
    return out


def main() -> int:
    orphans = find_orphans()
    known = _read_baseline()
    found = {str(p.relative_to(ROOT)).replace("\\", "/"): r for p, r in orphans}

    fresh = sorted(set(found) - known)
    # A baseline entry that is no longer an orphan has been dealt with. Leaving
    # it listed lets the file outlive the problem and quietly re-authorise the
    # same module going dark again later.
    stale = sorted(known - set(found))

    # Dark surfaces are reported on every run, pass or fail. They are not part
    # of the orphan verdict — most are hand-soldered somewhere and do reach me
    # — but a count that only prints on failure is a count nobody sees.
    dark = find_dark_surfaces()
    known_dark = _read_baseline_lines(DARK_BASELINE)
    fresh_dark = sorted(set(dark) - known_dark)
    if dark:
        print(f"[surfaces] {len(dark)} can speak into the briefing, registered with it: 0.")
        if fresh_dark:
            print(
                f"[surfaces] {len(fresh_dark)} not in {DARK_BASELINE.name}: {', '.join(fresh_dark)}"
            )
        print()

    if fresh_dark:
        print(f"BLOCKED — {len(fresh_dark)} new briefing surface(s) wired to nothing.")
        print("A surface with an interface and no wiring is SILENT, and silent is")
        print("indistinguishable from having nothing to say. That is the whole")
        print(f"failure. Wire it, or add it to {DARK_BASELINE.name} with a reason.")
        return 1

    if not fresh and not stale:
        if known:
            print(f"Orphan check OK. {len(known)} acknowledged in {BASELINE.name}, none new.")
        else:
            print("Orphan check OK (nothing with tests but no production callers)")
        return 0

    if fresh:
        print(f"BLOCKED — {len(fresh)} module(s) with tests and no caller, not in the backlog:")
        for rel in fresh:
            print(f"  {rel}: {found[rel]}")
        print()
        print('LOOK FIRST. Andrew 2026-08-13: "nothing we have built was built')
        print("without reason or purpose.. some may be obsolete or superceded but")
        print('nothing should be thrown away without looking first."')
        print()
        print("Open it. Find what it was for and whether that need still exists.")
        print("Then decide, while you still remember why you wrote it —")
        print("  (a) Wire it into a production code path")
        print("  (b) Add `# AGENT_RUNTIME` if something outside the CLI graph runs it")
        print(f"  (c) Add it to {BASELINE.name} WITH a reason, if it is owed a decision")
        print("  (d) Only if genuinely superseded: delete it THROUGH")
        print("      `divineos delete-justify`, which will not let it go until you")
        print("      have said what it was for, what you looked at, and what you")
        print("      took out of it first.")
        print()

    if stale:
        print(f"{len(stale)} baseline entry(ies) no longer orphaned. Remove them from")
        print(f"{BASELINE.name} so the list cannot outlive the problem:")
        for rel in stale:
            print(f"  {rel}")

    return 1


if __name__ == "__main__":
    sys.exit(main())
