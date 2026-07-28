"""TF-IDF nearest-neighbor semantic classifier.

Given a text that a keyword detector would fire on, decide whether
the text is truly a correction (positive → fire the gate) or a false-
positive (negative → silence the gate) based on cosine similarity to
labeled examples in the corpus.

Design decisions:

- **TF-IDF + cosine + weighted-KNN** rather than deep embeddings.
  sklearn is already available; deep embedding models are not. This
  is v1 — measurably better than pure keyword-matching, no external
  dependencies, no per-call API cost. Upgrade path to embeddings is
  clean if v1 proves insufficient.

- **Weighted vote** by inverse-distance so a very-near labeled
  neighbor counts more than a barely-near one. Prevents distant
  ties from misclassifying.

- **Class-imbalance handling**: positives (~169) outnumber negatives
  (~24) roughly 7:1 as of 2026-07-27. Without correction the KNN
  vote would default-positive for anything ambiguous. We normalize
  the vote by class prior so the classifier reports the SHAPE of
  the neighborhood, not the base rate.

- **Fail-safe default**: if the corpus is empty or the classifier
  errors, classify returns ``('fire', 0.0)`` — meaning the caller
  should honor the keyword detector's original verdict. Never
  silence a keyword-fire based on a broken classifier.

Public API:
    SemanticClassifier(corpus_texts, corpus_labels) — build from corpus
    classifier.classify(text) -> (verdict, confidence)
        verdict: 'fire' or 'silence'
        confidence: 0.0..1.0 (0.0 = no evidence, silencing suppressed)
"""

from __future__ import annotations

from typing import Any

from divineos.core.semantic_classifier.corpus import (
    LABEL_NEGATIVE,
    LABEL_POSITIVE,
)

# Minimum corpus size required to run the classifier. Below this, we
# fall back to fire-verdict (honor the keyword detector). Chosen so
# the classifier has at least a handful of examples per class before
# it's allowed to override the keyword layer.
_MIN_CORPUS_SIZE = 20
_MIN_NEGATIVES = 5

# Number of nearest neighbors to consider for the weighted vote.
# Small K works well on small corpora and captures local structure.
_K_NEIGHBORS = 5

# Similarity threshold below which the classifier abstains (fire, 0.0).
# If nothing in the corpus is within this cosine similarity, there's
# no meaningful signal to override the keyword layer.
_MIN_SIMILARITY = 0.15


class SemanticClassifier:
    """Nearest-neighbor classifier with graceful degradation."""

    def __init__(
        self,
        corpus_texts: list[str],
        corpus_labels: list[str],
    ) -> None:
        self._texts = corpus_texts
        self._labels = corpus_labels
        self._ready = False
        self._vectorizer: Any = None
        self._matrix: Any = None
        self._n_positives = 0
        self._n_negatives = 0

        if not self._corpus_sufficient():
            return

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer

            self._vectorizer = TfidfVectorizer(
                lowercase=True,
                strip_accents="unicode",
                ngram_range=(1, 2),
                min_df=1,
                max_df=0.95,
                sublinear_tf=True,
            )
            self._matrix = self._vectorizer.fit_transform(corpus_texts)
            self._n_positives = sum(1 for lbl in corpus_labels if lbl == LABEL_POSITIVE)
            self._n_negatives = sum(1 for lbl in corpus_labels if lbl == LABEL_NEGATIVE)
            self._ready = True
        except (ImportError, ValueError):
            # sklearn missing or corpus too degenerate for TF-IDF —
            # fall back to fire-verdict for all inputs.
            self._ready = False

    def _corpus_sufficient(self) -> bool:
        """True iff corpus has enough data to make classification meaningful."""
        if len(self._texts) < _MIN_CORPUS_SIZE:
            return False
        n_neg = sum(1 for lbl in self._labels if lbl == LABEL_NEGATIVE)
        return n_neg >= _MIN_NEGATIVES

    def classify(self, text: str) -> tuple[str, float]:
        """Classify ``text`` as ``('fire', conf)`` or ``('silence', conf)``.

        Fail-safe: any error path returns ``('fire', 0.0)`` — the
        caller should honor the keyword detector's original verdict.
        Never silence a keyword-fire based on a broken classifier.
        """
        if not self._ready or not text or not text.strip():
            return ("fire", 0.0)

        try:
            from sklearn.metrics.pairwise import cosine_similarity
        except ImportError:
            return ("fire", 0.0)

        try:
            query_vec = self._vectorizer.transform([text])
            similarities = cosine_similarity(query_vec, self._matrix)[0]
        except (ValueError, AttributeError):
            return ("fire", 0.0)

        # Find K nearest neighbors by cosine similarity (highest first).
        k = min(_K_NEIGHBORS, len(similarities))
        # argsort gives ascending indices; take last k and reverse.
        top_indices = list(similarities.argsort()[-k:][::-1])

        # If the best neighbor is below the minimum-similarity floor,
        # there's no meaningful signal; honor the keyword verdict.
        if similarities[top_indices[0]] < _MIN_SIMILARITY:
            return ("fire", 0.0)

        # Weighted vote by similarity, normalized by class prior so
        # the vote reports the SHAPE of the neighborhood, not the
        # base rate. Weight = similarity / class_prior.
        pos_weight = 0.0
        neg_weight = 0.0
        pos_prior = max(self._n_positives / max(1, len(self._labels)), 1e-6)
        neg_prior = max(self._n_negatives / max(1, len(self._labels)), 1e-6)

        for idx in top_indices:
            sim = float(similarities[idx])
            if sim < _MIN_SIMILARITY:
                continue
            label = self._labels[idx]
            if label == LABEL_POSITIVE:
                pos_weight += sim / pos_prior
            elif label == LABEL_NEGATIVE:
                neg_weight += sim / neg_prior

        total_weight = pos_weight + neg_weight
        if total_weight <= 0:
            return ("fire", 0.0)

        # Verdict = whichever class dominates the weighted vote.
        # Confidence = normalized share of the winning class.
        if neg_weight > pos_weight:
            return ("silence", neg_weight / total_weight)
        else:
            return ("fire", pos_weight / total_weight)


__all__ = ["SemanticClassifier"]
