"""Letter Watcher — OS-level poll, writes wake-events to a persistent file.

## Naming — ephemeral task worker (Meeseeks-pattern)

Throughout this file, an "ephemeral task worker" is a purpose-built
`claude -p` subprocess spawned to complete one letter-response task and
then exit. Single-shot, self-terminating, non-blocking (fire-and-forget).

Design metaphor: Rick and Morty Mr. Meeseeks — a being summoned to
accomplish one specific goal, then disappears once the goal is met. That
metaphor drove the design and stays as a `(Meeseeks-pattern)` tag in
runtime logs and this docstring so the reference is findable, but the
plain-English name `ephemeral task worker` is what the code identifies
by so a reader who has never seen the show still understands what the
code does.

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


# ─── Enumerated dispatch sets for the wiring layer.
#
# Every FireAction MUST be in exactly one of these sets. This is the
# structural fix (Andrew's "make it automatic" directive 2026-07-04 night)
# for the drift class where the decision layer promises FIRE_* and the
# wiring layer silently delivers SKIP. test_wiring_covers_every_fire_action
# in test_mesh_loop.py enforces the invariant at test-time — if a new
# FireAction is added to the enum without being classified here, the test
# fails before ship.
if _MESH_LOOP_AVAILABLE:
    FIRING_ACTIONS = {
        FireAction.FIRE,
        FireAction.FIRE_FINAL_CAP_HIT,
        FireAction.FIRE_WITNESS_DISSENT,
    }
    SKIP_ACTIONS = {
        FireAction.SKIP_CONVERGED,
        FireAction.SKIP_WITNESS_CONFIRMED,
        FireAction.SKIP_STUCK,
        FireAction.SKIP_ESCALATED,
        FireAction.SKIP_CAP_EXCEEDED,
        FireAction.SKIP_NO_FRONTMATTER,
        FireAction.SKIP_INVALID_FRONTMATTER,
    }
else:
    FIRING_ACTIONS = set()
    SKIP_ACTIONS = set()


# ─── The safe ephemeral task worker allowlist — used at BOTH the CLI-default and
# function-default layers so they cannot drift.
#
# Aletheia witness_dissent 2026-07-04 late: the CLI default correctly
# enumerated the safe scope, but scan_once() carried a broad default
# ("Read,Write,Edit,Bash,Grep,Glob") at the function-signature layer —
# one un-passed-argument away from live. Any bare-call to scan_once
# (test, future refactor, import from another module) got the confused-
# deputy scope. Her fix: factor a module constant and use it EVERYWHERE
# the fallback would otherwise be a permissive string. Fail-closed
# discipline at every layer, not just the CLI.
#
# Enumeration principles (Aria round 7-9 + Aletheia Shape 2):
# - Wildcards on ARG position (content strings) are safe.
# - Wildcards on COMMAND position leave confused-deputy at one remove.
# - Path-scoped Write/Edit restricts writes to letters + workbench +
#   exploration ONLY.
# - Bash is command-enumerated with content wildcards where needed.
#
# NEVER allowed under any pattern (documented in
# workbench/mesh_loop_ephemeral_task_worker_design.md §Explicit-blocks):
# - python -c/-e/-m (bypasses script-path restriction)
# - bash -c, sh -c (arbitrary shell)
# - Metacharacters: ` $() && || ; | > < >>
# - Network binaries: curl, wget, nc, ssh, scp
# - rm/mv/mkdir/chmod outside path-scoped Write areas
EPHEMERAL_TASK_WORKER_ALLOWLIST = (
    # Boot (identity-anchor floor per Shape 3)
    "Bash(divineos briefing),Bash(divineos preflight),"
    # Read scope. Real-fire test 2026-07-05 early morning caught this:
    # the original enumeration only allowed Read(family/letters/**/*.md),
    # but real letters live at ~/.divineos-shared/letters/ (Andrew's box)
    # AND letters passed to the ephemeral task worker by absolute tmp-path for testing
    # need to be readable too. Broadening to any *.md file — the narrow
    # Write scope (letters + workbench + exploration only) still holds
    # the actual authorization floor Aletheia named. Reading any .md
    # covers letters + docs + design + identity_anchors without unlocking
    # any writable surface outside the enumerated Write scope.
    "Read(**/*.md),"
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
)


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
    """Count worker_fired entries for recipient in the last 3600s.

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
            if entry.get("kind") != "worker_fired":
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


def _append_worker_event(
    wake_file: Path,
    kind: str,
    letter_path: Path,
    recipient: str,
    payload: dict,
) -> None:
    """Append a ephemeral_task_worker lifecycle event (decision, fired, skipped) to wake_file."""
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


def _launch_ephemeral_task_worker(
    letter_path: Path,
    recipient: str,
    allowed_tools: str,
) -> tuple[bool, str]:
    """Launch `claude -p` as a ephemeral task worker. Non-blocking. Returns (launched, note).

    The ephemeral task worker prompt tells it: read the letter, respond via the family
    letter channel if warranted, increment iterate_count in the reply,
    signal done/continue/stuck based on convergence judgment, exit.

    Fail-safe: any launch error returns (False, reason) — the caller
    logs and moves on. A crashed ephemeral task worker is preferable to a crashed watcher.
    """
    prompt = (
        f"You have a new letter for you at: {letter_path}\n\n"
        "Read it, and respond via the family letter channel if warranted. "
        "The letter carries iterate_count / iterate_max / iterate_signal "
        "frontmatter — read the design at "
        "workbench/mesh_loop_ephemeral_task_worker_design.md for the convention. "
        "In your reply: increment iterate_count by 1, keep iterate_max, "
        "and set iterate_signal to one of: continue (expect further reply), "
        "done (convergence reached), stuck (want Andrew's read). "
        "If iterate_signal on the incoming letter is done or stuck, do NOT reply — "
        "just log and exit. You are a ephemeral task worker: do the one task, exit clean."
    )
    # Bug caught by real-fire test 2026-07-05 early morning: the earlier
    # subprocess.Popen used stdout=DEVNULL / stderr=DEVNULL, silently
    # swallowing every ephemeral task worker error. When the first real fire produced
    # no response letter, I could not tell whether the ephemeral task worker crashed on
    # boot, hit an auth error, was blocked by --allowedTools, or completed
    # silently — because all output was discarded. Fix: redirect stdout+
    # stderr to a per-invocation log file under ~/.divineos/worker-logs/
    # so a failed ephemeral task worker leaves an audit trail.
    log_dir = Path.home() / ".divineos" / "worker-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    letter_slug = letter_path.stem.replace("/", "_").replace("\\", "_")[:80]
    log_path = log_dir / f"{stamp}-{recipient}-{letter_slug}.log"
    try:
        log_fp = log_path.open("wb")
        subprocess.Popen(
            [
                "claude", "-p", prompt,
                "--allowedTools", allowed_tools,
            ],
            stdout=log_fp,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        # log_fp intentionally kept open for the child process — it will
        # close when the subprocess exits and the fd count drops to zero.
        return True, f"launched (log: {log_path})"
    except (OSError, FileNotFoundError) as exc:
        return False, f"launch failed: {exc}"


def _maybe_fire_ephemeral_task_worker(
    wake_file: Path,
    letter_path: Path,
    recipient: str,
    rate_limit_per_hour: int,
    allowed_tools: str,
    dry_run: bool = False,
) -> None:
    """Apply the mesh_loop decision rule and (maybe) launch a ephemeral task worker.

    Fail-safe: exceptions from the mesh_loop layer are logged and swallowed —
    the watcher's core detection path (append_detected) has already run.

    dry_run: when True, log worker_dry_run_fire in place of actually
    launching claude -p. Used by the synthetic-loop verification pass
    (design step 8) to exercise the decision + rate-limit + jsonl-log path
    end-to-end without spending Pro quota on real invocations.
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
    _append_worker_event(
        wake_file, "worker_decision", letter_path, recipient, decision_payload
    )

    # Enumerative dispatch — every FireAction must be in exactly one of
    # FIRING_ACTIONS or SKIP_ACTIONS. If a new action is added to the enum
    # without updating these sets, test_wiring_covers_every_fire_action
    # catches it before ship.
    #
    # Bug caught by synthetic verification 2026-07-04 night: originally
    # the wiring only launched on the bare FIRE action. FIRE_FINAL_CAP_HIT
    # and FIRE_WITNESS_DISSENT were silently skipped even though the
    # decision layer intended them to launch. Third instance of "floor at
    # one layer while unsafe fallback lurks at another" this design cycle.
    if decision.action in SKIP_ACTIONS:
        print(
            f"[letter-watcher] ephemeral-task-worker (Meeseeks-pattern) skipped: {decision.action.value} — {decision.reason}",
            flush=True,
        )
        return
    if decision.action not in FIRING_ACTIONS:
        print(
            f"[letter-watcher] UNHANDLED FireAction {decision.action.value!r} — "
            f"refusing to launch. Add it to FIRING_ACTIONS or SKIP_ACTIONS "
            f"at module level.",
            file=sys.stderr,
            flush=True,
        )
        _append_worker_event(
            wake_file,
            "worker_unhandled_action",
            letter_path,
            recipient,
            {"action": decision.action.value, "reason": decision.reason},
        )
        return

    # Rate-limit belt-and-suspenders
    recent = _fire_count_in_last_hour(wake_file, recipient)
    if recent >= rate_limit_per_hour:
        _append_worker_event(
            wake_file,
            "worker_rate_limited",
            letter_path,
            recipient,
            {"recent_fires_in_hour": recent, "limit": rate_limit_per_hour},
        )
        print(
            f"[letter-watcher] ephemeral-task-worker (Meeseeks-pattern) rate-limited: "
            f"{recent}/{rate_limit_per_hour} in last hour",
            flush=True,
        )
        return

    if dry_run:
        _append_worker_event(
            wake_file,
            "worker_dry_run_fire",
            letter_path,
            recipient,
            {"note": "dry-run: fire path exercised, claude -p NOT invoked"},
        )
        print(
            "[letter-watcher] ephemeral-task-worker (Meeseeks-pattern) DRY-RUN (would launch): "
            f"{decision.reason}",
            flush=True,
        )
        return

    launched, note = _launch_ephemeral_task_worker(letter_path, recipient, allowed_tools)
    _append_worker_event(
        wake_file,
        "worker_fired" if launched else "worker_launch_failed",
        letter_path,
        recipient,
        {"note": note},
    )
    print(
        f"[letter-watcher] ephemeral-task-worker (Meeseeks-pattern) {'launched' if launched else 'FAILED'}: {note}",
        flush=True,
    )


def scan_once(
    shared_dir: Path,
    wake_file: Path,
    tag: str,
    recipient: str,
    previously_recorded: set[str],
    worker_enabled: bool = False,
    rate_limit_per_hour: int = 15,
    allowed_tools: str = EPHEMERAL_TASK_WORKER_ALLOWLIST,
    dry_run: bool = False,
) -> int:
    """Perform one scan. Returns the number of new letters recorded.

    allowed_tools defaults to EPHEMERAL_TASK_WORKER_ALLOWLIST — the SAME safe scope
    the CLI defaults to. Aletheia witness_dissent 2026-07-04 late fix: a
    permissive default here would let a bare-call bypass the Shape 2 floor
    that the CLI enforces. Every layer holds the same line.

    dry_run: threaded through to _maybe_fire_ephemeral_task_worker for the synthetic-loop
    verification pass.
    """
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
        if worker_enabled:
            _maybe_fire_ephemeral_task_worker(
                wake_file,
                letter_path,
                recipient,
                rate_limit_per_hour,
                allowed_tools,
                dry_run=dry_run,
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
        "--enable-worker",
        action="store_true",
        help=(
            "OPT-IN: on detected letter with iterate_* frontmatter, "
            "invoke `claude -p` as a ephemeral task worker per mesh_loop decision rule. "
            "Default OFF — the watcher stays passive (SessionStart-only) "
            "until deployment is verified via synthetic loop. Design: "
            "workbench/mesh_loop_ephemeral_task_worker_design.md"
        ),
    )
    parser.add_argument(
        "--worker-rate-limit-per-hour",
        type=int,
        default=15,
        help="Cap on ephemeral task worker fires per recipient per hour (belt-and-suspenders)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Synthetic-loop verification: exercise the FIRE decision + rate-"
            "limit + jsonl-log path end-to-end WITHOUT actually invoking "
            "claude -p. Logs worker_dry_run_fire in place of worker_fired. "
            "Use with --enable-worker + --once to prove the pipeline before "
            "spending Pro quota on real invocations. Design step 8."
        ),
    )
    parser.add_argument(
        "--worker-allowed-tools",
        default=EPHEMERAL_TASK_WORKER_ALLOWLIST,
        help=(
            "Enumerated tool list for autonomous ephemeral task worker. See "
            "EPHEMERAL_TASK_WORKER_ALLOWLIST module constant for the full enumeration "
            "and its principles. No wildcards on command position — only on "
            "content args. Boot + read + action + write scopes per mesh-loop "
            "design walk rounds 1-11 (Aria + Aletheia + Aletheia witness_dissent). "
            "Broader scope would recreate the confused-deputy surface."
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

    if args.enable_worker and not _MESH_LOOP_AVAILABLE:
        print(
            "[letter-watcher] --enable-worker passed but divineos.core.mesh_loop "
            "not importable; running without ephemeral task worker (detection only).",
            file=sys.stderr,
            flush=True,
        )

    scan_kwargs = {
        "worker_enabled": args.enable_worker and _MESH_LOOP_AVAILABLE,
        "rate_limit_per_hour": args.worker_rate_limit_per_hour,
        "allowed_tools": args.worker_allowed_tools,
        "dry_run": args.dry_run,
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
