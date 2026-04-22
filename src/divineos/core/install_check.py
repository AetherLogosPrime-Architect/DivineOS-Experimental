"""Install-location divergence check.

Autonomy-first diagnostic: warns at every CLI invocation when the
installed `divineos` package points at a source tree different from the
current working directory's git repo. Without this check the symptom is
baffling — "ModuleNotFoundError on a module I just created" or "the
code I just edited isn't running" — and the root cause is a
silent-editable-install pointing at a sibling worktree.

When it fires:
  - The user is inside a git working tree.
  - `divineos.__file__` resolves to a path outside that git tree.

That condition is the exact shape of "this worktree is not the one
that `pip install -e .` registered." Fix is always: `pip install -e .`
from the current worktree. The warning names that fix directly so the
agent doesn't have to diagnose the issue from first principles.

Suppression: set `DIVINEOS_SUPPRESS_INSTALL_WARNING=1` in the environment
for intentional cross-repo invocations (e.g. CI pipelines running one
worktree's CLI against another's state).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _git_toplevel(cwd: Path) -> Path | None:
    """Return the git repo root for cwd, or None if not inside a git tree."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if out.returncode != 0:
        return None
    top = out.stdout.strip()
    return Path(top).resolve() if top else None


def _installed_package_root() -> Path | None:
    """Return the parent of `divineos.__file__`, or None if unresolvable."""
    try:
        import divineos

        pkg_file = getattr(divineos, "__file__", None)
        if not pkg_file:
            return None
        return Path(pkg_file).resolve().parent
    except (ImportError, OSError, ValueError):
        return None


# Per-process cache. cwd and installed-package location don't change
# mid-process, so the divergence verdict is stable for the life of a
# single CLI invocation. Without caching, every divineos command paid
# two `git rev-parse` subprocess calls (~50-100ms on Windows). Sentinel
# object distinguishes "not computed" from "computed, result was None".
_CACHE_SENTINEL = object()
_cached_result: object = _CACHE_SENTINEL


def _reset_cache_for_tests() -> None:
    """Test-only helper to reset the per-process cache between cases."""
    global _cached_result
    _cached_result = _CACHE_SENTINEL


def check_install_divergence() -> str | None:
    """Return a one-line warning if install location diverges from cwd repo.

    Returns None when:
      - Suppression env var is set.
      - Not inside a git working tree.
      - Package location cannot be resolved.
      - Installed package is a descendant of the current git repo.

    The fast-path (suppression env var) is checked first so this function
    imposes near-zero overhead in CI / bulk-command contexts. Results are
    cached per-process after the first call (cwd and install location are
    stable within a process).
    """
    global _cached_result
    if _cached_result is not _CACHE_SENTINEL:
        return _cached_result  # type: ignore[return-value]

    if os.environ.get("DIVINEOS_SUPPRESS_INSTALL_WARNING"):
        _cached_result = None
        return None

    try:
        cwd = Path.cwd().resolve()
    except (OSError, RuntimeError):
        _cached_result = None
        return None

    toplevel = _git_toplevel(cwd)
    if toplevel is None:
        _cached_result = None
        return None  # not a git tree, no expectation to check

    pkg_root = _installed_package_root()
    if pkg_root is None:
        _cached_result = None
        return None

    # Compare the git toplevel of the installed package against the cwd's
    # git toplevel. Worktrees each have their own --show-toplevel (they
    # are not descendants of each other's toplevel in Git's sense), so
    # this check correctly distinguishes "cwd and install are the same
    # worktree" from "cwd is in worktree A, install points at worktree B".
    pkg_toplevel = _git_toplevel(pkg_root)
    if pkg_toplevel is None:
        _cached_result = None
        return None  # pkg not in any git tree — e.g. pip wheel install
    if pkg_toplevel == toplevel:
        _cached_result = None
        return None  # same worktree: fine

    msg = (
        f"[install warning] divineos installed from {pkg_toplevel} "
        f"but cwd is {toplevel}. "
        f"New files here will not be seen by the CLI until you run: "
        f"pip install -e ."
    )
    _cached_result = msg
    return msg


def emit_install_warning() -> None:
    """Print the divergence warning to stderr, if any. One-line, loud."""
    msg = check_install_divergence()
    if msg is None:
        return
    print(msg, file=sys.stderr)
