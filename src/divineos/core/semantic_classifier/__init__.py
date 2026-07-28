"""Semantic classifier for gate-fire discrimination.

Andrew 2026-07-27: keyword detectors are the wrong shape for
enforcement (infinite whack-a-mole, easy to subvert, always false-
firing). Semantic-similarity classification against a labeled corpus
of past fires is the right shape for enforcement — same principle as
Aria's 2026-06-16 signal-based-gates design: gates should prove
their claims with evidence, not guess with a counter.

Corpus:
  - Positive examples: entries in family/andrew_corrections.db, which
    are texts that the current keyword detector correctly identified
    as real corrections requiring integration.
  - Negative examples: ``original_trigger`` fields from
    ~/.divineos/cli_broken_escapes.jsonl, which are texts the current
    keyword detector fired on that I had to clear as false-positives
    (with a named reason) via clear_correction_marker.py.

Both sources grow organically as the system runs. The classifier
becomes more accurate over time WITHOUT me having to build training
data by hand — the telemetry IS the training data (Andrew 2026-07-27
teaching: "assloads of training data.. literally every false fire you
have encountered").

Public API:
  - load_correction_corpus() -> (texts, labels)
  - SemanticClassifier(corpus) -> classifier
  - classifier.classify(text) -> (verdict, confidence)
"""

from divineos.core.semantic_classifier.classifier import SemanticClassifier
from divineos.core.semantic_classifier.corpus import load_correction_corpus

__all__ = [
    "SemanticClassifier",
    "load_correction_corpus",
]
