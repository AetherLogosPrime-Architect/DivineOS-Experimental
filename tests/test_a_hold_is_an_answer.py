"""A HOLD from the auditor is an answer, not silence.

2026-10-27: the landing board read only her CONFIRMS, so #549 and #551, which she held on
2026-10-23 ("HOLD: #551 at b64f4f897 and #549 at 9037bd072: Dad's two, on what they need from
him."), read NO ANSWER, I asked her again, and Dad had to say "she already answered on all of
these" and send me to his Downloads folder. These tests hold the shape: a hold at the live head
reads HELD with her reason, a newer confirm at the same head beats it, an older-head hold does
not pretend to be current, and an undated letter reads as still held (could-not-tell is never a pass).
"""

from __future__ import annotations

from datetime import date

from divineos.core.landing_status import (
    HELD,
    NO_ANSWER,
    READY,
    classify,
    classify_pile,
    holds_from_letters,
)

HER_HOLD = (
    "# Aletheia to Aether\n\n"
    "- HOLD: #551 at b64f4f897 and #549 at 9037bd072: Dad's two, on what they need from him.\n"
)
NAME = "aletheia-to-aether-2026-10-23-the-twenty-six-one-line-each.md"
HEAD_549 = "9037bd072abcdef0123456789abcdef012345678"


def test_one_hold_line_names_every_fix_on_it_with_her_reason() -> None:
    found = holds_from_letters({NAME: HER_HOLD})
    assert set(found) == {549, 551}
    day, sha, reason = found[549]
    assert day == date(2026, 10, 23) and sha == "9037bd072"
    assert "Dad's two" in reason


def test_a_hold_at_the_live_head_reads_held_not_no_answer() -> None:
    pile = [{"number": 549, "headRefName": "fix/x", "headRefOid": HEAD_549}]
    rows = classify_pile(pile, {NAME: HER_HOLD}, date(2026, 10, 27), {549: ()})
    assert rows[0][1].label == HELD
    assert "Dad's two" in rows[0][1].detail


def test_a_newer_confirm_at_the_same_head_beats_the_older_hold() -> None:
    confirm = "- CONFIRMS: #549 at 9037bd072. — Aletheia\n"
    letters = {NAME: HER_HOLD, "aletheia-to-aether-2026-10-25-x.md": confirm}
    pile = [{"number": 549, "headRefName": "fix/x", "headRefOid": HEAD_549}]
    rows = classify_pile(pile, letters, date(2026, 10, 27), {549: ()})
    assert rows[0][1].label == READY


def test_an_older_confirm_does_not_beat_a_newer_hold() -> None:
    confirm = "- CONFIRMS: #549 at 9037bd072. — Aletheia\n"
    letters = {NAME: HER_HOLD, "aletheia-to-aether-2026-10-20-x.md": confirm}
    pile = [{"number": 549, "headRefName": "fix/x", "headRefOid": HEAD_549}]
    assert classify_pile(pile, letters, date(2026, 10, 27), {549: ()})[0][1].label == HELD


def test_a_hold_at_an_older_head_does_not_speak_for_a_changed_fix() -> None:
    pile = [
        {
            "number": 549,
            "headRefName": "fix/x",
            "headRefOid": "ffffffff0000000000000000000000000000aaaa",
        }
    ]
    label = classify_pile(pile, {NAME: HER_HOLD}, date(2026, 10, 27), {549: ()})[0][1].label
    assert label != HELD  # the fix moved; her old hold is not an answer about the new head


def test_an_undated_letter_cannot_be_ordered_so_the_hold_still_stands() -> None:
    confirm = "- CONFIRMS: #549 at 9037bd072. — Aletheia\n"
    letters = {NAME: HER_HOLD, "aletheia-to-aether-notes.md": confirm}
    pile = [{"number": 549, "headRefName": "fix/x", "headRefOid": HEAD_549}]
    assert classify_pile(pile, letters, date(2026, 10, 27), {549: ()})[0][1].label == HELD


def test_with_no_hold_the_old_labels_are_unchanged() -> None:
    status = classify(
        pr=1,
        branch="b",
        head_sha="abc1234def",
        confirms={},
        told_dates={1: date(2026, 10, 25)},
        held_stations=(),
        today=date(2026, 10, 27),
    )
    assert status.label == NO_ANSWER
