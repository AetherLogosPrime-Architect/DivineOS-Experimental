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


def extract_plain_section(text: str) -> str | None:
    """Return the plain-language section of `text` if present, else None.

    The "section" is the text from the plain-marker through the end of
    the reply (or until the next structural break). Used as the
    translation when auto-discharging outstanding debts.
    """
    if not text:
        return None
    m = _PLAIN_SECTION_RE.search(text)
    if not m:
        return None
    # Take from the match onward as the plain section. Trim to a
    # reasonable size (debts are tracked with translation text; very
    # long translations are not more useful than medium ones).
    section = text[m.start() :].strip()
    if len(section) > 4_000:
        section = section[:4_000]
    return section if section else None


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
