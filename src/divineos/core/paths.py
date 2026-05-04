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
"""

from __future__ import annotations

import os
from pathlib import Path


def divineos_home() -> Path:
    """Return the base ``~/.divineos`` directory (or override).

    Honors the ``DIVINEOS_HOME`` environment variable if set —
    used by the test conftest to give each test a private state
    directory. Otherwise falls back to ``~/.divineos``.

    Does NOT create the directory; callers are responsible for
    ensuring it exists before writing.
    """
    override = os.environ.get("DIVINEOS_HOME")
    if override:
        return Path(override)
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
