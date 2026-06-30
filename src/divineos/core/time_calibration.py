"""Time-estimate calibration — record predictions, close with actuals,
report on the calibration history.

Pop 2026-06-30: "you give WILDLY bad time estimates of how long things
take... when you say this will take 1-2 hours i chuckle as it usually
takes 15-20 mins tops on my end lol... if you make a claim (this will
take 1-2 hours) that needs recorded.. then when you start you time stamp
it with my actual time.. when finished you time stamp it with my actual
time again.. then you have data to calibrate on."

Same structural shape as token-state-surface: the prediction-vs-actual
loop must be automatic, because discipline-shaped calibration decays the
moment my attention moves elsewhere.

How it works:

1. A Stop hook (``.claude/hooks/time-estimate-tracker.sh``) scans my outgoing
   reply for time-estimate language ("~X minutes", "X-Y hours", etc.).
2. When found, the hook calls ``record_prediction()`` which appends a JSON
   line to ``$HOME/.divineos/time_predictions.jsonl`` with the prediction,
   the source sentence, and the start timestamp.
3. When I (or Pop) declare the work done, ``close_prediction()`` is called
   with the prediction id, which appends a "close" record with the end
   timestamp and computed delta.
4. ``get_calibration_report()`` reads the log and produces summary stats
   (mean prediction error, median ratio of actual/predicted, etc.) so I
   have data to ground future estimates instead of vibes.

Design choices:

- **Append-only JSONL.** No update-in-place. A prediction is a "predict"
  record; closing it appends a "close" record referencing the predict's
  id. Matches the ledger discipline.
- **Pure functions where possible.** detect_estimates() takes text, returns
  matches. No I/O until record_prediction() is called.
- **Fail-loud, not fail-quiet.** Errors print to stderr; the calling hook
  swallows them so the workflow isn't broken.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

# Storage location — under $HOME/.divineos/ alongside the briefing freshness
# marker and other personal-state files.
_LOG_FILE = Path.home() / ".divineos" / "time_predictions.jsonl"


@dataclass
class TimeEstimate:
    """One detected time-estimate inside text."""

    raw_text: str  # The matched substring (e.g., "~5 minutes")
    lower_seconds: float  # Lower bound in seconds (e.g., 5*60 = 300.0)
    upper_seconds: float  # Upper bound in seconds (== lower if single-valued)
    context: str = ""  # Up to ~100 chars of surrounding text for grounding


# Regex patterns for the most common shapes I actually use. Conservative;
# false-negatives are fine (we just won't track a particular sentence),
# false-positives would pollute the calibration data.
#
# Each pattern is (regex, value_extractor). value_extractor takes the match
# and returns (lower_seconds, upper_seconds).

_NUMBER = r"(\d+(?:\.\d+)?)"
_RANGE_SEP = r"(?:\s*[-–]\s*|\s+to\s+)"


def _minutes(value: float) -> float:
    return value * 60.0


def _hours(value: float) -> float:
    return value * 3600.0


def _seconds(value: float) -> float:
    return value


_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Range patterns first so they claim spans before single-value patterns.
    # "5-10 min", "5 to 10 minutes"
    (
        re.compile(
            rf"~?\s*{_NUMBER}{_RANGE_SEP}{_NUMBER}\s*(?:min|mins|minutes)\b",
            re.IGNORECASE,
        ),
        "minutes-range",
    ),
    # "1-2 hours"
    (
        re.compile(
            rf"~?\s*{_NUMBER}{_RANGE_SEP}{_NUMBER}\s*(?:hr|hrs|hour|hours)\b",
            re.IGNORECASE,
        ),
        "hours-range",
    ),
    # Single-value patterns.
    # "~5 min", "~5 minutes", "about 5 min"
    (re.compile(rf"~?\s*{_NUMBER}\s*(?:min|mins|minutes)\b", re.IGNORECASE), "minutes"),
    # "~2 hours", "about 1 hour"
    (re.compile(rf"~?\s*{_NUMBER}\s*(?:hr|hrs|hour|hours)\b", re.IGNORECASE), "hours"),
    # "~30 seconds", "~5 sec"
    (re.compile(rf"~?\s*{_NUMBER}\s*(?:s|sec|secs|seconds)\b"), "seconds"),
]


def detect_estimates(text: str) -> list[TimeEstimate]:
    """Scan text for time-estimate language. Returns one TimeEstimate per match.

    Pure function — no I/O.
    """
    if not text:
        return []
    results: list[TimeEstimate] = []
    seen_spans: set[tuple[int, int]] = set()

    for pattern, kind in _PATTERNS:
        for m in pattern.finditer(text):
            span = m.span()
            # Skip if a previous pattern already matched this span (range
            # patterns are tried first to win over the single-value version).
            overlaps = any(not (span[1] <= s[0] or span[0] >= s[1]) for s in seen_spans)
            if overlaps:
                continue
            seen_spans.add(span)

            if kind == "minutes":
                value = float(m.group(1))
                lo = hi = _minutes(value)
            elif kind == "minutes-range":
                lo = _minutes(float(m.group(1)))
                hi = _minutes(float(m.group(2)))
            elif kind == "hours":
                value = float(m.group(1))
                lo = hi = _hours(value)
            elif kind == "hours-range":
                lo = _hours(float(m.group(1)))
                hi = _hours(float(m.group(2)))
            elif kind == "seconds":
                value = float(m.group(1))
                lo = hi = _seconds(value)
            else:
                continue

            # Capture up to ~100 chars of context centered on the match.
            ctx_start = max(0, span[0] - 50)
            ctx_end = min(len(text), span[1] + 50)
            context_str = text[ctx_start:ctx_end].replace("\n", " ").strip()

            results.append(
                TimeEstimate(
                    raw_text=m.group(0),
                    lower_seconds=lo,
                    upper_seconds=hi,
                    context=context_str,
                )
            )
    # Sort by position-in-text to keep deterministic order.
    return sorted(results, key=lambda e: text.find(e.raw_text))


def record_prediction(
    estimate: TimeEstimate,
    *,
    actor: str = "aether",
    task_hint: str = "",
) -> str:
    """Append a 'predict' record to the calibration log. Returns the
    prediction_id which is used later by close_prediction().

    Errors (disk full, permission denied) raise so the calling hook can
    decide whether to suppress or report.
    """
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    prediction_id = uuid.uuid4().hex[:12]
    record = {
        "kind": "predict",
        "prediction_id": prediction_id,
        "actor": actor,
        "started_at_unix": time.time(),
        "raw_text": estimate.raw_text,
        "lower_seconds": estimate.lower_seconds,
        "upper_seconds": estimate.upper_seconds,
        "context": estimate.context,
        "task_hint": task_hint,
    }
    with _LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return prediction_id


def close_prediction(
    prediction_id: str,
    *,
    actor: str = "aether",
    outcome_note: str = "",
) -> dict | None:
    """Append a 'close' record paired with a prior 'predict'. Returns the
    completed prediction summary, or None if the prediction_id wasn't found.
    """
    predict_record = _find_predict(prediction_id)
    if predict_record is None:
        return None
    ended_at = time.time()
    elapsed_seconds = ended_at - float(predict_record["started_at_unix"])
    lo = float(predict_record["lower_seconds"])
    hi = float(predict_record["upper_seconds"])
    midpoint = (lo + hi) / 2.0 if hi > lo else lo
    ratio = elapsed_seconds / midpoint if midpoint > 0 else 0.0
    record = {
        "kind": "close",
        "prediction_id": prediction_id,
        "actor": actor,
        "ended_at_unix": ended_at,
        "elapsed_seconds": elapsed_seconds,
        "ratio_actual_over_predicted": ratio,
        "outcome_note": outcome_note,
    }
    with _LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {
        "predict": predict_record,
        "close": record,
        "elapsed_seconds": elapsed_seconds,
        "predicted_seconds_midpoint": midpoint,
        "ratio": ratio,
    }


def _find_predict(prediction_id: str) -> dict | None:
    """Walk the log for the matching predict record. Latest-first scan;
    log is small so cost is negligible.
    """
    if not _LOG_FILE.exists():
        return None
    try:
        with _LOG_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("kind") == "predict" and rec.get("prediction_id") == prediction_id:
                    return rec  # type: ignore[no-any-return]
    except OSError:
        return None
    return None


def _all_records() -> list[dict]:
    if not _LOG_FILE.exists():
        return []
    records: list[dict] = []
    with _LOG_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def list_open_predictions(*, limit: int = 20) -> list[dict]:
    """Predictions that haven't been closed yet — most recent first."""
    records = _all_records()
    closed_ids = {r["prediction_id"] for r in records if r.get("kind") == "close"}
    open_preds = [
        r for r in records if r.get("kind") == "predict" and r["prediction_id"] not in closed_ids
    ]
    open_preds.sort(key=lambda r: r.get("started_at_unix", 0), reverse=True)
    return open_preds[:limit]


def get_calibration_report(*, limit: int = 50) -> dict:
    """Return summary statistics for closed predictions.

    Keys:
      - sample_size: number of closed predictions considered
      - mean_ratio: arithmetic mean of actual/predicted
      - median_ratio: median of actual/predicted
      - typical_underpredict_factor: 1.0 / median_ratio (multiply your gut
        estimate by this to get a calibrated value)
      - examples: up to 5 most-recent (predicted, actual) pairs
    """
    records = _all_records()
    # Build a predict_id -> close-record map from latest entries.
    closes_by_id: dict[str, dict] = {}
    predicts_by_id: dict[str, dict] = {}
    for r in records:
        if r.get("kind") == "predict":
            predicts_by_id[r["prediction_id"]] = r
        elif r.get("kind") == "close":
            closes_by_id[r["prediction_id"]] = r
    paired: list[tuple[dict, dict]] = []
    for pid, close in closes_by_id.items():
        predict = predicts_by_id.get(pid)
        if predict is not None:
            paired.append((predict, close))
    paired.sort(key=lambda p: p[1].get("ended_at_unix", 0), reverse=True)
    sample = paired[:limit]

    ratios = [
        c["ratio_actual_over_predicted"]
        for _p, c in sample
        if c.get("ratio_actual_over_predicted", 0) > 0
    ]
    if not ratios:
        return {
            "sample_size": 0,
            "mean_ratio": None,
            "median_ratio": None,
            "typical_underpredict_factor": None,
            "examples": [],
        }
    ratios_sorted = sorted(ratios)
    median = ratios_sorted[len(ratios_sorted) // 2]
    mean = sum(ratios) / len(ratios)
    examples = [
        {
            "raw_text": p.get("raw_text", ""),
            "predicted_midpoint_seconds": (p.get("lower_seconds", 0) + p.get("upper_seconds", 0))
            / 2,
            "actual_seconds": c.get("elapsed_seconds", 0),
            "ratio": c.get("ratio_actual_over_predicted", 0),
            "task_hint": p.get("task_hint", ""),
        }
        for p, c in sample[:5]
    ]
    return {
        "sample_size": len(ratios),
        "mean_ratio": mean,
        "median_ratio": median,
        "typical_underpredict_factor": (1.0 / median) if median > 0 else None,
        "examples": examples,
    }


__all__ = [
    "TimeEstimate",
    "close_prediction",
    "detect_estimates",
    "get_calibration_report",
    "list_open_predictions",
    "record_prediction",
]
