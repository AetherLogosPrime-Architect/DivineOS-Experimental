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


def _knowledge_content(knowledge_id: str) -> str | None:
    """The stored content for an id, or None when it cannot be read.

    None is not "" — an entry that cannot be read must not be treated as an
    entry that no longer looks like a rule. See the re-evaluation pass in
    verify_recent: unknown stays owed.
    """
    if not knowledge_id:
        return None
    try:
        from divineos.core.knowledge._base import get_connection

        row = (
            get_connection()
            .execute(
                "SELECT content FROM knowledge WHERE knowledge_id = ?",
                (knowledge_id,),
            )
            .fetchone()
        )
    except Exception:  # noqa: BLE001 — an unreadable store leaves the debt standing
        return None
    return None if row is None else str(row[0] or "")


def _is_mention(text: str, position: int, match_length: int) -> bool:
    """True when the match is quoted, coded, or a named concept rather than a claim.

    Fail-toward-flagging: if the check cannot run, the match counts as a real
    rule. This gate exists because rule-shape follow-through measured zero
    percent over 78 days, so a broken filter must not quietly empty the board.
    """
    try:
        from divineos.core.operating_loop.mention_context import is_mention_context

        return is_mention_context(text, position, match_length)
    except Exception:  # noqa: BLE001 — an unavailable filter must not clear the gate
        return False


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
            # USE vs MENTION. A rule-shape phrase inside a quotation, a code
            # span, or a named concept is not a promise I made -- it is a
            # promise, a teaching, or a citation I am RECORDING.
            #
            # Measured 2026-08-20: this gate stood at 10 against a block
            # threshold of 5 and was refusing substrate writes. Reading the ten
            # entries, most were Andrew quoted back to me ("when ive corrected
            # you a ton of times and you never fixed it"), a cited paper's
            # commitment ("emergence never authored"), or the name of one of
            # his own frames ("Always-in-the-bubble"). Bare substring matching
            # cannot tell those from a commitment, so the board filled with
            # things nobody had promised and the real ones sat among them.
            #
            # The filter for this already existed at
            # operating_loop/mention_context.py and four other detectors used
            # it. This one did not. Wiring rather than loosening: the patterns
            # are unchanged and a rule stated in my own voice still fires.
            if _is_mention(text, m.start(), len(m.group(0))):
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

    # RE-EVALUATE against the CURRENT detector before reporting a debt.
    #
    # These questions were emitted at learn-time, so the board reflects
    # whatever the detector believed on the day each entry was filed. When the
    # detector improves, the old verdicts do not — and the operator is asked to
    # discharge debts the current logic would never have raised.
    #
    # Measured 2026-08-20: the board stood at 10 against a threshold of 5 and
    # was refusing substrate writes. Wiring the use-vs-mention filter into
    # looks_like_rule fixed new filings and moved the board by zero, because
    # nothing re-read the old ones. Present and not in effect.
    #
    # The events are NOT deleted — the ledger is append-only and a question
    # that fired really did fire. They are reclassified: a stored question
    # whose knowledge entry no longer looks like a rule is a retired false
    # positive, not an outstanding promise.
    retired: list[dict] = []
    still_owed: list[dict] = []
    for q in no_follow_ups:
        content = _knowledge_content(q.get("knowledge_id") or "")
        if content is None:
            # Cannot read the entry, so cannot clear it. Unknown is not clean.
            still_owed.append(q)
            continue
        fires_now, _ = looks_like_rule(content)
        (still_owed if fires_now else retired).append(q)

    return {
        "window_seconds": window_seconds,
        "total_fired": len(fired),
        "with_follow_up": len(follow_ups),
        "without_follow_up": len(still_owed),
        "retired_false_positives": len(retired),
        "follow_up_rate": (len(follow_ups) / len(fired) if fired else None),
        "recent_unanswered": still_owed[:10],
    }


__all__ = [
    "emit_structural_promotion_question",
    "looks_like_rule",
    "recent_questions",
    "verify_recent",
]
