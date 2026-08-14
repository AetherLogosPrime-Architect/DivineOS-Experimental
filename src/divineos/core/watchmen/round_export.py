"""Export audit rounds to committed files so CI can verify they exist.

The merge-review gate's third requirement is that the round named in the
trailer is actually logged. It looked that up with ``get_round()``, which
reads ``DIVINEOS_HOME/data/event_ledger.db`` -- a file on the machine that
did the audit, gitignored, invisible to anything else.

The gate runs on a GitHub runner. There, that database does not exist; the
``audit_rounds`` table is not even created. ``_round_is_logged`` catches the
resulting error and returns False, so requirement 3 failed on every run no
matter what anyone did. Verified 2026-08-14 by pointing DIVINEOS_HOME at an
empty directory: ``sqlite3.OperationalError: no such table: audit_rounds``.
Across the 25 most recent integrity-audit runs the job never once passed on
its merits. Approvals could not have fixed it; nothing could.

Exporting the round into the repo fixes the visibility, and it makes the
requirement mean more than it did. A round in a local database is a claim
only the machine holding it can see. A round in ``docs/audit_rounds/`` lands
in the PR diff, so the operator reads the audit record in the same view where
they approve the merge.

What this does NOT do is make the round *trustworthy*. I write these files,
the same way I wrote the database rows. Requirement 3 has only ever proved a
round-id is not a typo. The load-bearing anchor is the operator's GitHub
approval on the head commit -- the one input I cannot produce -- and that is
untouched here.

Mirrors ``divineos prereg export``, which already puts pre-registrations in
``docs/pre_regs/`` for the same portability reason.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

EXPORT_DIRNAME = Path("docs") / "audit_rounds"


def export_dir(repo_root: Path) -> Path:
    return repo_root / EXPORT_DIRNAME


def round_export_path(repo_root: Path, round_id: str) -> Path:
    return export_dir(repo_root) / f"{round_id}.json"


def _plain(value: Any) -> Any:
    """Make a store record JSON-safe without hiding what it held."""
    if is_dataclass(value) and not isinstance(value, type):
        return {k: _plain(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_plain(v) for v in value]
    # Severity/Category/Status/Tier/ReviewStance are all str-valued enums.
    inner = getattr(value, "value", None)
    if inner is not None and not callable(inner):
        return _plain(inner)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def build_export(round_id: str) -> dict[str, Any] | None:
    """Assemble the round and its findings. None when the round is unknown."""
    from divineos.core.watchmen.store import get_round, list_findings

    record = get_round(round_id)
    if record is None:
        return None
    findings = list_findings(round_id=round_id, limit=500)
    return {
        "round": _plain(record),
        "findings": [_plain(f) for f in findings],
    }


def export_round(repo_root: Path, round_id: str) -> Path | None:
    """Write ``docs/audit_rounds/<round-id>.json``. None when unknown locally.

    Rewrites on every call. The export is a projection of the store, not a
    second source of truth: if a CONFIRMS arrives after the first export, the
    file has to be able to catch up or it would certify a stale count.
    """
    payload = build_export(round_id)
    if payload is None:
        return None
    path = round_export_path(repo_root, round_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def exported_round_exists(repo_root: Path, round_id: str) -> bool:
    """True when a well-formed export for ``round_id`` is present in the repo.

    A file whose contents name a different round does not count -- otherwise
    a copied filename would pass for a round nobody audited.
    """
    if not round_id:
        return False
    path = round_export_path(repo_root, round_id)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    record = payload.get("round")
    return isinstance(record, dict) and record.get("round_id") == round_id


__all__ = [
    "EXPORT_DIRNAME",
    "build_export",
    "export_dir",
    "export_round",
    "exported_round_exists",
    "round_export_path",
]
