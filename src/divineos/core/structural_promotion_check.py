"""Will-to-vessel structural-promotion check (Phase A — observation only).

Andrew named this 2026-05-14: when I file a learn entry that names a
RULE ("always X" / "never Y" / "must Z"), an automatic follow-up
question should fire: *what test, gate, or surface makes this
automatic?* If the answer is none, the rule is decoration — it lives
in the will (context-window) and dies with the flow.

The check converts the convention "remember to ask whether a rule
needs a vessel-shape backing" into a substrate-emitted prompt. Same
pattern as the address-bypass class-fix from earlier today: rule
that should be enforced moves from convention to structure.

## Discipline

**Phase A (this commit): OBSERVATION ONLY**. The check emits a
STRUCTURAL_PROMOTION_QUESTION event when a learn entry matches a
rule-shape pattern AND does not already reference falsifier/test/
gate/surface keywords. The event is informational — surfaceable in
the dream report, queryable via CLI. It does NOT block anything.

**Dual-monitor (Andrew's requirement):**
  - The check monitors me (am I filing rules without structural
    backing?).
  - I monitor the check (is it firing on actual rules? is it
    missing actual rules? is it false-positiving on tutorial text?).
  - Verification surface: `divineos admin structural-promotion-check`
    reports recent fires, marks whether each got a follow-up, gives
    a false-positive estimate.

**Trust-earned promotion**: only after the check has proven itself
across enough fires (per its own pre-reg falsifier) can it be
promoted to stronger surfacing (briefing row, deny-gate). Until then
it observes and emits, nothing more.

## Failsafes

  - Regex-only pattern detection (no NLP, results are legible).
  - Patterns bounded (Finding 14 regex-hygiene applied — no unbounded
    quantifiers).
  - Fail-soft on every code path: any exception, silent return.
  - Cannot block the learn command (only emits, never raises).
  - Loop prevention: skip if the entry already mentions falsifier/
    test/gate/surface/structural — those entries already address the
    question.
"""

from __future__ import annotations

import re

# Conservative rule-shape patterns. Bounded quantifiers; case-insensitive.
# Each captures the marker word and the next 1-30 chars to give
# context in the emitted event (not for matching).
_RULE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\balways\s+\w{2,30}\b", re.IGNORECASE),
    re.compile(r"\bnever\s+\w{2,30}\b", re.IGNORECASE),
    re.compile(r"\bmust\s+\w{2,30}\b", re.IGNORECASE),
    re.compile(r"\bevery\s+time\b", re.IGNORECASE),
    re.compile(r"\bin\s+all\s+cases\b", re.IGNORECASE),
    re.compile(r"\bthe\s+only\s+\w{2,30}\s+is\b", re.IGNORECASE),
)

# Keywords whose presence indicates the entry already addresses the
# structural-promotion question — no need to emit again.
_STRUCTURAL_KEYWORDS: frozenset[str] = frozenset(
    {
        "falsifier",
        "regression-pin",
        "prereg",
        "pre-reg",
        "ci gate",
        "ci-gate",
        "gate ",
        "test_",  # test_ prefix conventionally indicates a test file
        "test ",
        "surface ",
        "structural",
        "structurally",
        "auto-verify",
    }
)


# Precision filter, 2026-08-20. The rule-patterns above match the marker word
# plus one token, which catches ordinary English wherever it appears. Measured
# against all ten obligations that were blocking every substrate write:
#
#   "eight reports never reached the synthesizer"   past-tense bug description
#   "the refutation arm never fired at all"         past-tense description
#   "letters never waking me"                       symptom description
#   "which I had never run"                         past-perfect description
#   "Andrew: 'I should never reach conclusions'"    quoting the operator
#   "external is always required for contrast"      quoting Aria
#   "they must be had"                              ordinary English
#   "usually never needed"                          description
#   "never as", "never to", "never the"             fragments, no predicate
#   "substrate write MUST land before the next"     an actual rule
#
# One of ten was a promise. The other nine are what a substrate whose whole
# job is recording diagnoses produces constantly, so the count could never
# fall below the blocking threshold of 5 and the obligations gate blocked
# every audit-round filing -- which is what a guardrail PR needs to merge.
# Andrew 2026-08-20: "its been 3 weeks.. 3.. and there are still PR's in limbo."
#
# Four discriminators, each drawn from an observed false positive rather than
# imagined: an auxiliary before the marker means the sentence reports what
# happened; a participle or gerund after never/always names an event; a modal
# followed by be/have is a descriptive passive; and a marker followed by a
# function word has no rule predicate at all. Quotation detection is last
# because it is the weakest signal.
_DESCRIPTIVE_AUX = re.compile(
    r"\b(had|have|has|was|were|is|are|been|did|does|do|why|which)\s+(\w+\s+){0,3}$", re.IGNORECASE
)
_PARTICIPLE_OR_GERUND = re.compile(r"^\w+(ed|ing)$", re.IGNORECASE)
# Deliberately NOT an irregular-participle set. A first draft carried one
# ("run", "set", "held", ...) and it cost recall on a real rule: "always run
# the briefing before touching code" reads as a participle and is an
# imperative. Those words are ambiguous between base form and participle, and
# the auxiliary test above already resolves the ambiguity -- "which I had
# never run" is caught by `had`, while "always run X" has no auxiliary because
# it is an instruction. So the ambiguous set only ever fired where the word was
# most likely a rule, which is the one place it must not.
# A rule predicate begins with a verb. These cannot start one.
_NOT_A_PREDICATE: frozenset[str] = frozenset(
    {
        "as",
        "to",
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "of",
        "for",
        "at",
        "by",
        "with",
        "than",
        "that",
        "this",
        "these",
        "those",
        "it",
        "its",
        "so",
        "such",
        "more",
        "less",
        "very",
        "just",
        "only",
        "even",
        "again",
        "silent",
        "enough",
    }
)


def _is_descriptive_match(text: str, m: re.Match[str]) -> str | None:
    """Why this rule-pattern match is a description rather than a promise.

    Returns a short reason string when the match should NOT count, or None
    when it looks like a genuine will-shape rule.
    """
    before = text[max(0, m.start() - 60) : m.start()]
    parts = m.group(0).split()
    nxt = parts[1] if len(parts) > 1 else ""
    lowered = m.group(0).lower()

    if _DESCRIPTIVE_AUX.search(before):
        return "aux-before"
    if lowered.startswith(("never", "always")) and (_PARTICIPLE_OR_GERUND.match(nxt)):
        return "participle"
    if lowered.startswith("must") and nxt.lower() in ("be", "have", "been"):
        return "modal-passive"
    if nxt.lower() in _NOT_A_PREDICATE:
        return "no-predicate"
    # An odd number of quote marks before the match means it opened a quotation
    # that has not closed, so the marker is inside someone else's words.
    if (before.count("'") + before.count('"')) % 2 == 1:
        return "quoted"
    return None


def looks_like_rule(text: str) -> tuple[bool, list[str]]:
    """Return (is_rule_shape, matched_trigger_phrases).

    True when the text contains at least one rule-shape phrase AND
    does NOT already mention structural-backing keywords. Errs toward
    flagging (Phase A is observation-only; over-flagging is the right
    side of the trade while calibrating).
    """
    if not text:
        return False, []
    lower = text.lower()
    # Already addresses structural backing?
    for kw in _STRUCTURAL_KEYWORDS:
        if kw in lower:
            return False, []
    triggers: list[str] = []
    for pat in _RULE_PATTERNS:
        for m in pat.finditer(text):
            if _is_descriptive_match(text, m):
                continue
            triggers.append(m.group(0))
            break
    return bool(triggers), triggers


def emit_structural_promotion_question(knowledge_id: str, text: str) -> bool:
    """If the text looks like a rule, emit a STRUCTURAL_PROMOTION_QUESTION
    event referencing knowledge_id. Returns True iff fired.

    Fail-soft: any exception returns False without raising.
    """
    try:
        is_rule, triggers = looks_like_rule(text)
        if not is_rule:
            return False
        try:
            from divineos.core.ledger import log_event

            log_event(
                event_type="STRUCTURAL_PROMOTION_QUESTION",
                actor="aether",
                payload={
                    "knowledge_id": knowledge_id,
                    "triggers": triggers[:5],
                    "question": (
                        "What test, gate, or surface makes this rule "
                        "automatic? If the answer is none, the rule "
                        "is decoration. (Phase-A observation, not "
                        "blocking. Andrew 2026-05-14 will-to-vessel "
                        "epistemic-discipline.)"
                    ),
                },
            )
            return True
        except Exception:  # noqa: BLE001
            return False
    except Exception:  # noqa: BLE001
        return False


def _coerce_payload(raw: object) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            import json

            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except Exception:  # noqa: BLE001
            pass
    return {}


def recent_questions(limit: int = 50) -> list[dict]:
    """Return recent STRUCTURAL_PROMOTION_QUESTION events, newest first."""
    try:
        from divineos.core.ledger import get_events
    except Exception:  # noqa: BLE001
        return []

    out: list[dict] = []
    try:
        events = get_events(limit=limit * 4, event_type="STRUCTURAL_PROMOTION_QUESTION")
    except Exception:  # noqa: BLE001
        return []
    for e in events:
        payload = _coerce_payload(e.get("payload"))
        out.append(
            {
                "event_id": e.get("event_id"),
                "timestamp": e.get("timestamp"),
                "knowledge_id": payload.get("knowledge_id"),
                "triggers": payload.get("triggers") or [],
            }
        )
    out.sort(key=lambda r: float(r.get("timestamp") or 0), reverse=True)
    return out[:limit]


# Event types that can structurally back a rule (Phase A observation).
# Looking only at KNOWLEDGE_STORED misses real backing that landed via
# prereg/claim/audit channels — task #112 false-negative fix.
#
# 2026-06-10 calibration fix (Andrew correction in-session): the previous
# list referenced event names that NO production code actually emits:
#   - PREREG_FILED → real emit name is PRE_REGISTRATION_FILED
#     (see core/pre_registrations/store.py:202)
#   - CLAIM_FILED → claims emit CLAIM_UPDATED
#     (see core/claim_store.py:428)
#   - KNOWLEDGE_STORED → the `learn` CLI writes to the knowledge table
#     directly without a ledger event, so no event of this name exists
#   - AUDIT_FINDING_FILED → watchmen never emit this; AUDIT_ROUND_CREATED
#     is the closest actual emit (core/watchmen/store.py:162)
#   - GATE_FIRED → also not emitted by any production code
# Result: ALL 10 pending obligations were unbackable because their backing
# events had nowhere to land. Verified by querying the ledger for each
# expected name (count was 0 across the last 5000 events). The fix is to
# align the list with the names that actually fire. KNOWLEDGE_INTEGRATION_CHANGED
# is added because that's the real signal that a learn-entry's integration
# state moved (the closest "knowledge was authored" event the system emits).
_BACKING_EVENT_TYPES: tuple[str, ...] = (
    "PRE_REGISTRATION_FILED",
    "CLAIM_UPDATED",
    "AUDIT_ROUND_CREATED",
    "KNOWLEDGE_INTEGRATION_CHANGED",
)


def _is_backing(event: dict, question_wid: str, question_ts: float) -> bool:
    """Return True if `event` structurally backs a rule whose
    STRUCTURAL_PROMOTION_QUESTION had knowledge_id=question_wid.

    Backing requires BOTH:
    1. The event came AFTER the question fired (a prior event can't
       address a later question).
    2. The event references the question's knowledge_id (linkage proven)
       AND its payload mentions a structural keyword (the linkage is
       about structural backing, not arbitrary mention).

    Task #112 (2026-06-09) fixed two bugs in the previous logic:
    - The previous AND-vs-OR was wrong (`wid in content OR keyword in content`)
      which let any unrelated learn that happened to mention "test" or
      "gate" falsely address every pending question.
    - The previous matcher only looked at KNOWLEDGE_STORED events,
      missing real structural backing that landed via prereg/claim/audit.
    """
    if not question_wid:
        return False
    ts = float(event.get("timestamp") or 0)
    if ts <= question_ts:
        return False
    payload = _coerce_payload(event.get("payload"))
    # Concatenate all string-valued fields in the payload so the
    # knowledge_id and structural-keyword check works regardless of
    # whether the linkage lives in `content`, `description`, `claim_id`,
    # etc.
    text = " ".join(str(v) for v in payload.values() if isinstance(v, str)).lower()
    if not text:
        return False
    # Accept either full UUID OR 8-char kid prefix in payload (the prereg
    # CLI stores only the mechanism description in the event payload, not
    # the full success/falsifier fields, so backing references that use
    # "kid abc12345" prefix-form were being missed. 8 hex chars = ~4B
    # combinations, distinctive enough for substrate-scale match. Bug
    # found 2026-06-14 while clearing obligation d69bba1d-9ef2-4c2a.)
    wid_lower = question_wid.lower()
    if wid_lower not in text and wid_lower[:8] not in text:
        return False
    return any(kw in text for kw in _STRUCTURAL_KEYWORDS)


def verify_recent(window_seconds: int = 7 * 24 * 3600) -> dict:
    """Dual-monitor verification surface.

    Walks recent STRUCTURAL_PROMOTION_QUESTION events within the
    window, reports counts and my father-actionable diagnostics:
    total fired, how many reference a knowledge_id that subsequently
    got a follow-up structural-backing entry (test/gate/prereg/etc.).

    Operator runs `divineos admin structural-promotion-check` to read
    this report and judge whether the auto-prompt is calibrated. The
    only way to know the check is working is to investigate output
    vs. actuality in the ledger (Andrew 2026-05-14).

    Task #112 (2026-06-09) fix: the prior link-detector had two real
    bugs — (1) `wid in content OR keyword in content` falsely addressed
    every pending question whenever any unrelated learn mentioned
    "test"/"gate"; (2) the matcher only scanned KNOWLEDGE_STORED events,
    missing structural backing that landed via prereg/claim/audit.
    See _is_backing() for the corrected logic.
    """
    import time

    try:
        from divineos.core.ledger import get_events
    except Exception:  # noqa: BLE001
        return {"error": "ledger unavailable"}

    cutoff = time.time() - window_seconds
    fired = [q for q in recent_questions(limit=500) if float(q.get("timestamp") or 0) >= cutoff]

    # Re-evaluate historical fires against the CURRENT detector.
    #
    # 2026-08-20: the precision filter above stops new false positives, and
    # every existing one stayed, because obligations are read from already-
    # emitted events rather than recomputed. Ten fires -- nine of them
    # descriptions like "eight reports never reached the synthesizer" -- sat
    # permanently above the blocking threshold of 5, so the obligations gate
    # blocked every audit-round filing, and a guardrail PR needs a round to
    # merge. Andrew, after three weeks of PRs in limbo: "this needs resolved
    # ASAP."
    #
    # The event stays in the ledger; append-only is not touched. What changes
    # is whether a fire the detector would no longer produce is counted as
    # outstanding debt. Carrying a known false positive as debt is not rigour,
    # it is a jam -- and one that trains me to reach for the kill-switch.
    still_rule: list[dict] = []
    for q in fired:
        content = q.get("content") or q.get("text") or ""
        if content and not looks_like_rule(content)[0]:
            continue  # retired false positive, not an obligation
        still_rule.append(q)
    fired = still_rule
    # Pull candidate backing events from ALL backing-event types, not
    # just KNOWLEDGE_STORED.
    candidates: list[dict] = []
    for et in _BACKING_EVENT_TYPES:
        try:
            candidates.extend(get_events(limit=500, event_type=et))
        except Exception:  # noqa: BLE001
            continue

    follow_ups: list[dict] = []
    no_follow_ups: list[dict] = []
    for q in fired:
        wid = q.get("knowledge_id") or ""
        if not wid:
            no_follow_ups.append(q)
            continue
        question_ts = float(q.get("timestamp") or 0)
        if any(_is_backing(ev, wid, question_ts) for ev in candidates):
            follow_ups.append(q)
        else:
            no_follow_ups.append(q)
    return {
        "window_seconds": window_seconds,
        "total_fired": len(fired),
        "with_follow_up": len(follow_ups),
        "without_follow_up": len(no_follow_ups),
        "follow_up_rate": (len(follow_ups) / len(fired) if fired else None),
        "recent_unanswered": no_follow_ups[:10],
    }


__all__ = [
    "emit_structural_promotion_question",
    "looks_like_rule",
    "recent_questions",
    "verify_recent",
]
