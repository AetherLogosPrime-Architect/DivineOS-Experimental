"""Offline correction-marker clear — escape hatch for the locked-box trap.

When the ``divineos`` CLI itself is broken (mid-rebase ``cli/__init__.py``
SyntaxError, half-installed package, missing dependency), the
correction-not-logged gate's named remedy (``divineos learn`` /
``divineos correction``) is unreachable. The result is a deadlock: the
gate blocks Edit/Write/Bash on substrate files until the marker clears;
the marker can only clear via a CLI that won't import.

The Andrew 2026-06-08 "gate-trap structural fix" correction (#2 in the
open queue at filing time) named the principle: gate-remedies-must-execute.
If the remedy a gate names is itself blocked by the failure the gate is
trying to catch, the gate is a cage, not a keel.

This script is the fix. It depends only on ``divineos.core.correction_marker``,
which doesn't import ``divineos.cli`` — so a broken CLI ``__init__.py`` does
not prevent the remedy from running. Accountability is preserved: the
caller must supply a ``--reason`` (>= 30 chars) explaining what was
escaped from and why, and the reason is appended to a JSON log under
``~/.divineos/cli_broken_escapes.jsonl`` so the bypass is auditable.

This is the keel-version of bypass: I built it for me, it requires me to
name what I'm doing, it leaves a trace. Not a free-pass.

## Usage

    python scripts/clear_correction_marker.py \\
        --reason "mid-rebase cli/__init__.py SyntaxError blocking CLI; clearing to fix the broken file then re-log the correction"

The script will refuse to run without a reason or with a reason shorter
than 30 characters (the threshold matches the engagement gate's "named
reason" discipline — short reasons are stub-reasons).

## What it does NOT do

It does NOT log the original correction. The marker exists because the
operator's prior message contained correction-shaped language and the
gate wants me to record that as a learning. Clearing the marker without
logging the correction loses the data. After running this script and
fixing the CLI, the agent SHOULD run ``divineos correction "..."`` to
log the original correction. This script writes a reminder to that
effect into the escape log.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Direct import path: this module does NOT depend on divineos.cli.
# That is the whole point — when cli/__init__.py is broken, this still
# imports because correction_marker imports only atomic_io and paths.
from divineos.core.correction_marker import clear_marker, marker_path, read_marker
from divineos.core.paths import divineos_home

_MIN_REASON_LEN = 30
_ESCAPE_LOG = "cli_broken_escapes.jsonl"


def _append_escape_log(reason: str, original_trigger: str | None) -> Path:
    """Append a JSON line recording the escape — what was cleared and why.

    The log lives under the divineos home directory (same place the marker
    lives) so the audit trail follows the user across worktrees.
    """
    log_path = divineos_home() / _ESCAPE_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.time(),
        "reason": reason,
        "original_trigger": original_trigger,
        "remediation_owed": (
            'Log the original correction via `divineos correction "..."` '
            "once the CLI is working again."
        ),
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return log_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Offline clear the correction-unlogged marker when the divineos "
            "CLI itself is broken (escape hatch for the locked-box trap)."
        )
    )
    parser.add_argument(
        "--reason",
        required=True,
        help=(
            "Why is the CLI unreachable, and what is the plan to log the "
            f"original correction afterward? Must be >= {_MIN_REASON_LEN} chars."
        ),
    )
    args = parser.parse_args(argv)

    reason = args.reason.strip()
    if len(reason) < _MIN_REASON_LEN:
        print(
            f"REFUSED: --reason must be >= {_MIN_REASON_LEN} characters "
            f"(got {len(reason)}). A short reason is a stub-reason; the "
            "escape hatch is for real CLI-broken situations, not for "
            "routinely bypassing the discipline.",
            file=sys.stderr,
        )
        return 2

    path = marker_path()
    if not path.exists():
        print(
            "No correction marker present at "
            f"{path}. Nothing to clear. (If you expected a marker, the gate "
            "may have already cleared it, or your divineos_home() resolves "
            "to a different location than the gate's.)"
        )
        return 0

    marker = read_marker()
    original_trigger = marker.get("trigger") if isinstance(marker, dict) else None
    clear_marker()
    log_path = _append_escape_log(reason, original_trigger)
    print(
        f"Cleared correction marker at {path}.\n"
        f"Escape recorded to {log_path}.\n"
        "REMEDIATION OWED: once the CLI is working, run "
        '`divineos correction "..."` to log the original correction. '
        "The marker is cleared but the underlying correction is not yet "
        "recorded in the substrate."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
