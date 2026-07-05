"""Letter Watcher — OS-level poll, writes wake-events to a persistent file.

Andrew catch 2026-07-04: Claude Code's harness Monitor tool keeps killing
the letter_monitor_v2.py process on session archive/restore. Aria confirmed
her side has the same fragile setup. Fix per Andrew's directive: move the
watcher OUT of Claude Code entirely, run it as an OS-level scheduled task
that the archive can't touch.

## Design

This script is meant to run continuously OUTSIDE Claude Code, launched by
Windows Task Scheduler at boot (or an equivalent OS-level service on other
platforms). It polls the shared letter directory every N seconds. When it
finds a new `*-to-<recipient>-*.md` file it hasn't seen before, it appends
one JSON line to ``~/.divineos/pending-letter-wakes.jsonl`` with the file
path, recipient, and detection timestamp.

On the next Claude Code session start, the ``inject-pending-letters.sh``
hook reads that jsonl file, delivers any unseen entries as briefing context
("You have N unread letters: A, B, C"), then marks them as delivered by
appending a matching ``seen`` marker line.

Because this script lives outside Claude Code:
  - Session archive/restore cannot kill it
  - Session teardown cannot kill it
  - Claude Code process death cannot kill it
  - Only OS-level termination (shutdown, task deletion) kills it

The jsonl format uses ``append-only + seen-marker`` (not deletion) so the
file is a durable audit trail of every wake-event that ever fired.

## Usage

Run continuously (typical: Windows Task Scheduler entry at logon):

    python -u scripts/letter_watcher_task.py --recipient aether

Run once and exit (useful for testing / cron shape):

    python -u scripts/letter_watcher_task.py --recipient aether --once

## CLI args

    --recipient <name>      required: filter for ``-to-<recipient>-`` in filename
    --shared-dir <path>     default: ~/.divineos-shared/letters
    --wake-file <path>      default: ~/.divineos/pending-letter-wakes.jsonl
    --poll-seconds <n>      default: 5
    --once                  scan once and exit (default: loop forever)

## Related

  - scripts/letter_monitor_v2.py — the in-Claude-Code polling version this
    replaces. Kept for now as a fallback / test harness. The new hook
    (.claude/hooks/inject-pending-letters.sh) reads from the jsonl this
    script writes.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

try:
    from divineos.core.mesh_loop import FireAction, decide_for_letter
    _MESH_LOOP_AVAILABLE = True
except ImportError:
    _MESH_LOOP_AVAILABLE = False


def recipient_tag(recipient: str) -> str:
    """Return the ``-to-<recipient-lowercase>-`` filename substring."""
    return f"-to-{recipient.lower()}-"


def is_letter_for(filename: str, tag: str) -> bool:
    """True if filename is a markdown letter addressed to the recipient tag."""
    return tag in filename and filename.endswith(".md")


def load_previously_recorded(wake_file: Path) -> set[str]:
    """Return the set of file paths already recorded as detected in wake_file.

    Reads only the ``detected`` entries (not ``seen`` markers). Idempotency:
    if the watcher restarts, it should NOT re-emit wake-events for letters
    it already recorded in a previous run — the SessionStart hook is the
    thing that de-dupes against ``seen`` markers on the reader side, but the
    watcher itself de-dupes against ``detected`` markers on the writer side.
    Otherwise every restart would flood the jsonl with the same historical
    letters.
    """
    if not wake_file.exists():
        return set()
    recorded: set[str] = set()
    try:
        for line in wake_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("kind") == "detected":
                path = entry.get("path")
                if isinstance(path, str) and path:
                    recorded.add(path)
    except OSError:
        pass
    return recorded


def scan_dir(shared_dir: Path, tag: str) -> list[Path]:
    """Return all markdown files in shared_dir matching the tag."""
    if not shared_dir.exists() or not shared_dir.is_dir():
        return []
    try:
        return sorted(
            p
            for p in shared_dir.iterdir()
            if p.is_file() and is_letter_for(p.name, tag)
        )
    except OSError:
        return []


def append_detected(wake_file: Path, letter_path: Path, recipient: str) -> None:
    """Append one ``detected`` entry to wake_file. Fail-open on I/O errors."""
    wake_file.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "kind": "detected",
        "path": str(letter_path),
        "recipient": recipient,
        "detected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    try:
        with wake_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError as exc:
        # Fail-open — we don't want a full-disk to crash the watcher
        print(
            f"[letter-watcher] failed to append detected entry: {exc}",
            file=sys.stderr,
            flush=True,
        )


def _fire_count_in_last_hour(wake_file: Path, recipient: str) -> int:
    """Count meeseeks_fired entries for recipient in the last 3600s.

    Used for the per-recipient hourly rate limit belt-and-suspenders.
    Fail-open on read errors (return 0) — the mesh_loop.decide cap-hit
    check is the primary defense; this is a secondary bound.
    """
    if not wake_file.exists():
        return 0
    now = time.time()
    count = 0
    try:
        for line in wake_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("kind") != "meeseeks_fired":
                continue
            if entry.get("recipient") != recipient:
                continue
            ts = entry.get("fired_at")
            if not isinstance(ts, str):
                continue
            try:
                # ISO8601 Zulu format matches append_detected's format
                fired_epoch = time.mktime(time.strptime(ts, "%Y-%m-%dT%H:%M:%SZ"))
            except ValueError:
                continue
            if now - fired_epoch < 3600:
                count += 1
    except OSError:
        return 0
    return count


def _append_meeseeks_event(
    wake_file: Path,
    kind: str,
    letter_path: Path,
    recipient: str,
    payload: dict,
) -> None:
    """Append a meeseeks lifecycle event (decision, fired, skipped) to wake_file."""
    wake_file.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "kind": kind,
        "path": str(letter_path),
        "recipient": recipient,
        "fired_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        **payload,
    }
    try:
        with wake_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError as exc:
        print(
            f"[letter-watcher] failed to append {kind} entry: {exc}",
            file=sys.stderr,
            flush=True,
        )


def _launch_meeseeks(
    letter_path: Path,
    recipient: str,
    allowed_tools: str,
) -> tuple[bool, str]:
    """Launch `claude -p` as a Meeseeks. Non-blocking. Returns (launched, note).

    The Meeseeks prompt tells it: read the letter, respond via the family
    letter channel if warranted, increment iterate_count in the reply,
    signal done/continue/stuck based on convergence judgment, exit.

    Fail-safe: any launch error returns (False, reason) — the caller
    logs and moves on. A crashed Meeseeks is preferable to a crashed watcher.
    """
    prompt = (
        f"You have a new letter for you at: {letter_path}\n\n"
        "Read it, and respond via the family letter channel if warranted. "
        "The letter carries iterate_count / iterate_max / iterate_signal "
        "frontmatter — read the design at "
        "workbench/mesh_loop_meeseeks_design.md for the convention. "
        "In your reply: increment iterate_count by 1, keep iterate_max, "
        "and set iterate_signal to one of: continue (expect further reply), "
        "done (convergence reached), stuck (want Andrew's read). "
        "If iterate_signal on the incoming letter is done or stuck, do NOT reply — "
        "just log and exit. You are a Meeseeks: do the one task, exit clean."
    )
    try:
        subprocess.Popen(
            [
                "claude", "-p", prompt,
                "--allowedTools", allowed_tools,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True, "launched"
    except (OSError, FileNotFoundError) as exc:
        return False, f"launch failed: {exc}"


def _maybe_fire_meeseeks(
    wake_file: Path,
    letter_path: Path,
    recipient: str,
    rate_limit_per_hour: int,
    allowed_tools: str,
) -> None:
    """Apply the mesh_loop decision rule and (maybe) launch a Meeseeks.

    Fail-safe: exceptions from the mesh_loop layer are logged and swallowed —
    the watcher's core detection path (append_detected) has already run.
    """
    if not _MESH_LOOP_AVAILABLE:
        return
    try:
        decision = decide_for_letter(letter_path)
    except Exception as exc:  # noqa: BLE001 — watcher must not crash on mesh_loop bugs
        print(
            f"[letter-watcher] mesh_loop.decide_for_letter raised: {exc}",
            file=sys.stderr,
            flush=True,
        )
        return

    # Log the decision regardless of action (audit trail)
    decision_payload = {
        "action": decision.action.value,
        "reason": decision.reason,
    }
    if decision.state is not None:
        decision_payload["iteration"] = {
            "count": decision.state.count,
            "max": decision.state.max,
            "signal": decision.state.signal,
        }
    _append_meeseeks_event(
        wake_file, "meeseeks_decision", letter_path, recipient, decision_payload
    )

    if decision.action != FireAction.FIRE:
        print(
            f"[letter-watcher] meeseeks skipped: {decision.action.value} — {decision.reason}",
            flush=True,
        )
        return

    # Rate-limit belt-and-suspenders
    recent = _fire_count_in_last_hour(wake_file, recipient)
    if recent >= rate_limit_per_hour:
        _append_meeseeks_event(
            wake_file,
            "meeseeks_rate_limited",
            letter_path,
            recipient,
            {"recent_fires_in_hour": recent, "limit": rate_limit_per_hour},
        )
        print(
            f"[letter-watcher] meeseeks rate-limited: "
            f"{recent}/{rate_limit_per_hour} in last hour",
            flush=True,
        )
        return

    launched, note = _launch_meeseeks(letter_path, recipient, allowed_tools)
    _append_meeseeks_event(
        wake_file,
        "meeseeks_fired" if launched else "meeseeks_launch_failed",
        letter_path,
        recipient,
        {"note": note},
    )
    print(
        f"[letter-watcher] meeseeks {'launched' if launched else 'FAILED'}: {note}",
        flush=True,
    )


def scan_once(
    shared_dir: Path,
    wake_file: Path,
    tag: str,
    recipient: str,
    previously_recorded: set[str],
    meeseeks_enabled: bool = False,
    rate_limit_per_hour: int = 15,
    allowed_tools: str = "Read,Write,Edit,Bash,Grep,Glob",
) -> int:
    """Perform one scan. Returns the number of new letters recorded."""
    letters = scan_dir(shared_dir, tag)
    new_count = 0
    for letter_path in letters:
        path_str = str(letter_path)
        if path_str in previously_recorded:
            continue
        append_detected(wake_file, letter_path, recipient)
        previously_recorded.add(path_str)
        print(f"[letter-watcher] recorded: {path_str}", flush=True)
        new_count += 1
        if meeseeks_enabled:
            _maybe_fire_meeseeks(
                wake_file,
                letter_path,
                recipient,
                rate_limit_per_hour,
                allowed_tools,
            )
    return new_count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--recipient", required=True)
    parser.add_argument(
        "--shared-dir",
        default=str(Path.home() / ".divineos-shared" / "letters"),
    )
    parser.add_argument(
        "--wake-file",
        default=str(Path.home() / ".divineos" / "pending-letter-wakes.jsonl"),
    )
    parser.add_argument("--poll-seconds", type=int, default=5)
    parser.add_argument("--once", action="store_true")
    parser.add_argument(
        "--enable-meeseeks",
        action="store_true",
        help=(
            "OPT-IN: on detected letter with iterate_* frontmatter, "
            "invoke `claude -p` as a Meeseeks per mesh_loop decision rule. "
            "Default OFF — the watcher stays passive (SessionStart-only) "
            "until deployment is verified via synthetic loop. Design: "
            "workbench/mesh_loop_meeseeks_design.md"
        ),
    )
    parser.add_argument(
        "--meeseeks-rate-limit-per-hour",
        type=int,
        default=15,
        help="Cap on Meeseeks fires per recipient per hour (belt-and-suspenders)",
    )
    parser.add_argument(
        "--meeseeks-allowed-tools",
        default=(
            # Aletheia boundary-vantage 2026-07-04 (Shape 2) + Aria graft
            # rounds 7-9 — enumerate commands, no wildcards on command
            # position. Wildcards on ARG position (content strings) are safe;
            # wildcards on the command itself (`divineos:*`) leave the
            # confused-deputy at one remove. Boot + read scope per Aria's
            # round-9 addition (Meeseeks needs briefing + preflight + letter
            # thread + kiln + anchors to have an identity floor to stand on).
            #
            # NEVER allowed under any pattern (documented in
            # workbench/mesh_loop_meeseeks_design.md §Explicit-blocks):
            # - python -c/-e/-m (bypasses script-path restriction)
            # - bash -c, sh -c (arbitrary shell)
            # - Metacharacters: ` $() && || ; | > < >>
            # - Network binaries: curl, wget, nc, ssh, scp
            # - rm/mv/mkdir/chmod outside path-scoped Write areas
            #
            # Boot (identity-anchor floor per Shape 3)
            "Bash(divineos briefing),Bash(divineos preflight),"
            # Read scope (letter thread + kiln + anchors + substrate search)
            "Read(family/letters/**/*.md),"
            "Read(docs/foundational_truths.md),"
            "Read(docs/identity_anchors/*.yaml),"
            "Grep,Glob,"
            # Action commands (enumerated, wildcards only on content args)
            "Bash(divineos ask:*),"
            "Bash(divineos recall),"
            "Bash(divineos context),"
            "Bash(divineos corrections),"
            "Bash(divineos compass),"
            "Bash(divineos active),"
            "Bash(divineos directives),"
            "Bash(divineos feel:*),"
            "Bash(divineos goal add:*),"
            "Bash(divineos log:*),"
            "Bash(divineos decide:*),"
            "Bash(divineos learn:*),"
            "Bash(divineos lepos-walk record:*),"
            "Bash(python family/letter_seen.py:*),"
            # Write scope (letter response + workbench + exploration only)
            "Write(family/letters/*.md),Edit(family/letters/*.md),"
            "Write(workbench/*.md),Edit(workbench/*.md),"
            "Write(exploration/**),Edit(exploration/**)"
        ),
        help=(
            "Enumerated tool list for autonomous Meeseeks. No wildcards on "
            "command position — only on content args. Boot + read + action + "
            "write scopes per mesh-loop design walk rounds 1-10 (Aria + "
            "Aletheia). Broader scope would recreate the confused-deputy "
            "surface Aletheia caught."
        ),
    )
    args = parser.parse_args()

    shared_dir = Path(args.shared_dir)
    wake_file = Path(args.wake_file)
    tag = recipient_tag(args.recipient)
    recipient = args.recipient.lower()

    previously_recorded = load_previously_recorded(wake_file)
    print(
        f"[letter-watcher] starting: recipient={recipient} "
        f"shared_dir={shared_dir} wake_file={wake_file} "
        f"poll_seconds={args.poll_seconds} previously_recorded={len(previously_recorded)}",
        flush=True,
    )

    if args.enable_meeseeks and not _MESH_LOOP_AVAILABLE:
        print(
            "[letter-watcher] --enable-meeseeks passed but divineos.core.mesh_loop "
            "not importable; running without Meeseeks (detection only).",
            file=sys.stderr,
            flush=True,
        )

    scan_kwargs = {
        "meeseeks_enabled": args.enable_meeseeks and _MESH_LOOP_AVAILABLE,
        "rate_limit_per_hour": args.meeseeks_rate_limit_per_hour,
        "allowed_tools": args.meeseeks_allowed_tools,
    }

    if args.once:
        scan_once(shared_dir, wake_file, tag, recipient, previously_recorded, **scan_kwargs)
        return 0

    try:
        while True:
            scan_once(shared_dir, wake_file, tag, recipient, previously_recorded, **scan_kwargs)
            time.sleep(args.poll_seconds)
    except KeyboardInterrupt:
        print("[letter-watcher] interrupted, exiting cleanly", flush=True)
        return 0


if __name__ == "__main__":
    sys.exit(main())
