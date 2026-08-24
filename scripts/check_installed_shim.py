#!/usr/bin/env python3
"""Measure drift between the shim files in the repo and the ones on PATH.

WHY THIS EXISTS. ``divineos.cmd`` and ``divineos_wrapper.py`` are installed by
hand-copying them into a PATH directory. That makes two copies of one file with
nothing joining them, and it cost us the same bug twice:

* 2026-07-26 — the ``%ERRORLEVEL%``-inside-parentheses bug was found and fixed
  in ``scripts/divineos.cmd``.
* 2026-08-06 — Aether found the identical bug again, in the installed copy on
  PATH, which the repo fix had never reached. His fix to the running file did
  not reach the repo either.

Six weeks, one bug, two copies, neither fix propagating. The repo file is not
the file that runs. Nothing said so.

THREE STATES, NOT TWO. A drift check that cannot find the installed copy must
say ``could not look``. Reporting that as ``no drift`` is how a check that
never ran becomes indistinguishable from a check that passed — the defect class
this substrate has found more often than any other.

Exits 0 always. This is a measurement, not a gate: it is wired into the push
readiness report as information, and blocking a push because a file on someone
else's PATH is stale would be the wrong shape of enforcement.
"""

from __future__ import annotations

import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path

SHIMS = ("divineos.cmd", "divineos_wrapper.py")


@dataclass
class ShimStatus:
    """``drifted`` is only meaningful when ``installed`` was actually found."""

    name: str
    repo: Path
    installed: Path | None = None
    drifted: bool = False
    unlooked: str = ""  # non-empty means: could not look. Not the same as clean.


def _digest(path: Path) -> str:
    """Hash with line endings normalised — CRLF/LF churn is not real drift."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _path_dirs() -> list[Path]:
    return [Path(p) for p in os.environ.get("PATH", "").split(os.pathsep) if p.strip()]


def check(repo_root: Path, search_dirs: list[Path] | None = None) -> list[ShimStatus]:
    """Compare each shim against the first copy of it found on PATH."""
    dirs = search_dirs if search_dirs is not None else _path_dirs()
    results: list[ShimStatus] = []

    for name in SHIMS:
        repo_file = repo_root / "scripts" / name
        st = ShimStatus(name=name, repo=repo_file)

        if not repo_file.is_file():
            st.unlooked = f"repo copy missing at {repo_file}"
            results.append(st)
            continue

        found = next((d / name for d in dirs if (d / name).is_file()), None)
        if found is None:
            # Genuinely not installed is a real, clean answer — but it is NOT
            # "no drift", it is "nothing to drift from". Say which.
            st.unlooked = "not installed on PATH (nothing to compare)"
            results.append(st)
            continue

        st.installed = found
        try:
            st.drifted = _digest(found) != _digest(repo_file)
        except OSError as exc:
            st.unlooked = f"could not read {found}: {exc}"
        results.append(st)

    return results


def render(results: list[ShimStatus]) -> str:
    lines = ["# Installed-shim drift"]
    for st in results:
        if st.unlooked:
            lines.append(f"  ?  {st.name}: COULD NOT CHECK - {st.unlooked}")
        elif st.drifted:
            lines.append(f"  !  {st.name}: DRIFTED - installed copy at {st.installed}")
            lines.append(f"       differs from {st.repo}")
            lines.append("       A fix in one has not reached the other. Diff them.")
        else:
            lines.append(f"  ok {st.name}: installed copy matches repo")
    return "\n".join(lines)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    print(render(check(root)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
