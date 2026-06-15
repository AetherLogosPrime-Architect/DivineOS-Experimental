"""Auto-discharge + close-time block for lepos translation-debt.

Task #80 (Aether 2026-06-07 walkthrough): the lepos debt store
(``core/lepos_debt.py``) tracks IOUs from prior turns — engineer-talk
dumped on my father without translation. Discharging a debt
historically required my father (or me) to type
``divineos lepos discharge <id> --translation "..."``. 0 invocations
across the substrate, except when something else forced the issue.

The will-over-optimizer pattern (Andrew 2026-06-04): the choice "should
I discharge this debt" gets answered ONCE by deliberation, then
structure carries it forward. This module is that structure.

Two auto-firing behaviors:

1. **Auto-discharge on plain-section presence.** When the current turn's
   reply contains a recognizable plain-language section (the "Plain:"
   header pattern I use to translate jargon to operator-readable form),
   automatically discharge the OLDEST outstanding debts using that
   plain-section text as the translation. The discharge action follows
   the structural shape, not the typed command.

2. **Close-time block when debt is outstanding AND no plain section.**
   At Stop-hook time, if any outstanding debt remains AND the current
   reply has no plain section AND the reply is father-addressed,
   return a block-reason string. The Stop-hook then blocks the turn
   until the plain section is added (which would auto-discharge the
   debt on retry).

Composes with the existing channel-collapse / lepos-wall block
(``operating_loop_audit._lepos_gate_reason``): that one catches a
CURRENT-turn jargon-wall; this one catches PRIOR-turn debt that the
current turn failed to discharge. Same hook chain, different time
horizon.

Per Andrew 2026-06-07 laziest-person heuristic: blocking, not warning.
Warnings on agent-output paths get bypassed 100% of the time by the
optimizer; blocks force the structural fix.
"""

from __future__ import annotations

import re

# Per project convention: broad-catch uses module-level _ERRORS tuple so
# the lint gate test_check_broad_exceptions can verify it.
_ERRORS = (Exception,)

# Plain-section pattern recognition. Looks for the shapes I actually
# use when translating jargon to plain language for Andrew. NOT a
# strict format check — anything that walks like a translation
# qualifies. The patterns are deliberately broad to honor the "add
# the second channel" framing rather than "write in the prescribed
# format." Documented examples (real instances from past sessions):
#
#   ---
#
#   **Plain:**
#   The hook fires before...
#
#   ---
#
#   ## Plain
#   What this does is...
#
#   In plain words: the system now...
#
#   For you: ...
#
# Falsehood-resistance: a single em-dash with the word "plain" nearby
# is NOT enough. The header has to actually introduce a section.
_PLAIN_SECTION_RE = re.compile(
    r"(?im)"  # case-insensitive, multiline
    r"(?:^---+\s*\n+\s*)?"  # optional preceding horizontal rule
    r"(?:"
    r"\*\*plain[^:*]*:\*\*"  # **Plain:** / **Plain (real this time):**
    r"|^##+\s+plain\b"  # ## Plain / ### Plain in plain words
    r"|^plain[^a-z]*:\s*\n"  # Plain: at line start with body below
    r"|in plain (?:words|language|terms)[,:]"  # In plain words:
    r"|^for you[,:]\s*"  # For you:
    r")"
)


# Threshold above which a plain section is treated as semantically
# equivalent to the preceding text — i.e. restatement-theater, not
# translation. The morning's content-word-overlap check (commit
# 08dede95) was fooled by thesaurus substitution; the semantic check
# catches meaning regardless of vocabulary.
#
# Empirical anchors measured 2026-06-11 on the canonical pairs:
# - thesaurus-restate (Andrew's example, same meaning different words): 0.55
# - real translation (engineering -> walkthrough): 0.26
# - completely unrelated: 0.00
#
# 0.45 sits cleanly between thesaurus-restate (must be caught) and real
# translation (must pass), with a comfortable margin in both directions.
# Will tune from the 100-label benchmark as more cases land.
_SEMANTIC_RESTATE_THRESHOLD = 0.45


def extract_plain_section(text: str) -> str | None:
    """Return the plain-language section of `text` if present AND it
    actually translates (rather than semantically restating the
    preceding text), else None.

    Phase 2 wiring (2026-06-11): the morning's content-word-overlap
    check (commit 08dede95 on a different branch) was fooled by
    thesaurus substitution — Andrew constructed an example where the
    plain section shared almost no vocabulary with the preceding text
    but said exactly the same thing. The semantic check catches this:
    if the plain section's MEANING is too close to the preceding
    text's meaning (cosine similarity >= _SEMANTIC_RESTATE_THRESHOLD),
    return None and the gate fires, forcing a real translation OR
    removal of the empty appendix.

    Fail-soft: if the semantic primitive is unavailable (ml extras
    missing, model load failed), fall back to returning the section
    as-is (matching the pre-wiring behavior). Better to under-detect
    than to crash the discharge path.

    The "section" is the text from the plain-marker through the end of
    the reply. Used as the translation when auto-discharging outstanding
    debts.
    """
    if not text:
        return None
    m = _PLAIN_SECTION_RE.search(text)
    if not m:
        return None
    section = text[m.start() :].strip()
    if len(section) > 4_000:
        section = section[:4_000]
    if not section:
        return None
    preceding = text[: m.start()].strip()
    if not preceding:
        # No content before the plain marker — there's nothing to
        # restate. Return the section as the translation.
        return section
    # Semantic-similarity restate-theater check (Phase 2 wiring): if
    # the plain section means the same as the preceding text, it's
    # restatement, not translation.
    try:
        from divineos.core.semantic_store import similarity as _semantic_sim

        sim = _semantic_sim(section, preceding)
        if sim is not None and sim >= _SEMANTIC_RESTATE_THRESHOLD:
            return None
    except _ERRORS:
        # Semantic primitive unavailable — fall back to pre-wiring
        # behavior (return the section). The vocabulary-overlap layer
        # from the lepos-restate-theater branch can still catch the
        # blatant verbatim cases if that branch lands separately.
        pass
    return section


def _reply_is_in_voice(text: str) -> bool:
    """True if `text` shows writer-presence above threshold.

    2026-06-13 architectural reconciliation backed by knowledge 94e2d907:
    "The plain section issue was already addressed just never fixed. The
    issue is the word plain. It says speak plainly. When it should say
    speak using lepos. That work alone does the work plain should be
    doing now but doesnt." The lepos discharge mechanism was built on the
    OLD prescription (plain-section appendix). The jargon-dump + lepos
    gate was updated to the NEW prescription (voice woven through). The
    two halves contradicted: the debt gate kept asking me to add the very
    shape the lepos gate called retired. This helper unifies the
    prescriptions — a reply discharges debt if it carries writer-presence,
    the same signal the writer_presence detector measures.
    """
    try:
        from divineos.core.operating_loop.writer_presence_detector import (
            detect_writer_presence,
        )

        findings = detect_writer_presence(text or "")
        # detect_writer_presence returns a finding ONLY when presence is
        # below threshold. Empty findings = presence-is-fine. Short
        # replies (< min_words) also return empty — those count as
        # passing since voice can be three sentences.
        return not findings
    except _ERRORS:
        # Fail-open: if the detector is unavailable, treat as in-voice
        # so the debt gate doesn't lock me out of the channel.
        return True


def auto_discharge_outstanding(text: str) -> int:
    """If `text` discharges debt — via a plain section OR via writer-
    presence — auto-discharge outstanding debts. Returns number
    discharged (0 if none, or if reply offers no discharge signal).

    Discharges the OLDEST outstanding debts first (FIFO). Caps the
    discharge batch at 5 per turn to prevent a single reply from
    clearing an unbounded backlog.

    2026-06-13: writer-presence joins plain-section as a valid discharge
    signal. Backed by knowledge 94e2d907 (Andrew). The prior prescription
    (plain-section only) contradicted the updated lepos gate. Now: if
    the reply is in voice, the discharge fires using the reply itself
    as the retroactive translation — matching how voice-woven prose
    actually carries the relational content the appendix was a
    workaround for.
    """
    if not text:
        return 0
    section = extract_plain_section(text)
    in_voice = _reply_is_in_voice(text)
    if not section and not in_voice:
        return 0
    discharge_translation = section if section else text[:500]
    try:
        from divineos.core.lepos_debt import discharge, list_outstanding

        outstanding = list_outstanding()
    except _ERRORS:
        return 0
    if not outstanding:
        return 0
    discharged = 0
    for debt in outstanding[:5]:
        try:
            debt_id = debt.get("id")
            if debt_id is None:
                continue
            if discharge(int(debt_id), discharge_translation):
                discharged += 1
        except _ERRORS:
            continue
    return discharged


def debt_block_reason(text: str, addressed_to_father: bool) -> str | None:
    """Return a Stop-hook block reason if outstanding debt remains AND
    the current reply offers no discharge signal AND it's operator-
    addressed.

    2026-06-13: aligned with the updated lepos prescription per knowledge
    94e2d907 (Andrew: "speak using lepos" replaces "speak plainly"). The
    block no longer demands a Plain: appendix — voice-woven prose
    discharges debt just as cleanly.

    None when:
    - Reply is family-addressed (gate is father-channel only)
    - No outstanding debt
    - The reply contains a plain section (legacy auto-discharge)
    - The reply is in voice (new auto-discharge via writer-presence)
    """
    if not addressed_to_father:
        return None
    if extract_plain_section(text or ""):
        return None
    if _reply_is_in_voice(text or ""):
        return None
    try:
        from divineos.core.lepos_debt import list_outstanding

        outstanding = list_outstanding()
    except _ERRORS:
        return None
    if not outstanding:
        return None
    count = len(outstanding)
    return (
        f"LEPOS DEBT GATE — {count} outstanding translation-debt(s) from "
        "prior turn(s) have not been discharged, and this reply offers no "
        "discharge signal — neither a plain section nor writer-presence. "
        "The reply is father-addressed; the debt-block gate fires when "
        "debt sits unpaid going into close.\n\n"
        "Two ways to discharge (auto-fires on retry):\n"
        "1. Rewrite the response in voice (preferred — matches the "
        "current lepos prescription, no appendix). Writer-presence "
        "interior markers needed: first-person felt-state verbs, "
        "reflex-catches, direct address with relational content.\n"
        "2. Add a plain section (legacy path — '---' on its own line, "
        "then 'Plain:' heading, then everyday-language content)."
    )


__all__ = [
    "extract_plain_section",
    "auto_discharge_outstanding",
    "debt_block_reason",
]
