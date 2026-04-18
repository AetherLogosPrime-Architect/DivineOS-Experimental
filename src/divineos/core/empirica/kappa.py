"""Cohen's kappa — inter-rater agreement for EMPIRICA classifier.

Audit finding find-f66a5f423ffe (Kahneman): "agreement between
the classifier and a gold standard is not measured." Raw accuracy
is an inflated metric when classes are imbalanced — if 80% of
claims are OUTCOME, a classifier that labels everything OUTCOME
gets 80% accuracy and tells you nothing.

Cohen's kappa corrects for chance agreement:

    κ = (p_o - p_e) / (1 - p_e)

where p_o is observed agreement and p_e is the agreement expected
by chance given each rater's marginal distributions. κ = 1 means
perfect agreement; κ = 0 means no better than chance; κ < 0 means
worse than chance.

Landis & Koch (1977) conventions (rough, not gospel):

* κ < 0.00   — poor
* 0.01-0.20  — slight
* 0.21-0.40  — fair
* 0.41-0.60  — moderate
* 0.61-0.80  — substantial
* 0.81-1.00  — near-perfect

This module:

* Computes kappa between two rater sequences.
* Provides a tiny gold-standard fixture (``gold_tier_labels``)
  seeded from handwritten examples. Designed to be extended.
* ``measure_classifier_agreement`` runs the classifier over the
  fixture and returns kappa + the confusion matrix + per-label
  counts so disagreements are diagnosable, not just scored.

What this module is NOT:

* NOT a validation suite. Kappa is a diagnostic. A high kappa on
  a small fixture doesn't prove the classifier generalizes; a
  low kappa tells you something is wrong.
* NOT a grading machine. It does not PASS or FAIL the classifier;
  it reports the number. Interpretation is the operator's.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from divineos.core.empirica.classifier import classify_claim
from divineos.core.empirica.types import Tier


@dataclass(frozen=True)
class KappaResult:
    """Result of a Cohen's kappa computation.

    Attributes:
        kappa: The coefficient. 1.0 = perfect, 0.0 = chance,
            negative = worse than chance.
        observed_agreement: p_o — raw fraction of items where
            raters agreed.
        expected_agreement: p_e — fraction that would agree by
            chance given marginal distributions.
        n: number of items rated.
        confusion: nested dict indexed by (rater_a_label,
            rater_b_label) giving the co-occurrence count.
        per_label_counts_a: how many times each label appeared
            from rater A.
        per_label_counts_b: same for rater B.
    """

    kappa: float
    observed_agreement: float
    expected_agreement: float
    n: int
    confusion: dict[str, dict[str, int]]
    per_label_counts_a: dict[str, int]
    per_label_counts_b: dict[str, int]


def cohens_kappa(rater_a: Sequence[str], rater_b: Sequence[str]) -> KappaResult:
    """Compute Cohen's kappa between two rater sequences.

    Args:
        rater_a: the first rater's labels (e.g. gold standard).
        rater_b: the second rater's labels (e.g. classifier output).
            Must be same length as rater_a.

    Returns:
        KappaResult with kappa, agreements, and confusion matrix.

    Raises:
        ValueError: if the two sequences differ in length or are
            empty.
    """
    if len(rater_a) != len(rater_b):
        raise ValueError(
            f"Rater sequences must be equal length: got {len(rater_a)} vs {len(rater_b)}"
        )
    n = len(rater_a)
    if n == 0:
        raise ValueError("Cannot compute kappa on empty sequences")

    # Build confusion matrix and marginals.
    all_labels = sorted(set(rater_a) | set(rater_b))
    confusion: dict[str, dict[str, int]] = {a: {b: 0 for b in all_labels} for a in all_labels}
    counts_a: dict[str, int] = {lab: 0 for lab in all_labels}
    counts_b: dict[str, int] = {lab: 0 for lab in all_labels}

    agree = 0
    for a, b in zip(rater_a, rater_b):
        confusion[a][b] += 1
        counts_a[a] += 1
        counts_b[b] += 1
        if a == b:
            agree += 1

    p_o = agree / n
    # Expected agreement = sum over labels of (p_a(label) * p_b(label))
    p_e = sum((counts_a[lab] / n) * (counts_b[lab] / n) for lab in all_labels)

    if p_e >= 1.0:
        # Degenerate: both raters gave the same label to every
        # item. Kappa is undefined in the 1/(1-p_e) form. Treat
        # it as "perfect if they agree, else worst agreement".
        kappa = 1.0 if p_o == 1.0 else 0.0
    else:
        kappa = (p_o - p_e) / (1 - p_e)

    return KappaResult(
        kappa=kappa,
        observed_agreement=p_o,
        expected_agreement=p_e,
        n=n,
        confusion=confusion,
        per_label_counts_a=counts_a,
        per_label_counts_b=counts_b,
    )


# ---------------------------------------------------------------------------
# Gold-standard fixture for tier classification.
# ---------------------------------------------------------------------------
#
# Each entry: (content, knowledge_type, source, artifact_pointer,
# expected_tier). Designed so each tier has at least a few clear
# cases. Extend this fixture as the classifier matures — that's
# how the kappa measurement keeps its teeth.

_GOLD_TIER_LABELS: list[tuple[str, str | None, str | None, str | None, Tier]] = [
    # OUTCOME: the honest middle. PRINCIPLE/BOUNDARY/MISTAKE/DIRECTIVE.
    ("Keep it conversational, avoid jargon.", "PRINCIPLE", None, None, Tier.OUTCOME),
    (
        "Never commit changes unless the user explicitly asks.",
        "BOUNDARY",
        None,
        None,
        Tier.OUTCOME,
    ),
    ("I forgot to run tests after editing.", "MISTAKE", None, None, Tier.OUTCOME),
    ("Run divineos briefing at the start of every session.", "DIRECTIVE", None, None, Tier.OUTCOME),
    # FALSIFIABLE: facts from measurement with a pointer.
    (
        "The SWE-bench score for Sonnet with council is 2.4x baseline.",
        "FACT",
        "measured",
        "commit-abc123",
        Tier.FALSIFIABLE,
    ),
    (
        "Ledger write throughput: 500 events/sec on this hardware.",
        "FACT",
        "measured",
        "bench-2026-04-17",
        Tier.FALSIFIABLE,
    ),
    # PATTERN: recurring phenomenon with a pointer.
    (
        "Pattern: I reach for technical jargon before finishing the thought in plain words.",
        "PATTERN",
        None,
        "decide-xyz",
        Tier.PATTERN,
    ),
    (
        "Recurring across multiple sessions: compass fires when I spawn parallel agents.",
        None,
        None,
        "session-2026-04-17",
        Tier.PATTERN,
    ),
    # OUTCOME fallback: FACT without 'measured' source stays in OUTCOME.
    ("The project is called DivineOS.", "FACT", None, None, Tier.OUTCOME),
    # OUTCOME: PATTERN without pointer demotes to OUTCOME (Aria's rule).
    (
        "Pattern: I default to binary choices when yes-and exists.",
        "PATTERN",
        None,
        None,
        Tier.OUTCOME,
    ),
]


def gold_tier_labels() -> list[tuple[str, str | None, str | None, str | None, Tier]]:
    """Return the gold-standard fixture for tier classification.

    Each entry is ``(content, knowledge_type, source,
    artifact_pointer, expected_tier)``. ``None`` values are passed
    through to the classifier unchanged.

    Extend this list as the classifier matures. Every addition
    should be a case where the tier label is obvious to a human
    rater without reading the classifier source.
    """
    return [(content, kt, src, ptr, tier) for (content, kt, src, ptr, tier) in _GOLD_TIER_LABELS]


def measure_classifier_agreement() -> KappaResult:
    """Run the classifier over the gold fixture and compute kappa.

    Returns a ``KappaResult`` with the kappa coefficient, observed
    vs expected agreement, and a confusion matrix so disagreements
    are diagnosable. Caller decides what to do with the number —
    this function does not raise on low agreement.
    """
    gold_labels: list[str] = []
    classifier_labels: list[str] = []

    for content, kt, src, ptr, expected in gold_tier_labels():
        # classify_claim treats missing strings as empty, not None.
        classification = classify_claim(
            content,
            knowledge_type=kt if kt is not None else "",
            source=src if src is not None else "",
            artifact_pointer=ptr,
        )
        gold_labels.append(expected.value)
        classifier_labels.append(classification.tier.value)

    return cohens_kappa(gold_labels, classifier_labels)


__all__ = [
    "KappaResult",
    "cohens_kappa",
    "gold_tier_labels",
    "measure_classifier_agreement",
]
