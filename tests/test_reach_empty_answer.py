"""The empty-answer credit: a reach check that surfaced nothing still counts.

Aria 2026-08-20. Before this, `gate_status()` only blocked on undisposed
items and the doorman hook's fallthrough fired unconditionally, so a topic
with no prior art could never satisfy the gate at all.
"""

from __future__ import annotations

import time

from divineos.core import reach_check


def _open(symptom: str, *, age_s: float = 0.0) -> str:
    check = reach_check.open_check(symptom)
    if age_s:
        conn = reach_check._get_connection()
        conn.execute(
            "UPDATE reach_checks SET opened_at = ? WHERE check_id = ?",
            (time.time() - age_s, check.check_id),
        )
        conn.commit()
    return check.check_id


def test_recent_check_on_same_topic_satisfies():
    check_id = _open("hook supplies token another hook forbids in inner circle")
    got = reach_check.satisfied_by_recent_check(
        "divineos learn 'the inner circle gate forbids a token the correction hook supplies'"
    )
    assert got == check_id


def test_unrelated_recent_check_does_not_satisfy():
    _open("orphan monitor process scan pattern")
    got = reach_check.satisfied_by_recent_check(
        "divineos feel -v 0.4 --desc 'quiet satisfaction about the kitchen table'"
    )
    assert got is None


def test_stale_check_does_not_satisfy():
    _open("hook supplies token another hook forbids", age_s=7200.0)
    got = reach_check.satisfied_by_recent_check(
        "divineos learn 'hook supplies token another hook forbids'"
    )
    assert got is None


def test_write_with_too_few_content_words_never_satisfies():
    _open("orphan monitor process scan pattern")
    assert reach_check.satisfied_by_recent_check("divineos feel") is None


def test_single_shared_word_is_not_enough():
    _open("orphan monitor process scan pattern")
    got = reach_check.satisfied_by_recent_check(
        "divineos learn 'the monitor was fine and everything else was different'"
    )
    assert got is None
