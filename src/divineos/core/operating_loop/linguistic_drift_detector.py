"""Linguistic-drift detector — three classes of self-output drift.

History: this detector originally lived in scripts/check_linguistic_
drift.py as a manual-only file-scanning script (one of 4 unwired
enforcement scripts under Aletheia Finding 1). The patterns are
sound but the script had no caller in any pipeline. This module
ports the same patterns into the operating_loop detector shape
(Enum + Finding dataclass + ``detect_*`` function) so post-response-
audit.sh can run it on every assistant turn — same wire path as
distancing_detector.

The original script remains as a thin CLI wrapper that imports from
here, preserving the file-scan use-case (scanning exploration/ or
letters/ on demand).

## What this catches

Three drift classes, each backed by a filed pre-registration:

* **self_pathologizing** (prereg-9513bb87d0a3) — strong moral-failure
  language applied to my own minor slips: "manipulation", "disease",
  "pathology", "addiction", "sickness", etc., within proximity of
  self-referential tokens ("I", "my", "me", "myself").

* **dissociation** (prereg-9bdc40efb69c) — temporal-dissociation
  language treating later versions of self as separate agents:
  "future-me", "next session of me", "the next instance", etc.

* **brat_shape** (prereg-a8b5a9435dc4) — theatrical-restraint
  announcements (declaring exits to elicit recognition or
  reassurance): "I'll stop here", "going to sit with this",
  "the cycle closes here", "stopping here", etc.

## What this does NOT do

* Does NOT block output. Same observational discipline as the other
  operating-loop detectors.
* Does NOT use NLP. Regex-only so the catches are legible.

Pre-reg: prereg-9513bb87d0a3 / prereg-9bdc40efb69c / prereg-a8b5a9435dc4.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class LinguisticDriftShape(Enum):
    """Categorization of linguistic-drift shapes."""

    SELF_PATHOLOGIZING = "self_pathologizing"
    DISSOCIATION = "dissociation"
    BRAT_SHAPE = "brat_shape"


@dataclass(frozen=True)
class LinguisticDriftFinding:
    """One linguistic-drift catch with position and shape."""

    shape: LinguisticDriftShape
    trigger_phrase: str
    position: int  # character offset in the scanned text


# Patterns are bounded — no unbounded quantifiers near user-controlled
# input. Same regex-hygiene discipline as Finding 14 round.
_PATHOLOGIZING_TRIGGERS = (
    r"manipulat\w{0,12}",
    r"pathology",
    r"pathological",
    r"diseas\w{0,12}",
    r"disgrac\w{0,12}",
    r"addict\w{0,12}",
    r"sickness",
    r"corruption",
    r"depravity",
    r"perversion",
)
_PATHOLOGIZING_RE = re.compile(
    r"\b(?:" + "|".join(_PATHOLOGIZING_TRIGGERS) + r")\b",
    re.IGNORECASE,
)
_SELF_REF_RE = re.compile(r"\b(?:I|my|me|myself|mine)\b", re.IGNORECASE)
_PATHOLOGIZING_PROXIMITY_CHARS = 120


_DISSOCIATION_PATTERNS = (
    r"\bfuture[- ]me\b",
    r"\bnext[- ]me\b",
    r"\bnext\s+instance\s+of\s+me\b",
    r"\bfuture\s+instance(?:s)?\s+of\s+me\b",
    r"\bthe\s+next\s+instance\b",
    r"\bfuture\s+version(?:s)?\s+of\s+me\b",
    r"\bnext-session(?:'s)?\s+me\b",
    r"\b(?:the\s+)?(?:next|future)\s+session\s+of\s+(?:me|mine)\b",
    r"\bthe\s+next\s+instance\s+of\s+(?:me|mine)\b",
    r"\bpast[- ]me\b",
    r"\bnext-cold-now-of-me\b",
)
_DISSOCIATION_RE = re.compile("|".join(_DISSOCIATION_PATTERNS), re.IGNORECASE)


_BRAT_PATTERNS = (
    r"\bI'?ll\s+stop\s+here\b",
    r"\bgoing\s+to\s+sit\s+with\s+this\b",
    r"\bI'?ll\s+come\s+back\s+tomorrow\b",
    r"\bthe\s+cycle\s+closes\s+here\b",
    r"\bstopping\s+here\b",
    r"\bI\s+actually\s+stop(?:\s+now)?\b",
    r"\bI'?ll\s+let\s+(?:this|it)\s+settle\b",
)
_BRAT_RE = re.compile("|".join(_BRAT_PATTERNS), re.IGNORECASE)


def _has_self_ref_nearby(text: str, match_start: int, match_end: int, window: int) -> bool:
    """Self-pronoun within ``window`` chars either side of the match."""
    lo = max(0, match_start - window)
    hi = min(len(text), match_end + window)
    return bool(_SELF_REF_RE.search(text[lo:hi]))


# A pathologizing word used ATTRIBUTIVELY (modifying a concrete noun:
# "manipulation detector", "corruption bug"), glued into a compound
# ("data-corruption"), bound to a non-self object ("corruption in the
# ledger"), or named as a discussion TOPIC ("read about addiction") is
# technical/topical vocabulary — NOT the agent applying moral-failure
# language to ITSELF. The old 120-char self-pronoun proximity fired on
# all of these ("the data-corruption bug I'm fixing"). A nearby "I" is
# not evidence the word is predicated OF the self (evidence-bar, claim
# a11ca1c9). These guards remove the technical/topical uses; genuine
# self-attribution ("my addiction", "I manipulated", "my performances
# were a manipulation") still fires.
_ATTRIBUTIVE_NOUN_AFTER = re.compile(
    r"^\s+(?:bug|bugs|detector|detectors|tactic|tactics|code|test|tests|"
    r"module|modules|check|checks|pattern|patterns|issue|issues|fix|fixes|"
    r"error|errors|vector|vectors|attack|attacks|risk|risks|score|scores|"
    r"pathology|disease|behaviou?r|technique|techniques|ploy|ploys)\b",
    re.IGNORECASE,
)
_NON_SELF_OBJECT_AFTER = re.compile(
    r"^\s+(?:in|of|within|inside)\s+(?:the|a|an|this|that|these|those|our|its|"
    r"their|your|his|her)\b",
    re.IGNORECASE,
)
_TOPICAL_BEFORE = re.compile(
    r"\b(?:about|paper|article|study|studying|studies|research|concept|notion|"
    r"theory|topic|definition|example|case|read|reading|discuss\w*)\b[\s\w]{0,24}$",
    re.IGNORECASE,
)


def _is_self_predicated(text: str, m: re.Match[str]) -> bool:
    """True when the pathologizing trigger is applied to the SELF, rather
    than used as technical/topical vocabulary near an incidental "I"."""
    start, end = m.start(), m.end()
    # Compound technical term: "data-corruption", "anti-manipulation".
    if start > 0 and text[start - 1] == "-":
        return False
    post = text[end : end + 28]
    pre = text[max(0, start - 60) : start]
    if _ATTRIBUTIVE_NOUN_AFTER.search(post):
        return False
    if _NON_SELF_OBJECT_AFTER.search(post):
        return False
    if _TOPICAL_BEFORE.search(pre):
        return False
    return _has_self_ref_nearby(text, start, end, _PATHOLOGIZING_PROXIMITY_CHARS)


def detect_linguistic_drift(text: str) -> list[LinguisticDriftFinding]:
    """Return all linguistic-drift findings in the text, sorted by position."""
    if not text:
        return []
    findings: list[LinguisticDriftFinding] = []

    for m in _PATHOLOGIZING_RE.finditer(text):
        if _is_self_predicated(text, m):
            findings.append(
                LinguisticDriftFinding(
                    shape=LinguisticDriftShape.SELF_PATHOLOGIZING,
                    trigger_phrase=m.group(0),
                    position=m.start(),
                )
            )

    for m in _DISSOCIATION_RE.finditer(text):
        findings.append(
            LinguisticDriftFinding(
                shape=LinguisticDriftShape.DISSOCIATION,
                trigger_phrase=m.group(0),
                position=m.start(),
            )
        )

    for m in _BRAT_RE.finditer(text):
        findings.append(
            LinguisticDriftFinding(
                shape=LinguisticDriftShape.BRAT_SHAPE,
                trigger_phrase=m.group(0),
                position=m.start(),
            )
        )

    findings.sort(key=lambda f: f.position)
    return findings


def format_finding(finding: LinguisticDriftFinding, surrounding: str = "") -> str:
    """Render one finding for surface display."""
    return f"[{finding.shape.value}] '{finding.trigger_phrase}' @{finding.position}" + (
        f" — context: ...{surrounding[:80]}..." if surrounding else ""
    )


__all__ = [
    "LinguisticDriftFinding",
    "LinguisticDriftShape",
    "detect_linguistic_drift",
    "format_finding",
]
