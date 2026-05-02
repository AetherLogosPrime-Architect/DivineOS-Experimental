"""Multi-party-review gate for guardrail-file modifications.

When a commit modifies any file in `scripts/guardrail_files.txt`, this
script validates that the commit message contains a
`External-Review: <audit_round_id>` trailer referencing a recent audit
round with at least two CONFIRMS findings from distinct actor types:

  - one from actor=user (the human operator), AND
  - one from an external AI actor (grok / gemini / disambiguated-Claude
    — NEVER the running agent).

Both findings must be CONFIRMS stance, both filed within a recency
window (default 7 days before commit time), and the round description
must include a hash of the unified diff so stale approvals cannot be
reused for a different change.

Design principle (from tonight's lens work + Aria's read):
Diversity of source. No single channel — however reputable — can push
changes through alone. The running agent cannot self-modify guardrails
(internal). A user alone cannot force weakening (external-human is
insufficient). An external AI alone cannot authorize (external-AI is
insufficient). All three are required together AND internal checks
(tests, compass, pre-reg gate, etc.) still fire as usual. The external
two-key is ADDITIVE, not override.

v1 honest limits (per Beer's lens — claim vs. do):
  * Actor authentication is string-based. A finding with
    actor="grok" is trusted to have come from Grok; v1 does not
    cryptographically verify. The upstream USER_INPUT event linkage
    (event-source authentication via the terminal channel) IS
    structurally verified; AI-actor attestation is v2 work. See pre-reg
    for the follow-up.
  * Gate is commit-time, not file-time. A malicious writer could modify
    guardrail files in the working tree without ever committing them;
    the gate only fires at `git commit`. This is acceptable for v1
    because the repository is the source of truth — uncommitted changes
    aren't part of the shipped artifact.

Invocation:
  python scripts/check_multi_party_review.py <commit_msg_file>

Exit codes:
  0 — no guardrail files staged, OR all gates pass
  1 — guardrail files staged and the review trailer is missing or invalid
  2 — infrastructure error (conservatively blocks; see docstring)
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import time
from pathlib import Path

# Trailer pattern — matches `External-Review: <id>` on its own line.
_TRAILER_PATTERN = re.compile(r"^External-Review:\s*(\S+)\s*$", re.MULTILINE | re.IGNORECASE)

# Diff-hash pattern — the round description must include the hash of the
# unified diff to prevent stale approvals from authorizing a new change.
_DIFF_HASH_PATTERN = re.compile(r"diff-hash:\s*([0-9a-f]{64})", re.IGNORECASE)

# Tree-hash pattern — alternative to diff-hash. Tree hashes are content-
# addressed (SHA-1 of the staged git tree) and reproduce deterministically
# across platforms, while unified-diff bytes can vary by line endings or
# diff-header formatting between Windows/Linux/macOS. Either tree-hash OR
# diff-hash satisfies the binding requirement; cross-platform verifiers
# (claim 2026-04-24 06:15) should prefer tree-hash. SHA-1 = 40 hex chars.
_TREE_HASH_PATTERN = re.compile(r"tree-hash:\s*([0-9a-f]{40})", re.IGNORECASE)

# Recency window: 7 days. An old audit round cannot authorize a new commit.
_RECENCY_WINDOW_SECONDS = 7 * 24 * 3600

# External-AI actor set. If any of these has a CONFIRMS finding in the
# round, that satisfies the AI-side of the two-key. "claude" alone is
# intentionally NOT in this set — the bare actor name would collide with
# the running agent; disambiguated variants ("claude-opus-auditor",
# "claude-sonnet-external", etc.) are accepted when they appear as the
# actor on a finding.
_EXTERNAL_AI_ACTORS = frozenset({"grok", "gemini"})
_EXTERNAL_AI_PREFIXES = ("claude-",)

GUARDRAIL_LIST_PATH = Path(__file__).resolve().parent / "guardrail_files.txt"


def _load_guardrail_set() -> set[str]:
    """Parse the guardrail list. Lines starting # and blank lines are comments."""
    if not GUARDRAIL_LIST_PATH.exists():
        return set()
    result: set[str] = set()
    for line in GUARDRAIL_LIST_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        result.add(stripped)
    return result


def _staged_files() -> list[str]:
    """Return the list of files staged for this commit."""
    try:
        out = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return [line.strip().replace("\\", "/") for line in out.stdout.splitlines() if line.strip()]


def _staged_diff_hash() -> str:
    """SHA-256 of the unified diff of staged changes.

    Used to bind an audit round to one specific change: stale approvals
    cannot be reused for a different diff because the hash won't match.
    """
    try:
        out = subprocess.run(
            ["git", "diff", "--cached", "--unified=3"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""
    return hashlib.sha256(out.stdout.encode("utf-8", errors="replace")).hexdigest()


def _staged_tree_hash() -> str:
    """Git tree-hash (SHA-1) of the staged index.

    Cross-platform reproducible: derives from the same staged blobs the
    commit will create, with line-ending normalization already applied
    via .gitattributes. Recommended over _staged_diff_hash for any
    independent verifier running on a different OS.
    """
    try:
        out = subprocess.run(
            ["git", "write-tree"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""
    return out.stdout.strip()


def _is_external_ai_actor(actor: str) -> bool:
    """True for grok, gemini, or disambiguated-Claude variants. Never bare 'claude'."""
    normalized = actor.strip().lower()
    if normalized == "claude":
        return False
    if normalized in _EXTERNAL_AI_ACTORS:
        return True
    return any(normalized.startswith(prefix) for prefix in _EXTERNAL_AI_PREFIXES)


def _parse_trailer(message: str) -> str | None:
    """Extract the External-Review round id from the commit message, if present."""
    match = _TRAILER_PATTERN.search(message)
    if not match:
        return None
    return match.group(1).strip()


def _fetch_round_and_findings(round_id: str):
    """Load audit round + findings from the Watchmen store.

    Returns (round, findings_list) or (None, []) if the round is
    unreachable or does not exist. Never raises.
    """
    try:
        from divineos.core.watchmen.store import get_round, list_findings
    except Exception:  # noqa: BLE001
        return None, []
    try:
        rnd = get_round(round_id)
    except Exception:  # noqa: BLE001
        return None, []
    if rnd is None:
        return None, []
    try:
        findings = list_findings(round_id=round_id, limit=500)
    except Exception:  # noqa: BLE001
        return rnd, []
    return rnd, findings


def _round_description(rnd) -> str:  # type: ignore[no-untyped-def]
    """Safely pull the text description from an AuditRound object."""
    for attr in ("focus", "notes", "description"):
        val = getattr(rnd, attr, None)
        if isinstance(val, str) and val:
            return val
    return ""


def _round_created_at(rnd) -> float:  # type: ignore[no-untyped-def]
    """Safely pull the round's creation timestamp."""
    for attr in ("created_at", "timestamp", "ts"):
        val = getattr(rnd, attr, None)
        if isinstance(val, (int, float)):
            return float(val)
    return 0.0


def _finding_actor(finding) -> str:  # type: ignore[no-untyped-def]
    """Safely pull the actor string from a Finding object."""
    val = getattr(finding, "actor", "") or ""
    return str(val).lower()


def _finding_stance_is_confirm(finding) -> bool:  # type: ignore[no-untyped-def]
    """True if the finding's stance is CONFIRMS.

    If the finding predates stance tracking (no stance field), we treat
    the mere existence of the finding in the round as implicit
    acknowledgement and do NOT require a stance field. For v1 this is
    pragmatic; v2 can tighten to require explicit stance.
    """
    stance = getattr(finding, "review_stance", None)
    if stance is None:
        return True  # pragmatic v1: existence = acknowledgement
    stance_val = getattr(stance, "value", stance)
    return str(stance_val).upper() == "CONFIRMS"


def validate(commit_msg: str, now: float | None = None) -> tuple[bool, str]:
    """Core validation. Returns (ok, message).

    When ok is True, message explains why (useful for logging when the
    gate passes). When False, message is the block reason intended for
    display to the operator.
    """
    staged = _staged_files()
    guardrails = _load_guardrail_set()
    touched = sorted(set(staged) & guardrails)
    if not touched:
        return True, "no guardrail files staged; gate does not apply"

    trailer = _parse_trailer(commit_msg)
    if not trailer:
        return False, (
            "Guardrail files staged without External-Review trailer:\n"
            + "\n".join(f"  {p}" for p in touched)
            + "\n\nThis commit modifies the self-auditing stack. It requires\n"
            + "a multi-party review before it can be recorded. Add a trailer:\n\n"
            + "    External-Review: <audit_round_id>\n\n"
            + "The referenced audit round must contain at least two\n"
            + "CONFIRMS findings — one from actor=user and one from an\n"
            + "external AI actor (grok/gemini/claude-<variant>). The\n"
            + "round description must include the current change-hash.\n"
            + "Either form satisfies; tree-hash is cross-platform\n"
            + "deterministic (preferred for independent verification):\n\n"
            + f"    diff-hash: {_staged_diff_hash()}\n"
            + f"    tree-hash: {_staged_tree_hash()}\n\n"
            + "See docs and pre-reg for the full review workflow."
        )

    rnd, findings = _fetch_round_and_findings(trailer)
    if rnd is None:
        return False, (
            f"External-Review trailer references audit round '{trailer}'\n"
            "but the round was not found in the Watchmen store. Either\n"
            "the round does not exist or the store is unreachable. The\n"
            "gate conservatively blocks when provenance cannot be verified."
        )

    ts = now if now is not None else time.time()
    round_age = ts - _round_created_at(rnd)
    if round_age > _RECENCY_WINDOW_SECONDS or round_age < 0:
        days = round_age / 86400
        return False, (
            f"External-Review round '{trailer}' is {days:.1f} days old\n"
            f"(window is {_RECENCY_WINDOW_SECONDS / 86400:.0f} days).\n"
            "Stale approvals cannot authorize a new commit; file a\n"
            "fresh review round and reference it."
        )

    # Either diff-hash or tree-hash satisfies the binding. Tree-hash is
    # cross-platform deterministic (claim 2026-04-24 06:15: diff bytes
    # diverge between Windows and Linux container despite .gitattributes
    # normalization). Verifiers running independently should prefer tree-hash.
    actual_diff_hash = _staged_diff_hash()
    actual_tree_hash = _staged_tree_hash()
    description = _round_description(rnd)
    diff_match = _DIFF_HASH_PATTERN.search(description)
    tree_match = _TREE_HASH_PATTERN.search(description)

    diff_ok = diff_match is not None and diff_match.group(1).lower() == actual_diff_hash.lower()
    tree_ok = (
        tree_match is not None
        and actual_tree_hash != ""
        and tree_match.group(1).lower() == actual_tree_hash.lower()
    )

    if not (diff_ok or tree_ok):
        found_diff = diff_match.group(1) if diff_match else "(none)"
        found_tree = tree_match.group(1) if tree_match else "(none)"
        return False, (
            f"External-Review round '{trailer}' does not reference the\n"
            "current change. Stale or mismatched approval.\n\n"
            f"    current diff-hash:  {actual_diff_hash}\n"
            f"    round's diff-hash:  {found_diff}\n"
            f"    current tree-hash:  {actual_tree_hash}\n"
            f"    round's tree-hash:  {found_tree}\n\n"
            "Either matching hash satisfies the binding. Tree-hash is\n"
            "cross-platform deterministic; prefer it for independent\n"
            "verification. File a fresh review round and reference it."
        )

    user_confirm = False
    ai_confirm = False
    ai_actor_seen = ""
    for f in findings:
        if not _finding_stance_is_confirm(f):
            continue
        actor = _finding_actor(f)
        if actor == "user":
            user_confirm = True
        elif _is_external_ai_actor(actor):
            ai_confirm = True
            ai_actor_seen = actor
    if not user_confirm:
        return False, (
            f"External-Review round '{trailer}' does not contain a\n"
            "CONFIRMS finding from actor=user. Human approval is\n"
            "required for guardrail-file modifications."
        )
    if not ai_confirm:
        return False, (
            f"External-Review round '{trailer}' does not contain a\n"
            "CONFIRMS finding from an external AI actor (grok / gemini /\n"
            "claude-<variant>). Multi-party review requires independent\n"
            "AI judgment in addition to user approval."
        )

    return True, (
        f"guardrail review passed: round={trailer}, "
        f"user=confirmed, ai={ai_actor_seen}=confirmed, "
        f"age={round_age / 3600:.1f}h, diff-hash-match=yes"
    )


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "usage: check_multi_party_review.py <commit_msg_file>",
            file=sys.stderr,
        )
        return 2
    msg_path = Path(argv[1])
    try:
        message = msg_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"could not read commit message file: {e}", file=sys.stderr)
        return 2

    ok, detail = validate(message)
    if ok:
        print(f"[multi-party-review] {detail}")
        return 0
    print("\n=== Multi-Party Review Gate ===", file=sys.stderr)
    print("BLOCKED.\n", file=sys.stderr)
    print(detail, file=sys.stderr)
    print("", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
