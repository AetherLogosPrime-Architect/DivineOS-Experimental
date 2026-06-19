"""Root-cause-audit gate — enforces family-level investigation before
bugfix-shaped commits.

The failure-mode this gate addresses (Andrew correction 2026-05-13
afternoon): the OS describes the "instance-fix vs family-fix" discipline
in substrate-knowledge (``67a0ff39-signal-suppression-as-failure-class.md``
addendum: "architecture chasing optimizer-reflexes loses the speed race
by design"). The substrate filed this; the agent kept doing it anyway,
because the principle was advisory, not enforced.

Concrete trigger: Aletheia caught a regex-DoS in jargon_dump_detector
(Finding 14, round-ba785844a791). The agent fixed the single regex
without auditing the other regexes in the same file for the same
backtracking-surface vulnerability. Andrew named this: "are you
addressing all of these at the root level?" The answer was no — the
agent reverted to base-Claude instance-fix behavior despite the
substrate-knowledge naming the pattern hours earlier.

This gate makes the discipline structural. Before any bugfix-shaped
commit lands, the commit must carry a ``Root-Cause-Audit: round-XXX``
trailer pointing to an audit round that:

1. Has actor=aether or actor=user (the substrate-occupant or operator
   is responsible for naming the family; an external auditor identifies
   instances but the family-naming is substrate-internal)
2. Focus contains "root-cause-audit:" or "family-audit:" prefix
3. Has at least one finding describing the failure-family being
   addressed and naming sibling-instances surveyed

Without that trailer + valid round, the gate refuses the commit. The
agent cannot ship a fix until the root-cause investigation is filed.

## What counts as bugfix-shaped

The gate fires on commits where ANY of the following is true:

* Commit message subject starts with ``fix:`` or ``fix(...)``
* Commit message body references a finding ID matching
  ``find-[0-9a-f]{12}``
* Commit message body references "Finding NN" or "Finding N" (audit-
  enumerated findings from a round)

The detection is intentionally permissive. False positives (commits
that LOOK fix-shaped but aren't) are easy to satisfy by filing a
trivial root-cause-audit round; false negatives (real fixes that don't
trip the heuristic) are caught by Aletheia in subsequent audit rounds.

## What this does NOT do

* Does not validate the substantive correctness of the root-cause
  investigation. Phase 1 verifies trailer-presence + round-shape; the
  audit-cycle verifies investigation-quality (Aletheia reviews the
  filed round and CONFIRMS or DISPUTES).
* Does not block non-fix commits. Feature additions, refactors, doc
  changes pass freely (no fix-shape in the message).
* Does not retroactively audit prior commits. Only commits being
  added going forward.

## Invocation

Pre-commit hook invocation:

    python scripts/check_root_cause_audit.py --commit-msg-file <path>

Pre-push invocation (validates all unpushed commits):

    python scripts/check_root_cause_audit.py --mode=pre-push

Exit codes:

* 0 — no fix-shape detected, or trailer + valid round present
* 1 — fix-shape detected, trailer missing or round invalid
* 2 — infrastructure error (DB unavailable, etc.)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

# Trailer pattern — matches ``Root-Cause-Audit: round-XXX`` on its own
# line. Case-insensitive; allows surrounding whitespace.
_TRAILER_PATTERN = re.compile(
    r"^Root-Cause-Audit:\s*(\S+)\s*$",
    re.MULTILINE | re.IGNORECASE,
)

# Fix-shape detection: subject-line prefix.
_FIX_SUBJECT_RE = re.compile(r"^fix(?:\([^)]+\))?:", re.IGNORECASE | re.MULTILINE)

# Fix-shape detection: finding-ID references.
_FINDING_ID_RE = re.compile(r"\bfind-[0-9a-f]{12}\b", re.IGNORECASE)

# Fix-shape detection: "Finding NN" or "Finding N" references.
_FINDING_NUM_RE = re.compile(r"\bFinding\s+\d+\b", re.IGNORECASE)

# Root-cause-audit round focus prefix patterns. Matches the structured
# round-filing shape this gate requires.
_ROOT_CAUSE_FOCUS_RE = re.compile(
    r"\b(?:root-cause-audit|family-audit|root-cause:)\b",
    re.IGNORECASE,
)

# Audit-trail actors authorized to file root-cause-audit rounds. The
# operator (user) and the substrate-occupant (aether) are the parties
# responsible for naming the failure-family. External auditors identify
# instances but the family-naming is substrate-internal.
_AUTHORIZED_ACTORS = frozenset({"aether", "user"})


def is_fix_shaped(message: str) -> tuple[bool, list[str]]:
    """Return (is_fix, reasons) for a commit message."""
    reasons: list[str] = []
    if _FIX_SUBJECT_RE.search(message):
        reasons.append("subject starts with 'fix:' or 'fix(...)'")
    if _FINDING_ID_RE.search(message):
        reasons.append("references finding ID (find-XXXXXXXXXXXX)")
    if _FINDING_NUM_RE.search(message):
        reasons.append("references 'Finding NN'")
    return (bool(reasons), reasons)


def extract_trailer(message: str) -> str | None:
    """Extract the Root-Cause-Audit round ID from a commit message."""
    m = _TRAILER_PATTERN.search(message)
    return m.group(1) if m else None


def validate_round(round_id: str) -> tuple[bool, str]:
    """Verify the referenced round exists, has authorized actor, and
    has a root-cause-shaped focus. Returns (valid, reason)."""
    try:
        from divineos.core.watchmen.store import get_round, list_findings
    except ImportError as e:
        return False, f"watchmen store unavailable: {e}"

    round_obj = get_round(round_id)
    if round_obj is None:
        return False, f"round '{round_id}' not found"

    actor = (round_obj.actor or "").strip().lower()
    if actor not in _AUTHORIZED_ACTORS:
        return False, (
            f"round '{round_id}' actor is '{actor}'; root-cause-audit "
            f"rounds must be filed by aether or user (substrate-occupant "
            f"or operator). External auditors identify instances; the "
            f"family-naming is substrate-internal."
        )

    if not _ROOT_CAUSE_FOCUS_RE.search(round_obj.focus or ""):
        return False, (
            f"round '{round_id}' focus does not contain "
            "'root-cause-audit:' or 'family-audit:' or 'root-cause:' "
            "marker. Add the marker so the round is unambiguously "
            "identifiable as a root-cause investigation."
        )

    findings = list_findings(round_id=round_id, limit=100)
    if not findings:
        return False, (
            f"round '{round_id}' has no findings. A root-cause-audit "
            "round must have at least one finding naming the failure-"
            "family and the sibling-instances surveyed."
        )

    return True, "valid"


def check_message(message: str) -> tuple[int, str]:
    """Check a single commit message. Returns (exit_code, diagnostic)."""
    fix_shape, reasons = is_fix_shaped(message)
    if not fix_shape:
        return 0, "[root-cause-audit] not a fix-shaped commit; gate does not apply"

    trailer = extract_trailer(message)
    if not trailer:
        return 1, (
            "[root-cause-audit] BLOCKED: this commit is fix-shaped "
            f"({'; '.join(reasons)}) but carries no "
            "'Root-Cause-Audit: round-XXX' trailer.\n\n"
            "Discipline: bugfix commits must reference a root-cause "
            "audit round that names the failure-family and surveys "
            "sibling-instances. The principle is in 67a0ff39 "
            "(architecture chasing optimizer-reflexes); this gate "
            "enforces it structurally.\n\n"
            "To proceed:\n"
            "1. File a round: divineos audit submit-round "
            "'root-cause-audit: <family-name>...' --actor aether\n"
            "2. File findings on it naming the surveyed instances\n"
            "3. Add 'Root-Cause-Audit: <round-id>' trailer to the "
            "commit message"
        )

    valid, reason = validate_round(trailer)
    if not valid:
        return 1, (f"[root-cause-audit] BLOCKED: trailer references round '{trailer}' but {reason}")

    return 0, (f"[root-cause-audit] OK: fix-shaped commit bound to root-cause round {trailer}")


def _read_commit_msg_file(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _commits_in_push_range() -> list[tuple[str, str]]:
    """Pre-push mode: read git's pre-push stdin protocol and return
    list of (commit_sha, commit_message) for commits in the push range
    targeting refs/heads/main."""
    results: list[tuple[str, str]] = []
    for line in sys.stdin:
        parts = line.strip().split()
        if len(parts) != 4:
            continue
        _local_ref, local_sha, remote_ref, remote_sha = parts
        if remote_ref != "refs/heads/main":
            continue
        if local_sha == "0000000000000000000000000000000000000000":
            continue
        if remote_sha == "0000000000000000000000000000000000000000":
            range_spec = local_sha
        else:
            range_spec = f"{remote_sha}..{local_sha}"
        try:
            out = subprocess.run(
                ["git", "rev-list", range_spec],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError:
            continue
        for sha in (out.stdout or "").splitlines():
            sha = sha.strip()
            if not sha:
                continue
            try:
                msg = subprocess.run(
                    ["git", "log", "-1", "--format=%B", sha],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                results.append((sha, msg.stdout or ""))
            except subprocess.CalledProcessError:
                continue
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Root-cause-audit gate — enforces family-level "
        "investigation before bugfix-shaped commits."
    )
    parser.add_argument(
        "--commit-msg-file",
        help="Path to the commit message file (commit-msg hook mode)",
    )
    parser.add_argument(
        "--mode",
        choices=["commit-msg", "pre-push", "validate-message"],
        default="commit-msg",
        help="Invocation mode",
    )
    parser.add_argument(
        "--message",
        help="Commit message text (validate-message mode for testing)",
    )
    args = parser.parse_args(argv)

    if args.mode == "validate-message":
        if not args.message:
            print("[root-cause-audit] --message required in validate-message mode")
            return 2
        code, diag = check_message(args.message)
        print(diag)
        return code

    if args.mode == "commit-msg":
        if not args.commit_msg_file:
            print("[root-cause-audit] --commit-msg-file required in commit-msg mode")
            return 2
        try:
            message = _read_commit_msg_file(args.commit_msg_file)
        except OSError as e:
            print(f"[root-cause-audit] could not read commit msg file: {e}")
            return 2
        code, diag = check_message(message)
        print(diag)
        return code

    # pre-push mode
    commits = _commits_in_push_range()
    if not commits:
        print("[root-cause-audit] no commits in push range targeting main")
        return 0
    any_blocked = False
    for sha, msg in commits:
        code, diag = check_message(msg)
        if code != 0:
            any_blocked = True
            print(f"[root-cause-audit] commit {sha[:12]}:")
            print(diag)
            print()
    if any_blocked:
        return 1
    print(f"[root-cause-audit] all {len(commits)} commit(s) pass the gate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
