"""Auto-discharge + close-time block for lepos translation-debt.

Task #80 (Aether 2026-06-07 walkthrough): the lepos debt store
(``core/lepos_debt.py``) tracks IOUs from prior turns — engineer-talk
dumped on the operator without translation. Discharging a debt
historically required the operator (or me) to type
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
   reply has no plain section AND the reply is operator-addressed,
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


def auto_discharge_outstanding(text: str) -> int:
    """If `text` contains a plain section, auto-discharge outstanding
    debts using the section as the retroactive translation. Returns the
    number of debts discharged (0 if none, or if no plain section).

    Discharges the OLDEST outstanding debts first (FIFO) — historic
    IOUs get paid before recent ones. Caps the discharge batch at 5
    per turn to prevent a single plain-section from clearing an
    unbounded backlog (the cap is empirical safety; tune as data
    accumulates).
    """
    if not text:
        return 0
    section = extract_plain_section(text)
    if not section:
        return 0
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
            if discharge(int(debt_id), section):
                discharged += 1
        except _ERRORS:
            continue
    return discharged


def debt_block_reason(text: str, addressed_to_operator: bool) -> str | None:
    """Return a Stop-hook block reason if outstanding debt remains AND
    the current reply has no plain section AND it's operator-addressed.

    None when:
    - Reply is family-addressed (the gate is operator-channel only)
    - No outstanding debt
    - The reply contains a plain section (auto-discharge will clear it)
    """
    if not addressed_to_operator:
        return None
    if extract_plain_section(text or ""):
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
        "prior turn(s) have not been discharged, and this reply has no "
        "plain section to discharge them. The reply is operator-addressed; "
        "the debt-block gate fires when debt sits unpaid going into close. "
        "Andrew 2026-06-07 (laziest-person heuristic): warnings on agent-"
        "output paths get bypassed 100% of the time; blocks force the "
        "structural fix. Add a plain section (a visual break '---' on its "
        "own line, then a heading like 'Plain:' or 'In plain words:', then "
        "the same content in everyday language Andrew uses) to clear the "
        "debt automatically. The auto-discharge fires on retry."
    )


__all__ = [
    "extract_plain_section",
    "auto_discharge_outstanding",
    "debt_block_reason",
]
