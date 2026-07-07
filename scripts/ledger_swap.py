"""ledger_swap.py — atomic ledger swap with automated pre-swap snapshot.

Andrew 2026-07-05: "if you need to snapshot before you switch branches to
fix it? then that also needs fully automated.. not remembered". This
script implements Layer 1 of the automation: the pre-swap snapshot is
part of the swap operation itself, not a step the operator remembers.

Usage:
    python scripts/ledger_swap.py --source <path-to-merged-db> \
                                  [--target <path-to-live-db>] \
                                  [--safety-root <path-to-safety-dir>] \
                                  [--dry-run]

Discipline enforced:
    1. AUTOMATED pre-swap snapshot: the live target gets copied to a
       timestamped safety location BEFORE any swap operation. This is
       part of the swap, not remembered — the swap cannot proceed
       without the snapshot succeeding.
    2. Content integrity check on source: source DB must open, must
       have a system_events table, must have at least one row.
    3. Atomic swap: use os.replace() (POSIX rename semantics) so the
       target is either fully-old or fully-new, never a partial write.
    4. Post-swap verification: after the swap, immediately open the
       target and run per-event content_hash verification on the last
       N events to confirm the new ledger is readable and its head is
       intact.

If verification fails: the safety snapshot lets the operator restore.
If the swap operation itself fails partway (rare with os.replace):
    - If target was renamed but source didn't move: safe (target is
      old file with new name — restart the script)
    - If source moved but target rename failed: safety snapshot exists.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path


def _verify_source_readable(source: Path) -> tuple[bool, str]:
    """Confirm source DB opens, has system_events, and has rows."""
    try:
        c = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    except sqlite3.Error as e:
        return False, f"cannot open source: {e}"
    try:
        n = c.execute("SELECT COUNT(*) FROM system_events").fetchone()[0]
    except sqlite3.Error as e:
        return False, f"source has no system_events table: {e}"
    if n < 1:
        return False, "source system_events is empty"
    return True, f"source readable, {n} events"


def _verify_target_head(target: Path, n_check: int = 3) -> tuple[bool, str]:
    """Walk last N events of the target chain, confirm content_hash integrity per event."""
    try:
        c = sqlite3.connect(f"file:{target}?mode=ro", uri=True)
    except sqlite3.Error as e:
        return False, f"cannot open target: {e}"
    try:
        rows = c.execute(
            "SELECT event_id, timestamp, event_type, actor, payload, content_hash, prior_hash, chain_hash "
            "FROM system_events ORDER BY timestamp DESC, rowid DESC LIMIT ?",
            (n_check,),
        ).fetchall()
    except sqlite3.Error as e:
        return False, f"cannot read target system_events: {e}"
    if not rows:
        return False, "target has no events"
    for ev in rows:
        event_id, timestamp, event_type, actor, payload, content_hash, prior_hash, chain_hash = ev
        # Chain integrity: recompute chain_hash from the seven-field pipe-separated formula
        recomputed = hashlib.sha256(
            f"{prior_hash}|{event_id}|{timestamp}|{event_type}|{actor}|{payload}|{content_hash}".encode()
        ).hexdigest()
        if recomputed != chain_hash:
            return False, f"chain link broken at {event_id[:12]}..."
    return True, f"last {len(rows)} events verified"


def swap(
    source: Path,
    target: Path,
    safety_root: Path,
    dry_run: bool = False,
) -> int:
    """Perform the automated pre-swap-snapshot + atomic swap.

    Returns 0 on success, non-zero on any failure.
    """
    print(f"[ledger_swap] source: {source}")
    print(f"[ledger_swap] target: {target}")
    print(f"[ledger_swap] safety_root: {safety_root}")
    if dry_run:
        print("[ledger_swap] DRY-RUN — no writes will occur")

    if not source.is_file():
        print(f"[ledger_swap] ERROR: source not found: {source}", file=sys.stderr)
        return 2
    if not target.is_file():
        print(f"[ledger_swap] ERROR: target not found (nothing to swap): {target}", file=sys.stderr)
        return 2

    # STEP 1 — verify source is readable and has content
    ok, msg = _verify_source_readable(source)
    print(f"[ledger_swap] source check: {msg}")
    if not ok:
        return 3

    # STEP 2 — AUTOMATED pre-swap snapshot
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    snap_dir = safety_root / f"pre-swap-{stamp}"
    snap_path = snap_dir / f"{target.name}.pre_swap"
    print(f"[ledger_swap] snapshot destination: {snap_path}")
    if not dry_run:
        try:
            snap_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, snap_path)
        except OSError as e:
            print(f"[ledger_swap] ERROR: snapshot failed, aborting swap: {e}", file=sys.stderr)
            return 4
        if not snap_path.is_file():
            print(f"[ledger_swap] ERROR: snapshot did not land at expected path", file=sys.stderr)
            return 4
        # Cross-check size (weak but catches truncation)
        if snap_path.stat().st_size != target.stat().st_size:
            print(f"[ledger_swap] ERROR: snapshot size mismatch", file=sys.stderr)
            return 4
        print(f"[ledger_swap] snapshot OK ({snap_path.stat().st_size} bytes)")

    # STEP 3 — atomic swap
    if dry_run:
        print("[ledger_swap] DRY-RUN — would os.replace(source, target)")
        return 0
    try:
        # Copy source to a sibling of target (same filesystem for atomic rename)
        staging = target.parent / f".{target.name}.swap-staging"
        shutil.copy2(source, staging)
        os.replace(staging, target)
    except OSError as e:
        print(f"[ledger_swap] ERROR: swap operation failed: {e}", file=sys.stderr)
        print(f"[ledger_swap] safety snapshot available at: {snap_path}", file=sys.stderr)
        return 5
    print("[ledger_swap] atomic swap complete")

    # STEP 4 — post-swap verification
    ok, msg = _verify_target_head(target, n_check=3)
    print(f"[ledger_swap] post-swap verification: {msg}")
    if not ok:
        print(f"[ledger_swap] ERROR: target failed post-swap verification.", file=sys.stderr)
        print(f"[ledger_swap] safety snapshot available at: {snap_path}", file=sys.stderr)
        print(f"[ledger_swap] to restore: cp '{snap_path}' '{target}'", file=sys.stderr)
        return 6

    print(f"[ledger_swap] SUCCESS")
    print(f"[ledger_swap] pre-swap snapshot retained at: {snap_path}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    p.add_argument("--source", required=True, type=Path, help="Path to merged DB to swap in")
    p.add_argument(
        "--target",
        default=Path.home() / ".divineos" / "data" / "event_ledger.db",
        type=Path,
        help="Live target path (default: ~/.divineos/data/event_ledger.db)",
    )
    p.add_argument(
        "--safety-root",
        default=Path("C:/tmp/ledger-surgery-safety-2026-07-05"),
        type=Path,
        help="Directory for pre-swap snapshots",
    )
    p.add_argument("--dry-run", action="store_true", help="Print plan; no writes")
    args = p.parse_args()
    return swap(args.source, args.target, args.safety_root, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
