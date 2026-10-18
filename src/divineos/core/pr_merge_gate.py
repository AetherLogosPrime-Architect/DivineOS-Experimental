"""PR-merge gate — block `gh pr merge` on guardrail-touching PRs without
a valid External-Review audit round.

## Why this exists

PR #50 (bandit, 2026-05-28) modified moral_compass.py (a guardrail file)
and merged without an External-Review trailer, producing a permanent red
Integrity Audit badge on main. Root cause: nothing checked the PR's file
list against the guardrail registry at merge-action time. The pre-merge
CI check fired red but GitHub didn't refuse the merge button.

Andrew 2026-05-28: the fix has to ship in the OS itself, not as an
operator-side GitHub branch-protection setting a fresh DivineOS install
would have to learn to flip. Clone the repo → discipline is inherited.

## Architecture

Thin doorman, same shape as deletion_discipline. The hook
(.claude/hooks/gh-pr-merge-gate.sh) reads the Bash command and asks
``block_reason()`` here for a verdict; the verdict comes from the
underlying check ``audit_pr_for_guardrail_touches()``. Per
[code-does-not-think]: the gate enforces that the audit-round-binding
was made, not whether it was wise.

## Falsifier

The gate should NOT fire when:
* The bash command is not a `gh pr merge`.
* The PR touches no guardrail files (lookup via guardrail_files.txt).
* The `gh pr merge` command's --body or --subject contains an
  ``External-Review: <round-id>`` trailer pointing at a valid round.

The gate SHOULD fire when:
* `gh pr merge <N>` is invoked AND the PR touches at least one
  guardrail file AND no External-Review trailer is in the command.

See prereg-b6dcddd005b0 for the falsifier and 30-day review.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

from divineos.core.command_match import at_command_position, strip_quoted

__guardrail_required__ = True

_GH_PR_MERGE_PATTERN = re.compile(r"\bgh\s+pr\s+merge\s+(\d+)\b")
# Trailer format (Phase 2, 2026-06-13):
#   External-Review: <round-id> [tree-hash:<40-hex>]
# Round-id is required; tree-hash suffix is optional during the
# transition window. The server-side CI gate verifies tree-hash
# when present; the local pre-merge gate only checks trailer
# presence and round validity (substance-binding happens at the
# CI layer, not here).
_TRAILER_PATTERN = re.compile(
    r"^External-Review:\s*(\S+)(?:\s+tree-hash:[a-f0-9]+)?",
    re.MULTILINE | re.IGNORECASE,
)
_GUARDRAIL_LIST_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "guardrail_files.txt"
)


def _load_guardrail_set() -> set[str]:
    if not _GUARDRAIL_LIST_PATH.exists():
        return set()
    out: set[str] = set()
    for line in _GUARDRAIL_LIST_PATH.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out.add(s)
    return out


def _pr_files(pr_number: int) -> list[str] | None:
    """Return the list of files in the PR via `gh pr view`.

    Returns None on any failure (gh missing, network error, bad PR
    number) — caller treats None as "cannot verify, fail-open".
    """
    try:
        proc = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--json", "files"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    files = data.get("files") or []
    return [
        (f.get("path") or "").replace("\\", "/")
        for f in files
        if isinstance(f, dict) and f.get("path")
    ]


def audit_pr_for_guardrail_touches(pr_number: int) -> tuple[bool, list[str]]:
    """Return (touches_guardrail, touched_file_list).

    ``touches_guardrail=False`` means either the PR is clean OR the file
    list could not be fetched (fail-open at the audit-data layer; the
    gate's job is to enforce the binding when it CAN see a touch, not
    to invent touches it can't observe).
    """
    files = _pr_files(pr_number)
    if not files:
        return False, []
    guardrails = _load_guardrail_set()
    touched = sorted(set(files) & guardrails)
    return bool(touched), touched


def pr_body_trailer(pr_number: int) -> str | None:
    """Return the round-id from the PR BODY's External-Review trailer, or None.

    Structural backing for knowledge 75cfce90 (documenting-as-doing), and the
    gap it was filed for. Everything else in this module checks a body we are
    ABOUT to write -- the `--body` of a `gh pr merge` invocation. Nothing
    checked the body already stored on the PR, which is what the CI fallback
    in scripts/ci_check_guardrail_trailer.sh actually greps when a commit
    carries no trailer of its own.

    WHY THAT GAP COST SOMETHING. PR #432's body said, in prose, "213b2dea
    touches four guardrail files ... and needs an External-Review trailer
    before merge." The CI fallback greps for a line STARTING `External-Review:`.
    Prose about a trailer is not a trailer, so the gate stayed red and I spent
    a session investigating a field I had authored myself. Aria found it by
    stubbing `gh` and running the real gate rather than reading the body and
    judging it satisfied.

    THE RULE THIS ENFORCES: when an artifact must satisfy a machine check, run
    the check the consumer runs. Reading the body and seeing the words
    "External-Review" proves nothing -- position matters, and only the regex
    knows about position.

    Deliberately reuses _TRAILER_PATTERN rather than writing a fifth copy of
    it. Four already exist (pr_merge_gate, push_ready, merge_review_gate,
    check_multi_party_review) and a fifth that drifted would reintroduce the
    class this function exists to catch.

    Returns None on any failure (gh missing, network, bad PR number) -- the
    caller cannot distinguish "no trailer" from "could not look", which is
    why this returns None rather than False. Absence of evidence is not
    evidence of absence, and that conflation is its own failure mode.
    """
    try:
        proc = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--json", "body"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    body = data.get("body")
    if not isinstance(body, str):
        return None
    match = _TRAILER_PATTERN.search(body)
    return match.group(1) if match else None


def _command_has_external_review_trailer(command: str) -> bool:
    """True if the bash command body contains an External-Review trailer.

    Looks at the whole command (which for a `gh pr merge ... --body
    "..."` invocation includes the body text). Pragmatic v1: we don't
    try to perfectly parse shell quoting; the trailer pattern is
    distinctive enough that regex on the raw command suffices.
    """
    return bool(_TRAILER_PATTERN.search(command))


def _find_usable_audit_round(pr_number: int, recency_days: int = 14) -> tuple[str | None, str, str]:
    """Task #114 (2026-06-09): look up whether a usable audit round
    exists that would let this PR's merge proceed, so the gate's block
    message can embed the ready-to-paste merge body inline instead of
    making the operator run a second command to find it.

    Returns a tuple ``(round_id, merge_body, diagnosis)``:
      - If a valid round exists: (round_id, merge_body, "")
      - If no valid round exists: (None, "", human-readable diagnosis
        naming the most-recent round's specific gap — missing
        user-CONFIRMS / missing AI-CONFIRMS / round is stale)

    "Valid" mirrors prepare-merge's checks exactly:
      1. round.status not closed
      2. ≥1 finding with actor=user, stance=CONFIRMS
      3. ≥1 finding with actor in external-AI set, stance=CONFIRMS
      4. round.created_at within recency_days

    Failures inside this helper are silent; the surrounding block_reason
    falls back to the long-form instructions.
    """
    try:
        from divineos.cli.audit_commands import _EXTERNAL_AI_ACTORS  # type: ignore
        from divineos.core.watchmen.store import list_findings, list_rounds
    except Exception:  # noqa: BLE001
        return None, "", ""

    try:
        rounds = list_rounds(limit=50)
    except Exception:  # noqa: BLE001
        return None, "", ""

    now = time.time()
    diagnosis_for_most_recent: str = ""
    most_recent_seen = False

    for rnd in rounds:
        try:
            round_id = getattr(rnd, "round_id", None) or getattr(rnd, "id", None)
            if not round_id:
                continue
            findings = list_findings(round_id=round_id, limit=500)
        except Exception:  # noqa: BLE001
            continue

        def _actor_of(f: object) -> str:
            val = getattr(f, "actor", "") or ""
            return str(val).lower()

        def _is_confirm(f: object) -> bool:
            stance = getattr(f, "review_stance", None)
            if stance is None:
                return True
            val = getattr(stance, "value", stance)
            return str(val).upper() == "CONFIRMS"

        # 2026-10-04: only confirms that name THIS PR count. Before, any round
        # with both confirms qualified, so merging #588 offered #582's round,
        # and pasting it would have said on main that a review covered a
        # change it never saw (Aletheia's most serious finding, three times).
        names_this_pr = re.compile(rf"CONFIRMS:\s*#{pr_number}\b", re.IGNORECASE)
        confirming = [
            f
            for f in findings
            if _is_confirm(f) and names_this_pr.search(str(getattr(f, "title", "") or ""))
        ]
        user_confirms = [f for f in confirming if _actor_of(f) == "user"]
        ai_confirms = [f for f in confirming if _actor_of(f) in _EXTERNAL_AI_ACTORS]
        if not confirming:
            continue

        created_at = getattr(rnd, "created_at", None) or getattr(rnd, "timestamp", None) or 0
        if isinstance(created_at, str):
            try:
                import datetime as _dt

                created_at = _dt.datetime.fromisoformat(
                    created_at.replace("Z", "+00:00")
                ).timestamp()
            except Exception:  # noqa: BLE001
                created_at = 0
        age_days = (now - float(created_at)) / 86400.0 if created_at else 999.0

        # Capture diagnosis for the FIRST (most recent) round, in case
        # nothing turns out valid further down.
        if not most_recent_seen:
            most_recent_seen = True
            if not user_confirms:
                diagnosis_for_most_recent = (
                    f"Most recent round '{round_id}' is missing a user-CONFIRMS finding."
                )
            elif not ai_confirms:
                diagnosis_for_most_recent = (
                    f"Most recent round '{round_id}' is missing an external-AI-CONFIRMS "
                    "finding (aletheia / grok / gemini)."
                )
            elif age_days > recency_days:
                diagnosis_for_most_recent = (
                    f"Most recent round '{round_id}' is {age_days:.1f}d old "
                    f"(recency window is {recency_days}d). Stale rounds cannot "
                    "authorize a new merge."
                )

        if not user_confirms or not ai_confirms or age_days > recency_days:
            continue

        # Valid round found — compose the ready-to-paste merge body.
        #
        # ROUND ONLY (2026-10-08). This used to add a tree-hash, so the body the
        # gate handed out repeated the very defect it should prevent. A squash
        # commit's tree is main plus the branch and cannot equal any tree known
        # before the merge, so the post-merge audit found no trailer tree-hash
        # matching and went red on a fully reviewed commit (#582, permanent). The
        # tree binding belongs on the pull request body, where the head's tree
        # exists.
        trailer = f"External-Review: {round_id}"
        focus = getattr(rnd, "focus", "") or f"PR #{pr_number} merge under audit"
        merge_body = (
            f"{focus}\n\n"
            f"Reviewed via audit round {round_id} "
            f"(operator-CONFIRMS + external-AI-CONFIRMS, age {age_days:.1f}d, "
            f"within {recency_days}d recency window).\n\n"
            f"{trailer}"
        )
        return round_id, merge_body, ""

    return None, "", diagnosis_for_most_recent


_TREE_HASH_AFTER_ROUND = re.compile(
    r"External-Review:\s*(\S+)\s+tree-hash:[a-f0-9]{7,40}", re.IGNORECASE
)
# The one expansion the gate can read: the literal heredoc it prints itself.
_LITERAL_HEREDOC = re.compile(
    r"\$\(\s*cat\s+<<-?\s*'(\w+)'.*?\n[ \t]*\1[ \t]*\n?[ \t]*\)", re.DOTALL
)


def _is_redirect_ampersand(text: str, i: int) -> bool:
    """An `&` that belongs to a redirect (`2>&1`, `>&2`, `&>file`), not to `&&` or a
    background `&`. Aria's cold read of #688: treating every `&` as the end of the
    statement let a redirect written before the body hide a variable behind it."""
    before = text[i - 1] if i > 0 else ""
    after = text[i + 1] if i + 1 < len(text) else ""
    return before in "<>" or after == ">"


def _message_is_unreadable(command: str, start: int) -> bool:
    """True if the `gh pr merge` statement beginning at `start` takes its
    message from somewhere the gate cannot read: something the shell would
    expand (a variable, a command substitution, a backtick) or a file.

    The gate reads the command's text. A body passed as "$B" is invisible to it:
    on 2026-10-17 two merges (#603, #679) went through with a tree-hash in their
    squash message because the gate saw `--body "$B"` and no trailer at all, and
    main's Integrity Audit went red on both. Single quotes are literal and pass;
    the heredoc the gate prints itself is literal and passes. The rule is an
    allowlist of what can be read, not a list of the ways to hide a message.

    The invariant it protects: every character of the message that reaches
    GitHub appears in the command's own text. Known to be unsound at one point:
    an ANSI-C string ($'...') ends the single-quote scan at an escaped quote
    (Aria's cold read of #688); no realistic merge needs that form.
    """
    text = _LITERAL_HEREDOC.sub("HEREDOC", command[start:])
    in_single = in_double = False
    i = 0
    while i < len(text):
        ch = text[i]
        if in_single:
            if ch == "'":
                in_single = False
        elif ch == "\\":
            i += 1
        elif ch == "'" and not in_double:
            in_single = True
        elif ch == '"':
            in_double = not in_double
        elif ch == "&" and not in_double and _is_redirect_ampersand(text, i):
            pass  # 2>&1, >&2, &>file: part of the statement, not the end of it
        elif not in_double and ch in ";&|\n":
            return False
        elif ch == "`":
            return True
        elif (
            ch == "$"
            and i + 1 < len(text)
            and (text[i + 1] in "{(_?$!#@*-'\"" or text[i + 1].isalnum())
        ):
            # $'...' decodes escapes (\x3a is a colon) and $"..." is translated text, so both
            # send characters the gate never saw. Aletheia's hold on #688, 2026-10-17.
            return True
        elif not in_double and (i == 0 or text[i - 1].isspace()):
            rest = text[i:]
            if re.match(r"(--body-file|-F)(?=[\s=]|$)", rest):
                return True
        i += 1
    return False


def block_reason(bash_command: str) -> str | None:
    """Verdict for the PreToolUse hook.

    Returns a denial message if the command is a guardrail-violating
    `gh pr merge`, else None. Fail-open on any error.
    """
    if not isinstance(bash_command, str) or not bash_command.strip():
        return None
    # Quote-scrubbed and command-position anchored: a gate that searches the
    # raw string cannot tell INVOKING this from MENTIONING it, and measured
    # 4 of 5 cases wrong (2026-08-22) -- grepping for the phrase, the phrase
    # in prose, in a string literal, and as an argument to another command all
    # matched. Its sibling gh-pr-ready-gate had already solved this inline
    # after the same defect blocked an `audit submit-round` whose focus text
    # described the transition; that solution was never extracted, so two
    # siblings kept the bug. It lives in command_match now.
    scrubbed = strip_quoted(bash_command)
    match = next(
        (
            m
            for m in _GH_PR_MERGE_PATTERN.finditer(scrubbed)
            if at_command_position(scrubbed, m.start())
        ),
        None,
    )
    if not match:
        return None
    try:
        pr_number = int(match.group(1))
    except ValueError:
        return None
    # A TREE-HASH IN THE SQUASH MESSAGE IS ALWAYS WRONG (2026-10-08, #582). The
    # tree of a squash commit is main plus the branch and does not exist until
    # the merge, so no value typed beforehand can match except by accident.
    # The pull request body is the right place for a tree-hash (the head's tree
    # exists there); the merge message carries the round only. This runs before
    # the guardrail question on purpose: the post-merge audit applies to
    # everything entering main now, not to a listed few.
    stamped = _TREE_HASH_AFTER_ROUND.search(bash_command)
    if stamped:
        return (
            f"BLOCKED: this merge message carries a tree-hash after the round "
            f"'{stamped.group(1)}'.\n\n"
            f"  A squash commit's tree is main plus the branch, and it does not exist "
            f"until the merge happens, so a tree-hash typed into the message can never "
            f"match it. The post-merge Integrity Audit then goes red on a reviewed "
            f"commit, and a red badge on main is permanent (#582, 2026-10-08).\n\n"
            f"  Use the round only:\n\n"
            f"      External-Review: {stamped.group(1)}\n\n"
            f"  The tree-hash belongs on the pull request body, where the head's tree "
            f"exists, and `divineos ship {pr_number}` composes the right message for you."
        )
    # A BODY THE GATE CANNOT READ IS A BODY IT CANNOT CHECK (2026-10-17, #603 and
    # #679). The check above reads the command's text; a message handed over as
    # "$B" or $(gh pr view ...) hides a tree-hash from it, and both of those
    # merges went red on main. Refuse what cannot be read, and name the way.
    if _message_is_unreadable(bash_command, match.start()):
        return (
            f"BLOCKED: this merge takes its message from something the gate cannot "
            f"read (a variable, a command substitution, a backtick or a file), so "
            f"it cannot check what the squash message will say.\n\n"
            f"  It reads the text of the command. A message built from a variable can "
            f"carry a tree-hash the gate would refuse if it could see it, and on "
            f"2026-10-17 two merges (#603, #679) did, and went red on main.\n\n"
            f"  Write the message out in full, as literal text in the command. This "
            f"shape is readable, and `divineos ship {pr_number}` prints the whole "
            f"command when it can:\n\n"
            f'  gh pr merge {pr_number} --squash --subject "<title> (#{pr_number})" '
            f"--body \"$(cat <<'EOF'\n"
            f"  <what changed and why>\n\n"
            f"  External-Review: <round-id>\n"
            f"  EOF\n"
            f'  )"\n\n'
            f"  The round only after External-Review, never a tree-hash: the "
            f"tree-hash belongs on the pull request body, the round on the squash."
        )
    try:
        touches, touched_files = audit_pr_for_guardrail_touches(pr_number)
    except Exception:  # noqa: BLE001
        return None
    if not touches:
        return None
    if _command_has_external_review_trailer(bash_command):
        return None
    file_list = "\n".join(f"      - {p}" for p in touched_files)

    # Task #114 (2026-06-09): try to embed the ready-to-paste merge body
    # inline so the operator doesn't have to run pr-merge-check separately.
    # Same shape as PR #117's gate-recovery-by-construction — when the
    # gate can compute its own remedy, it should hand it over instead
    # of making the operator chase it across two commands.
    try:
        round_id, merge_body, diagnosis = _find_usable_audit_round(pr_number)
    except Exception:  # noqa: BLE001
        round_id, merge_body, diagnosis = None, "", ""

    if round_id and merge_body:
        # Found a valid round — embed the ready-to-paste body.
        return (
            f"BLOCKED: PR #{pr_number} modifies guardrail file(s) but the merge "
            f"command carries no External-Review trailer.\n\n"
            f"  Guardrail files touched:\n{file_list}\n\n"
            f"  A valid audit round IS available — round '{round_id}' has the "
            f"required user-CONFIRMS + external-AI-CONFIRMS findings within the "
            f"14-day recency window. Retry the merge with this body:\n\n"
            f"  gh pr merge {pr_number} --squash --body \"$(cat <<'EOF'\n"
            f"{merge_body}\n"
            f"EOF\n"
            f'  )"\n\n'
            f"  (The External-Review trailer above satisfies the multi-party-review "
            f"CI check; that's the only thing the gate is enforcing.)"
        )

    # No valid round — fall back to the long-form instructions, but
    # name the SPECIFIC gap if there's a recent-but-invalid round.
    diagnosis_block = ""
    if diagnosis:
        diagnosis_block = f"\n  Diagnosis: {diagnosis}\n"

    return (
        f"BLOCKED: PR #{pr_number} modifies guardrail file(s) but the merge "
        f"command carries no External-Review trailer.\n\n"
        f"  Guardrail files touched:\n{file_list}\n"
        f"{diagnosis_block}\n"
        f"  Guardrail-touching PRs require multi-party External-Review "
        f"before merging into main. This gate enforces the binding at the "
        f"merge-action layer, structurally — so a fresh DivineOS install "
        f"inherits guardrail protection without operator-side configuration.\n\n"
        f"  Here is the way:\n"
        f"    1. File an audit round: divineos audit submit-round '...' "
        f"--actor user --source-ref <sha>\n"
        f"    2. Submit user-CONFIRMS finding (actor=user, severity=info, "
        f"stance=CONFIRMS).\n"
        f"    3. Submit external-AI-CONFIRMS finding (actor=aletheia / grok "
        f"/ gemini, stance=CONFIRMS).\n"
        f"    4. Run: divineos audit pr-merge-check {pr_number} "
        f"--audit-round <round-id>\n"
        f"       That command validates the round and emits the merge "
        f"body with the trailer.\n"
        f'    5. Paste the emitted body into your gh pr merge --body "..."\n\n'
        f"  See prereg-b6dcddd005b0 for the falsifier and review schedule."
    )
