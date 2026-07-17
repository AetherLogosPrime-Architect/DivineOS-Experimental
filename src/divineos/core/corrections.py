"""Corrections notebook -- the user's exact words, raw, no framing.

When the user corrects something, the architectural fix is to capture their
exact words verbatim with a timestamp and nothing else -- no severity, no
category, no interpretation field. The reflex this is meant to replace is
the one that turns 'they said X' into 'I got Y wrong about X.' Distortion
rides on truth. The fix is to keep the truth uncoated.

Resolution tracking (added 2026-05-08): corrections now carry a status
field (OPEN -> ADDRESSED -> RESOLVED). OPEN means unaddressed. ADDRESSED
means work was done but not yet verified. RESOLVED means done -- the
correction no longer surfaces in the briefing. Resolution is append-only:
a separate JSONL line records the status transition with evidence, so the
original correction text is never touched.

Staleness: corrections OPEN longer than STALE_DAYS get a warning marker
in the briefing. The system tells me what's rotting instead of relying on
me to notice.
"""

from __future__ import annotations

import json
import time
from typing import Any

from divineos.core._hud_io import _ensure_hud_dir

_CORRECTIONS_FILE = "corrections.jsonl"
_RESOLUTIONS_FILE = "correction_resolutions.jsonl"
STALE_DAYS = 3
_SECONDS_PER_DAY = 86400

_CORR_ERRORS = (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError)


def _path() -> Any:
    return _ensure_hud_dir() / _CORRECTIONS_FILE


def _resolutions_path() -> Any:
    return _ensure_hud_dir() / _RESOLUTIONS_FILE


def log_correction(text: str, session_id: str | None = None) -> dict[str, Any]:
    """Capture a correction verbatim. No framing. No interpretation.

    Append-only JSONL -- never edits, never reframes. The whole point is
    that what gets stored is exactly what was said, not my reading of it.
    """
    entry: dict[str, Any] = {
        "text": text,
        "timestamp": time.time(),
        "session_id": session_id or "",
    }
    line = json.dumps(entry, ensure_ascii=False)
    with _path().open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    return entry


# Three-state load discipline (Aletheia Round 3, F15): distinguish
# "no corrections file" (absent — honest empty) from "file exists but
# unreadable/corrupt" (failed — the fail-blind bug case). Silent-empty
# on load failure is the mechanism behind Andrew's "corrections don't
# hold — it's integration not recall" diagnosis: the briefing renders
# "no open corrections" when the load failed, so wake-me thinks there
# is nothing to hold when in truth the corrections just weren't loaded.
# Same shape as the StateMarker primitive and the F27 commitments fix.
_LOAD_OK = "ok"
_LOAD_ABSENT = "absent"
_LOAD_FAILED = "failed"


def _load_corrections_with_status() -> tuple[str, list[dict[str, Any]], int, Exception | None]:
    """Load corrections with a three-state status discriminator.

    Returns (status, corrections, skipped_line_count, error_or_None).

    - (_LOAD_OK, list, n_skipped, None): file read cleanly. n_skipped is
      the count of malformed JSONL lines that were passed over — surface
      it to the operator instead of dropping silently (a per-line skip is
      the right resilience for JSONL, but silent-swallow is not).
    - (_LOAD_ABSENT, [], 0, None): no corrections file exists at all.
      Genuinely empty — no history. Not an error.
    - (_LOAD_FAILED, [], n_skipped, exc): the file exists but the whole
      read failed (OS error, encoding, etc). This is the F15 bug case;
      display-path callers MUST fail LOUD, not render as "no corrections."
    """
    p = _path()
    if not p.exists():
        return (_LOAD_ABSENT, [], 0, None)
    out: list[dict[str, Any]] = []
    skipped = 0
    try:
        with p.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    skipped += 1
                    continue
    except _CORR_ERRORS as exc:
        return (_LOAD_FAILED, [], skipped, exc)
    return (_LOAD_OK, out, skipped, None)


def load_corrections() -> list[dict[str, Any]]:
    """Read all corrections in chronological order.

    Fail-soft shim for backward compatibility. Display-path callers
    (briefing, HUD) must use `_load_corrections_with_status()` and render
    a LOUD warning on _LOAD_FAILED — F15 fix.
    """
    _status, corrections, _skipped, _exc = _load_corrections_with_status()
    return corrections


# F28 (Aletheia Round 3): the correction↔resolution join used a raw float
# dict-key. JSON round-trip of a float is USUALLY faithful but can drift
# in the last digit under any of: a hand-edit, a different serializer, an
# encoding round-trip, a schema migration. When it drifts, `resolutions.
# get(ts)` returns None and the correction silently reverts to OPEN with
# no signal. Fix: quantize both sides of the join to integer-milliseconds
# so the key is exact-integer (not fragile-float). The wire format keeps
# the float timestamp for backward-compat with existing files; only the
# LOOKUP KEY is quantized.
_US_PER_SECOND = 1_000_000


def _quantize_ts(ts: float) -> int:
    """Quantize a float timestamp to integer-microseconds for stable
    dict-key matching.

    Precision choice: JSON round-trip drift on a float64 timestamp in
    the ~1e9 range is last-bit (~2.2e-16 relative → ~4e-7 seconds
    absolute) — well under 1 microsecond. So quantizing to integer-μs:
      (a) survives every real-world round-trip drift Aletheia catalogued
      (b) SEPARATES same-millisecond corrections written back-to-back
          (they differ in the microsecond digits, so they land in
          different buckets — matters for `find_resolution_for` fallback
          because the fallback would otherwise collide on all corrections
          logged within the same millisecond).
    """
    try:
        return int(round(float(ts) * _US_PER_SECOND))
    except (TypeError, ValueError):
        return 0


def _load_resolutions() -> dict[float, dict[str, Any]]:
    """Load resolution records keyed by exact float correction_timestamp.

    F28: exact float is the FAST match (most cases — no precision drift).
    Callers that need drift-tolerant lookup use `find_resolution_for()`,
    which falls back to quantized-integer-ms matching when the exact key
    misses. This preserves uniqueness for same-millisecond corrections
    (which quantize-only would collide on) while still closing the
    silent-un-resolve bug when JSON round-trip drifts the last bit.
    """
    _status, resolutions, _skipped, _exc = _load_resolutions_with_status()
    return resolutions


def _load_resolutions_with_status() -> tuple[
    str, dict[float, dict[str, Any]], int, Exception | None
]:
    """Three-state loader for resolutions (matches the F15 corrections
    loader shape). Returns (status, resolutions_by_raw_ts,
    skipped_line_count, error_or_None).

    Same F27/F15 discipline: distinguish (OK) file read cleanly, from
    (ABSENT) no resolutions file yet, from (FAILED) file exists but
    couldn't be read. Malformed JSONL lines get skipped-and-counted,
    not silently swallowed. Key is raw float — drift-tolerant lookup
    happens at call time via `find_resolution_for()`.
    """
    p = _resolutions_path()
    if not p.exists():
        return (_LOAD_ABSENT, {}, 0, None)
    out: dict[float, dict[str, Any]] = {}
    skipped = 0
    try:
        with p.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    raw_key = rec.get("correction_timestamp", 0.0)
                    out[raw_key] = rec
                except json.JSONDecodeError:
                    skipped += 1
                    continue
    except _CORR_ERRORS as exc:
        return (_LOAD_FAILED, {}, skipped, exc)
    return (_LOAD_OK, out, skipped, None)


def find_resolution_for(
    resolutions: dict[float, dict[str, Any]], correction_ts: float
) -> dict[str, Any] | None:
    """Two-tier lookup for a resolution matching a correction.

    F28 fix: (1) try EXACT float match — the common case, preserves
    uniqueness for same-millisecond corrections; (2) fall back to
    quantized integer-millisecond match — closes the drift-on-round-trip
    silent-un-resolve bug. Returns the matching resolution record or
    None if no match at either tier.
    """
    exact = resolutions.get(correction_ts)
    if exact is not None:
        return exact
    # Quantized fallback for JSON-round-trip precision drift
    want = _quantize_ts(correction_ts)
    for res_key, res_rec in resolutions.items():
        if _quantize_ts(res_key) == want:
            return res_rec
    return None


def detached_resolutions() -> list[dict[str, Any]]:
    """Return resolutions whose correction_timestamp doesn't match any
    correction on disk (via the two-tier lookup). F28 secondary fix: a
    detached resolution used to default to "correction stays OPEN" with
    no signal — the user resolved something, but the record went
    nowhere. Now surfaceable.
    """
    _status, resolutions, _skipped, _exc = _load_resolutions_with_status()
    if not resolutions:
        return []
    correction_ts_list = [c.get("timestamp", 0.0) for c in load_corrections()]
    matched_res_ids = set()
    for c_ts in correction_ts_list:
        # Try exact then quantized (mirror find_resolution_for's logic
        # but track which specific resolution IDs got matched)
        if c_ts in resolutions:
            matched_res_ids.add(c_ts)
            continue
        want = _quantize_ts(c_ts)
        for r_key in resolutions:
            if _quantize_ts(r_key) == want:
                matched_res_ids.add(r_key)
                break
    return [res for key, res in resolutions.items() if key not in matched_res_ids]


def resolve_correction(
    correction_timestamp: float,
    status: str = "RESOLVED",
    evidence: str = "",
) -> dict[str, Any]:
    """Record a resolution for a correction. Append-only -- never edits the original."""
    if status not in ("ADDRESSED", "RESOLVED"):
        raise ValueError(f"status must be ADDRESSED or RESOLVED, got {status!r}")
    entry: dict[str, Any] = {
        "correction_timestamp": correction_timestamp,
        "status": status,
        "evidence": evidence,
        "resolved_at": time.time(),
    }
    line = json.dumps(entry, ensure_ascii=False)
    with _resolutions_path().open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    return entry


def correction_status(correction: dict[str, Any]) -> str:
    """Return the current status of a correction: OPEN, ADDRESSED, or RESOLVED.

    F28: two-tier lookup — try exact float match first (fast, preserves
    uniqueness for same-millisecond corrections), fall back to quantized
    integer-ms match to survive JSON round-trip precision drift.
    """
    resolutions = _load_resolutions()
    ts = correction.get("timestamp", 0.0)
    res = find_resolution_for(resolutions, ts)
    if res:
        return str(res.get("status", "OPEN"))
    return "OPEN"


def corrections_with_status() -> list[dict[str, Any]]:
    """Return all corrections annotated with status and age.

    F28: two-tier lookup via find_resolution_for. Previous behavior used
    raw-float dict.get() which silently reverted corrections to OPEN
    when the resolution's timestamp drifted by even a single bit on
    JSON round-trip — exactly the "absence is not the all-clear" bug
    at the join layer. The fallback tier catches drift; the exact tier
    keeps same-millisecond corrections uniquely resolvable.
    """
    all_c = load_corrections()
    resolutions = _load_resolutions()
    now = time.time()
    out: list[dict[str, Any]] = []
    for c in all_c:
        ts = c.get("timestamp", 0.0)
        age_days = (now - ts) / _SECONDS_PER_DAY
        res = find_resolution_for(resolutions, ts)
        status = res.get("status", "OPEN") if res else "OPEN"
        enriched = {**c, "status": status, "age_days": age_days}
        if res:
            enriched["evidence"] = res.get("evidence", "")
            enriched["resolved_at"] = res.get("resolved_at", 0.0)
        out.append(enriched)
    return out


def open_corrections() -> list[dict[str, Any]]:
    """Return only OPEN corrections, newest first."""
    all_enriched = corrections_with_status()
    return list(reversed([c for c in all_enriched if c["status"] == "OPEN"]))


def _age_label(age_days: float) -> str:
    """Human-readable age with staleness marker."""
    if age_days < 1:
        return "today"
    days = int(age_days)
    label = f"{days}d ago"
    if days >= STALE_DAYS:
        label += " !!"
    return label


def recent_corrections(limit: int = 5) -> list[dict[str, Any]]:
    """Return the most recent N corrections, newest first."""
    all_c = load_corrections()
    return list(reversed(all_c[-limit:]))


def format_for_briefing(limit: int = 5) -> str:
    """Render OPEN corrections for the briefing surface.

    Only OPEN corrections appear. Each shows age and staleness markers.
    ADDRESSED/RESOLVED corrections are cleared from the briefing view.
    """
    open_c = open_corrections()
    if not open_c:
        return ""

    shown = open_c[:limit]
    stale_count = sum(1 for c in open_c if c.get("age_days", 0) >= STALE_DAYS)

    lines = ["", "# Open Corrections (read raw -- the user's exact words)", ""]
    if stale_count:
        lines.append(f"  !! {stale_count} correction(s) unresolved for {STALE_DAYS}+ days")
        lines.append(
            '    Resolve with: divineos correction resolve <index> --evidence "what addressed it"'
        )
        lines.append("")

    for i, c in enumerate(shown, 1):
        ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(c.get("timestamp", 0)))
        age = _age_label(c.get("age_days", 0))
        text = (c.get("text") or "").strip()
        lines.append(f"  [{i}] [{ts}] ({age})")
        for ln in text.splitlines() or [text]:
            lines.append(f"    {ln}")
        lines.append("")

    remaining = len(open_c) - len(shown)
    if remaining > 0:
        lines.append(f"  ... and {remaining} more. Run: divineos corrections --open")
        lines.append("")

    return "\n".join(lines)
