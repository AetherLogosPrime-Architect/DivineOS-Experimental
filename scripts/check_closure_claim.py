#!/usr/bin/env python3
"""Closure-claim precommit gate.

Audit r9-21 round-3+ structural defense for the round-1/round-3
recurrence pattern (prereg-e30878ce3f09).

Background:
  Round 1 — I claimed Cyrillic homoglyph "fully closed" without
  verifying. The reviewer caught it.
  Round 3 — I claimed "0 unmarked orphans" without running the
  detector. Reviewer caught it again, eight commits later, with the
  round-1 lesson sitting in the substrate the whole time.

The lesson alone wasn't enough. The structural defense:

  When a commit message contains closure-claim phrasing, require
  evidence that a corresponding verifier was run within a recent
  window. If no recent verifier-run-log is present, block the commit
  with guidance.

What counts as a closure claim:

  * "X is closed", "X closed cleanly"
  * "0 unmarked", "no remaining", "all N findings closed"
  * "fully verified", "fully closed"
  * "verified clean", "no remaining surface"

What counts as a verifier run-log:

  * A line in ``~/.divineos/verifier_runs.jsonl`` recording a
    pytest, ruff, mypy, bandit, orphan-check, or other verification
    command run within the last ``_VERIFIER_FRESHNESS_MINUTES`` minutes.
  * Or a precommit-hook stamp from the same commit cycle (the
    precommit script writes a stamp when it runs successfully).

If no log is present, the gate prints what to run and exits
non-zero. Bypass with ``--no-verify`` if the operator explicitly
accepts the closure-claim-without-evidence shape (visible bypass,
not silent).

Usage as commit-msg hook (installed via setup-hooks):

    python scripts/check_closure_claim.py <commit-msg-file>

Standalone smoke test:

    python scripts/check_closure_claim.py --self-test
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
import time
from pathlib import Path

_VERIFIER_FRESHNESS_MINUTES = 30
_VERIFIER_LOG_PATH = Path.home() / ".divineos" / "verifier_runs.jsonl"

# Patterns that count as a closure claim. Word-boundaries and
# case-insensitive. A few of these are common enough that they
# need narrowing — "closed" alone is too broad, so we require it
# in a closure-claim context.
_CLOSURE_PATTERNS = (
    r"\bfully\s+closed\b",
    r"\bclosed\s+cleanly\b",
    r"\bno\s+remaining\s+(?:surface|orphans|findings|gaps)\b",
    r"\bzero\s+(?:remaining|unmarked|outstanding)\b",
    r"\b0\s+(?:remaining|unmarked|outstanding)\b",
    r"\ball\s+\d+\s+(?:findings|items|issues)\s+closed\b",
    r"\bfully\s+verified\b",
    r"\bverified\s+clean\b",
    r"\bcompletely\s+closed\b",
    r"\bdefinitively\s+closed\b",
    # External-review calibration tightening (recovered from old
    # 50d5fa2 via auditor 5th-pass finding 2026-05-04): the V1 patterns
    # caught the round-1 / round-3 audit-cleanup phrasings but missed
    # subsequent body-building commit-summary phrasings. Adding the
    # shapes the reviewer flagged so they bind on the next slip.
    # Allows optional adjective between count-word and noun ("all seven
    # friction points addressed" — adjective is "friction"), and
    # hyphenated nouns like "pre-regs".
    r"\ball\s+(?:\d+|\w+)(?:\s+\w+){0,2}\s+"
    r"(?:findings|points|defenses|fixes|items|tasks|issues|pre-?regs?|gates?|hooks?)\s+"
    r"(?:addressed|landed|closed|done|resolved|complete|filed|shipped)",
    r"\b(?:body-?building|cleanup|audit)\s+(?:done|complete|finished)\b",
    r"\beverything\s+(?:landed|closed|complete|done)\b",
)
_CLOSURE_RE = re.compile("|".join(_CLOSURE_PATTERNS), re.IGNORECASE)


def _has_recent_verifier_log() -> tuple[bool, str]:
    """Check if a verifier was run recently. Returns (ok, reason)."""
    if not _VERIFIER_LOG_PATH.exists():
        return False, f"no verifier log at {_VERIFIER_LOG_PATH}"
    cutoff = time.time() - _VERIFIER_FRESHNESS_MINUTES * 60
    try:
        with _VERIFIER_LOG_PATH.open(encoding="utf-8") as f:
            for line in reversed(list(f)):
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = entry.get("ts", 0)
                if ts >= cutoff:
                    cmd = entry.get("cmd", "?")
                    return True, f"recent verifier run: {cmd} at {entry.get('iso', ts)}"
    except OSError as e:
        return False, f"could not read verifier log: {e}"
    return False, f"no verifier run within last {_VERIFIER_FRESHNESS_MINUTES} minutes"


def _record_verifier_run(cmd: str) -> None:
    """Append a verifier-run log entry. Used by callers (precommit, manual)."""
    _VERIFIER_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.time(),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "cmd": cmd,
    }
    # Atomic append: write to tmp + os.replace for portability would be
    # over-engineered for an append-only newline-delimited log. The
    # standard append-mode write is durable enough; corruption only
    # hurts the freshness check, which fails-closed (no log = block).
    with _VERIFIER_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def find_closure_claims(commit_msg: str) -> list[str]:
    """Return all closure-claim phrases found in the commit message."""
    return [m.group(0) for m in _CLOSURE_RE.finditer(commit_msg)]


def check_commit(commit_msg: str) -> tuple[bool, str]:
    """Check a commit message for closure claims and verifier evidence.

    Returns (ok, message). ok=True means commit may proceed.
    """
    claims = find_closure_claims(commit_msg)
    if not claims:
        return True, ""
    has_log, reason = _has_recent_verifier_log()
    if has_log:
        return True, f"[closure-claim] {len(claims)} claim(s); {reason}"
    return False, (
        f"[closure-claim] BLOCKED — {len(claims)} closure claim(s) found:\n"
        + "\n".join(f"  * {c!r}" for c in claims)
        + f"\n\n{reason}\n\n"
        "Run a verifier (pytest, ruff, orphan check, bandit) and re-commit, OR\n"
        "rewrite the commit message to scope the closure to what was actually verified.\n"
        "Round-1 and round-3 audit slips both had this exact shape — the gate exists\n"
        "to make the verifier-first discipline structurally cheaper than skipping it.\n"
        "If you genuinely accept the closure-claim-without-evidence shape, use\n"
        "--no-verify on the commit (visible bypass; the audit ledger sees it)."
    )


def self_test() -> int:
    """Smoke test the detector + verifier-log machinery."""
    # Use a temp log path for isolation
    global _VERIFIER_LOG_PATH
    orig = _VERIFIER_LOG_PATH
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
        _VERIFIER_LOG_PATH = Path(tmp.name)
    try:
        # Empty log → closure-claim commit blocks
        ok, msg = check_commit("Audit r9-21 #X: thing fully closed.")
        assert not ok, "empty-log + closure-claim should block; got ok=True"

        # Stale log → still blocks
        _VERIFIER_LOG_PATH.write_text(
            json.dumps({"ts": time.time() - 7200, "cmd": "pytest"}) + "\n",
            encoding="utf-8",
        )
        ok, msg = check_commit("Audit thing fully closed.")
        assert not ok, "stale log should block"

        # Fresh log → passes
        _record_verifier_run("pytest tests/")
        ok, msg = check_commit("Audit thing fully closed.")
        assert ok, f"fresh log should pass; got: {msg}"

        # No closure claim → passes regardless
        _VERIFIER_LOG_PATH.unlink()
        ok, msg = check_commit("Just a normal commit message")
        assert ok, "non-closure message should always pass"

        print("self-test OK")
        return 0
    finally:
        if _VERIFIER_LOG_PATH.exists():
            _VERIFIER_LOG_PATH.unlink()
        _VERIFIER_LOG_PATH = orig


def main(argv: list[str]) -> int:
    args = argv[1:]
    if "--help" in args or "-h" in args or not args:
        print(__doc__)
        return 0
    if "--self-test" in args:
        return self_test()
    if "--record" in args:
        # `--record <cmd>` records a verifier run for the specified command
        idx = args.index("--record")
        cmd = args[idx + 1] if idx + 1 < len(args) else "manual"
        _record_verifier_run(cmd)
        print(f"[closure-claim] recorded verifier run: {cmd}")
        return 0

    # Commit-msg hook mode: argv[1] is the path to the commit message file
    msg_path = Path(args[0])
    if not msg_path.exists():
        print(f"[!] commit message file not found: {msg_path}", file=sys.stderr)
        return 2
    commit_msg = msg_path.read_text(encoding="utf-8", errors="replace")
    ok, info = check_commit(commit_msg)
    if info:
        print(info)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
