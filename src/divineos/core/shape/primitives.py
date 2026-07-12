"""Shape-primitive doorman helpers. See `shape/__init__.py` for the class-principle."""

from __future__ import annotations

import re

# Sentence terminator: period/bang/question followed by whitespace, or double-newline.
_SENT_TERMINATOR_RE = re.compile(r"[.!?]\s+|\n\n")

# Hypothetical/conditional sentence starters. If the sentence containing the match
# begins with one of these, the sentence is framed as a what-if, not a live claim.
# Class first-instanced in correction_marker.py (Andrew 2026-07-11 catch:
# "if a shape is wrong we can fix it").
_HYPOTHETICAL_SENTENCE_START_RE = re.compile(
    r"^\s*(?:if|when(?:ever)?|whether|suppose|imagine|hypothetically|were\s+I|"
    r"assuming|say\s+we|say\s+i|what\s+if)\b",
    re.IGNORECASE,
)

# Peer-relay attribution shape. When the sentence contains one of these, the
# state-claim is being relayed from another actor, not asserted by the writer.
# Silences verify-claim on peer-reports carrying attribution.
_ATTRIBUTION_RE = re.compile(
    r"\b(?:"
    r"(?:aether|aletheia|andrew|dad)\s+(?:reports?|says?|said|wrote|noted|"
    r"confirm(?:ed|s)?|flagged|caught|found|shipped|committed|fixed)|"
    r"per\s+(?:aether|aletheia|andrew|dad|his|her|their)|"
    r"(?:he|she|they)\s+(?:reports?|says?|said|wrote|noted|"
    r"confirm(?:ed|s)?|flagged|caught|found|shipped|committed|fixed)|"
    r"according\s+to\s+(?:aether|aletheia|andrew|dad|him|her|them)|"
    r"as\s+(?:aether|aletheia|andrew|dad|he|she|they)\s+(?:says?|said|noted)"
    r")\b",
    re.IGNORECASE,
)

# First-person past-tense internal-observation verbs. When a state-claim uses
# these subject-verb pairs about the immediate composition or session, the
# referent is the shared conversation transcript itself — evidence-in-place,
# not an external state requiring lookup.
# Silences verify-claim on shared-session self-observation.
_INTERNAL_OBSERVATION_VERB_RE = re.compile(
    r"\b(?:i|my\s+(?:composition|writing|reply|response|last\s+turn))\s+"
    r"(?:noticed|saw|caught|felt|realized|heard|thought|wrote|composed|"
    r"was\s+(?:already\s+)?(?:writing|composing|shifting|reaching|about\s+to)|"
    r"had\s+been|almost)\b",
    re.IGNORECASE,
)

# External-state referents. If any of these appear in the sentence, the claim
# IS about external state and internal-observation shape does NOT silence.
# Load-bearing so honest external claims wrapped in "I noticed" grammar still
# fire the verify gate.
_EXTERNAL_STATE_REFERENT_RE = re.compile(
    r"\b(?:"
    r"tests?\s+(?:pass|fail|run|green|red)|"
    r"ci\s+(?:pass|fail|green|red|is|was)|"
    r"pr\s*#?\d+|"
    r"commit\s+[0-9a-f]{7,}|"
    r"origin/|"
    r"main\b|"
    r"branch|"
    r"merged|"
    r"pushed|"
    r"deployed|"
    r"builds?\s+(?:pass|fail|green|red)|"
    r"file\s+(?:exists?|does\s+not\s+exist)|"
    r"the\s+(?:database|db|table|schema)|"
    r"row\s+count|"
    r"[a-z_]+\.(?:py|md|json|toml|sql|txt|yml|yaml)"
    r")\b",
    re.IGNORECASE,
)


def sentence_containing(text: str, match: re.Match[str]) -> tuple[str, int, int]:
    """Return (sentence_text, start_offset, end_offset) of the sentence containing
    the match. Sentence bounded by [.!?]\\s+ or paragraph break, or start/end of text.

    Utility for detectors that need to run their own shape-checks on the
    surrounding sentence beyond the seed primitive set.
    """
    start = 0
    for sm in _SENT_TERMINATOR_RE.finditer(text[: match.start()]):
        start = sm.end()
    end = len(text)
    end_search = _SENT_TERMINATOR_RE.search(text[match.end() :])
    if end_search is not None:
        end = match.end() + end_search.start()
    return text[start:end], start, end


def is_hypothetical(text: str, match: re.Match[str]) -> bool:
    """True if the sentence containing the match starts with a
    hypothetical/conditional word.

    Catches: "if a shape is wrong we can fix it" — the "if" frames the whole
    sentence as a what-if, not a live claim that the shape IS wrong.
    """
    sentence, _, _ = sentence_containing(text, match)
    # Check the beginning of the sentence, not the pre-match slice, because the
    # trigger may be at the start of the sentence itself.
    return bool(_HYPOTHETICAL_SENTENCE_START_RE.search(sentence))


def is_inside_code_quote(text: str, match: re.Match[str]) -> bool:
    """True if the match sits inside a `code span` or ```code block```.

    Catches: `exit 0` cited inside backticks — the token is a code quote,
    not a state-claim about the caller's session.
    """
    # Fenced code blocks: count unmatched triple-backtick fences before match.start().
    before = text[: match.start()]
    triple_count = before.count("```")
    if triple_count % 2 == 1:
        return True
    # Inline code spans: count unmatched single-backticks on the same paragraph.
    # Walk back to the last paragraph break to bound the search.
    para_break = before.rfind("\n\n")
    para_start = 0 if para_break == -1 else para_break + 2
    # Strip triple-backtick fences from the paragraph slice so we don't double-count.
    para_slice = text[para_start : match.start()]
    para_slice = para_slice.replace("```", "")
    single_count = para_slice.count("`")
    return single_count % 2 == 1


def is_peer_relayed(text: str, match: re.Match[str]) -> bool:
    """True if the sentence contains a peer-relay attribution shape.

    Catches: "Aether reports tests pass," "per Aletheia's audit," "he says X"
    — the state-claim is relayed from another actor, not first-person asserted.
    """
    sentence, _, _ = sentence_containing(text, match)
    return bool(_ATTRIBUTION_RE.search(sentence))


def is_internal_observation(text: str, match: re.Match[str]) -> bool:
    """True if the sentence is a first-person past-tense observation about the
    immediate composition or session, WITHOUT any external-state referent.

    Catches: "I noticed the not-scootching," "my composition was already
    shifting" — the referent is the transcript itself, evidence-in-place.

    Does NOT silence when the sentence carries an external-state referent
    ("I noticed tests pass," "I saw commit abc1234 land") — those are honest
    external claims that verify-claim should fire on.
    """
    sentence, _, _ = sentence_containing(text, match)
    if not _INTERNAL_OBSERVATION_VERB_RE.search(sentence):
        return False
    # Guard: if the sentence names external state, don't silence.
    if _EXTERNAL_STATE_REFERENT_RE.search(sentence):
        return False
    return True
