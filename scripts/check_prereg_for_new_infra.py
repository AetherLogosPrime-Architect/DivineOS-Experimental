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

_PROTECTED_PATHS = ("src/divineos/core/",)

_PREREG_PAT = re.compile(r"prereg-[0-9a-f]{12}", re.IGNORECASE)


def _merge_head() -> str | None:
    """The other parent's SHA when a merge is in progress, else None."""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", "MERGE_HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    sha = (r.stdout or "").strip()
    return sha or None


def _exists_in(rev: str, path: str) -> bool:
    """Whether path is tracked at the given revision."""
    try:
        r = subprocess.run(
            ["git", "cat-file", "-e", f"{rev}:{path}"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        # Fail toward flagging: an unverifiable file stays subject to the gate
        # rather than slipping through on a subprocess failure.
        return False
    return r.returncode == 0


def _staged_new_files() -> list[str]:
    """Paths newly added ('A') in this commit, excluding merge-inherited ones.

    MERGE FALSE-POSITIVE (Aria 2026-07-31, hit live on a real merge). During
    a merge, `git diff --cached` compares the merge RESULT against HEAD only,
    so every file the other side introduced reads as 'A' — newly added by this
    commit. The gate then demands a pre-registration for someone else's module
    that was already registered on its own commit. Merging origin/main asked
    for a re-registration of core/auto_goal.py, already carrying
    prereg-99f3fd587018 from PR #390.

    A file is genuinely new only when absent from BOTH parents. During a merge
    we therefore subtract anything already present at MERGE_HEAD. Outside a
    merge the behavior is unchanged — _merge_head() returns None and no
    filtering happens.

    Deliberately NOT a blanket merge exemption: a merge commit that introduces
    its OWN new infra file (conflict resolution that adds a module, say) still
    gets flagged, because that file exists at neither parent.
    """
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

    other = _merge_head()
    if other is None:
        return new_files
    return [p for p in new_files if not _exists_in(other, p)]


def _is_protected(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in _PROTECTED_PATHS) and path.endswith(".py")


def main(argv: list[str]) -> int:
    # Andrew 2026-05-19: emergency-bypass shape restored after the
    # overshoot of pure-removal. The legitimate case is malfunction
    # recovery / hotfix where pre-reg-first would be chicken-and-egg.
    # The bypass is DIVINEOS_NEW_INFRA_EMERGENCY=<reason>. Firing
    # executes the LOGGED, REPORTED, ADDRESSED, FIXED sequence:
    # bypass_telemetry record + auto-filed claim + auto-filed psf
    # obligation. Reason must be >= 20 chars or bypass refuses.
    emergency_reason = os.environ.get("DIVINEOS_NEW_INFRA_EMERGENCY", "").strip()
    if emergency_reason:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
            from divineos.core.emergency_bypass import record_emergency_use

            record_emergency_use(
                gate_name="pre-reg-required-before-infra",
                env_var="DIVINEOS_NEW_INFRA_EMERGENCY",
                reason=emergency_reason,
            )
            return 0
        except ValueError as exc:
            print(f"[prereg-required-before-infra] {exc}", file=sys.stderr)
            return 1
        except Exception:  # noqa: BLE001
            # If the bypass helper itself fails, fall through to block.
            pass

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
        "divineos prereg file <claim-statement>. No env-var bypass exists "
        "(Andrew 2026-05-19).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
