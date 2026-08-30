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

# Document-level meta-saturation. Added 2026-08-06 after three consecutive
# false-positive fires, two of them labelled into the corpus by hand.
#
# THE DEFECT WAS STRUCTURAL, NOT LEXICAL. Suppression was evaluated per USE
# match with an implicit OR: a reply saturated with meta-discussion still fired
# if ONE clause happened to sit in a clean 150-char window, and then reported
# confidence 1.0 because the confidence is that of the LEAST-suppressed match.
# A document-level judgment made from a single local sample and reported as a
# census — the same shape as the 100-file API cap that had me call a 446-file
# PR safe (correction #121).
#
# Adding suppressor words would have been whack-a-mole (Aether #151). This
# instead asks a question the per-match loop cannot: is the reply AS A WHOLE
# a discussion about correction?
#
# Measured separation on the two classes:
#   meta-heavy reply about the detector : 2.5 mention-hits per USE clause
#   bare admission ("I was wrong")      : 0.0
#
# CAN ONLY SUPPRESS, NEVER SENSITISE. Below the ratio, behaviour is byte-for-
# byte what it was. Above it, a window must be COMPLETELY clean to fire rather
# than merely under threshold. No USE pattern was touched; weakening the
# admission side is the shape that would let me tune my way out of being
# caught, so the fix deliberately does not go near it.
_META_SATURATION_RATIO = 2.0


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
    # True when document-level meta-saturation held back a fire that the
    # per-match rule alone would have produced. Never silent: a density
    # threshold on my own output is gameable, so each use of the relaxation
    # is on the record rather than merely making the gate quieter.
    saturation_suppressed: bool = False


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
        # The count belonging to the match that ACTUALLY DECIDED the verdict.
        # Reporting max_mention_hits in the fire branch produced literally
        # false diagnostics -- an observed fire read "MENTION suppressors
        # within window (2) below threshold (2)", because the decision came
        # from the LEAST-suppressed match while the message quoted the MOST-
        # suppressed one. The number reported was not the number the decision
        # used, which is the same defect as judging a document from one window
        # (see _META_SATURATION_RATIO above). A diagnostic I cannot trust is
        # worse than none: it sends triage at the wrong match.
        deciding_mention_hits: int | None = None
        min_mention_hits: int | None = None

        # Document-level question the per-match loop cannot ask: is this reply
        # AS A WHOLE a discussion about correction? A local window of 150 chars
        # cannot see that, which is how a meta-saturated reply fired at
        # confidence 1.0 off one clean clause.
        doc_mention_hits = sum(len(mp.findall(text)) for mp in _MENTION_PATTERNS)
        meta_ratio = doc_mention_hits / max(1, len(use_matches))
        saturated = meta_ratio >= _META_SATURATION_RATIO
        # Saturated documents demand a COMPLETELY clean window. Unsaturated
        # ones keep the original threshold exactly — this can only suppress.
        effective_threshold = 1 if saturated else _SUPPRESSOR_THRESHOLD
        # THE THRESHOLD IS NOT TRUSTED. Substrate knowledge (36x accessed):
        # "any output-surface measurement -- regex marker-counts, density
        # thresholds, phrase enumeration -- is fundamentally gameable by the
        # optimizer that produces the output." That is exactly what this is,
        # and it widens the gaming surface in one direction: sprinkle meta
        # vocabulary and a real admission goes quiet.
        #
        # So every use of the relaxation is RECORDED in the verdict rather than
        # applied silently. If I ever start writing meta-heavy near admissions,
        # the record shows the pattern instead of the gate simply going quiet.
        # An invisible weakening would be gaming; a measured one is evidence.
        saturation_suppressed = False

        for _p_idx, matched, position in use_matches:
            window_start = max(0, position - _SUPPRESSOR_WINDOW)
            window_end = min(len(text), position + len(matched) + _SUPPRESSOR_WINDOW)
            window_text = text[window_start:window_end]

            mention_count = 0
            for mp in _MENTION_PATTERNS:
                mention_count += len(mp.findall(window_text))
            max_mention_hits = max(max_mention_hits, mention_count)
            min_mention_hits = (
                mention_count if min_mention_hits is None else min(min_mention_hits, mention_count)
            )

            if mention_count < _SUPPRESSOR_THRESHOLD and mention_count >= effective_threshold:
                # Would have fired under the old rule; saturation held it back.
                # Recorded, never silent — see _saturation_suppressed below.
                saturation_suppressed = True
            if mention_count < effective_threshold:
                # Fire — this USE match is not surrounded by heavy
                # meta-discussion. Confidence = 1.0 minus fraction of
                # threshold consumed by mentions.
                conf = 1.0 - (mention_count / max(1, _SUPPRESSOR_THRESHOLD))
                if conf > best_fire_confidence:
                    best_fire_confidence = conf
                    deciding_mention_hits = mention_count

        if best_fire_confidence > 0.0:
            return SelfAdmissionVerdict(
                verdict="fire",
                confidence=best_fire_confidence,
                use_matches=use_matches,
                mention_hits=max_mention_hits,
                reason=(
                    f"USE clause matched ({len(use_matches)} hits); "
                    f"the deciding clause had {deciding_mention_hits} MENTION "
                    f"suppressor(s) in its window, below threshold "
                    f"({effective_threshold})"
                    + (
                        f" [other clauses had up to {max_mention_hits}]"
                        if max_mention_hits != deciding_mention_hits
                        else ""
                    )
                ),
            )
        else:
            return SelfAdmissionVerdict(
                verdict="silence",
                confidence=0.0,
                use_matches=use_matches,
                mention_hits=max_mention_hits,
                saturation_suppressed=saturation_suppressed,
                reason=(
                    f"USE clause matched ({len(use_matches)} hits) but "
                    f"MENTION suppressors dominate every window "
                    f"(the LEAST-suppressed had {min_mention_hits}, "
                    f">= threshold {effective_threshold})"
                    + (
                        f" | SATURATION-SUPPRESSED: the whole reply reads as "
                        f"meta-discussion ({meta_ratio:.1f} mention-hits per USE "
                        f"clause); this fire was held back by the document-level "
                        f"rule, not by the local windows. On the record because a "
                        f"density threshold on my own output is gameable."
                        if saturation_suppressed
                        else ""
                    )
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
