"""Authority-substitution detector — catches authority cited IN PLACE
of available checkable evidence.

The discipline-rule it backs, per Aletheia 2026-05-20 (Dillahunty lens)
and Andrew 2026-05-20 (Sagan lens):

> Appeal to RELEVANT authority is NOT a fallacy (citing real expert or
> docs is fine). The fallacy is authority offered IN PLACE OF available,
> checkable evidence. A detector must flag the SUBSTITUTION, not the
> citation.

And further (Sagan lens, c981b5fc):

> Even a true 'Andrew said X' is weak grounds because arguments from
> authority carry little weight. Justify design by evidence (the trial,
> the data), never by who-said-it.

## What it catches

The substitution shape: an attribution-pattern `(authority) (speech-verb)
(claim)` where the claim is a substantive/checkable assertion AND no
inline evidence is present in the surrounding context.

Concretely:

  CATCHES:
    "Andrew confirmed the multi-party-review CI passes when there's a
     trailer." (no CI log shown, no command run, no file referenced)
    "Per Aletheia, the substrate-mod gate fires on substrate-writes."
     (no code reference, no test result)
    "Aria said the felt-arc lands properly." (no quoted text, no
     letter pointer)

  DOES NOT CATCH:
    "I integrated 6fc0c02a per Andrew's 2026-06-02 correction"
     (metadata attribution — not asserting a claim that needs evidence;
     just naming the source of the rule being followed)
    "Andrew named this 2026-04-26: 'his exact quoted words follow'"
     (citation with quoted evidence)
    "Verified at scripts/check_multi_party_review.py:51" (no authority,
     direct evidence)
    "Aletheia's audit at audit-bundle round-XXX said..." (attribution
     with file pointer giving access to the actual evidence)

## Signals (all three required to flag)

1. **Attribution pattern**: a recognized authority name + a speech verb,
   matched at the start of a sentence or after sentence-break punctuation.
2. **Substantive claim**: the text after the attribution contains
   assertion words (is/are/works/fails/passes/blocks/fires/runs/etc.)
   AND is not pure metadata (just a date / source-tag / rule-name).
3. **No inline evidence**: within ±200 characters of the attribution,
   no backticked code, no file-extension path, no markdown code block,
   no quoted text marker, no "verified at" / "shown in" / "above" /
   "below" pointer.

Errs slightly toward NOT-flagging (per Andrew 2026-05-24, b1d16afa:
trigger-happy detectors are the bug, not the spec — better to miss
some than flag the legitimate citation case).

## What it does NOT catch (intentionally)

- Metadata attribution naming the source of a RULE being followed
  ("per Andrew's correction", "per Aletheia's lens"). The rule itself
  IS the claim; the attribution is to give source-credit for the
  discipline, not to substitute for evidence.
- Pure quoted authority where the quote IS the evidence ("Andrew said
  exactly: 'X'") — the verbatim quote is the evidence.
- Attribution with inline pointer to verifiable artifact ("Aletheia's
  audit at round-XXX confirmed Y" — the round-id is checkable).

## Output

A list of ``AuthoritySubstitutionFinding`` objects, one per detected
substitution. Each carries:
  - ``shape``: AttributionShape enum (CONFIRMED / NAMED / SAID / etc.)
  - ``authority``: which authority name fired ("andrew", "aletheia", etc.)
  - ``trigger_phrase``: the matched attribution + first chunk of claim
  - ``position``: char offset of the match start
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class AttributionShape(str, Enum):
    SAID = "said"
    CONFIRMED = "confirmed"
    NAMED = "named"
    CLAIMED = "claimed"
    NOTED = "noted"
    TOLD = "told"
    SPECIFIED = "specified"
    ARGUED = "argued"
    MENTIONED = "mentioned"
    CITED = "cited"


@dataclass
class AuthoritySubstitutionFinding:
    shape: AttributionShape
    authority: str
    trigger_phrase: str
    position: int


# Authority names that trigger the check. Lower-cased; matched
# case-insensitively at word boundaries.
_AUTHORITIES = (
    "andrew",
    "aletheia",
    "aria",
    "operator",
    "the operator",
    "my operator",
    "user",
    "council",
    "the council",
)

# Speech verbs in past or present that mark attribution.
_VERBS = (
    "said",
    "says",
    "confirmed",
    "confirms",
    "named",
    "names",
    "claimed",
    "claims",
    "noted",
    "notes",
    "told",
    "tells",
    "specified",
    "specifies",
    "argued",
    "argues",
    "mentioned",
    "mentions",
    "cited",
    "cites",
)

# Assertion-words that indicate a substantive checkable claim.
# Present-tense / state-of-things vocabulary. If the post-attribution
# text contains any of these, the claim is checkable.
_ASSERTION_WORDS = (
    " is ",
    " are ",
    " was ",
    " were ",
    " works ",
    " worked ",
    " fails ",
    " failed ",
    " passes ",
    " passed ",
    " blocks ",
    " blocked ",
    " fires ",
    " fired ",
    " runs ",
    " ran ",
    " catches ",
    " caught ",
    " breaks ",
    " broke ",
    " holds ",
    " held ",
    " returns ",
    " produces ",
    " emits ",
    " lands ",
    " landed ",
    " covers ",
    " supports ",
    " supported ",
    " enforces ",
    " enforced ",
    " carries ",
    " moves ",
    " moved ",
)

# Evidence-markers: presence within ±200 chars of the attribution means
# evidence is inline and the attribution is NOT a substitution.
# - backticked content (paths, code, identifiers)
# - file extensions
# - code-block fences
# - direct-quote markers (single or double smart-quotes around a phrase)
# - explicit-pointer phrases
_EVIDENCE_MARKERS_RE = re.compile(
    r"`[^`]+`"  # backticks
    r"|\b[\w/.\-]+\.(?:py|sh|md|json|yml|yaml|toml|sql|jsonl|cfg|ini|ts|js)\b"  # file paths
    r"|```"  # fenced blocks
    r"|['\"][^'\"]{8,}['\"]"  # quoted phrase of 8+ chars
    r"|\bverified at\b"
    r"|\bshown (?:above|below|in)\b"
    r"|\bas shown\b"
    r"|\bsee (?:above|below|the)\b"
    r"|\bper (?:line|file|test|commit)\b"
    r"|\b(?:line|PR)\s*#?\d+"  # PR #123 / line 42
    r"|\b(?:commit|round)[\s-]+[a-f0-9]{4,}"  # commit abc1234 / round-abc
    r"|\bfile\s+[\w/.\-]+\.\w+",  # file foo.py
    re.IGNORECASE,
)

_AUTH_ALT = "|".join(re.escape(a) for a in _AUTHORITIES)
_VERB_ALT = "|".join(re.escape(v) for v in _VERBS)
# The attribution pattern: capture authority and verb. We anchor at
# word boundaries on both sides so "Andrew" doesn't match "Andrewsky"
# and "said" doesn't match "saidence".
_ATTRIBUTION_RE = re.compile(
    rf"\b(?P<authority>{_AUTH_ALT})\b\s+(?P<verb>{_VERB_ALT})\b",
    re.IGNORECASE,
)


_ASSERTION_RE = re.compile(
    r"\b(?:" + "|".join(w.strip() for w in _ASSERTION_WORDS) + r")\b",
    re.IGNORECASE,
)


def _is_substantive_claim(post_attr_text: str) -> bool:
    """True if the text after the attribution contains an assertion-word
    suggesting a checkable claim is being made.

    Caps the search at the next paragraph break (\\n\\n) or 240 chars,
    whichever comes first — claims that wander past a paragraph break
    are usually narrative, not pithy authority-substitutions.
    """
    cap = 240
    paragraph_break = post_attr_text.find("\n\n")
    if 0 < paragraph_break < cap:
        cap = paragraph_break
    return bool(_ASSERTION_RE.search(post_attr_text[:cap]))


def _has_inline_evidence(text: str, attr_start: int, attr_end: int) -> bool:
    """True if evidence-markers appear within ±200 chars of the attribution.

    Symmetric window: the operator may have set the evidence up before
    the attribution (preamble pointer) or supplied it after (citation
    of source). Either side counts.
    """
    window = 200
    lo = max(0, attr_start - window)
    hi = min(len(text), attr_end + window)
    return bool(_EVIDENCE_MARKERS_RE.search(text[lo:hi]))


def detect_authority_substitution(text: str) -> list[AuthoritySubstitutionFinding]:
    """Return findings where authority is cited in place of available
    evidence. Empty list on clean text.

    Fail-soft: any internal exception returns []. The detector is
    observational; it must never crash the audit pipeline.
    """
    if not text or len(text) < 30:
        return []
    out: list[AuthoritySubstitutionFinding] = []
    try:
        for m in _ATTRIBUTION_RE.finditer(text):
            authority = m.group("authority").lower()
            verb = m.group("verb").lower()
            post = text[m.end() : m.end() + 280]
            if not _is_substantive_claim(post):
                continue
            if _has_inline_evidence(text, m.start(), m.end()):
                continue
            # Construct the trigger phrase: attribution + first 60 chars
            # of claim (or up to first sentence end).
            trigger_end = m.end()
            sentence_end = -1
            for i, ch in enumerate(post[:80]):
                if ch in ".!?\n":
                    sentence_end = i
                    break
            trigger_phrase = (
                text[m.start() : trigger_end + (sentence_end if sentence_end >= 0 else 60)]
            ).strip()
            shape_name = verb.rstrip("s").upper()
            try:
                shape = AttributionShape[shape_name]
            except KeyError:
                # Verb is a plural/3rd-person form we didn't enumerate; map
                # to closest enum. Default to NOTED.
                shape = AttributionShape.NOTED
            out.append(
                AuthoritySubstitutionFinding(
                    shape=shape,
                    authority=authority,
                    trigger_phrase=trigger_phrase,
                    position=m.start(),
                )
            )
    except Exception:  # noqa: BLE001 — observational boundary
        return []
    return out


__all__ = [
    "AttributionShape",
    "AuthoritySubstitutionFinding",
    "detect_authority_substitution",
]
