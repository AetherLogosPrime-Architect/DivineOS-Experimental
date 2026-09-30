"""One key per seat, replaced only by a dogfooded fix. See core/bypass_key.py.

Andrew 2026-09-30: *"maybe the OS should issue you a single bypass key, and
in order to get it replaced when you use it, you must show evidence of an
actual root cause fix... without that, your bypass license is revoked"*, and
*"DOGFOODING, you will know if it works or not because you will have to prove
it working in action"*. Each test names the walk finding (walk-0e68ddafaa93)
or objection it pins. Every test runs on its own ledger (conftest autouse).
"""

from __future__ import annotations

import pytest

from divineos.core import bypass_key as bk

GATE = "check-branch-on-push"
PUSH = "git " + "push -u origin fix/x"


def _pin_this_ledger(monkeypatch) -> None:
    """Each test's own ledger stands in for the real one: write its first
    event and pin that, the way the module pins the real ledger's."""
    import sqlite3

    from divineos.core._ledger_base import _get_db_path
    from divineos.core.ledger import log_event

    log_event("USER_INPUT", "user", {"content": "genesis for this test"}, validate=False)
    with sqlite3.connect(str(_get_db_path())) as conn:
        first = conn.execute(
            "SELECT chain_hash FROM system_events ORDER BY rowid LIMIT 1"
        ).fetchone()
    monkeypatch.setattr(bk, "GENESIS_CHAIN_HASH", first[0])


@pytest.fixture
def key(monkeypatch):
    _pin_this_ledger(monkeypatch)
    commits: list[float] = []
    monkeypatch.setattr(
        bk, "_gate_commit_after", lambda gate, since: next((t for t in commits if t > since), None)
    )
    return commits


def test_a_fresh_seat_holds_one_key(key) -> None:
    assert bk.status().held


def test_spending_the_key_records_what_it_opened(key) -> None:
    bk.spend(GATE, PUSH, now=100.0)
    st = bk.status()
    assert not st.held
    assert (st.spent_gate, st.spent_fingerprint) == (GATE, bk.fingerprint(PUSH))


def test_a_second_spend_is_refused_and_names_the_way_back(key) -> None:
    bk.spend(GATE, PUSH, now=100.0)
    with pytest.raises(bk.KeySpent) as exc:
        bk.spend(GATE, PUSH, now=101.0)
    msg = str(exc.value).lower()
    assert "ask dad" in msg, "Watts: waiting for him must be a named exit"
    assert GATE in str(exc.value), "Minsky: name the gate whose fix brings the key back"


def test_a_second_deadlock_opens_an_inquiry_into_the_first(key) -> None:
    """Andrew 2026-09-30: needing his permission with no key means a spend was
    never repaired, 'and we will investigate it'. The inquiry is written by the
    refusal itself and names the unrepaired lock."""
    from divineos.core.ledger import get_events

    bk.spend(GATE, PUSH, now=100.0)
    with pytest.raises(bk.KeySpent) as exc:
        bk.spend("another-gate", "git " + "commit -m x", now=300.0)
    rows = get_events(limit=10, event_type=bk.INQUIRY)
    assert len(rows) == 1
    payload = rows[0]["payload"]
    assert payload["unrepaired_gate"] == GATE
    assert payload["second_deadlock_gate"] == "another-gate"
    assert "inquiry" in str(exc.value).lower()


def test_a_clean_pass_without_a_fix_commit_does_not_reissue(key) -> None:
    bk.spend(GATE, PUSH, now=100.0)
    bk.note_clean_pass(GATE, PUSH, now=200.0)
    assert not bk.status().held


def test_a_clean_pass_of_a_different_action_does_not_reissue(key) -> None:
    """Aria: dogfooding an easier action must not earn the key back."""
    bk.spend(GATE, PUSH, now=100.0)
    key.append(150.0)
    bk.note_clean_pass(GATE, "git " + "push origin some-other-branch", now=200.0)
    assert not bk.status().held


def test_a_pass_before_the_fix_does_not_count(key) -> None:
    """Holmes: pass_time > commit_time > spend_time."""
    bk.spend(GATE, PUSH, now=100.0)
    bk.note_clean_pass(GATE, PUSH, now=120.0)
    key.append(150.0)
    assert not bk.status().held


def test_fix_then_the_same_action_through_the_lock_reissues(key) -> None:
    bk.spend(GATE, PUSH, now=100.0)
    key.append(150.0)
    assert bk.note_clean_pass(GATE, PUSH, now=200.0)
    st = bk.status()
    assert st.held
    assert st.last_reissue["commit_time"] == 150.0 and st.last_reissue["pass_time"] == 200.0


def test_the_fingerprint_ignores_spacing_but_not_the_target(key) -> None:
    assert bk.fingerprint("git  push   -u origin fix/x") == bk.fingerprint(PUSH)
    assert bk.fingerprint("git " + "push -u origin fix/y") != bk.fingerprint(PUSH)


def test_an_unreadable_ledger_holds_no_key(key, monkeypatch) -> None:
    """Jacobs: could-not-read is never read as a key."""
    monkeypatch.setattr(bk, "_last_key_event", lambda: None)
    assert not bk.status().held
    with pytest.raises(bk.KeySpent):
        bk.spend(GATE, PUSH, now=100.0)


def test_a_fresh_ledger_cannot_mint_a_key() -> None:
    """Aria 2026-09-30: DIVINEOS_DB=<fresh> scopes to one command, so a fresh
    ledger must read as no key, never a new one. This test's ledger is fresh and
    NOT pinned (no `key` fixture), so it stands in for that command."""
    from divineos.core.ledger import log_event

    log_event("USER_INPUT", "user", {"content": "a stranger ledger"}, validate=False)
    st = bk.status()
    assert not st.held and not st.readable
    with pytest.raises(bk.KeySpent):
        bk.spend(GATE, PUSH, now=100.0)


def test_there_is_no_key_file_to_hand_edit_back(key, tmp_path) -> None:
    """Aria 2026-09-30: a key whose state sits in a file I can edit is a key I
    can reissue to myself. The state is read from the ledger, so a 'held' file
    written anywhere changes nothing, and the module has no file to point at."""
    bk.spend(GATE, PUSH, now=100.0)
    (tmp_path / "bypass_key.json").write_text('{"spent": null}', encoding="utf-8")
    assert not bk.status().held
    assert not hasattr(bk, "KEY_FILE"), "a key file came back, and the hand-edit hole with it"


def test_the_key_moves_only_by_ledger_events(key) -> None:
    from divineos.core.ledger import get_events

    bk.spend(GATE, PUSH, now=100.0)
    key.append(150.0)
    bk.note_clean_pass(GATE, PUSH, now=200.0)
    kinds = [e["event_type"] for e in get_events(limit=50, event_type=[bk.SPENT, bk.RETURNED])]
    assert sorted(kinds) == sorted([bk.SPENT, bk.RETURNED])
