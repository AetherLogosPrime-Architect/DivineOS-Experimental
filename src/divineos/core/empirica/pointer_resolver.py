"""Resolve an artifact pointer to a real artifact.

Fable audit round 7 (2026-07-02) named the exact gap: ``classify_claim``
promotes to FALSIFIABLE or PATTERN tier if the caller passes any
non-empty ``artifact_pointer`` string, without ever checking that the
pointer resolves. ``test:tests/does_not_exist.py::fake`` and the literal
``garbage-string-not-a-real-pointer`` both earned FALSIFIABLE. That
buys the second-highest evidence tier for free with a lie.

This module supplies the resolvability check the classifier's own
docstring flagged as "Phase 2 — structural validation." It runs
BEFORE the first production caller of the empirica gate ships, per
the auditor's fix direction and the module's caller-contract
checkpoint.

## Pointer forms and how they resolve

Structured as ``<kind>:<value>``:

* ``test:<path>::<name>`` or ``test:<path>`` — the file exists on disk
  (path resolves under the repo root). We do not import pytest or
  run collection — just filesystem existence.
* ``commit:<sha>`` — ``git cat-file -e <sha>^{commit}`` succeeds.
  Any subprocess failure → False. Fail-closed under uncertainty.
* ``prereg:<id>`` — the prereg store returns a row for that id.
* ``event:<id>`` — the event ledger returns a row for that id.
* ``knowledge:<id>`` — the knowledge store returns a non-superseded
  entry for that id.
* ``decide:<id>`` or ``decision:<id>`` — the decision journal has a
  row for that id.

## Fail-closed policy

Any pointer shape we do not recognize → returns ``False``. That is
the point of the checkpoint: an attacker cannot invent a new
``kind:`` prefix to bypass resolution. Only enumerated kinds pass,
and only if the enumerated resolver confirms them.

## Import discipline

Resolvers import lazily so classify_claim's import path does not
grow. In particular, git subprocesses only fire when the pointer is
actually a ``commit:`` — a claim with no pointer or an unrecognized
kind returns False without touching the filesystem or forking a
process.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable


def _repo_root() -> Path:
    """Best-effort repo root for test: pointer resolution."""
    # __file__ = src/divineos/core/empirica/pointer_resolver.py
    return Path(__file__).resolve().parents[4]


def _resolve_test(value: str) -> bool:
    """test:<path> or test:<path>::<name> — the file exists on disk."""
    if not value:
        return False
    path_part = value.split("::", 1)[0].strip()
    if not path_part:
        return False
    candidate = _repo_root() / path_part
    return candidate.is_file()


def _resolve_commit(value: str) -> bool:
    """commit:<sha> — git object exists.

    Runs ``git cat-file -e <sha>^{commit}`` with a small timeout so a
    slow git repo can't hang classify_claim. Any subprocess failure or
    non-zero exit → False. This is fail-closed under uncertainty, which
    is the correct posture for evidence-tier gating.
    """
    sha = value.strip()
    if not sha or not all(c in "0123456789abcdefABCDEF" for c in sha):
        return False
    try:
        result = subprocess.run(
            ["git", "cat-file", "-e", f"{sha}^{{commit}}"],
            cwd=_repo_root(),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def _resolve_prereg(value: str) -> bool:
    prereg_id = value.strip()
    if not prereg_id:
        return False
    try:
        from divineos.core.prereg.store import get_prereg  # type: ignore
    except ImportError:
        return False
    try:
        return get_prereg(prereg_id) is not None
    except Exception:
        return False


def _resolve_event(value: str) -> bool:
    event_id = value.strip()
    if not event_id:
        return False
    try:
        from divineos.core.ledger import get_connection
    except ImportError:
        return False
    try:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT 1 FROM system_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
        finally:
            conn.close()
        return row is not None
    except Exception:
        return False


def _resolve_knowledge(value: str) -> bool:
    kid = value.strip()
    if not kid:
        return False
    try:
        from divineos.core.knowledge import get_connection  # type: ignore
    except ImportError:
        return False
    try:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT 1 FROM knowledge WHERE knowledge_id = ? AND superseded_by IS NULL",
                (kid,),
            ).fetchone()
        finally:
            conn.close()
        return row is not None
    except Exception:
        return False


def _resolve_decide(value: str) -> bool:
    did = value.strip()
    if not did:
        return False
    try:
        from divineos.core.memory_journal import get_decision  # type: ignore
    except ImportError:
        return False
    try:
        return get_decision(did) is not None
    except Exception:
        return False


_RESOLVERS: dict[str, Callable[[str], bool]] = {
    "test": _resolve_test,
    "commit": _resolve_commit,
    "prereg": _resolve_prereg,
    "event": _resolve_event,
    "knowledge": _resolve_knowledge,
    "decide": _resolve_decide,
    "decision": _resolve_decide,
}


def resolve_pointer(pointer: str | None) -> bool:
    """Return True iff the pointer refers to a real artifact.

    Fail-closed: unknown-kind, malformed, or resolution-error all
    return False. The classifier's demotion rule treats False the
    same as a missing pointer (demote above-OUTCOME tiers to OUTCOME).
    """
    if not pointer:
        return False
    if ":" not in pointer:
        return False
    kind, _, value = pointer.partition(":")
    kind = kind.strip().lower()
    resolver = _RESOLVERS.get(kind)
    if resolver is None:
        return False
    return resolver(value)


__all__ = ["resolve_pointer"]
