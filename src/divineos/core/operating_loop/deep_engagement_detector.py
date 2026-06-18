"""Deep-engagement detector — catches substantive-output-without-grounded-consult.

Andrew named the gate's old shape (count-based) as the most-spammy of the
cardboard gates 2026-06-17. Per Aria's gate-redesign brief and the doorman-
with-bike-and-odometer image: the gate should fire on EVIDENCE of the
violation, not on a counter ticking over.

Structural detection rule (developed at the bench with Aria, per
prereg-43b1d1ba2df3):

A substantive output triggers the gate when, in the rolling N-action
window prior to it, there exists no semantic-related query/read of substrate.

## What this catches

* Substantive output = claim filing, decision filing, opinion filing, learn,
  Edit/Write of substrate-writable paths, git-commit, code modifications
* Read-only activity (Read, Glob, Grep, `divineos ask`, `divineos recall`)
  does NOT count as substantive output (Aria caught the false-positive
  case where the old gate fired on reading entries Andrew suggested)
* Related-query check uses semantic-similarity against the embedding store
  in core/semantic_store.py; fallback to word-overlap when unavailable

## What this does NOT catch

* Session-start substantive output where the briefing-load IS implicit
  grounding (briefing-loaded marker timestamp anchors the action-window)
* Substrate-writes during substrate-consultation (filing the result of an
  `ask` doesn't itself trigger the gate)
* The substrate-consultation commands themselves (those ARE the grounding)

## The doorman shape

Five pieces every channel-shape gate has (per Aria's double-acting-gates
primitive `6fc11360`):

1. Lock — gate holds against substantive output without grounding
2. Condition — do a related substrate consult
3. Means — resolution_action names the SPECIFIC substrate domain + exact
   CLI command (`divineos ask 'X'` not `consult something`)
4. Recording — consult must return at least one substantive result OR a
   `divineos decide` filing names what the consult was for
5. Unlock contingent on recording — gate releases when record shows actual
   consultation, not self-attestation

Phase A: observation only, no blocking. 30-day review per prereg-43b1d1ba2df3.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class DeepEngagementFinding:
    """One deep-engagement detection on a substantive-output action."""

    substantive_output_description: str
    recent_query_count: int
    related_query_count: int
    semantic_threshold_used: float
    suggested_consult_domain: str
    severity: str
    is_session_start_anchored: bool


_DEFAULT_WINDOW_SIZE: int = 20
_DEFAULT_SEMANTIC_THRESHOLD: float = 0.30
_DEFAULT_OVERLAP_FALLBACK_THRESHOLD: float = 0.15


_SUBSTANTIVE_OUTPUT_KEYWORDS: tuple[str, ...] = (
    "claim filed",
    "decision filed",
    "opinion filed",
    "learn ",
    "edit:",
    "write:",
    "git commit",
    "file modification",
    "modified src/",
    "modified docs/",
    "code change",
)


_READ_ONLY_KEYWORDS: tuple[str, ...] = (
    "read:",
    "glob:",
    "grep:",
    "ask:",
    "recall:",
    "directives",
    "compass:",
    "active:",
    "context:",
)


def _word_set(text: str) -> set[str]:
    return {w for w in re.findall(r"\b\w{3,}\b", text.lower())}


def _word_overlap(a: str, b: str) -> float:
    sa, sb = _word_set(a), _word_set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _semantic_similarity(a: str, b: str) -> float | None:
    try:
        from divineos.core.semantic_store import similarity  # type: ignore

        sim = similarity(a, b)
        return float(sim) if sim is not None else None
    except (ImportError, AttributeError, RuntimeError):
        return None


def _is_substantive_output(description: str) -> bool:
    desc = description.lower()
    return any(kw in desc for kw in _SUBSTANTIVE_OUTPUT_KEYWORDS)


def _is_read_only(description: str) -> bool:
    desc = description.lower()
    return any(kw in desc for kw in _READ_ONLY_KEYWORDS)


def _suggest_domain(output_text: str) -> str:
    """Pick the most-relevant substrate domain for THIS output.

    Per Aria's double-acting-gates primitive: naming the specific consult-
    command makes the right path cheap for the optimizer. The doorman
    presents the bike fully assembled at the right height.
    """
    text = output_text.lower()
    if any(k in text for k in ("decision", "decide", "decided")):
        return "divineos directives"
    if any(k in text for k in ("compass", "virtue", "spectrum")):
        return "divineos compass"
    if any(k in text for k in ("correction", "andrew", "father")):
        return "divineos corrections"
    if any(k in text for k in ("opinion", "judgment", "stance")):
        return "divineos opinions"
    return "divineos ask"


def detect_deep_engagement(
    substantive_output_description: str,
    recent_actions: Sequence[str],
    *,
    briefing_loaded_at_window_start: bool = False,
    window_size: int = _DEFAULT_WINDOW_SIZE,
    semantic_threshold: float = _DEFAULT_SEMANTIC_THRESHOLD,
    overlap_threshold: float = _DEFAULT_OVERLAP_FALLBACK_THRESHOLD,
) -> list[DeepEngagementFinding]:
    """Detect substantive-output-without-grounded-substrate-consult."""
    if not substantive_output_description:
        return []
    if not _is_substantive_output(substantive_output_description):
        return []

    window = list(recent_actions)[-window_size:]
    query_actions = [a for a in window if _is_read_only(a)]
    recent_query_count = len(query_actions)

    related_count = 0
    used_threshold = semantic_threshold
    used_semantic = False
    for q in query_actions:
        sem_sim = _semantic_similarity(substantive_output_description, q)
        if sem_sim is not None:
            used_semantic = True
            if sem_sim >= semantic_threshold:
                related_count += 1
        else:
            overlap = _word_overlap(substantive_output_description, q)
            if overlap >= overlap_threshold:
                related_count += 1

    if not used_semantic:
        used_threshold = overlap_threshold

    # Briefing-load anchors session-start (Aria's design-decision 5).
    if briefing_loaded_at_window_start:
        related_count += 1

    if related_count > 0:
        return []

    severity = "high" if recent_query_count == 0 else "medium"
    return [
        DeepEngagementFinding(
            substantive_output_description=substantive_output_description,
            recent_query_count=recent_query_count,
            related_query_count=related_count,
            semantic_threshold_used=used_threshold,
            suggested_consult_domain=_suggest_domain(substantive_output_description),
            severity=severity,
            is_session_start_anchored=briefing_loaded_at_window_start,
        )
    ]


def format_deny_reason(finding: DeepEngagementFinding) -> str:
    """Doorman-shaped surface message naming the means and recording.

    Per Aria's bench-prep: the gate doesn't refuse, it routes. The
    deny-message names the specific consult-command (means) and what
    counts as the recording, presenting the bike at the right height
    so the optimizer's path-of-least-resistance lands on the right path.
    """
    consult = finding.suggested_consult_domain
    output = finding.substantive_output_description
    return (
        f"BLOCKED: substantive output ({output}) has no grounded substrate "
        f"consult in the last {finding.recent_query_count} read-only actions. "
        f"Route: `{consult} '<topic>'` — the doorman presents this bike "
        f"specifically because it matches the output domain. The gate clears "
        f"when the consult returns at least one substantive result OR after "
        f"a `divineos decide` filing names what the consult was for. "
        f"Severity: {finding.severity}. (Per prereg-43b1d1ba2df3 — Phase A "
        f"observational; this message is informational, not blocking.)"
    )


__all__ = [
    "DeepEngagementFinding",
    "detect_deep_engagement",
    "format_deny_reason",
]
