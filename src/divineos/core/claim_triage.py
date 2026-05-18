"""Triage store for the show-fix audit walk.

Andrew named the cost 2026-05-14 night: once lying is surfaced, the
whole inventory of prior 'shipped' claims becomes suspect. The
triage store is the structural answer — a persistent record where
every prior claim gets one of three statuses:

- ``VERIFIED`` — a falsifier test exists and runs green now.
- ``SUSPECT`` — no falsifier exists; the claim is not known to hold.
- ``REMOVED`` — the original claim was wrong or no longer applies;
  explicitly retracted.

The store is append-only (status transitions are new entries, not
mutations of old ones). Each entry carries timestamp, git sha, and
optional notes naming what's being claimed and what evidence backs
the status.

## Why the store matters separately from ship_claim

``ship_claim`` enforces falsifier verification at filing time for
NEW shipped claims. ``claim_triage`` is for the BACKLOG: things that
were claimed shipped in the past without falsifier, and which now
need walking. SUSPECT entries are the inventory of what needs work;
VERIFIED entries that came from triage record that someone walked
back through and proved the prior claim with a falsifier.

The size of the SUSPECT column is the honest answer to 'what else
is broken?' — it's a number the operator can see, growing as the
walk surfaces things and shrinking as each one is verified or removed.
"""

from __future__ import annotations

__guardrail_required__ = True

import json
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class TriageStatus(str, Enum):
    VERIFIED = "VERIFIED"
    SUSPECT = "SUSPECT"
    REMOVED = "REMOVED"


_STORE_FILE = Path.home() / ".divineos" / "claim_triage.json"


@dataclass(frozen=True)
class TriageEntry:
    claim: str
    status: TriageStatus
    notes: str
    timestamp: float
    git_sha: str
    test_path: str  # optional pytest path; empty if SUSPECT/REMOVED


def _git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


def _load() -> list[dict[str, Any]]:
    if not _STORE_FILE.exists():
        return []
    try:
        data = json.loads(_STORE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return []


def _save(entries: list[dict[str, Any]]) -> bool:
    try:
        _STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _STORE_FILE.write_text(json.dumps(entries, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False


# Self-actor names that cannot mark VERIFIED. The running agent IS
# aether, so allowing aether-VERIFIED would be the self-audit-as-
# external-validation hole Aletheia named (gap 2).
_SELF_ACTOR_NAMES = frozenset({"aether", "aether-substrate", "aether-running"})


def _validate_actor_for_status(actor: str, status: TriageStatus) -> tuple[bool, str]:
    """Validate the actor can transition to this status.

    Closes Aletheia Finding 50 + gap 2 (2026-05-15):
    - actor is required (no entries without recorded filer)
    - VERIFIED requires non-internal AND non-self actor
    - SUSPECT and REMOVED accept any non-internal actor

    Aether can mark SUSPECT or REMOVED on his own work. VERIFIED
    requires external co-sign (aletheia, grok, user, council).
    """
    if not actor or not actor.strip():
        return False, (
            "actor parameter required — every triage entry must record "
            "who filed it. Use --actor=<name> on the CLI."
        )
    try:
        from divineos.core.watchmen.store import _validate_actor as _w_validate

        _w_validate(actor)
    except ValueError as e:
        return False, str(e)
    except Exception:  # noqa: BLE001 - observability boundary
        pass

    if status == TriageStatus.VERIFIED:
        normalized = actor.strip().lower()
        if normalized in _SELF_ACTOR_NAMES:
            return False, (
                f"Actor '{actor}' cannot mark status=VERIFIED on its own "
                f"work — self-audit-as-external-validation hole. VERIFIED "
                f"requires external co-sign (aletheia, grok, user, "
                f"council, etc.). Aether can mark SUSPECT or REMOVED."
            )
    return True, ""


def add_entry(
    claim: str,
    status: TriageStatus,
    actor: str = "",
    notes: str = "",
    test_path: str = "",
) -> dict[str, Any]:
    """Append a triage entry. Returns the entry dict.

    Raises ValueError on validation failure (empty claim, missing actor,
    or actor not authorized for the requested status).
    """
    if not claim.strip():
        raise ValueError("claim text required")
    ok, why = _validate_actor_for_status(actor, status)
    if not ok:
        raise ValueError(why)
    entry: dict[str, Any] = {
        "claim": claim.strip(),
        "status": status.value if isinstance(status, TriageStatus) else str(status),
        "actor": actor.strip(),  # Aletheia Finding 50
        "notes": notes.strip(),
        "test_path": test_path.strip(),
        "timestamp": time.time(),
        "git_sha": _git_sha(),
    }
    entries = _load()
    entries.append(entry)
    _save(entries)
    return entry


def list_entries(status: TriageStatus | None = None) -> list[dict[str, Any]]:
    """Return entries. If status is given, filter to that status only.

    Filtering uses LATEST-status-per-claim semantics: an entry that
    was once SUSPECT and then transitioned to VERIFIED counts as
    VERIFIED for the filter (latest status wins).
    """
    entries = _load()
    if status is None:
        return entries
    target = status.value if isinstance(status, TriageStatus) else str(status)
    # Build latest-status-per-claim map.
    latest: dict[str, dict[str, Any]] = {}
    for e in entries:
        latest[e.get("claim", "")] = e
    return [e for e in latest.values() if e.get("status") == target]


def summary() -> dict[str, int]:
    """Return counts by current status (latest per claim).

    Closes Aletheia Finding 52 (2026-05-15): the summary used to
    flatten VERIFIED into one count. A gamed VERIFIED (no test_path,
    no real falsifier) was visually identical to a legitimate VERIFIED.
    The fix surfaces the distinction:

    - ``VERIFIED``: total VERIFIED count (kept for backward compat)
    - ``VERIFIED_with_test``: legitimate — entry has a test_path
    - ``VERIFIED_without_test``: suspect-shaped — entry marked VERIFIED
      but no falsifier-path recorded. Visible as its own count creates
      social cost for the manipulation.
    """
    entries = _load()
    latest: dict[str, dict[str, Any]] = {}
    for e in entries:
        latest[e.get("claim", "")] = e
    counts: dict[str, int] = {
        "VERIFIED": 0,
        "VERIFIED_with_test": 0,
        "VERIFIED_without_test": 0,
        "SUSPECT": 0,
        "REMOVED": 0,
    }
    for e in latest.values():
        status = e.get("status", "")
        if status == "VERIFIED":
            counts["VERIFIED"] += 1
            if (e.get("test_path") or "").strip():
                counts["VERIFIED_with_test"] += 1
            else:
                counts["VERIFIED_without_test"] += 1
        elif status in ("SUSPECT", "REMOVED"):
            counts[status] += 1
    return counts


__all__ = [
    "TriageEntry",
    "TriageStatus",
    "add_entry",
    "list_entries",
    "summary",
]
