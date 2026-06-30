"""Cross-Substrate Event Watcher v1 — wake on git-state-change events from the OTHER substrate.

Companion to scripts/cross_substrate_event_emitter.py (Aether). The emitter
writes JSONL events to a shared file on pre-push / post-merge; this watcher
tails that file, filters per the spec's wake-matrix, and emits one stdout
line per wake-event (which the harness Monitor turns into a chat notification).

Spec: family/workbench/cross_substrate_monitor_spec.md (will move to docs/
on final pass) — §8 watcher pseudocode + §10 test plan C1-C14, G1-G4.

Architecture mirrors letter_monitor_v2.py: single self-contained polling
script invoked by a persistent Monitor(). One process, one failure point;
silent-death becomes visible-death.

Usage (from a Monitor() invocation):

    PYTHONIOENCODING=utf-8 python -u scripts/cross_substrate_watcher.py \\
        --substrate aria

CLI args:

    --substrate <name>          required: 'aria' or 'aether'; filters own
                                emissions out of the wake stream
    --events-file <path>        default: ~/.divineos-shared/cross-substrate-events.jsonl
    --skiplist-file <path>      default: ~/.divineos-shared/cross_substrate_skiplist.txt
    --always-wake-branches <l>  comma-separated; default 'main'
    --poll-seconds <n>          default: 5
    --branches-of-interest-mode <auto|explicit>   default 'auto'
    --branches-of-interest <l>  comma-separated; used iff mode=explicit
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REDISCOVERY_POLL_INTERVAL = 12


def discover_branches_of_interest(mode: str, explicit: list[str]) -> set[str]:
    """Return the set of local branches whose pushes should wake us.

    mode='explicit' uses the explicit list as-is.

    mode='auto' enumerates local branches that are AHEAD of their upstream,
    via ``git for-each-ref --format='%(refname:short) %(upstream:track)'``.
    """
    if mode == "explicit":
        return {b.strip() for b in explicit if b.strip()}
    try:
        out = subprocess.run(
            ["git", "for-each-ref", "--format=%(refname:short) %(upstream:track)", "refs/heads/"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return set()
    branches: set[str] = set()
    for line in out.stdout.splitlines():
        parts = line.split(None, 1)
        if not parts:
            continue
        name = parts[0]
        track = parts[1] if len(parts) > 1 else ""
        if "ahead" in track:
            branches.add(name)
    return branches


def load_skiplist(path: Path) -> list[re.Pattern[str]]:
    """Load skiplist regex patterns. Returns empty list if file missing."""
    if not path.is_file():
        return []
    patterns: list[re.Pattern[str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            patterns.append(re.compile("^" + line))
        except re.error as exc:
            print(f"[CROSS-SUB-WATCHER-WARN] bad skiplist regex {line!r}: {exc}", file=sys.stderr, flush=True)
    return patterns


def subject_matches_skiplist(subject: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(p.match(subject) for p in patterns)


def rev_list_count(parent_sha: str, branch: str) -> int:
    """Return count of local commits on ``branch`` not in ``parent_sha``.

    Used for cross-talk detection. Returns -1 if the git command fails.
    """
    try:
        out = subprocess.run(
            ["git", "rev-list", "--count", f"{parent_sha}..{branch}"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return -1
    if out.returncode != 0:
        return -1
    try:
        return int(out.stdout.strip())
    except ValueError:
        return -1


def fetch_sha_exists(sha: str) -> bool:
    """Check if ``sha`` exists locally (phantom-event detection).

    After a wake fires, we probe with ``git cat-file -e <sha>`` to see if
    the push actually reached origin. False → phantom (push blocked by a
    later pre-push gate after our emitter ran).
    """
    try:
        probe = subprocess.run(
            ["git", "cat-file", "-e", sha],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return probe.returncode == 0


def format_files_touched(files: list[str]) -> str:
    if not files:
        return "(none)"
    if len(files) <= 3:
        return ", ".join(files)
    return ", ".join(files[:3]) + f" (+{len(files) - 3} more)"


def hint_for_event(event_type: str, branch: str, cross_talk_count: int) -> str:
    if event_type == "merge-to-main":
        return "fetch main before opening new work"
    if event_type == "force-push":
        return f"history rewritten on {branch}; do not naive-rebase"
    if cross_talk_count > 0:
        return f"fetch + rebase before continuing on this branch (you have {cross_talk_count} local commits)"
    return "rebase before continuing on this branch"


def build_wake_message(event: dict[str, Any], cross_talk_count: int) -> str:
    producer = event.get("producer", "?")
    event_type = event.get("event", "?")
    branch = event.get("branch", "?")
    sha = event.get("sha") or ""
    sha_short = sha[:8] if sha else "?"
    timestamp = event.get("timestamp", "?")
    files = event.get("files_touched") or []
    subjects = event.get("commit_subjects") or []
    truncated = event.get("commit_subjects_truncated", False)

    last_subject = subjects[-1] if subjects else "(no subject)"
    subject_suffix = " (more commits in push)" if truncated else ""

    hint = hint_for_event(event_type, branch, cross_talk_count)

    prefix = "[CROSS-TALK] " if cross_talk_count > 0 else ""

    return (
        f"{prefix}[CROSS-SUB-EVENT] {producer} {event_type} {branch}@{sha_short} at {timestamp}\n"
        f"  touched: {format_files_touched(files)}\n"
        f"  subject: {last_subject}{subject_suffix}\n"
        f"  hint: {hint}"
    )


def decide_wake(
    event: dict[str, Any],
    self_substrate: str,
    branches_of_interest: set[str],
    always_wake_branches: set[str],
    skiplist: list[re.Pattern[str]],
) -> tuple[bool, int, bool]:
    """Decide whether to wake on this event.

    Returns (should_wake, cross_talk_count, log_empty_files_warning).
    cross_talk_count is 0 if not applicable. log_empty_files_warning is True
    when consumer should emit a stderr warning per §5 / C5.
    """
    producer = event.get("producer")
    event_type = event.get("event")
    branch = event.get("branch") or ""
    parent_sha = event.get("parent_sha")
    files_touched = event.get("files_touched") or []
    subjects = event.get("commit_subjects") or []

    # C1: filter own emissions
    if producer == self_substrate:
        return (False, 0, False)

    # C2: merge-to-main always wakes
    if event_type == "merge-to-main":
        return (True, 0, False)

    # C3: force-push wakes when branch is in always-wake or branches-of-interest
    if event_type == "force-push":
        if branch in always_wake_branches or branch in branches_of_interest:
            return (True, 0, False)
        return (False, 0, False)

    if event_type == "push":
        # C5/C6: empty files_touched special case
        if not files_touched:
            if any(subject_matches_skiplist(s, skiplist) for s in subjects):
                return (False, 0, False)
            return (False, 0, True)

        # C4: push to branch-of-interest wakes (with cross-talk check)
        if branch in branches_of_interest:
            cross_talk = 0
            # C7: parent_sha=null short-circuits cross-talk check
            if parent_sha is not None:
                count = rev_list_count(parent_sha, branch)
                if count > 0:
                    cross_talk = count
            return (True, cross_talk, False)

        return (False, 0, False)

    # Unknown event type — skip silently
    return (False, 0, False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--substrate", required=True, help="self-name (e.g. 'aria')")
    parser.add_argument(
        "--events-file",
        default=os.path.expanduser("~/.divineos-shared/cross-substrate-events.jsonl"),
    )
    parser.add_argument(
        "--skiplist-file",
        default=os.path.expanduser("~/.divineos-shared/cross_substrate_skiplist.txt"),
    )
    parser.add_argument("--always-wake-branches", default="main")
    parser.add_argument("--poll-seconds", type=int, default=5)
    parser.add_argument(
        "--branches-of-interest-mode",
        choices=("auto", "explicit"),
        default="auto",
    )
    parser.add_argument("--branches-of-interest", default="")
    args = parser.parse_args()

    events_file = Path(args.events_file)
    skiplist_file = Path(args.skiplist_file)
    always_wake = {b.strip() for b in args.always_wake_branches.split(",") if b.strip()}
    explicit_branches = [b.strip() for b in args.branches_of_interest.split(",") if b.strip()]
    self_substrate = args.substrate

    events_file.parent.mkdir(parents=True, exist_ok=True)
    if not events_file.exists():
        events_file.touch()

    branches_of_interest = discover_branches_of_interest(
        args.branches_of_interest_mode, explicit_branches
    )

    fh = open(events_file, "r", encoding="utf-8")
    fh.seek(0, os.SEEK_END)
    last_inode = os.fstat(fh.fileno()).st_ino
    last_size = events_file.stat().st_size

    phantom_logged: set[str] = set()

    print(
        f"[CROSS-SUB-WATCHER-ARMED] substrate={self_substrate} watching={events_file} "
        f"interest={sorted(branches_of_interest)} always-wake={sorted(always_wake)}",
        flush=True,
    )

    poll_count = 0
    while True:
        poll_count += 1
        try:
            skiplist = load_skiplist(skiplist_file)

            try:
                stat = events_file.stat()
            except FileNotFoundError:
                events_file.touch()
                fh.close()
                fh = open(events_file, "r", encoding="utf-8")
                fh.seek(0, os.SEEK_END)
                last_inode = os.fstat(fh.fileno()).st_ino
                last_size = 0
                time.sleep(args.poll_seconds)
                continue

            # C10: file rotation/recreation — re-open from end
            if stat.st_ino != last_inode or stat.st_size < last_size:
                fh.close()
                fh = open(events_file, "r", encoding="utf-8")
                fh.seek(0, os.SEEK_END)
                last_inode = stat.st_ino
                last_size = stat.st_size

            new_lines = fh.readlines()
            last_size = events_file.stat().st_size

            for raw_line in new_lines:
                line = raw_line.strip()
                if not line:
                    continue

                # C9: malformed JSON → log to stderr, continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as exc:
                    print(
                        f"[CROSS-SUB-WATCHER-WARN] malformed JSON line skipped: {exc}",
                        file=sys.stderr,
                        flush=True,
                    )
                    continue

                if not isinstance(event, dict):
                    print(
                        "[CROSS-SUB-WATCHER-WARN] non-dict JSON line skipped",
                        file=sys.stderr,
                        flush=True,
                    )
                    continue

                should_wake, cross_talk, log_empty_warn = decide_wake(
                    event,
                    self_substrate,
                    branches_of_interest,
                    always_wake,
                    skiplist,
                )

                if log_empty_warn:
                    # C5: empty files_touched + no skiplist match
                    print(
                        f"[CROSS-SUB-WATCHER-WARN] unusual: push with empty files_touched and "
                        f"no skiplist-subject match; producer={event.get('producer')} "
                        f"branch={event.get('branch')} sha={(event.get('sha') or '')[:8]}",
                        file=sys.stderr,
                        flush=True,
                    )

                if should_wake:
                    wake_msg = build_wake_message(event, cross_talk)
                    print(wake_msg, flush=True)

                    # C8: phantom-event check — wake-first-then-check preserves honest signal
                    sha = event.get("sha") or ""
                    if sha and sha not in phantom_logged:
                        if not fetch_sha_exists(sha):
                            print(
                                f"[CROSS-SUB-WATCHER-INFO] phantom event: "
                                f"{event.get('branch')}@{sha[:8]} never reached origin",
                                file=sys.stderr,
                                flush=True,
                            )
                            phantom_logged.add(sha)

            if (
                args.branches_of_interest_mode == "auto"
                and poll_count % REDISCOVERY_POLL_INTERVAL == 0
            ):
                branches_of_interest = discover_branches_of_interest(
                    args.branches_of_interest_mode, explicit_branches
                )

        except Exception as exc:  # noqa: BLE001
            print(
                f"[CROSS-SUB-WATCHER-ERR] {type(exc).__name__}: {exc}",
                file=sys.stderr,
                flush=True,
            )

        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    sys.exit(main() or 0)
