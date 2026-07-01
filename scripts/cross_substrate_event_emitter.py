"""Cross-substrate event emitter — pushes/merges from one substrate become
events the other substrate's watcher wakes on.

Spec: `$HOME/.divineos-shared/workbench/cross_substrate_monitor_spec.md`
Co-authored 2026-06-30 by Aether + Aria with Andrew in the room.

Invoked from two git hooks (both already exist for other purposes; the
emitter runs as one delegate line in each):

  pre-push:   reads ref-update lines from stdin, emits one event per
              non-skipped ref. Push vs force-push decided by AHEAD/BEHIND
              divergence between local_sha and remote_sha (§9).
  post-merge: emits 'merge-to-main' when the current branch is `main`.

CLI entry points::

  python scripts/cross_substrate_event_emitter.py pre-push      < refs-on-stdin
  python scripts/cross_substrate_event_emitter.py post-merge

Both modes are observational: they never block the git operation. Any
internal failure prints to stderr and exits 0.

Tested against P1–P16 in §10 of the spec. The crash/race tests (P12, P16)
exercise the POSIX O_APPEND atomicity contract — that's why the JSONL
append goes through ONE `os.write()` call with all bytes prepared in
memory (not `f.write(json)` then `f.write("\n")` — two syscalls would
leave a half-line under SIGKILL).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------
# Paths (shared dir is the single source of truth — see §6 spec resolution)
# --------------------------------------------------------------------------

_SHARED_DIR = Path.home() / ".divineos-shared"
_EVENTS_FILE = _SHARED_DIR / "cross-substrate-events.jsonl"
_SKIPLIST_FILE = _SHARED_DIR / "cross_substrate_skiplist.txt"
_ZERO_SHA = "0" * 40

_TRACE = os.environ.get("DIVINEOS_CROSS_SUBSTRATE_TRACE") == "1"


def _trace(msg: str) -> None:
    if _TRACE:
        print(f"[cross-substrate-emitter] {msg}", file=sys.stderr)


def _err(msg: str) -> None:
    print(f"[cross-substrate-emitter] {msg}", file=sys.stderr)


# --------------------------------------------------------------------------
# Producer name resolution (§9)
# --------------------------------------------------------------------------


def _resolve_producer_name() -> str:
    """Read $HOME/.divineos-shared/cross_substrate_producer.<hostname>.txt
    if it exists. Otherwise fall back to the basename of the repo root.

    Explicit file > heuristic, per §9.
    """
    import socket

    hostname = socket.gethostname()
    explicit = _SHARED_DIR / f"cross_substrate_producer.{hostname}.txt"
    if explicit.exists():
        try:
            name = explicit.read_text(encoding="utf-8").strip()
            if name:
                return name
        except OSError:
            pass

    # Fallback: basename of the repo root.
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            root = Path(result.stdout.strip())
            base = root.name.lower()
            # Convention: 'DivineOS-Experimental' -> 'aether'
            #             'DivineOS-Experimental-Aria-new' -> 'aria'
            if "aria" in base:
                return "aria"
            if "aletheia" in base:
                return "aletheia"
            return "aether"
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


# --------------------------------------------------------------------------
# Skiplist (§6 — lives in shared dir, evolved without commit/pull cycle)
# --------------------------------------------------------------------------


def _load_skiplist_patterns() -> list[re.Pattern[str]]:
    """One regex per line in the skiplist file, anchored to start-of-subject.

    Missing or unreadable file -> empty list (no patterns match, nothing
    gets skipped — fail-open).
    """
    if not _SKIPLIST_FILE.exists():
        return []
    patterns: list[re.Pattern[str]] = []
    try:
        for line in _SKIPLIST_FILE.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                # Anchor to start of subject per §6.
                patterns.append(re.compile("^" + stripped))
            except re.error as exc:
                _err(f"skiplist: invalid regex {stripped!r}: {exc}")
    except OSError as exc:
        _err(f"skiplist: read error: {exc}")
        return []
    return patterns


def _all_subjects_match_skiplist(subjects: list[str], patterns: list[re.Pattern[str]]) -> bool:
    """True iff every subject matches at least one skiplist pattern.

    Per §3, the producer must check ALL subjects in the push-range (not
    just the included-5) so cap-of-5 cannot hide non-bot commits from
    the skip-check.

    Empty subjects list => no commits => no push => caller already
    handled. Returning False keeps the emit-default safe.
    """
    if not subjects:
        return False
    return all(any(p.match(s) for p in patterns) for s in subjects)


def _load_branch_skiplist(producer: str) -> list[re.Pattern[str]]:
    """Per-substrate branch skiplist at
    `$HOME/.divineos-shared/cross_substrate_branch_skip.<producer>.txt`.
    Same regex-per-line shape, anchored to branch name.
    """
    path = _SHARED_DIR / f"cross_substrate_branch_skip.{producer}.txt"
    if not path.exists():
        return []
    out: list[re.Pattern[str]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                out.append(re.compile("^" + stripped))
            except re.error as exc:
                _err(f"branch-skiplist: invalid regex {stripped!r}: {exc}")
    except OSError:
        return []
    return out


# --------------------------------------------------------------------------
# JSONL append — single atomic write per event (P12 / P16 contract)
# --------------------------------------------------------------------------


def _append_event(event: dict[str, Any]) -> bool:
    """Append one event as a JSONL line to the shared events file.

    Returns True on success, False (with stderr message) on failure.

    Critical: serialize JSON + newline INTO ONE bytes object, then call
    os.write() exactly once on an O_APPEND fd. POSIX guarantees that
    O_APPEND writes <= PIPE_BUF (typically >= 4096 on Linux/macOS,
    >= 512 on minimal POSIX) are atomic w.r.t. other O_APPEND writers
    on the same file. A typical event line is ~500 bytes; well under
    the floor.

    A two-syscall implementation (`f.write(json)` then `f.write("\\n")`)
    would leave a half-line if the process is SIGKILLed between writes
    (P12 fails).
    """
    try:
        _SHARED_DIR.mkdir(parents=True, exist_ok=True)
        payload = (json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
        fd = os.open(str(_EVENTS_FILE), flags, 0o644)
        try:
            os.write(fd, payload)
        finally:
            os.close(fd)
        _trace(f"emitted {event.get('event')} for {event.get('branch')}")
        return True
    except OSError as exc:
        _err(f"append failed: {exc}")
        return False


# --------------------------------------------------------------------------
# Git introspection helpers
# --------------------------------------------------------------------------


def _git(*args: str) -> tuple[int, str, str]:
    """Run `git <args>`. Return (returncode, stdout, stderr).

    Never raises — failures become (nonzero, "", err-text) so the caller
    decides whether to emit or skip the event silently.
    """
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode, result.stdout, result.stderr
    except OSError as exc:
        return 1, "", str(exc)


def _rev_list_count(rev_range: str) -> int | None:
    """`git rev-list --count <range>`. Returns None on git failure
    (P15 — must NOT emit a malformed event when rev-list fails)."""
    rc, out, err = _git("rev-list", "--count", rev_range)
    if rc != 0:
        _err(f"git rev-list --count {rev_range} failed: {err.strip()}")
        return None
    try:
        return int(out.strip())
    except ValueError:
        return None


def _commit_subjects(rev_range: str, limit: int | None = None) -> list[str] | None:
    """`git log --format=%s <range>` (optionally limited to last N)."""
    args = ["log", "--format=%s"]
    if limit is not None:
        args.extend(["-n", str(limit)])
    args.append(rev_range)
    rc, out, err = _git(*args)
    if rc != 0:
        _err(f"git log --format=%s {rev_range} failed: {err.strip()}")
        return None
    return [line for line in out.splitlines() if line]


def _files_touched(rev_range: str) -> list[str] | None:
    """`git diff --name-only <range>`. Empty list is a valid result
    (per §5 — metadata-only or amend-only commits)."""
    rc, out, err = _git("diff", "--name-only", rev_range)
    if rc != 0:
        _err(f"git diff --name-only {rev_range} failed: {err.strip()}")
        return None
    return [line for line in out.splitlines() if line]


def _utc_now_iso() -> str:
    """RFC3339 UTC timestamp."""
    return _dt.datetime.now(tz=_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _short_branch(ref: str) -> str:
    """`refs/heads/feat/foo` -> `feat/foo`."""
    if ref.startswith("refs/heads/"):
        return ref[len("refs/heads/") :]
    return ref


# --------------------------------------------------------------------------
# pre-push mode
# --------------------------------------------------------------------------


def _handle_pre_push(stdin_text: str) -> int:
    """Read pre-push stdin (`<local_ref> <local_sha> <remote_ref> <remote_sha>`
    per ref-update), emit one event per non-skipped ref.

    Exit code is always 0 — the emitter is observational.
    """
    producer = _resolve_producer_name()
    subject_patterns = _load_skiplist_patterns()
    branch_patterns = _load_branch_skiplist(producer)

    for line in stdin_text.splitlines():
        parts = line.strip().split()
        if len(parts) != 4:
            continue
        local_ref, local_sha, remote_ref, remote_sha = parts

        # 2.a — ref deletion: skip silently.
        if local_sha == _ZERO_SHA:
            continue
        # 2.b — tags out of scope v1 (P14).
        if remote_ref.startswith("refs/tags/"):
            continue

        branch = _short_branch(remote_ref)

        # 2.c — divergence detection.
        if remote_sha == _ZERO_SHA:
            # New branch on remote — every commit is "ahead", no parent.
            ahead = _rev_list_count(local_sha)
            behind = 0
            parent_sha: str | None = None
        else:
            ahead = _rev_list_count(f"{remote_sha}..{local_sha}")
            behind = _rev_list_count(f"{local_sha}..{remote_sha}")
            parent_sha = remote_sha

        # P15: any rev-list failure -> log + skip (no malformed event).
        if ahead is None or behind is None:
            continue
        if ahead == 0:
            continue

        event_type = "force-push" if behind > 0 else "push"

        # 2.f — branch skiplist.
        if any(p.match(branch) for p in branch_patterns):
            _trace(f"branch-skipped {branch}")
            continue

        # 2.d — gather subjects (ALL for skip-check; last-5 for payload).
        if remote_sha == _ZERO_SHA:
            range_for_log = local_sha
        else:
            range_for_log = f"{remote_sha}..{local_sha}"
        all_subjects = _commit_subjects(range_for_log)
        if all_subjects is None:
            continue
        included_subjects = all_subjects[-5:] if all_subjects else []
        truncated = len(all_subjects) > len(included_subjects)

        # 2.e — skiplist: all-subjects-match -> skip whole push silently.
        if subject_patterns and _all_subjects_match_skiplist(all_subjects, subject_patterns):
            _trace(f"subject-skipped {branch} ({len(all_subjects)} commits)")
            continue

        files = _files_touched(range_for_log)
        if files is None:
            continue

        # 2.g — build payload.
        event: dict[str, Any] = {
            "producer": producer,
            "event": event_type,
            "branch": branch,
            "sha": local_sha,
            "parent_sha": parent_sha,
            "timestamp": _utc_now_iso(),
            "files_touched": files,
            "commit_subjects": included_subjects,
        }
        if truncated:
            event["commit_subjects_truncated"] = True

        _append_event(event)

    return 0


# --------------------------------------------------------------------------
# post-merge mode
# --------------------------------------------------------------------------


def _handle_post_merge() -> int:
    """Emit 'merge-to-main' when the current branch is `main` (v1 scope).

    Exit code always 0 — observational.
    """
    producer = _resolve_producer_name()

    rc, out, _ = _git("symbolic-ref", "--short", "HEAD")
    if rc != 0:
        return 0
    current = out.strip()
    if current not in ("main",):
        return 0

    rc, out, _ = _git("rev-parse", "HEAD")
    if rc != 0:
        return 0
    sha = out.strip()

    subjects = _commit_subjects("HEAD~..HEAD", limit=5) or []
    files = _files_touched("HEAD~..HEAD") or []

    event = {
        "producer": producer,
        "event": "merge-to-main",
        "branch": "main",
        "sha": sha,
        "parent_sha": None,  # per §9 — merge-to-main doesn't carry parent
        "timestamp": _utc_now_iso(),
        "files_touched": files,
        "commit_subjects": subjects,
    }
    _append_event(event)
    return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Cross-substrate event emitter (pre-push / post-merge)."
    )
    parser.add_argument(
        "mode",
        choices=["pre-push", "post-merge"],
        help="Which git-hook mode to run.",
    )
    args = parser.parse_args(argv)

    try:
        if args.mode == "pre-push":
            stdin_text = sys.stdin.read() if not sys.stdin.isatty() else ""
            return _handle_pre_push(stdin_text)
        if args.mode == "post-merge":
            return _handle_post_merge()
    except Exception as exc:  # noqa: BLE001 - observational boundary
        _err(f"unexpected error: {exc}")
        return 0  # observational — never block the git operation

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
