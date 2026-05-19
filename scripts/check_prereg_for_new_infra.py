#!/usr/bin/env python3
"""Block commits that add NEW infra modules without a Pre-Reg reference.

Andrew 2026-05-18: when an agent ships new core infrastructure without
having pre-registered the design, the work bypasses the falsifier-first
discipline. Substrate fix: a commit-msg gate that requires either a
`prereg-XXX` reference in the message OR an explicit opt-in env var
(DIVINEOS_NEW_INFRA_NO_PREREG=1) when adding new files under
``src/divineos/core/``.

Existing-file modifications are NOT gated — the discipline targets the
moment a new capability lands, where pre-reg has the most leverage.

Usage (from commit-msg hook): pass commit-message file path as $1.

Exit codes:
  0  - no new infra files, or pre-reg referenced, or bypass set
  1  - new infra file(s) added without pre-reg reference
  2  - infrastructure error (script can't run; fail-open is caller's job)
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

# Module-level guardrail marker — Andrew 2026-05-18.
__guardrail_required__ = True

_PROTECTED_PATHS = (
    "src/divineos/core/",
)

_PREREG_PAT = re.compile(r"prereg-[0-9a-f]{12}", re.IGNORECASE)


def _staged_new_files() -> list[str]:
    """Return list of paths newly added (status 'A') in this commit."""
    try:
        r = subprocess.run(
            ["git", "diff", "--cached", "--name-status"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if r.returncode != 0:
        return []
    new_files: list[str] = []
    for line in r.stdout.splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2 and parts[0].strip() == "A":
            new_files.append(parts[1].replace("\\", "/"))
    return new_files


def _is_protected(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in _PROTECTED_PATHS) and path.endswith(".py")


def main(argv: list[str]) -> int:
    if os.environ.get("DIVINEOS_NEW_INFRA_NO_PREREG", "0") == "1":
        return 0  # Named bypass.

    if len(argv) < 2:
        return 2  # No commit-message file path provided.

    msg_path = Path(argv[1])
    if not msg_path.exists():
        return 2

    try:
        msg = msg_path.read_text(encoding="utf-8")
    except OSError:
        return 2

    new_files = _staged_new_files()
    protected_new = [p for p in new_files if _is_protected(p)]
    if not protected_new:
        return 0

    if _PREREG_PAT.search(msg):
        return 0

    print(
        "[prereg-required-before-infra] BLOCKED — new infra file(s) added "
        "without a prereg-XXX reference in the commit message:",
        file=sys.stderr,
    )
    for p in protected_new:
        print(f"  - {p}", file=sys.stderr)
    print("", file=sys.stderr)
    print(
        "New modules under src/divineos/core/ should be pre-registered as "
        "designs with named falsifiers BEFORE the code lands. This gate "
        "fires the falsifier-first discipline at commit time.",
        file=sys.stderr,
    )
    print("", file=sys.stderr)
    print(
        "Fix: include the relevant prereg ID in the commit message body, "
        "e.g. 'per prereg-abc123def456'. File a pre-reg first with: "
        "divineos prereg file <claim-statement>",
        file=sys.stderr,
    )
    print(
        "Or, for legitimate non-pre-reg-able cases, set "
        "DIVINEOS_NEW_INFRA_NO_PREREG=1 and explain in the commit body.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
