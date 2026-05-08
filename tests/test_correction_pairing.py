"""Regression test for the observe-then-learn pairing checker.

Audit r9-21 round-3+ — prereg-301e34c8bf39.

The detector finds compass observations that look like correction-
responses but have no matching learn entry filed within the expected
window. This isolates the heuristic and validates its behavior on
synthetic event sequences.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "event_ledger.db"))
    yield


def _seed_correction_event(when: float) -> None:
    """Insert a USER_CORRECTION event with a specified timestamp.

    log_event() stamps the event with the current time, which makes
    backdating impossible via that path. We INSERT directly so the
    test can position events in time relative to each other.
    """
    import json
    import uuid

    from divineos.core._ledger_base import get_connection
    from divineos.core.ledger import init_db

    init_db()
    conn = get_connection()
    try:
        eid = str(uuid.uuid4())
        payload = json.dumps({"trigger": "synthetic test correction"})
        conn.execute(
            "INSERT INTO system_events "
            "(event_id, timestamp, event_type, actor, payload, content_hash) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (eid, when, "USER_CORRECTION", "user", payload, "0" * 32),
        )
        conn.commit()
    finally:
        conn.close()


def _seed_observation(when: float, spectrum: str = "truthfulness") -> str:
    """Insert a compass observation at the given timestamp."""
    import sqlite3
    import uuid

    from divineos.core._ledger_base import get_connection

    conn = get_connection()
    try:
        # Ensure the table exists by issuing a CREATE IF NOT EXISTS that
        # matches the production schema. This avoids importing the
        # compass module (which is a guardrail file).
        conn.execute(
            "CREATE TABLE IF NOT EXISTS compass_observation ("
            "observation_id TEXT PRIMARY KEY, created_at REAL NOT NULL, "
            "spectrum TEXT NOT NULL, position REAL NOT NULL, "
            "evidence TEXT, source TEXT, session_id TEXT, "
            "tags TEXT, fire_id TEXT)"
        )
        oid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO compass_observation "
            "(observation_id, created_at, spectrum, position, evidence) "
            "VALUES (?, ?, ?, ?, ?)",
            (oid, when, spectrum, 0.0, "synthetic test observation"),
        )
        conn.commit()
    except sqlite3.OperationalError as e:
        pytest.skip(f"Compass schema unavailable in test env: {e}")
    finally:
        conn.close()
    return oid


def _seed_learn(when: float) -> None:
    """Insert a KNOWLEDGE_STORED event with a specified timestamp."""
    import json
    import uuid

    from divineos.core._ledger_base import get_connection
    from divineos.core.ledger import init_db

    init_db()
    conn = get_connection()
    try:
        eid = str(uuid.uuid4())
        payload = json.dumps({"content": "synthetic test learn entry"})
        conn.execute(
            "INSERT INTO system_events "
            "(event_id, timestamp, event_type, actor, payload, content_hash) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (eid, when, "KNOWLEDGE_STORED", "agent", payload, "0" * 32),
        )
        conn.commit()
    finally:
        conn.close()


def test_no_corrections_means_no_unpaired():
    """If there are no correction events at all, observations don't get flagged."""
    from check_correction_pairing import find_unpaired
    from divineos.core.ledger import init_db

    init_db()  # Ensure system_events table exists for get_events()
    _seed_observation(time.time())
    assert find_unpaired() == []


def test_correction_followed_by_observation_without_learn_flags():
    """Synthetic case: correction then observation, no learn → flagged."""
    from check_correction_pairing import find_unpaired

    now = time.time()
    _seed_correction_event(now - 60)  # correction 1 minute ago
    _seed_observation(now - 30)  # observation 30 seconds ago
    # No learn entry follows
    unpaired = find_unpaired()
    assert len(unpaired) == 1, f"expected 1 unpaired, got {len(unpaired)}"


def test_correction_observation_learn_chain_pairs_correctly():
    """Synthetic case: correction → observation → learn → no unpaired flag."""
    from check_correction_pairing import find_unpaired

    now = time.time()
    _seed_correction_event(now - 90)
    _seed_observation(now - 60)
    _seed_learn(now - 30)
    assert find_unpaired() == []


def test_observation_without_recent_correction_not_flagged():
    """Observation with no correction in the lookback window: not a correction-response."""
    from check_correction_pairing import find_unpaired

    now = time.time()
    # Correction is well outside the lookback window (60 minutes ago)
    _seed_correction_event(now - 3600)
    _seed_observation(now - 60)
    # No learn entry, but observation isn't tied to a recent correction
    assert find_unpaired() == []
