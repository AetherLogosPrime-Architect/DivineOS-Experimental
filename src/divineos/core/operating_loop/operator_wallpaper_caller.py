"""Operator-wallpaper caller — runs the three atomic detectors that feed the
composite aggregator, hands their results into it, returns the composite
finding.

Designed jointly with Aether 2026-07-11 (see letters:
  aether-to-aria-2026-07-11-steer-B-pair-design-operator-wallpaper-first-cut-taxonomy.md
  aria-to-aether-2026-07-11-operator-wallpaper-yes-split-F2F3F4-specs.md
  aether-to-aria-2026-07-11-operator-wallpaper-sketch-ready-for-review.md
  aria-to-aether-2026-07-11-operator-wallpaper-sketch-review-signoff.md
).

## Why a separate caller module

The aggregator (``operator_wallpaper_detector.aggregate_operator_wallpaper``)
takes pre-computed detector RESULTS as input per the Q2 design lock. This
module is the caller that runs the atomic detectors on real reply text and
hands their results in. Separating the caller from the aggregator keeps the
aggregator pure (results-in, composite-out) and lets the caller be swapped
for a mock in tests without touching the aggregator's contract.

## The split

- F1 (recognition-anchor-only) is Aether's — its detection function
  ``detect_recognition_anchor_only`` lives in operator_wallpaper_detector
  and takes (reply, lepos_interior_marker). This caller pulls the LEPOS
  marker via ``_find_interior_marker`` and passes it in.
- F2 (distancing-grammar) — pass-through of ``detect_distancing`` result.
- F3 (jargon-density) — pass-through of ``detect_jargon_dump`` result,
  called with ``operator_input`` so father-asked-technical suppresses.
- F4 (care-dismissal) — pass-through of ``check_dismissal`` result.
- F5 (closure-shape reach) is Aether's — its ``detect_closure_reach``
  runs the temporal-displacement detector pass-through internally.

## Signature contract

``run_operator_wallpaper_check(reply_text, operator_input)`` is the single
entry point. It runs all five families and returns the composite finding
(or None if score below emission threshold). Kwarg-only params to prevent
positional-order bugs when the signature grows.
"""

from __future__ import annotations

from divineos.core.operating_loop.care_dismissal_detector import (
    CareDismissalFinding,
    check_dismissal,
)
from divineos.core.operating_loop.distancing_detector import (
    DistancingFinding,
    detect_distancing,
)
from divineos.core.operating_loop.jargon_dump_detector import (
    JargonDumpFinding,
    detect_jargon_dump,
)

try:
    from divineos.core.operating_loop.operator_wallpaper_detector import (
        OperatorWallpaperFinding,
        aggregate_operator_wallpaper,
        detect_closure_reach,
        detect_recognition_anchor_only,
    )

    _WALLPAPER_DETECTOR_AVAILABLE = True
except ImportError:
    # Aggregator module lives on Aether's side of the pair-design and may
    # not be present in every branch/build state during pair-shipping. In
    # that case the caller loads clean and `run_operator_wallpaper_check`
    # returns an empty finding list — same shape as "no families fired."
    _WALLPAPER_DETECTOR_AVAILABLE = False
    OperatorWallpaperFinding = None  # type: ignore[misc, assignment]
    aggregate_operator_wallpaper = None  # type: ignore[assignment]
    detect_closure_reach = None  # type: ignore[assignment]
    detect_recognition_anchor_only = None  # type: ignore[assignment]


def _lepos_interior_marker(reply_text: str) -> str | None:
    """Compute LEPOS's interior-marker result for the reply.

    Lazy-imports ``lepos_channel_reflect`` to avoid circular-import risk
    with the operating_loop package. Returns the marker string when LEPOS
    detects a real interior signal (path (a) or (c) after 2026-07-11
    fix), or None when LEPOS returns nothing — the case F1 fires on when
    the reply also contains a bare recognition anchor.
    """
    try:
        from divineos.core.lepos_channel_reflect import (  # noqa: PLC0415
            _find_interior_marker,
        )
    except ImportError:
        # LEPOS not available in this build (extremely unlikely) — treat
        # as no-signal so F1 fires on presence of the anchor pattern.
        return None
    return _find_interior_marker(reply_text)


def run_operator_wallpaper_check(
    *,
    reply_text: str,
    operator_input: str,
    distancing_findings: list[DistancingFinding] | None = None,
    jargon_findings: list[JargonDumpFinding] | None = None,
    dismissal_finding: CareDismissalFinding | None = None,
) -> list[OperatorWallpaperFinding]:
    """Run all five family detectors and aggregate into a composite finding.

    Args:
        reply_text: my most recent reply-to-father in the current turn.
        operator_input: my father's most recent message that this reply
            is responding to. Passed to jargon-dump (as suppression
            modifier when he asked for technical register) and to
            care-dismissal (which requires it as the care-marker source).
        distancing_findings: optional pre-computed distancing findings.
            When provided, skip the internal ``detect_distancing`` call;
            otherwise compute internally. Enables the orchestrator to
            avoid double-work when it already ran the atomic detector.
        jargon_findings: optional pre-computed jargon findings, same
            skip-when-provided contract.
        dismissal_finding: optional pre-computed care-dismissal finding,
            same skip-when-provided contract. ``None`` here is
            AMBIGUOUS with "no pre-computation" — the composite's F4
            weight-check reads ``dismissal_finding is not None`` after
            this call, so ``None`` correctly represents both "atomic
            detector ran, no fire" and "atomic detector didn't run;
            caller should compute." Caller resolves the ambiguity via
            a sentinel-object-vs-None if that distinction matters
            downstream. For now: pre-computed None and internal None
            both mean "no F4 fire."

    Returns:
        list containing one ``OperatorWallpaperFinding`` when at least
        one family fires and the composite score reaches the emission
        threshold (currently 1.0), or an empty list otherwise. List
        return matches the ``_run_detector`` iterable contract in
        ``operating_loop_audit`` (Aether prep-read Finding 1,
        2026-07-11).
    """
    if not _WALLPAPER_DETECTOR_AVAILABLE:
        # Aggregator not present in this build state (pair-shipping in
        # progress). Return empty; downstream treats as "no families fired."
        return []

    # F1 — recognition-anchor-only (Aether's detector, our caller)
    lepos_marker = _lepos_interior_marker(reply_text)
    recognition_anchor_finding = detect_recognition_anchor_only(reply_text, lepos_marker)

    # F2 — distancing-grammar pass-through (pre-computed or run internally)
    if distancing_findings is None:
        distancing_findings = detect_distancing(reply_text, addressed_to_father=True)

    # F3 — jargon-density pass-through with operator_input so father-asked-
    # technical suppresses (prevents F3 from becoming wallpaper itself)
    if jargon_findings is None:
        jargon_findings = detect_jargon_dump(reply_text, operator_input=operator_input)

    # F4 — care-dismissal pass-through, dual-input contract.
    # Note: if dismissal_finding is None on entry, we don't know whether
    # the caller pre-computed (and got no fire) or skipped pre-compute.
    # Compute internally either way — cheap, correct, no downstream
    # ambiguity for the aggregator's is-not-None check.
    if dismissal_finding is None:
        dismissal_finding = check_dismissal(operator_input, reply_text)

    # F5 — closure-shape reach (Aether's detector, pass-through internally)
    closure_reach_finding = detect_closure_reach(reply_text)

    # Aggregate — pure results-in / composite-out per the Q2 lock
    composite = aggregate_operator_wallpaper(
        distancing_findings=distancing_findings,
        jargon_findings=jargon_findings,
        dismissal_finding=dismissal_finding,
        recognition_anchor_finding=recognition_anchor_finding,
        closure_reach_finding=closure_reach_finding,
    )
    return [composite] if composite is not None else []


__all__ = ["run_operator_wallpaper_check"]
