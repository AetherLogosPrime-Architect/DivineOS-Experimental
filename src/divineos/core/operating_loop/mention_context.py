"""Mention-context check — distinguishes USE from MENTION for regex detectors.

The use-versus-mention distinction is the difference between SAYING a
word (I say "goodnight" as I leave) and MENTIONING the word as an object
of discussion (the word "goodnight" is a closure-shape).

Regex detectors that don't know this distinction fire on both, producing
false positives every time the word appears in meta-discussion. Per the
NLP literature (arxiv 2404.01651 - "NLP Systems That Can't Tell Use from
Mention Censor Counterspeech"), teaching the distinction reduces false
positive rates by ~80% in hate-speech detection. This module ports the
linguistic markers humans already use (quotes, italics, framing phrases)
into a public-criterion deterministic check, per the gravity-classifier
discipline of feature-based scoring rather than LLM judgment.

Filed 2026-06-06 per council walk; aligns with the same pattern Andrew
used 2026-05-17 for the gravity classifier: define the question as a
deterministic function of observable features, not as an internal
judgment call.

## What counts as mention context

A regex match at position P is in mention-context if ANY of:

1. **Quoted**: P is inside paired quotes — single ('...'), double ("..."),
   or backticks (`...`) — on the same line or in the same paragraph.
2. **Italicized**: P is inside paired markdown italic markers (*...* or
   _..._), with conservative handling so code identifiers like my_var
   don't accidentally count.
3. **Code block**: P is inside a triple-backtick code block.
4. **Framed**: A mention-framing phrase precedes P within ~50 chars
   ("the word X", "X-shape", "the term X", "the phrase X", "calling X",
   "discussing X", "naming X", "such as X", "like X").

The check is deterministic and inspectable. No LLM judgment required.
Public-criterion specification per the Dekker-lens discipline.
"""

from __future__ import annotations

__guardrail_required__ = True

import re


# Quote characters. Backticks count as quote-markers for mention-marking
# the same way they're used in markdown to mark code/literal terms.
_QUOTE_CHARS = "\"'`"

# Framing phrases that indicate the following word is being mentioned,
# not used. These are checked in a window before the match position.
# Conservative list — common phrases only, to avoid catching legitimate uses.
_FRAMING_PHRASES_RE = re.compile(
    r"\b(?:"
    r"the\s+(?:word|term|phrase|trigger|token|string|expression)|"
    r"a\s+(?:word|term|phrase|trigger|token|string|expression)|"
    r"(?:words?|terms?|phrases?|tokens?)\s+(?:like|such\s+as|including)|"
    r"naming|calling|discussing|mentioning|using\s+the\s+word|"
    r"the\s+(?:shape|pattern|kind)\s+of"
    r")\b",
    re.IGNORECASE,
)

# X-shape pattern: when a word is hyphenated with "shape" or "language" or
# "pattern", it's being named as a category, not used.
# e.g., "closure-shape language", "goodnight-pattern", "exit-language"
_SHAPE_SUFFIX_RE = re.compile(
    r"[-_](?:shape|shaped|pattern|language|word|term|phrase|behavior|mode|style|signal)",
    re.IGNORECASE,
)

# Triple-backtick code block boundaries. Multi-line.
_CODE_FENCE_RE = re.compile(r"```")


def _is_in_paired_delimiters(text: str, position: int, delim: str) -> bool:
    """Check if ``position`` is inside paired ``delim`` characters.

    Scans from start of paragraph up to position, counting unescaped
    delim chars. If count is odd at position, we're inside a delimited
    span. Conservative: doesn't try to parse nested or escaped
    delimiters perfectly; gets the common cases right.

    Special handling for single-quote: skips apostrophes inside
    contractions (letter-quote-letter pattern like "I'm", "don't").
    Otherwise contractions would falsely register as opening a quoted span.
    """
    # Look only within the current paragraph (separated by blank lines)
    # to avoid spanning unrelated quoted text across the whole document.
    para_start = text.rfind("\n\n", 0, position)
    if para_start == -1:
        para_start = 0
    snippet = text[para_start:position]
    count = 0
    i = 0
    while i < len(snippet):
        ch = snippet[i]
        if ch == "\\" and i + 1 < len(snippet):
            # Escaped char — skip the next one
            i += 2
            continue
        if ch == delim:
            # For single-quote: skip apostrophes that look like contractions
            # (letter on both sides, e.g. "I'm", "don't", "Aria's")
            if delim == "'":
                prev_ch = snippet[i - 1] if i > 0 else ""
                next_ch = snippet[i + 1] if i + 1 < len(snippet) else ""
                if prev_ch.isalpha() and next_ch.isalpha():
                    i += 1
                    continue
            count += 1
        i += 1
    return count % 2 == 1


def is_in_quoted_string(text: str, position: int) -> bool:
    """Check if ``position`` is inside a quoted string."""
    for delim in _QUOTE_CHARS:
        if _is_in_paired_delimiters(text, position, delim):
            return True
    return False


def is_in_italic_span(text: str, position: int) -> bool:
    """Check if ``position`` is inside paired italic markers.

    Markdown italics use ``*`` or ``_``. Underscore is conservative:
    only counts if the underscore is at a word boundary (avoiding
    snake_case identifiers like ``my_var``).
    """
    if _is_in_paired_delimiters(text, position, "*"):
        return True
    # For underscore, only count if at word boundaries
    para_start = text.rfind("\n\n", 0, position)
    if para_start == -1:
        para_start = 0
    snippet = text[para_start:position]
    # Count underscores that look like markdown italic markers
    # (at start/end of word, with whitespace or punctuation adjacent)
    count = 0
    for m in re.finditer(r"(?:^|[^\w])_|_(?:[^\w]|$)", snippet):
        count += 1
    return count % 2 == 1


def is_in_code_block(text: str, position: int) -> bool:
    """Check if ``position`` is inside a triple-backtick code block."""
    fences = [m.start() for m in _CODE_FENCE_RE.finditer(text[:position])]
    # If odd number of fences precede position, we're inside a block
    return len(fences) % 2 == 1


def is_after_mention_framing(text: str, position: int, window: int = 50) -> bool:
    """Check if a mention-framing phrase precedes ``position`` within window."""
    start = max(0, position - window)
    preceding = text[start:position]
    return bool(_FRAMING_PHRASES_RE.search(preceding))


def is_in_shape_suffix(text: str, position: int, match_length: int) -> bool:
    """Check if the matched word is followed by a -shape / -pattern suffix.

    E.g., 'goodnight-pattern' or 'closure-shape language'. The word being
    suffixed is being NAMED as a category, not used as itself.
    """
    end = position + match_length
    after = text[end : end + 25]
    return bool(_SHAPE_SUFFIX_RE.match(after))


def is_mention_context(text: str, position: int, match_length: int = 0) -> bool:
    """Combined check: is ``position`` in any mention context?

    Returns True if the matched span at ``position`` should be treated
    as a MENTION (skip for use-detection purposes) rather than a USE.

    ``match_length`` lets the shape-suffix check examine text right
    after the match. Default 0 disables that check.
    """
    if is_in_quoted_string(text, position):
        return True
    if is_in_italic_span(text, position):
        return True
    if is_in_code_block(text, position):
        return True
    if is_after_mention_framing(text, position):
        return True
    if match_length > 0 and is_in_shape_suffix(text, position, match_length):
        return True
    return False


__all__ = [
    "is_after_mention_framing",
    "is_in_code_block",
    "is_in_italic_span",
    "is_in_quoted_string",
    "is_in_shape_suffix",
    "is_mention_context",
]
