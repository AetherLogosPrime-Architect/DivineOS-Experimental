"""Structural backing for the push-landing verification boundary.

Aletheia 2026-06-04 (knowledge_id ef01caf7-...): the recurring slip across
THREE iterations in one exchange was honest-but-unverified about the push
actually landing — commit locally, launch background push, then assert the
push succeeded from felt-confidence rather than checking ``git ls-remote``.
The same shape hit again in this session: I treated background-task exit 0
as proof of push success, when the pre-push gate could be failing pytest
internally and rejecting the push while the harness still reported clean
exit on the wrapping shell.

This script is the "ALWAYS run" mechanical check. Given a branch name
and (optionally) an expected SHA, it queries ``git ls-remote origin <ref>``
and compares against local HEAD or the provided expected SHA. Exit 0 only
if they match. Non-zero with diagnostic on mismatch or any failure.

## Usage

    # Verify branch's remote tip matches local HEAD
    python scripts/verify_push_landed.py --branch fix/my-branch

    # Verify branch's remote tip equals a specific SHA
    python scripts/verify_push_landed.py --branch fix/my-branch --expected-sha 9d8c72de

    # Print only the remote SHA (for scripting)
    python scripts/verify_push_landed.py --branch fix/my-branch --print-only

## Why not a git hook

A local post-push hook would only help the operator who configured it.
The verification needs to be surfaceable to ANY caller — CI, a workflow,
the agent's own post-push verification step — so it lives as a script
that all of them can invoke uniformly.
"""

from __future__ import annotations

import argparse
import subprocess
import sys


def remote_sha(branch: str, remote: str = "origin") -> str | None:
    """Return the SHA at remote/<branch>, or None if the ref doesn't exist.

    Uses ``git ls-remote <remote> refs/heads/<branch>`` — the canonical
    network-truth source. ``git fetch`` is NOT used here on purpose: the
    point is to read the remote's authoritative current state, not the
    locally-cached refs/remotes/origin/<branch>.
    """
    result = subprocess.run(
        ["git", "ls-remote", remote, f"refs/heads/{branch}"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return None
    line = result.stdout.strip().split("\n")[0] if result.stdout.strip() else ""
    if not line:
        return None
    sha = line.split(maxsplit=1)[0].strip()
    return sha or None


def local_head_sha() -> str | None:
    """Return the current HEAD SHA, or None on failure."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify a remote branch tip matches local HEAD (or an expected "
            "SHA). Exit 0 only on match. Backing for obligation "
            "ef01caf7 (Aletheia 2026-06-04 push-landing verification)."
        )
    )
    parser.add_argument("--branch", required=True, help="Branch name to verify.")
    parser.add_argument(
        "--remote", default="origin", help="Remote name (default: origin)."
    )
    parser.add_argument(
        "--expected-sha",
        default=None,
        help="SHA the remote should be at. If omitted, uses local HEAD.",
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Print the remote SHA and exit 0 (no comparison).",
    )
    args = parser.parse_args(argv)

    rsha = remote_sha(args.branch, args.remote)
    if args.print_only:
        if rsha is None:
            print(f"REMOTE_REF_MISSING: {args.remote}/{args.branch}", file=sys.stderr)
            return 2
        print(rsha)
        return 0
    if rsha is None:
        print(
            f"VERIFY-FAIL: {args.remote}/{args.branch} does not exist on remote. "
            "The push likely did not land (pre-push gate may have rejected, "
            "or the push command itself failed silently).",
            file=sys.stderr,
        )
        return 1

    expected = args.expected_sha or local_head_sha()
    if expected is None:
        print(
            "VERIFY-FAIL: could not resolve expected SHA "
            "(no --expected-sha passed and `git rev-parse HEAD` failed).",
            file=sys.stderr,
        )
        return 1

    # Match against full SHA or any unique prefix (so callers can pass short SHAs).
    if rsha == expected or rsha.startswith(expected) or expected.startswith(rsha):
        print(
            f"VERIFY-OK: {args.remote}/{args.branch} = {rsha} "
            f"(matches expected {expected})"
        )
        return 0
    print(
        f"VERIFY-FAIL: {args.remote}/{args.branch} = {rsha}\n"
        f"              expected = {expected}\n"
        "The remote does not match what was expected — the push did not land "
        "(or landed at a different commit). Do NOT report the push as "
        "successful until the SHAs match.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
