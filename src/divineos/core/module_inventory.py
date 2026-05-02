"""Module-inventory surface — bridge from src/divineos/core/ to the briefing.

## Why this module exists

A pattern named in the council walk on 2026-04-24: I forgot
infrastructure I built. **Twice in one conversation.** First the
unmerged branches (closed by ``in_flight_branches.format_for_briefing``);
then ``core/knowledge/graph_retrieval.py`` — already in the codebase,
already documented in ``docs/ARCHITECTURE.md``, and I caught its
existence only because the precommit doc-drift check happened to
mention it. The OS knew. The OS just didn't surface it at session
start.

The council's meta-principle, surfaced via 5-lens convergence (Beer /
Hofstadter / Yudkowsky / Taleb / Dekker): *the pattern of forgetting
is data, not noise.* When the agent surprises itself with "oh right,
I already have that," the surface for that *kind of thing* is missing.

This module closes the specific case for ``src/divineos/core/``. It
lists the subpackages and the modules inside each one — names only,
no descriptions — so the agent reading the briefing sees
``knowledge/`` and reads ``graph_retrieval`` and recognizes its own
work without having to re-discover it.

## Why subpackages, not top-level

96 top-level ``.py`` files in ``core/`` is too many for a briefing
block. Subpackages (8 of them, totaling ~69 modules) are where
load-bearing infrastructure tends to cluster — the recall-failure
case (``graph_retrieval.py``) was in a subpackage. Top-level
modules get a count + pointer to ``docs/ARCHITECTURE.md`` for the
full tree. If subsequent failures show top-level recall is also a
hole, expand the surface then — discipline says scope narrow, ship,
observe.

## What this module does NOT do

* Does not summarize what each module *does*. Names are recognition
  prompts; the one-liner descriptions live in ``docs/ARCHITECTURE.md``
  where they're already maintained.
* Does not parse docstrings at briefing time. Static filesystem walk
  only — keeps the briefing fast and never crashes on a malformed
  source file.
* Does not interpret recency, importance, or status. Same descriptive-
  only discipline as ``in_flight_branches`` and ``presence_memory``.

## Pattern

Mirrors ``in_flight_branches.format_for_briefing`` and
``presence_memory.format_for_briefing``: a plain formatter that emits
a named block when there is something to surface, returns empty
string otherwise.
"""

from __future__ import annotations

from pathlib import Path

# Cap on module names listed per subpackage. The whole point is
# recognition; an unbounded wall of names defeats it. 25 covers the
# largest current subpackage (knowledge/ at 19) with headroom.
MAX_MODULES_PER_SUBPACKAGE = 25

# Names that don't represent meaningful modules. Filtered from the
# listing. ``__init__.py`` is the package marker, not a module the
# agent would recognize as work; private dunders are noise.
_SKIP_MODULE_NAMES = frozenset({"__init__", "__main__"})


def _find_core_root(start: Path | None = None) -> Path | None:
    """Locate the ``src/divineos/core/`` directory from a starting path.

    Walks up from ``start`` looking for a ``src/divineos/core/`` directory.
    Bounded by filesystem root. Returns None if not found — the
    briefing must never break because the surface module ran outside
    the repo.

    Falls back to resolving from this module's own ``__file__`` when
    ``start`` doesn't lead anywhere — this module *is* in ``core/``,
    so its install path is a reliable anchor when running outside any
    git checkout (e.g. installed as a package).
    """
    here = start if start is not None else Path.cwd()
    try:
        here = here.resolve()
    except OSError:
        return None

    for candidate in (here, *here.parents):
        target = candidate / "src" / "divineos" / "core"
        if target.is_dir():
            return target

    try:
        from divineos.core import module_inventory as _self  # noqa: PLC0415

        if _self.__file__:
            self_path = Path(_self.__file__).resolve()
            for candidate in self_path.parents:
                if candidate.name == "core" and candidate.parent.name == "divineos":
                    return candidate
    except (ImportError, AttributeError, OSError):
        pass

    return None


def _list_module_names(directory: Path) -> list[str]:
    """List ``.py`` module names directly in ``directory``, sorted alphabetically.

    Skips ``__init__.py``, ``__main__.py``, and anything not ending in
    ``.py``. Returns [] on any I/O error — best-effort.
    """
    try:
        entries = list(directory.iterdir())
    except OSError:
        return []
    names: list[str] = []
    for entry in entries:
        if not entry.is_file() or entry.suffix != ".py":
            continue
        stem = entry.stem
        if stem in _SKIP_MODULE_NAMES:
            continue
        names.append(stem)
    return sorted(names)


def _list_subpackages(core_root: Path) -> list[tuple[str, list[str]]]:
    """List ``(subpackage_name, [module_names])`` tuples, sorted.

    A subpackage is any direct subdirectory of ``core/`` that contains
    an ``__init__.py``. ``__pycache__`` and similar non-package dirs
    are skipped by the __init__.py check.
    """
    try:
        entries = list(core_root.iterdir())
    except OSError:
        return []
    subpackages: list[tuple[str, list[str]]] = []
    for entry in entries:
        if not entry.is_dir():
            continue
        if not (entry / "__init__.py").is_file():
            continue
        modules = _list_module_names(entry)
        subpackages.append((entry.name, modules))
    subpackages.sort(key=lambda item: item[0])
    return subpackages


def _count_top_level_modules(core_root: Path) -> int:
    """Count ``.py`` modules directly in ``core/`` (not in subpackages)."""
    return len(_list_module_names(core_root))


def format_for_briefing(start: Path | None = None) -> str:
    """Return a briefing-surface block listing core/ subpackages and modules.

    Returns empty string if ``src/divineos/core/`` cannot be located.
    The block is descriptive: subpackage names, the modules inside
    each, a count of top-level modules, and a pointer to
    ``docs/ARCHITECTURE.md`` for full descriptions.
    """
    core_root = _find_core_root(start=start)
    if core_root is None:
        return ""

    subpackages = _list_subpackages(core_root)
    top_level_count = _count_top_level_modules(core_root)

    if not subpackages and top_level_count == 0:
        return ""

    lines = [
        f"[module inventory] src/divineos/core/ — {top_level_count} top-level modules"
        f" + {len(subpackages)} subpackages:",
    ]
    for name, modules in subpackages:
        if not modules:
            lines.append(f"  - {name}/ — (empty)")
            continue
        if len(modules) > MAX_MODULES_PER_SUBPACKAGE:
            shown = modules[:MAX_MODULES_PER_SUBPACKAGE]
            extra = len(modules) - MAX_MODULES_PER_SUBPACKAGE
            joined = ", ".join(shown) + f", +{extra} more"
        else:
            joined = ", ".join(modules)
        lines.append(f"  - {name}/ ({len(modules)}) — {joined}")
    lines.append("  Recognition prompt only. Full descriptions: docs/ARCHITECTURE.md.")

    return "\n".join(lines) + "\n"


__all__ = ["format_for_briefing"]
