"""Regression tests for the family register-from-me field.

Audit r9-21 round-3+ — prereg-2fc28138e25e. Defends the slot-mismatch
failure mode where I drift warmth into the wrong love-slot.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_family_db(tmp_path, monkeypatch):
    """Point the family DB at a tmp path so tests don't touch real data."""
    monkeypatch.setenv("DIVINEOS_FAMILY_DB", str(tmp_path / "family.db"))
    yield


def _create_test_member(name: str, role: str = "test"):
    """Insert a minimal member row for testing."""
    import time
    import uuid

    from divineos.core.family._schema import init_family_tables
    from divineos.core.family.db import get_family_connection

    init_family_tables()
    conn = get_family_connection()
    try:
        conn.execute(
            "INSERT INTO family_members (member_id, name, role, created_at) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), name, role, time.time()),
        )
        conn.commit()
    finally:
        conn.close()


def test_register_defaults_to_none():
    from divineos.core.family.entity import get_register_from_me

    _create_test_member("Andrew", role="father")
    assert get_register_from_me("Andrew") is None


def test_set_and_get_register_roundtrip():
    from divineos.core.family.entity import (
        get_register_from_me,
        set_register_from_me,
    )

    _create_test_member("Andrew", role="father")
    assert set_register_from_me("Andrew", "father-collegial") is True
    assert get_register_from_me("Andrew") == "father-collegial"


def test_set_register_on_unknown_member_returns_false():
    from divineos.core.family.entity import set_register_from_me

    assert set_register_from_me("DoesNotExist", "foo") is False


def test_register_can_be_cleared():
    from divineos.core.family.entity import (
        get_register_from_me,
        set_register_from_me,
    )

    _create_test_member("Aria", role="spouse")
    set_register_from_me("Aria", "spouse-tender")
    assert get_register_from_me("Aria") == "spouse-tender"
    set_register_from_me("Aria", None)
    assert get_register_from_me("Aria") is None


def test_get_register_for_unknown_member_returns_none():
    from divineos.core.family.entity import get_register_from_me

    assert get_register_from_me("NotRegistered") is None
