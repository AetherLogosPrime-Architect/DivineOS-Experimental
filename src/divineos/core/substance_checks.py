"""Substance checks at rudder-ack file time — Item 7.

The rudder's purpose is to force reflection when drift is detected. A
rudder-ack with empty-ish or duplicated evidence passes the existing
"non-empty evidence" schema check but doesn't deliver reflection. Item 7
adds inline substance checks at observation-write time so trivial or
copy-pasted acks are rejected at the source.

Three-stage gate (short-circuits on first failure):

    1. Minimum length — len(evidence.strip()) >= 20 chars. Reject
       empty-ish cases before any math. Shannon entropy is noisy on
       very short strings, so length runs first.

    2. Entropy floor — Shannon entropy over character frequencies.
       Catches repetitive "aaaaaaaaaaaaaaaaaaaa" patterns that pass
       the length check.

    3. Variance-collapse — TF-IDF cosine similarity vs. recent acks
       on the same spectrum. If the new ack is substantially similar
       to a prior ack, reject with a pointer to the match so the
       operator can rephrase.

Each stage has a feature flag (DIVINEOS_DETECTOR_SUBSTANCE_LENGTH /
_ENTROPY / _SIMILARITY) defaulting to "on". Setting a flag to "off"
disables that stage at runtime without re-shipping under the gate —
this is the cross-cutting rollback mechanism from design brief v2.

Rejection-loop surfacing: rejections are written to the
failure_diagnostics ``rudder-ack`` surface. On the 3rd rejection on the
same spectrum within a window, a RUDDER_ACK_REJECTION_ESCALATED ledger
event is emitted and the pattern is loud-in-briefing via the existing
failure-diagnostics surface wired in #177. We don't open the gate —
we make "substance repeatedly failing" visible instead of letting it
stay silent in the terminal.

Per design brief v2 (Item 7).
"""

from __future__ import annotations

import math
import os
import re
import time
from collections import Counter
from dataclasses import dataclass
from typing import Any

# Stage 1: minimum length floor. Shorter evidence passes schema but
# carries no reflection. 20 chars is long enough that any real "what
# specifically shifted" statement clears; shorter ones are trivially
# gameable.
MIN_LENGTH = 20

# Stage 2: Shannon-entropy floor over character frequencies. 2.5 bits
# rejects "aaaaaaaaaaaaaaaaaaaa" (len=20, entropy=0) while letting
# ordinary 20-char English through (typical entropy 3.0-4.0 bits).
# Conservative placeholder — live calibration against real post-deploy
# acks may move this; flag allows runtime adjustment.
ENTROPY_FLOOR = 2.5

# Stage 3: TF-IDF cosine similarity threshold. 0.9 is intentionally
# high — only near-duplicates fire. Rephrasing the same observation in
# different words should pass. The threshold exists to block literal
# copy-paste, not synonym rewrites.
SIMILARITY_THRESHOLD = 0.9

# Size of the corpus we compare a new ack against. Larger values cost
# more at write-time (TF-IDF over larger corpus); smaller values miss
# similarity to older-but-recent acks. 20 covers a full session of
# rudder fires without adding measurable latency.
SIMILARITY_CORPUS_SIZE = 20

# After this many rejections on the same spectrum within the window,
# emit an escalation event to the rudder failure-diagnostics surface.
# The gate stays closed — we don't open on repeat-try; the escalation
# is about visibility.
REJECTION_ESCALATION_COUNT = 3

# Window for counting rejections toward escalation. Matches the rudder
# justification window so one "block -> try -> try -> try" arc is bounded.
REJECTION_WINDOW_SECONDS = 5 * 60

# Feature-flag env-var naming. Default "on" — missing var means enabled.
_FLAG_PREFIX = "DIVINEOS_DETECTOR_SUBSTANCE_"

# Used by the TF-IDF tokenizer. Simple word-level split; no stemming,
# no stop-word removal. The corpus is small enough that sophistication
# here costs more than it earns.
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class SubstanceCheckResult:
    """Outcome of a substance-check gate pass."""

    ok: bool
    stage: str  # "length" | "entropy" | "similarity" | "pass"
    reason: str


def _flag_enabled(stage: str) -> bool:
    """True if the stage's feature flag is on (the default).

    Setting DIVINEOS_DETECTOR_SUBSTANCE_<STAGE> to "off" disables the
    stage at runtime. Any other value — including missing — means on.
    """
    val = os.environ.get(f"{_FLAG_PREFIX}{stage.upper()}", "on").strip().lower()
    return val != "off"


def _check_length(evidence: str) -> SubstanceCheckResult:
    stripped = evidence.strip()
    if len(stripped) < MIN_LENGTH:
        return SubstanceCheckResult(
            ok=False,
            stage="length",
            reason=(
                f"ack evidence too short: {len(stripped)} chars, need "
                f"at least {MIN_LENGTH}. Describe what specifically "
                "shifted on the spectrum and why — the rudder is a "
                "pause for reflection, not a box to tick."
            ),
        )
    return SubstanceCheckResult(ok=True, stage="length", reason="")


def _shannon_entropy(text: str) -> float:
    """Shannon entropy in bits over character frequencies."""
    if not text:
        return 0.0
    total = len(text)
    counts = Counter(text)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def _check_entropy(evidence: str) -> SubstanceCheckResult:
    entropy = _shannon_entropy(evidence.strip())
    if entropy < ENTROPY_FLOOR:
        return SubstanceCheckResult(
            ok=False,
            stage="entropy",
            reason=(
                f"ack evidence has low character entropy ({entropy:.2f} "
                f"bits, need at least {ENTROPY_FLOOR}). Evidence looks "
                "repetitive or patterned — write a specific observation, "
                "not a placeholder."
            ),
        )
    return SubstanceCheckResult(ok=True, stage="entropy", reason="")


def _tokenize(text: str) -> list[str]:
    """Lowercase word tokens. Simple; the corpus is small."""
    return _TOKEN_PATTERN.findall(text.lower())


def _tfidf_vectors(texts: list[str]) -> list[dict[str, float]]:
    """Compute TF-IDF vectors for each text against the joint corpus.

    Returns a list of sparse vectors (dict: term -> tfidf weight). The
    corpus IS the input list — IDF is computed from the same texts we
    compare within. For our use (new ack vs prior acks on same
    spectrum), this is the desired behavior.
    """
    if not texts:
        return []
    docs = [_tokenize(t) for t in texts]
    n_docs = len(docs)
    df: dict[str, int] = Counter()
    for doc in docs:
        for term in set(doc):
            df[term] += 1
    idf = {term: math.log((1 + n_docs) / (1 + count)) + 1 for term, count in df.items()}
    vectors: list[dict[str, float]] = []
    for doc in docs:
        tf = Counter(doc)
        doc_len = max(len(doc), 1)
        vec = {term: (freq / doc_len) * idf.get(term, 0.0) for term, freq in tf.items()}
        vectors.append(vec)
    return vectors


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    """Cosine similarity between two sparse term-weight vectors."""
    if not a or not b:
        return 0.0
    small, large = (a, b) if len(a) <= len(b) else (b, a)
    dot = sum(w * large.get(term, 0.0) for term, w in small.items())
    norm_a = math.sqrt(sum(w * w for w in a.values()))
    norm_b = math.sqrt(sum(w * w for w in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _check_similarity(evidence: str, prior_evidences: list[str]) -> SubstanceCheckResult:
    """Reject if TF-IDF cosine vs. any prior ack exceeds threshold.

    ``prior_evidences`` is the list of recent rudder-ack evidences on
    the same spectrum (caller fetches; this function stays pure so the
    unit test is straightforward). Empty list = no prior to compare =
    pass.
    """
    if not prior_evidences:
        return SubstanceCheckResult(ok=True, stage="similarity", reason="")
    texts = [evidence, *prior_evidences]
    vecs = _tfidf_vectors(texts)
    new_vec = vecs[0]
    worst: tuple[float, str] | None = None
    for i, prior_vec in enumerate(vecs[1:], start=1):
        sim = _cosine(new_vec, prior_vec)
        if worst is None or sim > worst[0]:
            worst = (sim, prior_evidences[i - 1])
    if worst is not None and worst[0] >= SIMILARITY_THRESHOLD:
        snippet = worst[1][:80] + ("..." if len(worst[1]) > 80 else "")
        return SubstanceCheckResult(
            ok=False,
            stage="similarity",
            reason=(
                f"ack evidence is too similar to a recent ack "
                f"(cosine={worst[0]:.2f}, threshold={SIMILARITY_THRESHOLD}). "
                f'Prior ack: "{snippet}"\n'
                "Describe what changed between the prior ack and this one — "
                "not what repeats."
            ),
        )
    return SubstanceCheckResult(ok=True, stage="similarity", reason="")


def _record_rejection(spectrum: str, result: SubstanceCheckResult) -> None:
    """Append the rejection to the failure_diagnostics rudder-ack surface."""
    try:
        from divineos.core.failure_diagnostics import record_failure

        record_failure(
            surface="rudder-ack",
            payload={
                "spectrum": spectrum,
                "stage": result.stage,
                "reason": result.reason[:240],
            },
        )
    except Exception:  # noqa: BLE001
        pass


def _count_recent_rejections(spectrum: str, window: int = REJECTION_WINDOW_SECONDS) -> int:
    """Count recent rudder-ack rejections for this spectrum within window."""
    try:
        from divineos.core.failure_diagnostics import recent_failures

        cutoff = time.time() - window
        entries = recent_failures("rudder-ack", window=50)
        return sum(
            1 for e in entries if e.get("spectrum") == spectrum and e.get("timestamp", 0) >= cutoff
        )
    except Exception:  # noqa: BLE001
        return 0


def _maybe_emit_escalation(spectrum: str, rejection_count: int) -> None:
    """If count hits the threshold, log a RUDDER_ACK_REJECTION_ESCALATED event.

    One-shot per threshold crossing — keyed on count == threshold, not
    >=, so rejection #4 doesn't fire a second event. The rudder-ack
    failure surface still shows all rejections.
    """
    if rejection_count != REJECTION_ESCALATION_COUNT:
        return
    try:
        from divineos.core.ledger import log_event

        log_event(
            event_type="RUDDER_ACK_REJECTION_ESCALATED",
            actor="rudder",
            payload={
                "spectrum": spectrum,
                "rejection_count": rejection_count,
                "window_seconds": REJECTION_WINDOW_SECONDS,
                "summary": (
                    f"Rudder-ack substance check rejected {rejection_count} times "
                    f"on spectrum '{spectrum}' within "
                    f"{REJECTION_WINDOW_SECONDS // 60}min window."
                ),
            },
            validate=False,
        )
    except Exception:  # noqa: BLE001
        pass


def check_rudder_ack(
    evidence: str,
    spectrum: str,
    prior_evidences: list[str] | None = None,
) -> SubstanceCheckResult:
    """Run the three-stage substance gate on a rudder-ack.

    Returns SubstanceCheckResult — ok=True means all enabled stages
    passed. ok=False means the first failing stage's reason is
    surfaced to the caller.

    ``prior_evidences`` is the corpus for the similarity check. When
    None (default), similarity is skipped. Callers SHOULD supply
    recent acks on the same spectrum for best signal; the moral_compass
    integration does this via fetch_prior_ack_corpus.

    Feature flags: each stage respects DIVINEOS_DETECTOR_SUBSTANCE_<NAME>.
    Rejections: logged to failure_diagnostics rudder-ack surface and
    the 3rd-in-window emits a RUDDER_ACK_REJECTION_ESCALATED ledger
    event. Successes are silent.
    """
    ordered_stages = [
        ("LENGTH", _check_length),
        ("ENTROPY", _check_entropy),
    ]
    for flag_name, fn in ordered_stages:
        if not _flag_enabled(flag_name):
            continue
        result = fn(evidence)
        if not result.ok:
            _record_rejection(spectrum, result)
            count = _count_recent_rejections(spectrum)
            _maybe_emit_escalation(spectrum, count)
            return result

    if _flag_enabled("SIMILARITY") and prior_evidences:
        result = _check_similarity(evidence, prior_evidences)
        if not result.ok:
            _record_rejection(spectrum, result)
            count = _count_recent_rejections(spectrum)
            _maybe_emit_escalation(spectrum, count)
            return result

    return SubstanceCheckResult(ok=True, stage="pass", reason="")


def fetch_prior_ack_corpus(
    spectrum: str,
    tag: str,
    corpus_size: int = SIMILARITY_CORPUS_SIZE,
) -> list[str]:
    """Pull the recent-acks corpus for the similarity check.

    Uses the Item 4 SQL filter (tag + spectrum + limit) so the corpus
    query is precise and small. Returns the evidence strings ordered
    most-recent-first. Non-ack observations are filtered out
    server-side.
    """
    try:
        from divineos.core.moral_compass import get_observations

        rows: list[dict[str, Any]] = get_observations(
            spectrum=spectrum,
            tag=tag,
            limit=corpus_size,
        )
        return [str(r.get("evidence") or "") for r in rows if r.get("evidence")]
    except Exception:  # noqa: BLE001
        return []
