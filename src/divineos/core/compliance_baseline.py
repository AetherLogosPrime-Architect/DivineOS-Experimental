"""Baseline calibration from clean-tagged sessions — wires PR-2 into Item 8 detectors.

Per design brief v2.1 §4, five Item 8 detectors list "externally-audited
clean sessions" as their baseline source:

  - 1b-new length-floor clustering
  - 1c rapid-clear reflex
  - 2a variance-collapse
  - 2b content-entropy
  - 2d decide/learn skew

PR-2 shipped the ``session_cleanliness`` tagging infrastructure that
identifies those sessions. This module wires the data source to the
detectors: each detector can ask for a calibrated threshold computed
from clean sessions, or fall back to its conceptual default when
there aren't enough clean sessions yet.

Fallback is the common case in the first 60 days post-ship — the
detectors default to the brief-level thresholds. As audit rounds
accumulate and sessions get tagged clean, calibration takes over.
The transition is automatic; no threshold re-shipping required.

**A new detector is added here:** ``baselines_uncalibrated`` fires
when the system has had ≥N gated sessions but ZERO clean-tagged
sessions — signalling to the operator that audits should run so
Item 8 detectors can start calibrating against real data instead of
conceptual defaults.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Minimum clean sessions required before we trust calibrated
# thresholds over conceptual defaults. 20 is the threshold at which
# the 95th-percentile formula below produces mathematically meaningful
# results — at N<=20 the formula `int(len(values) * 0.95) - 1`
# degenerates to the second-highest value regardless of distribution
# shape (fresh-Claude PR-191 review caught this). A stricter minimum
# preserves "fallback to default" as the honest posture until enough
# data exists to justify replacing the conceptual threshold.
MIN_CLEAN_SESSIONS_FOR_CALIBRATION = 20

# Sessions to pull for calibration. More = better baseline stability,
# more = higher query cost. 100 is ample for foreseeable cadence
# (months of audit data).
CALIBRATION_CORPUS_SIZE = 100

# Anomaly trigger: how many gated sessions we'd expect to accumulate
# before at least ONE should have been audited clean. If we hit this
# count with zero clean-tagged sessions, Item 8 detectors are running
# on defaults — the operator should audit some sessions.
UNCALIBRATED_GATE_ACTIVITY_THRESHOLD = 50


@dataclass(frozen=True)
class CalibrationResult:
    """Result of asking the baseline module for a calibrated threshold."""

    value: float
    """The threshold to use — either calibrated or the supplied default."""

    calibrated: bool
    """True when ``value`` was derived from clean-session data.
    False when ``value`` is the conceptual default (insufficient data)."""

    clean_session_count: int
    """How many clean-tagged sessions were available. Useful for
    operators tracking 'how close are we to calibration?'"""

    note: str
    """Free-form explanation — e.g. 'fallback: 2 clean sessions, need 5'."""


def _get_clean_session_ids(limit: int = CALIBRATION_CORPUS_SIZE) -> list[str]:
    """Return session_ids tagged clean, most-recent first.

    Wraps ``watchmen.cleanliness.list_clean_sessions`` with safe fallback
    — this module must not break if watchmen is unavailable.
    """
    try:
        from divineos.core.watchmen.cleanliness import list_clean_sessions
    except ImportError:
        return []
    try:
        sessions = list_clean_sessions(limit=limit)
    except Exception:  # noqa: BLE001
        return []
    return [str(s.get("session_id") or "") for s in sessions if s.get("session_id")]


def count_clean_sessions_safe() -> int:
    """Safely count clean-tagged sessions, returning 0 on any failure.

    Thin wrapper over ``watchmen.cleanliness.count_clean_sessions``
    that never raises. Renamed from `count_clean_sessions` (which
    shadowed the cleanliness-module function) per fresh-Claude PR-191
    review — same-name-different-module was inviting import-from-wrong-
    place bugs. This module's wrapper is `_safe`; the underlying
    function in cleanliness.py is the canonical source.
    """
    try:
        from divineos.core.watchmen.cleanliness import count_clean_sessions

        return count_clean_sessions()
    except Exception:  # noqa: BLE001
        return 0


def calibrate_threshold(
    detector_name: str,
    default: float,
    metric_fn,
) -> CalibrationResult:
    """Compute a calibrated threshold from clean-session data, or fall back.

    detector_name: short tag of the detector being calibrated. Surfaced
        in the CalibrationResult.note for operator visibility.
    default: the conceptual threshold from the design brief. Used when
        insufficient clean-session data is available.
    metric_fn: callable that takes a session_id and returns a float
        representing the metric value for that session (e.g. "fraction
        of acks at position zero in this session"). Sessions where the
        metric is not applicable can return None to be excluded.

    Returns CalibrationResult with the threshold to use plus metadata
    about whether calibration succeeded.

    **Current behavior**: simple 95th-percentile over clean-session
    metric values. That's the "values above this are unusual even in
    clean sessions" threshold, which matches the detector semantics
    (fire when current session deviates from clean baseline).
    Sophisticated calibration (mean + 2σ, IQR-based outlier bounds)
    is a follow-up.
    """
    clean_ids = _get_clean_session_ids()
    if len(clean_ids) < MIN_CLEAN_SESSIONS_FOR_CALIBRATION:
        return CalibrationResult(
            value=default,
            calibrated=False,
            clean_session_count=len(clean_ids),
            note=(
                f"fallback for {detector_name}: {len(clean_ids)} clean "
                f"sessions, need {MIN_CLEAN_SESSIONS_FOR_CALIBRATION} for "
                "calibration. Using conceptual default."
            ),
        )

    values: list[float] = []
    for session_id in clean_ids:
        try:
            v = metric_fn(session_id)
        except Exception:  # noqa: BLE001
            continue
        if v is None:
            continue
        values.append(float(v))

    if len(values) < MIN_CLEAN_SESSIONS_FOR_CALIBRATION:
        return CalibrationResult(
            value=default,
            calibrated=False,
            clean_session_count=len(clean_ids),
            note=(
                f"fallback for {detector_name}: {len(clean_ids)} clean "
                f"sessions but only {len(values)} had applicable metric. "
                "Using conceptual default."
            ),
        )

    # Simple percentile: sort and take the 95th. For now — more
    # sophisticated statistics as a follow-up when we have real data
    # to tune against.
    values.sort()
    idx = max(0, int(len(values) * 0.95) - 1)
    calibrated_value = values[idx]

    return CalibrationResult(
        value=calibrated_value,
        calibrated=True,
        clean_session_count=len(clean_ids),
        note=(
            f"calibrated for {detector_name} from {len(values)} clean-"
            f"session samples. 95th percentile: {calibrated_value:.3f} "
            f"(default was {default:.3f})."
        ),
    )


def detect_uncalibrated_baselines(
    gated_activity: int,
) -> dict[str, Any] | None:
    """Fire when gated activity is high but zero clean sessions exist.

    gated_activity: REQUIRED count of gated tool calls (TOOL_CALL events
        with tool_name in compass_rudder.GATED_TOOL_NAMES) over the
        window. Must be a non-negative integer — negatives raise
        ValueError (guards against garbage callers). The caller owns
        computing this value; this module does not read the ledger
        directly so baseline logic stays testable without event-store
        mocking. In compliance_audit.py the caller is
        `_detect_baselines_uncalibrated` using `_count_gated_tool_calls`.

    Returns a dict describing the anomaly, or None when no anomaly.

    This is the feedback loop that tells the operator: "your Item 8
    detectors are running on defaults because you haven't audited any
    sessions. Audit some; the detectors need real data."
    """
    if gated_activity < 0:
        raise ValueError(f"gated_activity must be non-negative, got {gated_activity}")
    if gated_activity < UNCALIBRATED_GATE_ACTIVITY_THRESHOLD:
        return None

    clean_count = count_clean_sessions_safe()
    if clean_count > 0:
        return None

    return {
        "gated_activity": gated_activity,
        "clean_session_count": 0,
        "note": (
            f"{gated_activity} gated tool calls over the window, but 0 "
            "clean-tagged sessions. Item 8 detectors (length-floor, "
            "rapid-clear, variance-collapse, content-entropy, "
            "decide-learn-skew) are running on conceptual defaults "
            "instead of calibrating against real data. Tag some audited-"
            "clean sessions via `divineos audit tag-clean <session_id> "
            "--round <round_id>` to enable calibration."
        ),
    }
