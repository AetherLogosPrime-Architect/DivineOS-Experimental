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

import _repo_import  # noqa: F401  -- must precede any divineos import

# Direct import path: this module does NOT depend on divineos.cli.
# That is the whole point — when cli/__init__.py is broken, this still
# imports because correction_marker imports only atomic_io and paths.
from divineos.core.correction_marker import clear_marker, marker_path, read_marker  # noqa: E402
from divineos.core.paths import divineos_home  # noqa: E402

_MIN_REASON_LEN = 30
_MIN_MISREAD_LEN = 40
_ESCAPE_LOG = "cli_broken_escapes.jsonl"


def _append_escape_log(
    reason: str,
    original_trigger: str | None,
    misread_clauses: str | None = None,
    mode: str = "cli-broken",
) -> Path:
    """Append a JSON line recording the escape — what was cleared and why.

    The log lives under the divineos home directory (same place the marker
    lives) so the audit trail follows the user across worktrees.
    """
    log_path = divineos_home() / _ESCAPE_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.time(),
        "mode": mode,
        "reason": reason,
        "misread_clauses": misread_clauses,
        "original_trigger": original_trigger,
        "remediation_owed": (
            'Log the original correction via `divineos correction "..."` '
            "once the CLI is working again."
            if mode == "cli-broken"
            else (
                "Quoted clauses are on-record for audit. If those clauses "
                "are actually USE-shape (not MENTION), this clear was a "
                "bypass and a real correction was dodged."
            )
        ),
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return log_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Clear the correction-unlogged marker. Two supported modes: "
            "(a) --reason only = CLI-broken escape hatch (locked-box trap); "
            "(b) --reason + --misread-clauses = false-positive attribution "
            "(operator must quote the specific reply-clauses claimed to be "
            "MENTION-not-USE, so blind-clear cannot happen). Andrew 2026-07-29 "
            "correction #194: the false-positive path had no discriminator, "
            "allowing real self-admissions to be dodged as 'false positive' "
            "with a plausible 30-char reason. --misread-clauses closes that."
        )
    )
    parser.add_argument(
        "--reason",
        required=True,
        help=(
            "Why is the marker being cleared? For CLI-broken mode: why the "
            "CLI is unreachable and the plan to log the correction afterward. "
            "For false-positive mode: what class of MENTION was misread as "
            f"USE. Must be >= {_MIN_REASON_LEN} chars."
        ),
    )
    parser.add_argument(
        "--misread-clauses",
        default=None,
        help=(
            "REQUIRED for false-positive attribution (not for CLI-broken "
            "escape). Quote the specific reply-clauses that were misread as "
            "USE-shape self-admission. Must be >= "
            f"{_MIN_MISREAD_LEN} chars. Forces the operator to actually read "
            "their own text before clearing. If the quoted clauses are "
            "obviously USE-shape, the clear is a bypass on record."
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

    misread_clauses = (args.misread_clauses or "").strip() or None
    mode = "false-positive" if misread_clauses is not None else "cli-broken"
    if misread_clauses is not None and len(misread_clauses) < _MIN_MISREAD_LEN:
        print(
            f"REFUSED: --misread-clauses must be >= {_MIN_MISREAD_LEN} "
            f"characters (got {len(misread_clauses)}). To attribute a "
            "false-positive you must quote the specific reply-text you "
            "claim was misread. Stub-length clauses are stub-attribution.",
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
    log_path = _append_escape_log(reason, original_trigger, misread_clauses, mode)

    # 2026-07-30 (prereg-81b268695979): dismiss-is-bypass wiring.
    # Andrew directive: "dismissing is bypassing.. and unless you are
    # literally chicken and egged then you do not bypass.. and if you
    # do bypass that needs to auto trigger a root cause investigation
    # and fix." Route marker-clear through the same bypass telemetry
    # that other bypasses use, so a pending psf entry files and blocks
    # extract until closed with substantive evidence. Reason field
    # (and misread-clauses if FP-attribution mode) propagate into psf.
    # File-both design: both cli-broken and false-positive modes file,
    # per second council walk consult-d705189cf9d9 (5-lens convergent).
    try:
        from divineos.core.bypass_telemetry import record_bypass

        combined_reason = reason
        if misread_clauses:
            combined_reason = f"{reason} | misread-clauses: {misread_clauses}"
        record_bypass(
            gate_name="correction-unlogged",
            env_var=f"bypass:dismiss:correction-marker:{mode}",
            reason=combined_reason,
        )
    except Exception as exc:  # noqa: BLE001 — fail-soft
        print(
            f"[!] Bypass telemetry filing failed (marker already cleared): {exc}",
            file=sys.stderr,
        )

    if mode == "false-positive":
        print(
            f"Cleared correction marker at {path} (false-positive attribution).\n"
            f"Escape recorded to {log_path} with quoted clauses.\n"
            "The quoted clauses are ON RECORD. If those clauses are actually "
            "USE-shape rather than MENTION-shape, this clear was a bypass and "
            "the audit will show it."
        )
    else:
        print(
            f"Cleared correction marker at {path} (CLI-broken escape).\n"
            f"Escape recorded to {log_path}.\n"
            "REMEDIATION OWED: once the CLI is working, run "
            '`divineos correction "..."` to log the original correction. '
            "The marker is cleared but the underlying correction is not yet "
            "recorded in the substrate."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
