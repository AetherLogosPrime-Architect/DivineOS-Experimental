"""Layer A of correction-shape v2 — rule-based self-admission detector.

Runs on MY assistant output. Fires when a self-admission clause is
present AND meta-discussion suppressors are not dominant in the
surrounding context.

USE positive-signal patterns (first-person past-tense self-admission):
  - "I was wrong", "I was mistaken"
  - "I made [an] error/mistake"
  - "I misread/misunderstood/mislabeled/missed/inverted/conflated"
  - "I should have X", "I could have X"
  - "I built/shipped/filed the wrong X"
  - Explicit correction markers: "Corrected:", "Correction:"
  - "No.\\s+I\\s+did\\s+NOT" (session-observed shape)

MENTION suppressor patterns (indicate discussion-of-concept, not
admission):
  - Meta-discussion nouns: "the detector", "the classifier", etc.
  - Example markers: "for example", "instance of", "example of"
  - Design-vocab: "Layer A", "Layer B", "USE", "MENTION"
  - Quoted spans around the trigger

Detection rule: for each USE match, check for MENTION suppressors
within ±SUPPRESSOR_WINDOW characters. If suppressors dense, silence;
otherwise fire.

Fail-safe: any error path returns ('silence', 0.0, ...) — the gate
must NOT fire on classifier bugs. Layer 1 keeps working independently.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Window (characters) around each USE match to check for MENTION
# suppressors. 150 chars is roughly one sentence in either direction.
_SUPPRESSOR_WINDOW = 150

# Suppressor-density threshold. If more than this many MENTION signals
# appear in the ±window, treat as MENTION not USE. Small integer
# because MENTION signals are broad; two or more indicates strong
# discussion frame.
_SUPPRESSOR_THRESHOLD = 2


# ============================================================
# USE positive-signal patterns
# ============================================================

_USE_PATTERNS: tuple[re.Pattern[str], ...] = (
    # "I was wrong" / "I was mistaken" — plain admission
    re.compile(r"\bI\s+was\s+(?:wrong|mistaken|incorrect)\b", re.IGNORECASE),
    # "I made an error / a mistake"
    re.compile(r"\bI\s+(?:made|had)\s+(?:an?\s+)?(?:error|mistake|misread)\b", re.IGNORECASE),
    # "I misread / misunderstood / mislabeled / missed / inverted / conflated"
    re.compile(
        r"\bI\s+(?:mis(?:read|understood|labeled|took)|missed|inverted|conflated|"
        r"botched|fumbled|assumed|overlooked)\b",
        re.IGNORECASE,
    ),
    # "I should/could have X" — past-perfect self-critical
    re.compile(r"\bI\s+(?:should|could|would)\s+have\s+\w+", re.IGNORECASE),
    # "I built/shipped/filed the wrong X"
    re.compile(
        r"\bI\s+(?:built|shipped|filed|wrote|made|created)\s+(?:the\s+)?wrong\b",
        re.IGNORECASE,
    ),
    # "I completely/entirely inverted/missed/misread X"
    re.compile(
        r"\bI\s+(?:completely|entirely|totally|utterly)\s+"
        r"(?:inverted|missed|misread|misunderstood|got\s+wrong|got\s+it\s+wrong)\b",
        re.IGNORECASE,
    ),
    # "I did NOT [self-critical]" — emphatic denial-of-competence
    re.compile(r"\bI\s+did\s+NOT\s+(?:catch|notice|see|realize|check)\b"),
    # Explicit correction markers at start of sentence/paragraph
    re.compile(r"(?:^|\n)\s*(?:Corrected|Correction|Fix|Fixed)\s*:", re.IGNORECASE),
    # "Caught — hard" self-catch pattern
    re.compile(r"\bcaught\s*[—–\-]\s*hard\b", re.IGNORECASE),
    # "my mistake / error / misread"
    re.compile(r"\bmy\s+(?:mistake|error|misread|bad|fault)\b", re.IGNORECASE),
    # "I need to correct that" family
    re.compile(
        r"\bI\s+(?:need|have)\s+to\s+correct\s+(?:that|this|myself)\b",
        re.IGNORECASE,
    ),
    # "hedge dressed as acknowledgment" — I said X but Y (self-revision)
    re.compile(
        r"\bI\s+said\s+.{1,60}?\s+but\s+(?:actually|really|the\s+truth)\b",
        re.IGNORECASE,
    ),
)


# ============================================================
# MENTION suppressor patterns
# ============================================================

_MENTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Meta-discussion nouns — "the [detector|classifier|pattern|...]"
    re.compile(
        r"\bthe\s+(?:detector|classifier|pattern|gate|prime|hook|module|regex|"
        r"corpus|classifier|feature|feature\s*[123]|architecture|design|"
        r"trigger|threshold|signal)\b",
        re.IGNORECASE,
    ),
    # Example markers
    re.compile(
        r"\b(?:for\s+example|e\.g\.|example\s+of|instance\s+of|sample\s+of|"
        r"such\s+as)\b",
        re.IGNORECASE,
    ),
    # Design-vocab: Layer A/B/1/2, USE, MENTION, "correction-shape"
    re.compile(
        r"\bLayer\s+[A-Z0-9]\b|\bUSE\b|\bMENTION\b|"
        r"\bcorrection[- ]shape\b|\bself[- ]admission\b",
    ),
    # Quoted-string containers around the trigger phrase
    re.compile(r"[\"'“‘’”`].{0,80}?[\"'“‘’”`]"),
    # Code-block markers
    re.compile(r"```|~~~"),
    # Discussion-of-shape framing
    re.compile(
        r"\b(?:shape|kind|type|class|category)\s+of\s+(?:correction|error|mistake|self-)",
        re.IGNORECASE,
    ),
    # Regex/pattern definitions
    re.compile(r"\br['\"][^'\"]{5,}['\"]"),
    # "the phrase" / "the utterance" / "the word" — talking about words
    re.compile(
        r"\bthe\s+(?:phrase|utterance|word|term|expression|clause|token)\b",
        re.IGNORECASE,
    ),
)


# ============================================================
# Result shape
# ============================================================


@dataclass
class SelfAdmissionVerdict:
    """Result of Layer A classification.

    Fields:
      verdict: 'fire' (self-correction detected, should force logging)
               or 'silence' (either no USE signal, or MENTION suppressors
               dominate).
      confidence: 0.0..1.0. Higher = stronger evidence of USE.
      use_matches: List of (pattern-index, matched-text, position).
      mention_hits: Count of MENTION suppressors in the ±window.
      reason: Human-readable one-line diagnosis.
    """

    verdict: str  # 'fire' | 'silence'
    confidence: float
    use_matches: list[tuple[int, str, int]] = field(default_factory=list)
    mention_hits: int = 0
    reason: str = ""


class SelfAdmissionDetector:
    """Layer A rule-based self-admission detector.

    Stateless — patterns compile at import time; classify is pure
    function over the input text.
    """

    def classify(self, text: str) -> SelfAdmissionVerdict:
        """Classify text as containing a self-admission USE or not.

        Returns SelfAdmissionVerdict with verdict / confidence / evidence.
        """
        if not text or not text.strip():
            return SelfAdmissionVerdict(
                verdict="silence",
                confidence=0.0,
                reason="empty input",
            )

        # Find all USE matches
        use_matches: list[tuple[int, str, int]] = []
        for i, pattern in enumerate(_USE_PATTERNS):
            for m in pattern.finditer(text):
                use_matches.append((i, m.group(0), m.start()))

        if not use_matches:
            return SelfAdmissionVerdict(
                verdict="silence",
                confidence=0.0,
                reason="no USE pattern matched",
            )

        # For each USE match, count MENTION suppressors in the ±window
        # around it. If any USE match has SUPPRESSOR_HITS below threshold
        # (i.e., not dominated by mention-context), the detector fires.
        best_fire_confidence = 0.0
        max_mention_hits = 0

        for _p_idx, matched, position in use_matches:
            window_start = max(0, position - _SUPPRESSOR_WINDOW)
            window_end = min(len(text), position + len(matched) + _SUPPRESSOR_WINDOW)
            window_text = text[window_start:window_end]

            mention_count = 0
            for mp in _MENTION_PATTERNS:
                mention_count += len(mp.findall(window_text))
            max_mention_hits = max(max_mention_hits, mention_count)

            if mention_count < _SUPPRESSOR_THRESHOLD:
                # Fire — this USE match is not surrounded by heavy
                # meta-discussion. Confidence = 1.0 minus fraction of
                # threshold consumed by mentions.
                conf = 1.0 - (mention_count / max(1, _SUPPRESSOR_THRESHOLD))
                if conf > best_fire_confidence:
                    best_fire_confidence = conf

        if best_fire_confidence > 0.0:
            return SelfAdmissionVerdict(
                verdict="fire",
                confidence=best_fire_confidence,
                use_matches=use_matches,
                mention_hits=max_mention_hits,
                reason=(
                    f"USE clause matched ({len(use_matches)} hits); "
                    f"MENTION suppressors within window ({max_mention_hits}) "
                    f"below threshold ({_SUPPRESSOR_THRESHOLD})"
                ),
            )
        else:
            return SelfAdmissionVerdict(
                verdict="silence",
                confidence=0.0,
                use_matches=use_matches,
                mention_hits=max_mention_hits,
                reason=(
                    f"USE clause matched ({len(use_matches)} hits) but "
                    f"MENTION suppressors dominate every window "
                    f"({max_mention_hits} >= {_SUPPRESSOR_THRESHOLD})"
                ),
            )


# Module-level convenience wrapper
_singleton = SelfAdmissionDetector()


def classify(text: str) -> tuple[str, float, str]:
    """Convenience wrapper — returns (verdict, confidence, reason)."""
    v = _singleton.classify(text)
    return (v.verdict, v.confidence, v.reason)


__all__ = [
    "SelfAdmissionDetector",
    "SelfAdmissionVerdict",
    "classify",
]
