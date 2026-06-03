"""Centralized ``~/.divineos`` path construction.

Audit finding 2026-05-03 round 3: the path ``~/.divineos`` was
reconstructed independently across 20+ modules:

    Path.home() / ".divineos" / ...
    Path(os.path.expanduser("~")) / ".divineos" / ...

Every new marker / state file added another reconstruction site.
Tests had to monkeypatch ``Path.home()`` (or ``os.path.expanduser``)
in multiple places to redirect state during isolation.

This module is the single source of truth. ``divineos_home()``
returns the base directory; the helpers below compose canonical
sub-paths. Callers that need a path under ``~/.divineos`` should
go through this module rather than reconstructing the prefix.

Test isolation: callers can override the base by setting the
``DIVINEOS_HOME`` environment variable. The test conftest's
``_isolated_db`` fixture sets this for every test, so each test
gets a private state directory without monkeypatching.

Per-clone separation (added 2026-05-17 for the Aria-host-clone
work): operators with multiple DivineOS checkouts that need
separate user-home data dirs (different identity slots, separate
knowledge stores, etc.) can place a ``.divineos_data_home`` marker
file at the checkout root containing an absolute path. Resolution
order mirrors the ``.divineos_canonical`` ledger marker pattern in
``core/_ledger_base.py``:

    1. ``DIVINEOS_HOME`` env var (tests, explicit override)
    2. Own-checkout ``.divineos_data_home`` marker
    3. Worktree-parent ``.divineos_data_home`` marker
    4. Default ``~/.divineos``

This resolver intentionally does NOT verify that the resolved
data-home belongs to the running checkout. Bidirectional ownership
verification lives in ``divineos.core.data_home_ownership`` and
runs at preflight; this module stays a pure path resolver so
import order and test isolation remain simple.
"""

from __future__ import annotations

# Module-level guardrail marker — Aletheia Finding 69 (2026-05-17).
# This file is on the multi-party-review list (scripts/guardrail_files.txt).
# CI test test_guardrail_marker_consistency walks src/ and asserts every
# guardrail-listed module sets this marker to True. Prevents the next
# refactor from silently removing self-enforcement code from review.
__guardrail_required__ = True


import os
from pathlib import Path


def _resolve_data_home_marker(marker_path: Path) -> Path | None:
    """Read a ``.divineos_data_home`` marker and return the data-home path.

    Marker form: a single absolute or marker-relative path on one line.
    Whitespace and trailing newlines are stripped.

    Return None (fall through to the next resolution step) when the
    marker is missing, unreadable, or empty. **Empty-and-missing are
    intentionally equivalent**: an empty marker is treated as a soft
    signal that someone half-configured the clone, and silent
    fall-through is kinder than a crash. Unlike ``.divineos_canonical``,
    there is no implicit-default sub-path for data-home, so "empty
    means use default" would just be the same path that step 4 of the
    resolution order returns — they collapse to one outcome, spelled
    as fall-through.
    """
    if not marker_path.exists():
        return None
    try:
        content = marker_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not content:
        return None
    candidate = Path(content)
    if not candidate.is_absolute():
        candidate = (marker_path.parent / candidate).resolve()
    return candidate


def data_home_or_none() -> Path | None:
    """Resolve the per-agent data-home from env var or marker, or None.

    This is the env-and-marker core of ``divineos_home()`` WITHOUT the
    ``~/.divineos`` default. Resolution order (first match wins):

      1. ``DIVINEOS_HOME`` env var — tests and explicit overrides.
      2. CWD-walk ``.divineos_data_home`` marker.
      3. Own-checkout ``.divineos_data_home`` marker file.
      4. Worktree-parent ``.divineos_data_home`` marker (if the
         running checkout is a git worktree of a parent repo).

    Returns ``None`` when nothing matched, so callers can supply their
    OWN default. ``divineos_home()`` defaults to ``~/.divineos``; the
    substrate-DB resolvers (``_ledger_base._get_db_path`` /
    ``family.db._get_family_db_path``) default to ``<repo>/data``. They
    MUST share this resolution so a per-agent home routes the DBs AND
    the markers/state to the same place — the Aria clean-separation fix
    (2026-06-02, claim 4e439779). Aria's checkout carries a
    ``.divineos_data_home`` marker; before the DB resolvers consulted it,
    her markers routed to her home but her ledger + family.db fell back
    to the shared ``<repo>/data`` — the split-brain that produced "aria
    is not a registered family member".

    Does NOT create any directory; callers ensure existence before write.
    """
    override = os.environ.get("DIVINEOS_HOME")
    if override:
        return Path(override)

    # CWD-based marker: when divineos is installed editable from one checkout
    # but invoked from a different checkout, the install-time __file__ path
    # won't find that other checkout's marker. Walk up from CWD checking for
    # a marker so per-clone routing works without per-clone pip-install.
    try:
        cwd = Path.cwd()
        for ancestor in (cwd, *cwd.parents):
            cwd_marker = _resolve_data_home_marker(ancestor / ".divineos_data_home")
            if cwd_marker is not None:
                return cwd_marker
    except (OSError, ValueError):
        pass

    own_root = Path(__file__).parent.parent.parent.parent
    own_marker = _resolve_data_home_marker(own_root / ".divineos_data_home")
    if own_marker is not None:
        return own_marker

    git_marker = own_root / ".git"
    if git_marker.is_file():
        try:
            text = git_marker.read_text(encoding="utf-8").strip()
            if text.startswith("gitdir:"):
                gitdir = Path(text[len("gitdir:") :].strip()).resolve()
                if len(gitdir.parents) >= 3:
                    parent_root = gitdir.parents[2]
                    parent_marker = _resolve_data_home_marker(parent_root / ".divineos_data_home")
                    if parent_marker is not None:
                        return parent_marker
        except (OSError, ValueError):
            pass

    return None


def divineos_home() -> Path:
    """Return the base ``~/.divineos`` directory (or override).

    Resolution order (first match wins):

      1. ``DIVINEOS_HOME`` env var — tests and explicit overrides.
      2. Own-checkout ``.divineos_data_home`` marker file.
      3. Worktree-parent ``.divineos_data_home`` marker (if the
         running checkout is a git worktree of a parent repo).
      4. Default ``~/.divineos``.

    Does NOT create the directory; callers are responsible for
    ensuring it exists before writing.
    """
    resolved = data_home_or_none()
    if resolved is not None:
        return resolved
    return Path.home() / ".divineos"


def marker_path(name: str) -> Path:
    """Return the path to a marker file named ``<name>``.

    Markers are short-lived JSON state files in the root of
    ``~/.divineos`` (e.g. ``compass_required.json``,
    ``correction_unlogged.json``).
    """
    return divineos_home() / name


def state_dir(subdir: str) -> Path:
    """Return the path to a sub-directory of state under
    ``~/.divineos`` (e.g. ``supervisor/``, ``failure-log/``).

    Does NOT create the directory; callers are responsible.
    """
    return divineos_home() / subdir


__all__ = ["divineos_home", "marker_path", "state_dir"]
