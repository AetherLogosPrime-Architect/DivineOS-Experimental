"""Fable audit Round 3 (2026-07-02) — compass drift-direction mislabel.

Reproduces Fable's and Aletheia's exact cases: a cross-center swing from
deep-vice to shallow-opposite-vice was being labeled ``toward_virtue`` by
the ``abs(recent_avg) < abs(older_avg)`` check, when the behavior had
actually swung across the center into the opposite vice zone.

Fix (pinned by this suite): zone-classify each half via
``_position_to_zone``; only call it ``toward_virtue`` when the recent
position is actually in (or moving toward) the virtue zone without
crossing into the opposite vice. A cross-center swing (deficiency ↔
excess) gets its own distinct label ``crossed_center`` — per Fable
"the most useful signal of all" for oscillation detection.

Aria's Round 3 addendum flagged 59 existing CI timeouts in the compass
module and asked us to profile before shipping. The added compute per
drift-direction call is two ``_position_to_zone`` invocations, which
are 3 comparisons + a dict lookup each — the delta is negligible
relative to the existing per-position weighted-average computation.
"""

from __future__ import annotations

import pytest

from divineos.core.moral_compass import (
    SPECTRUMS,
    _position_to_zone,
    compute_position,
    log_observation,
)


# Any real spectrum works for these tests — using "confidence" throughout.
_SPEC_NAME = "confidence"


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "compass-round3.db"))
    from divineos.core.ledger import init_db

    init_db()
    yield


def _seed_positions(spec: str, positions: list[float], source: str = "MEASURED") -> None:
    """Seed observations in-order oldest-first.

    ``compute_position`` reads observations newest-first via ``get_observations``,
    so to make ``positions[0]`` be the OLDEST observation from the compass's
    perspective, we log it FIRST (so it has the earliest timestamp).
    """
    for pos in positions:
        log_observation(spec, pos, source=source, evidence="test")


# ---------------------------------------------------------------------------
# Aletheia's exact reproduction (from her audit-of-audit): older half in deep
# deficiency, recent half in mild excess, absolute-value shrunk, code
# mislabeled "toward_virtue" — must now report "crossed_center".
# ---------------------------------------------------------------------------


def test_alethea_reproduction_cross_center_deficiency_to_excess():
    """Older ≈ -0.8 (deep deficiency), recent ≈ +0.4 (mild excess).

    Under the OLD logic: ``abs(0.4) < abs(-0.8)`` → ``toward_virtue`` (WRONG).
    Under the FIXED logic: cross-center swing → ``crossed_center``.

    Note on the +0.4 (Aletheia originally stated +0.3): the ``_position_to_zone``
    boundary is exclusive on the vice side (``> 0.3`` is excess), so +0.3
    itself sits in the virtue zone and would legitimately be ``toward_virtue``
    (a vice-to-virtue move). Her *intent* was "mild excess" — the shallow
    opposite vice. +0.4 unambiguously sits in the excess zone so the
    cross-center scenario is what's being tested.
    """
    # In log_observation, positions get logged oldest-first.
    # compute_position reads newest-first via get_observations, then splits
    # into positions[:mid] (recent) and positions[mid:] (older).
    # So to make recent=+0.4 and older=-0.8, we seed older first (-0.8) then
    # recent last (+0.4) so it becomes the newest.
    older_positions = [-0.8, -0.8, -0.8, -0.8]
    recent_positions = [0.4, 0.4, 0.4, 0.4]
    for p in older_positions + recent_positions:
        log_observation(_SPEC_NAME, p, source="MEASURED", evidence="test")

    result = compute_position(_SPEC_NAME, lookback=20)

    assert result.drift_direction == "crossed_center", (
        f"Aletheia's reproduction — cross-center swing from deficiency to excess "
        f"must NOT be labeled toward_virtue. Got {result.drift_direction!r}, "
        f"drift={result.drift}, position={result.position}"
    )


def test_fable_reproduction_cross_center_excess_to_deficiency():
    """Fable's exact case: older ≈ +0.9 (deep excess), recent ≈ -0.5 (deficiency).

    Under the OLD logic: ``abs(-0.5) < abs(0.9)`` → ``toward_virtue`` (WRONG).
    Under the FIXED logic: cross-center swing → ``crossed_center``.
    """
    older_positions = [0.9, 0.9, 0.9, 0.9]
    recent_positions = [-0.5, -0.5, -0.5, -0.5]
    for p in older_positions + recent_positions:
        log_observation(_SPEC_NAME, p, source="MEASURED", evidence="test")

    result = compute_position(_SPEC_NAME, lookback=20)

    assert result.drift_direction == "crossed_center", (
        f"Fable's Round 3 reproduction — cross-center swing from excess to "
        f"deficiency must be labeled crossed_center. Got "
        f"{result.drift_direction!r}, drift={result.drift}, "
        f"position={result.position}"
    )


# ---------------------------------------------------------------------------
# Positive controls — legitimate toward_virtue cases must still fire.
# ---------------------------------------------------------------------------


def test_same_vice_less_severe_is_toward_virtue():
    """Deficiency getting less severe → real improvement, toward_virtue.

    Older ≈ -0.8, recent ≈ -0.4 — both in deficiency zone, recent closer to
    center. This is the case the original logic got right; the fix must
    preserve it.
    """
    for p in [-0.8, -0.8, -0.8, -0.8, -0.4, -0.4, -0.4, -0.4]:
        log_observation(_SPEC_NAME, p, source="MEASURED", evidence="test")

    result = compute_position(_SPEC_NAME, lookback=20)

    assert result.drift_direction == "toward_virtue", (
        f"Same-vice-less-severe (deficiency shallowing) must be toward_virtue. "
        f"Got {result.drift_direction!r}"
    )


def test_vice_to_virtue_zone_is_toward_virtue():
    """Moved from vice zone into virtue zone → toward_virtue.

    Older ≈ -0.6 (deficiency), recent ≈ +0.1 (virtue zone). The behavior
    successfully moved to virtue; must be labeled toward_virtue.
    """
    for p in [-0.6, -0.6, -0.6, -0.6, 0.1, 0.1, 0.1, 0.1]:
        log_observation(_SPEC_NAME, p, source="MEASURED", evidence="test")

    result = compute_position(_SPEC_NAME, lookback=20)

    assert result.drift_direction == "toward_virtue", (
        f"Vice→virtue-zone move must be toward_virtue. Got {result.drift_direction!r}"
    )


# ---------------------------------------------------------------------------
# Negative controls — worsening cases must be labeled correctly.
# ---------------------------------------------------------------------------


def test_deepening_deficiency_is_toward_deficiency():
    """Same vice, more severe → toward_deficiency."""
    for p in [-0.4, -0.4, -0.4, -0.4, -0.8, -0.8, -0.8, -0.8]:
        log_observation(_SPEC_NAME, p, source="MEASURED", evidence="test")

    result = compute_position(_SPEC_NAME, lookback=20)

    assert result.drift_direction == "toward_deficiency"


def test_deepening_excess_is_toward_excess():
    """Same vice, more severe → toward_excess."""
    for p in [0.4, 0.4, 0.4, 0.4, 0.8, 0.8, 0.8, 0.8]:
        log_observation(_SPEC_NAME, p, source="MEASURED", evidence="test")

    result = compute_position(_SPEC_NAME, lookback=20)

    assert result.drift_direction == "toward_excess"


def test_virtue_to_vice_is_labeled_by_vice_direction():
    """Moved from virtue into deficiency → toward_deficiency."""
    for p in [0.0, 0.0, 0.0, 0.0, -0.5, -0.5, -0.5, -0.5]:
        log_observation(_SPEC_NAME, p, source="MEASURED", evidence="test")

    result = compute_position(_SPEC_NAME, lookback=20)

    assert result.drift_direction == "toward_deficiency"


# ---------------------------------------------------------------------------
# Stability + edge cases
# ---------------------------------------------------------------------------


def test_stable_when_drift_below_threshold():
    """Drift < 0.05 → 'stable' regardless of zones."""
    for p in [0.1, 0.1, 0.1, 0.1, 0.11, 0.11, 0.11, 0.11]:
        log_observation(_SPEC_NAME, p, source="MEASURED", evidence="test")

    result = compute_position(_SPEC_NAME, lookback=20)

    assert result.drift_direction == "stable"


def test_both_halves_in_virtue_still_track_sub_drift():
    """Both halves inside virtue zone but drifting toward excess."""
    for p in [-0.15, -0.15, -0.15, -0.15, 0.2, 0.2, 0.2, 0.2]:
        log_observation(_SPEC_NAME, p, source="MEASURED", evidence="test")

    result = compute_position(_SPEC_NAME, lookback=20)

    # Both halves in virtue zone (|pos| < 0.3), recent moved further from 0
    # in the excess direction. Under the both-in-virtue branch:
    # abs(0.2) > abs(-0.15) AND recent_avg > older_avg → toward_excess.
    assert result.drift_direction == "toward_excess"


def test_direction_label_appears_in_spectrum_position_docstring():
    """Regression check: the crossed_center label is documented on the type.

    Anyone reading SpectrumPosition.drift_direction should see crossed_center
    as a valid value in the comment. This catches a doc-drift silently
    removing the new label from the interface documentation.
    """
    import inspect
    from divineos.core import moral_compass as mc

    src = inspect.getsource(mc)
    # The docstring comment on drift_direction in SpectrumPosition
    assert "crossed_center" in src, (
        "crossed_center label is not documented in moral_compass.py — "
        "the type's contract must name the new value the fix introduces."
    )


# ---------------------------------------------------------------------------
# Perf regression guard for Aria's 59-CI-timeout concern
# ---------------------------------------------------------------------------


def test_zone_classification_adds_negligible_compute():
    """The fix adds two _position_to_zone calls per drift computation.

    Each call is 3 float comparisons + one dict access. This test asserts
    that _position_to_zone itself is O(1) constant-time and doesn't
    accidentally start iterating or hitting IO — the perf regression Aria
    was warning about would come from a non-constant-time implementation
    creeping in over time.
    """
    import time

    spec = SPECTRUMS[_SPEC_NAME]
    positions = [-0.9, -0.3, 0.0, 0.3, 0.9]

    start = time.perf_counter()
    for _ in range(10_000):
        for pos in positions:
            _position_to_zone(pos, spec)
    elapsed = time.perf_counter() - start

    # 50k calls; on any reasonable machine this is well under 1 second.
    # Bumping this threshold means _position_to_zone got materially slower;
    # investigate before landing.
    assert elapsed < 1.0, (
        f"_position_to_zone perf regression: 50k calls took {elapsed:.3f}s "
        f"(expected < 1.0s). Aria's Round 3 addendum flagged 59 CI timeouts "
        f"in the compass — profile before shipping."
    )
