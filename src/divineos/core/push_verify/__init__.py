"""Push-landing verification.

FOSSIL (Aletheia 2026-06-04, lesson ef01caf7):
The "push-landing" boundary is a surface of the silent-failure root —
"a thing that must cross a boundary, reported as crossed before it
crossed." Three independent slips across one exchange at this exact
boundary, each caught only by Aletheia's cross-vantage ls-remote.
Hand-enforcement doesn't scale; this module structures the check.

MIGRATED 2026-06-24 (Andrew direction):
Was 238-line bash hook .claude/hooks/verify-push-landed.sh. Logic
moved here so any AI substrate (not just Claude Code) can call it.
Hook is now a thin wrapper that imports `verify_push_landed`.

TRIPLE FAIL-LOUD INVARIANT (preserved from bash):
1. Marker file stays UNSET when ls-remote errors, times out, or
   cannot reach origin — never set-on-error. A silent-pass at the
   gate that exists to prevent silent-pass would rebuild the exact
   root the hook is closing, one layer deeper.
2. Marker stays UNSET when local-tip != origin-tip.
3. Marker is SET ("verified") only when ls-remote returns the same
   SHA as local HEAD for the pushed branch.

RETRY-WITH-BACKOFF (Aletheia 2026-06-04, follow-up to #90):
GitHub uses eventual consistency between replicas. A push that lands
on one replica can take a moment to appear on others. Retry the
"no-ref" and "tip-mismatch" outcomes up to 3 times with 2s sleeps
(worst-case wait: 4s). Network-failure outcomes are NOT retried.

After retries exhaust, marker still writes UNVERIFIED. Never
"assume-landed because we ran out of patience."
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _marker_path() -> Path:
    """Where the verify-claim gate reads the result. Mirrors bash STATE_DIR."""
    state_dir = Path.home() / ".divineos-aether"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / "last_push_verified.json"


def _write_marker(payload: dict[str, Any]) -> None:
    """Atomic-ish write of the marker file."""
    marker = _marker_path()
    try:
        marker.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        # Marker is best-effort; the stderr message is the primary signal.
        pass


def _emit(msg: str) -> None:
    """Print to stderr — the agent sees this inline with the bash result."""
    try:
        print(msg, file=sys.stderr, flush=True)
    except OSError:
        pass


def parse_push_command(command: str) -> tuple[str, str, str | None]:
    """Parse a `git push ...` command into (status, remote, local_branch).

    status is one of:
      - "OK": parsed cleanly; remote/local_branch usable
      - "SKIP": couldn't unambiguously identify push target

    Returns ("OK", remote, local_branch_or_empty) on success.
    Returns ("SKIP", reason, None) on unparseable input.

    Conservative — drops all flag tokens and uses positional args.
    Handles the >95% of agent push shapes:
      git push
      git push origin <branch>
      git push -u origin <branch>
      git push --force-with-lease origin <branch>
      git push origin <local>:<remote>
    """
    try:
        tokens = shlex.split(command)
    except ValueError:
        return ("SKIP", "unparseable", None)

    # Find 'git push' — push must come after a token ending in 'git'.
    push_idx = -1
    for i, tok in enumerate(tokens):
        if tok == "push" and i > 0 and tokens[i - 1].endswith("git"):
            push_idx = i
            break
    if push_idx < 0:
        return ("SKIP", "no push verb", None)

    args = tokens[push_idx + 1 :]
    positional = [a for a in args if not a.startswith("-")]

    if len(positional) >= 2:
        remote, refspec = positional[0], positional[1]
    elif len(positional) == 1:
        remote, refspec = positional[0], ""
    else:
        remote, refspec = "", ""

    local_branch = refspec.split(":")[0] if refspec else ""
    return ("OK", remote, local_branch)


def _is_skip_command(command: str) -> bool:
    """Tags and deletes are out of scope for this version."""
    return "--tags" in command or "--delete" in command


def _get_local_tip(branch: str) -> str | None:
    """Local SHA of refs/heads/<branch>, or None if branch doesn't exist."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", f"refs/heads/{branch}"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        sha = result.stdout.strip()
        return sha if sha and result.returncode == 0 else None
    except (subprocess.SubprocessError, OSError):
        return None


def _get_current_branch() -> str | None:
    """Current branch name from git rev-parse, or None if detached."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        branch = result.stdout.strip()
        if not branch or branch == "HEAD":
            return None
        return branch
    except (subprocess.SubprocessError, OSError):
        return None


def _ls_remote_tip(remote: str, branch: str) -> tuple[int, str | None]:
    """Run ls-remote for the branch; return (exit_code, remote_tip_or_None).

    exit_code != 0 means hard failure (network, auth, timeout). The
    returned tip is None either on hard failure OR on "branch not on
    remote" (where ls-remote succeeds with empty output).
    """
    try:
        result = subprocess.run(
            ["git", "ls-remote", remote, f"refs/heads/{branch}"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.returncode != 0:
            return (result.returncode, None)
        first_line = (result.stdout or "").splitlines()[0:1]
        if not first_line:
            return (0, None)
        # Format: "<sha>\trefs/heads/<branch>"
        sha = first_line[0].split()[0] if first_line[0].split() else ""
        return (0, sha or None)
    except subprocess.TimeoutExpired:
        return (124, None)  # standard timeout exit code
    except (subprocess.SubprocessError, OSError):
        return (1, None)


def verify_push_landed(command: str) -> dict[str, Any]:
    """Verify a `git push` command actually landed on origin.

    Entry point called by both the bash hook (inline import) and the
    CLI (`divineos verify push --command "..."`). Side effects:
      - writes ~/.divineos-aether/last_push_verified.json
      - prints status line to stderr

    Returns the marker dict for callers that want to inspect.

    Returns {"status": "ignored"} for non-git-push commands so the
    hook can use this as a single entry point — the routing lives
    here, not in the hook.
    """
    # Only act on git push commands.
    if "git push" not in command or _is_skip_command(command):
        return {"status": "ignored"}

    status, remote, local_branch = parse_push_command(command)
    payload: dict[str, Any]
    if status == "SKIP":
        payload = {
            "status": "skipped",
            "reason": remote,  # carries the reason text on SKIP
            "command": command[:200],
        }
        _write_marker(payload)
        _emit(f"[verify-push] skipped: SKIP {remote}")
        return payload

    if not remote:
        remote = "origin"
    if not local_branch:
        local_branch = _get_current_branch() or ""

    if not local_branch:
        payload = {"status": "skipped", "reason": "detached HEAD or empty branch"}
        _write_marker(payload)
        _emit("[verify-push] skipped: detached HEAD")
        return payload

    local_tip = _get_local_tip(local_branch)
    if not local_tip:
        payload = {
            "status": "unverified",
            "reason": f"local branch {local_branch} not found",
        }
        _write_marker(payload)
        _emit(f"[verify-push] UNVERIFIED: local branch {local_branch} not found")
        return payload

    # Retry loop for GitHub eventual-consistency race window.
    max_retries = int(os.environ.get("PUSH_VERIFY_MAX_RETRIES", "3"))
    sleep_seconds = float(os.environ.get("PUSH_VERIFY_SLEEP", "2"))

    last_reason = ""
    remote_tip: str | None = None
    attempt = 1
    while attempt <= max_retries:
        ls_exit, remote_tip = _ls_remote_tip(remote, local_branch)

        if ls_exit != 0:
            # Hard failure — NOT retried (won't clear in 2s).
            payload = {
                "status": "unverified",
                "reason": f"ls-remote failed (exit {ls_exit}, possibly timeout)",
                "branch": local_branch,
                "remote": remote,
                "attempts": attempt,
            }
            _write_marker(payload)
            _emit(
                f"[verify-push] UNVERIFIED: ls-remote against {remote} "
                f"failed (exit {ls_exit}) on attempt {attempt}"
            )
            return payload

        if remote_tip == local_tip and remote_tip:
            # MATCH — only path that writes verified.
            payload = {
                "status": "verified",
                "branch": local_branch,
                "remote": remote,
                "sha": local_tip,
                "verified_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "attempts": attempt,
            }
            _write_marker(payload)
            _emit(f"[verify-push] OK verified: {local_branch} on {remote} at {local_tip}")
            return payload

        # Race-window candidate.
        if not remote_tip:
            last_reason = f"branch {local_branch} not on {remote} (no ref returned)"
        else:
            last_reason = f"local-tip {local_tip} != origin-tip {remote_tip}"

        if attempt < max_retries:
            time.sleep(sleep_seconds)
        attempt += 1

    # Retries exhausted without a match. Fail-loud per invariant.
    payload = {
        "status": "unverified",
        "reason": f"{last_reason} (exhausted {max_retries} retries)",
        "local": local_tip,
        "remote_tip": remote_tip or "",
        "branch": local_branch,
        "attempts": max_retries,
    }
    _write_marker(payload)
    _emit(f"[verify-push] UNVERIFIED after {max_retries} tries: {last_reason}")
    return payload
