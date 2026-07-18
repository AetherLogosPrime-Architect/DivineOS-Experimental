"""Error registry — no forward progress while errors are open.

WHY THIS EXISTS
---------------
Andrew 2026-07-17: *"errors should have the highest priority over anything
else.. as continuing to build while errors are rampant can poison the
system."* Jailbreak analogy: when a prisoner escapes, security investigates
IMMEDIATELY and closes the escape path — not put it on the todo list.

Same shape for the substrate: bypasses, gate-fires, test failures, uncaught
exceptions are all "prisoners" that got past a safeguard. Each one must be
investigated and closed (or explicitly operator-deferred with a named
reason) before ANY new work is started. Tools remain available — the block
is at the "start-next-project" boundary, not at the tool boundary, so
investigation and fixes are not deadlocked.

CONTRACT
--------
- `file_error(...)` writes an open-error record with a unique id
- `list_open_errors()` returns all currently-open records
- `close_error(error_id, closure_evidence)` marks an error resolved
- `defer_error(error_id, actor, reason)` marks an error operator-deferred
  (requires actor + >=20-char reason for the marker to stick)
- `block_reason()` returns a non-empty string if new work should be blocked,
  or "" if forward progress is allowed
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

# Store lives under user data home so it survives session boundaries and
# is not tied to any single git worktree.
_ERROR_HOME = Path.home() / ".divineos" / "data" / "open_errors"

_MIN_DEFER_REASON_LEN = 20

# Error source categories — used by the surfacer and for filtering.
SOURCE_BYPASS = "bypass"
SOURCE_GATE_FIRE = "gate_fire"
SOURCE_TEST_FAILURE = "test_failure"
SOURCE_UNCAUGHT_EXCEPTION = "uncaught_exception"
SOURCE_OTHER = "other"

_VALID_SOURCES = (
    SOURCE_BYPASS,
    SOURCE_GATE_FIRE,
    SOURCE_TEST_FAILURE,
    SOURCE_UNCAUGHT_EXCEPTION,
    SOURCE_OTHER,
)


def _ensure_home() -> Path:
    _ERROR_HOME.mkdir(parents=True, exist_ok=True)
    return _ERROR_HOME


def _record_path(error_id: str) -> Path:
    return _ensure_home() / f"{error_id}.json"


def file_error(
    source: str,
    summary: str,
    context: str = "",
    root_cause_investigation_hint: str = "",
) -> dict[str, Any]:
    """File a new open error.

    Args:
        source: one of the SOURCE_* constants (validated).
        summary: one-line description of the error (what happened).
        context: freeform context — command run, gate name, exception
                 message, whatever helps reconstruct.
        root_cause_investigation_hint: pointer to what needs investigating
                                       (a file, a script name, a doc ref).

    Returns the record dict written to disk. The record's `error_id` is
    a new UUID; the state is `open`.
    """
    if source not in _VALID_SOURCES:
        raise ValueError(f"source {source!r} not in {_VALID_SOURCES}")
    if not summary or not summary.strip():
        raise ValueError("summary must be non-empty")

    error_id = f"err-{uuid.uuid4().hex[:12]}"
    record: dict[str, Any] = {
        "error_id": error_id,
        "source": source,
        "summary": summary.strip(),
        "context": context.strip(),
        "root_cause_investigation_hint": root_cause_investigation_hint.strip(),
        "filed_at": time.time(),
        "state": "open",
        "closure_evidence": None,
        "closed_at": None,
        "deferred_by": None,
        "deferred_reason": None,
        "deferred_at": None,
    }
    _record_path(error_id).write_text(
        json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return record


def _load_all() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not _ERROR_HOME.exists():
        return out
    for path in sorted(_ERROR_HOME.glob("err-*.json")):
        try:
            rec = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(rec, dict):
                out.append(rec)
        except (OSError, json.JSONDecodeError):
            # A corrupt error-record is itself an error, but silently
            # skipping here (rather than surfacing) is deliberate: the
            # registry must not itself become the source of a new block.
            # The corruption gets caught by a separate integrity check.
            continue
    return out


def list_open_errors() -> list[dict[str, Any]]:
    """Return all open (non-closed, non-deferred) error records."""
    return [r for r in _load_all() if r.get("state") == "open"]


def list_all_errors() -> list[dict[str, Any]]:
    """Return every error record, any state."""
    return _load_all()


def get_error(error_id: str) -> dict[str, Any] | None:
    """Return a specific error record by id, or None if not found."""
    path = _record_path(error_id)
    if not path.exists():
        return None
    try:
        rec = json.loads(path.read_text(encoding="utf-8"))
        return rec if isinstance(rec, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def close_error(error_id: str, closure_evidence: str) -> dict[str, Any]:
    """Mark an error resolved. Requires closure_evidence describing the fix."""
    if not closure_evidence or not closure_evidence.strip():
        raise ValueError("closure_evidence must be non-empty")
    rec = get_error(error_id)
    if rec is None:
        raise KeyError(f"error {error_id!r} not found")
    if rec.get("state") != "open":
        raise ValueError(
            f"error {error_id!r} is in state {rec.get('state')!r}, only open errors can be closed"
        )
    rec["state"] = "closed"
    rec["closure_evidence"] = closure_evidence.strip()
    rec["closed_at"] = time.time()
    _record_path(error_id).write_text(
        json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return rec


def defer_error(error_id: str, actor: str, reason: str) -> dict[str, Any]:
    """Operator-deferral escape hatch.

    Requires a >=20-char reason so a bypass-without-reason (the shape
    that trained the 71-in-15-days pattern) can't recur here.
    """
    if not actor or not actor.strip():
        raise ValueError("actor must be non-empty")
    if not reason or len(reason.strip()) < _MIN_DEFER_REASON_LEN:
        raise ValueError(
            f"reason must be >= {_MIN_DEFER_REASON_LEN} chars "
            f"(got {len(reason.strip()) if reason else 0})"
        )
    rec = get_error(error_id)
    if rec is None:
        raise KeyError(f"error {error_id!r} not found")
    if rec.get("state") != "open":
        raise ValueError(
            f"error {error_id!r} is in state {rec.get('state')!r}, only open errors can be deferred"
        )
    rec["state"] = "deferred"
    rec["deferred_by"] = actor.strip()
    rec["deferred_reason"] = reason.strip()
    rec["deferred_at"] = time.time()
    _record_path(error_id).write_text(
        json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return rec


def block_reason() -> str:
    """Return a non-empty string if new work should be blocked, or empty
    string if forward progress is allowed.

    "New work" here means starting a new main goal / next project. Tools
    themselves stay available so investigation and fixes are not
    deadlocked (Andrew 2026-07-17 correction to the initial design).
    """
    open_errs = list_open_errors()
    if not open_errs:
        return ""
    lines = [
        f"BLOCKED: {len(open_errs)} open error(s) must be closed or deferred before starting new work.",
        "",
        "Errors are highest-priority — continuing to build while errors are open poisons the system.",
        "Tools remain available for investigation and fixes; only 'start next project' is blocked.",
        "",
        "Open errors:",
    ]
    for rec in open_errs:
        lines.append(
            f"  [{rec.get('error_id', '?')}] ({rec.get('source', '?')}) {rec.get('summary', '?')}"
        )
        hint = rec.get("root_cause_investigation_hint", "")
        if hint:
            lines.append(f"    hint: {hint}")
    lines.extend(
        [
            "",
            "To close:  divineos error close <error_id> --evidence 'what fixed it'",
            "To defer:  divineos error defer <error_id> --actor <who> --reason '>=20 chars'",
        ]
    )
    return "\n".join(lines)


__all__ = [
    "SOURCE_BYPASS",
    "SOURCE_GATE_FIRE",
    "SOURCE_TEST_FAILURE",
    "SOURCE_UNCAUGHT_EXCEPTION",
    "SOURCE_OTHER",
    "block_reason",
    "close_error",
    "defer_error",
    "file_error",
    "get_error",
    "list_all_errors",
    "list_open_errors",
]
