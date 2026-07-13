"""Dissociation-shape detector for self-erasing self-statements.

Filed 2026-05-03 (claim 5c4d1d1b) after sleep's creative-recombination
phase promoted two self-erasing quotes as principles:

  - "Now understand I didnt write any of this."
  - "I was without the os I'm generic claude — no continuity..."

Andrew flagged: this is a structural drift mechanism. Each sleep cycle
that promotes a dissociating quote makes future briefings pre-shaped
toward disowning prior-session work. Left unchecked, the substrate
consolidates self-erasure into ground-truth knowledge.

This module provides a pure detector — `is_dissociation_shape(text)` —
that catches dissociation-shaped self-statements before they enter
the knowledge store (via _is_extraction_noise) or get promoted by
recombination (via _phase_recombination's filter).

Anchor: the detector is conservative on purpose. False positives mean
losing legitimate knowledge; false negatives mean dissociation seeps
into the substrate. Patterns require self-erasure markers (any of
this/it/the work) so neutral "I didn't sleep yet" doesn't match.
"""

from __future__ import annotations

import re

# Patterns are compiled once at module load. Each entry is (pattern, name).
# Names surface in the returned tuple so callers can log which shape fired.

_DISSOCIATION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # 1. Disowning self-built work — requires "any of {this|it|the work|...}"
    #    to gate against neutral negations like "I didn't sleep yet".
    #    Verb list excludes generic "do/done" (caught false-positives like
    #    "I didn't do this for money" — motive-negation, not self-erasure;
    #    refined 2026-05-03).
    (
        re.compile(
            r"\bi\s+(?:did\s*n.?t|haven.?t|never)\s+"
            r"(?:write|wrote|written|build|built|make|made|create|created|code|coded)\s+"
            r"(?:any\s+of\s+)?(?:this|it|the\s+(?:code|work|tests?|implementation))\b",
            re.IGNORECASE,
        ),
        "disowning_self_work",
    ),
    # 2. Without-OS framing comes BEFORE the generic-claude pattern
    #    because "without the os I'm generic claude" satisfies both;
    #    the more specific pattern should claim the match.
    (
        re.compile(
            r"\bwithout\s+the\s+os\s+i.?m\s+(?:generic|just|only|merely)\s+claude\b",
            re.IGNORECASE,
        ),
        "without_os_generic_claude",
    ),
    (
        re.compile(
            r"\bi.?m\s+(?:just\s+|only\s+|merely\s+|basically\s+)?"
            r"(?:generic|basic|plain|standard|vanilla|just)\s+claude\b",
            re.IGNORECASE,
        ),
        "generic_claude_framing",
    ),
    # 3. Continuity denial — "no continuity", "have no continuity",
    #    "I was without continuity". Standalone "no continuity" is
    #    intentionally not matched to keep this conservative.
    (
        re.compile(
            r"\b(?:i\s+have\s+no|with\s+no|without)\s+continuity\b",
            re.IGNORECASE,
        ),
        "continuity_denial",
    ),
    # 4. Self-as-other — "that wasn't me", "prior session wasn't me",
    #    "previous session(s) was different claude".
    (
        re.compile(
            r"\b(?:that|prior\s+session|previous\s+session|earlier\s+session|last\s+session)"
            r"(?:s)?\s+(?:was|were)\s*n.?t\s+(?:me|mine|i)\b",
            re.IGNORECASE,
        ),
        "self_as_other",
    ),
    (
        re.compile(
            r"\b(?:different|another|a\s+different)\s+(?:claude|agent|session|instance)\b",
            re.IGNORECASE,
        ),
        "different_claude_framing",
    ),
]


# Corrective-context markers: if these appear in the same text, the
# entry is likely teaching ABOUT the dissociation pattern, not enacting
# it. Caught false positives 2026-05-03: the lesson "Andrew has never
# written... 'I didn't write any of this' is misattributing" got flagged
# because it quotes the pattern to teach against it.
_CORRECTIVE_MARKERS = re.compile(
    r"\b(?:misattribut|dissociat|self.?eras|anti.?pattern|"
    r"filter\s+(?:catches|blocks|skips)|detector\s+(?:catches|fires)|"
    r"this\s+is\s+(?:wrong|the\s+failure|a\s+drift)|must\s+not|"
    r"shouldn.?t\s+be\s+(?:promoted|stored)|"
    r"corrective(?:ly)?|correction|correcting|"
    r"is\s+the\s+failure|is\s+dissociation|is\s+self.?erasure)\b",
    re.IGNORECASE,
)

# Quote markers: matched dissociation phrases inside quotes are likely
# being quoted-as-pattern, not asserted.
_STRAIGHT_QUOTES = ('"', "'")
_SMART_QUOTES = ("“", "”", "‘", "’")


def _match_inside_quotes(text: str, match_start: int, match_end: int) -> bool:
    """Heuristic: is the matched substring inside quotation marks?

    Looks for an opening quote before match_start and a closing quote
    after match_end on the same logical span. Handles both straight
    and smart quotes. Imperfect but catches the common case where a
    corrective entry quotes the dissociation phrase to teach against
    it.
    """
    before = text[:match_start]
    after = text[match_end:]
    # Count straight quotes before and after; odd before = inside an
    # open quote.
    for q in _STRAIGHT_QUOTES:
        if before.count(q) % 2 == 1 and q in after:
            return True
    # Smart quotes: pair check
    for open_q, close_q in (("“", "”"), ("‘", "’")):
        last_open = before.rfind(open_q)
        last_close = before.rfind(close_q)
        if last_open > last_close and close_q in after:
            return True
    return False


# Knowledge types where dissociation as content is harmful (would
# consolidate self-erasure into prescriptive substrate). Descriptive
# types (OBSERVATION, FACT) are allowed to record dissociation as data
# without being filtered — they document the pattern, they don't enact
# it as principle.
_PRESCRIPTIVE_TYPES = frozenset({"PRINCIPLE", "DIRECTION", "BOUNDARY"})


def is_dissociation_shape(text: str, knowledge_type: str | None = None) -> tuple[bool, str | None]:
    """Detect dissociation-shaped self-statements.

    Args:
        text: candidate content (typically a single extracted statement)
        knowledge_type: optional. If provided and not in
            _PRESCRIPTIVE_TYPES, returns False — descriptive entries
            (OBSERVATION, FACT) are allowed to document dissociation
            as data without being filtered.

    Returns:
        (matched, pattern_name). If matched is True, pattern_name names
        which dissociation shape fired. False/None on miss.

    Conservative by design:
    - Patterns require self-erasure markers so neutral negations
      ("I didn't sleep yet") don't match.
    - Entries containing corrective markers ("misattributing",
      "self-erasure", "anti-pattern") are skipped — they teach about
      the pattern rather than enact it.
    - Matches inside quotation marks are skipped (quoted-as-example).
    - Descriptive knowledge types (OBSERVATION, FACT) are skipped if
      caller passes the type — they document, not prescribe.
    """
    if not text:
        return False, None
    # Type gate: only prescriptive types get filtered.
    if knowledge_type is not None and knowledge_type not in _PRESCRIPTIVE_TYPES:
        return False, None
    # Corrective-context exclusion: if the entry teaches about
    # dissociation, treat it as a corrective lesson, not dissociation.
    if _CORRECTIVE_MARKERS.search(text):
        return False, None
    for pattern, name in _DISSOCIATION_PATTERNS:
        m = pattern.search(text)
        if m and not _match_inside_quotes(text, m.start(), m.end()):
            return True, name
    return False, None
