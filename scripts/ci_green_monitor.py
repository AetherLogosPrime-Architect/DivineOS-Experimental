"""CI green-transition monitor — complementary to the failure-only ci-monitor.

The Claude Code harness's built-in ci-monitor fires on CI check failures and
merge conflicts. It does NOT fire when a check transitions from failing to
passing. That's silence-is-success by design.

But when Andrew watches me push a fix and wants confirmation the fix worked,
he has to tell me "CI is green" manually — because the harness will only
break its silence to say "still broken." He named that cost 2026-07-13:
having to tell me things I could have been notified about.

This monitor closes that gap. It polls `gh pr checks` every 30s on all open
PRs Aether is the author of, tracks a compact per-PR state ("any non-pass
check outstanding?"), and emits ONE line when a PR transitions from
had-failures → all-green. That's the notification the harness doesn't send.

Emits only on the interesting transition. No noise for pending or already-green
PRs. Not a status board; just a "your fix worked" pinger.

State persists to ~/.divineos-aether/ci_green_state.json so restarts don't
re-emit for PRs that were already green when we came back up.

Falsifier for the fix (per prereg-<future>): if Andrew never has to tell me
"CI is green" over 30 days of normal PR-push activity, the monitor is doing
its job. If he still has to tell me, either it never fires (bug) or fires but
I don't act on the notification (different problem).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


DEFAULT_POLL_SECONDS = 30
DEFAULT_STATE_DIR = Path.home() / ".divineos-aether"
DEFAULT_STATE_FILE = DEFAULT_STATE_DIR / "ci_green_state.json"
DEFAULT_REPO = "AetherLogosPrime-Architect/DivineOS-Experimental"
DEFAULT_AUTHOR = "@me"


def _run_gh(args: list[str], timeout: float = 30.0) -> tuple[int, str, str]:
    """Run a gh CLI command, returning (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


def _list_open_prs(repo: str, author: str) -> list[dict]:
    """Return open PRs authored by `author` in `repo`."""
    code, out, err = _run_gh(
        [
            "pr",
            "list",
            "--repo",
            repo,
            "--author",
            author,
            "--state",
            "open",
            "--json",
            "number,headRefName,url",
            "--limit",
            "50",
        ]
    )
    if code != 0:
        # Silent-swallow OK here — networking hiccup, retry next poll.
        return []
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return []


def _pr_check_state(repo: str, pr_number: int) -> tuple[bool, list[dict]]:
    """Return (any_non_pass, checks) for a PR.

    any_non_pass=True means at least one check is failing, pending, or in an
    unknown non-pass bucket. any_non_pass=False means all checks report
    'pass' (or skipping, which we treat as effectively-pass).
    """
    code, out, err = _run_gh(
        [
            "pr",
            "checks",
            str(pr_number),
            "--repo",
            repo,
            "--json",
            "name,bucket,state",
        ]
    )
    if code != 0:
        return True, []  # Assume something's up if we can't read state.
    try:
        checks = json.loads(out)
    except json.JSONDecodeError:
        return True, []
    if not checks:
        return True, []  # No checks reported yet; treat as pending.
    any_non_pass = any(
        c.get("bucket") not in ("pass", "skipping") for c in checks
    )
    return any_non_pass, checks


def _load_state(state_file: Path) -> dict[str, bool]:
    """Load per-PR non-pass state. Key is str(pr_number)."""
    if not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(state_file: Path, state: dict[str, bool]) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _watch_parent_and_exit(initial_ppid: int, poll_seconds: float = 5.0) -> None:
    """Exit if the process that launched us dies. Same shape as subprocess_jobs
    watchdog — a shell-script parent dying shouldn't leave this poller running."""
    while True:
        try:
            os.kill(initial_ppid, 0)  # Unix: signal 0 = liveness check.
        except (ProcessLookupError, PermissionError, OSError):
            os._exit(1)
        time.sleep(poll_seconds)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Emit a line when a PR's CI transitions from failing to all-green.",
    )
    parser.add_argument("--repo", default=DEFAULT_REPO, help="owner/repo. Default: %(default)s")
    parser.add_argument("--author", default=DEFAULT_AUTHOR, help="PR author. Default: %(default)s (means logged-in user)")
    parser.add_argument("--poll-seconds", type=float, default=DEFAULT_POLL_SECONDS, help="Poll interval in seconds. Default: %(default)s")
    parser.add_argument("--state-file", default=str(DEFAULT_STATE_FILE), help="Where to persist per-PR state. Default: %(default)s")
    args = parser.parse_args(argv)

    state_file = Path(args.state_file)
    state = _load_state(state_file)

    # Emit an armed line so the Monitor tool user knows we started.
    print(
        f"[CI-GREEN-ARMED] watching {args.repo} PRs by {args.author} — "
        f"poll={args.poll_seconds}s state={state_file}",
        flush=True,
    )

    # Arm parent-death watchdog on non-Windows (Windows doesn't reparent).
    if os.name != "nt":
        import threading
        threading.Thread(
            target=_watch_parent_and_exit, args=(os.getppid(),), daemon=True
        ).start()

    while True:
        try:
            prs = _list_open_prs(args.repo, args.author)
        except subprocess.TimeoutExpired:
            time.sleep(args.poll_seconds)
            continue

        seen_prs: set[str] = set()
        for pr in prs:
            pr_number = pr.get("number")
            if pr_number is None:
                continue
            key = str(pr_number)
            seen_prs.add(key)
            try:
                any_non_pass, checks = _pr_check_state(args.repo, pr_number)
            except subprocess.TimeoutExpired:
                continue

            prev_any_non_pass = state.get(key, True)  # Default: assume it was non-green.

            if prev_any_non_pass and not any_non_pass:
                # Transition: had failures → all green. Emit.
                head = pr.get("headRefName", "?")
                url = pr.get("url", "")
                print(
                    f"[CI-GREEN] PR #{pr_number} ({head}) all checks passed — {url}",
                    flush=True,
                )

            state[key] = any_non_pass

        # Prune PRs that are no longer open (merged or closed).
        state = {k: v for k, v in state.items() if k in seen_prs}
        _save_state(state_file, state)

        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.exit(130)
