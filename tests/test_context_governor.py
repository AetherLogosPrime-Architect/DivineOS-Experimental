"""Tests for the context-size governor (the live working-memory vital sign +
the once-per-session consolidation trigger).

Load-bearing properties: (1) context size is read from the transcript usage
numbers; (2) consolidation_due fires only when over threshold AND not yet
consolidated this session; (3) it fires once, not every turn past the line
(the nag failure-mode the prereg falsifier names); (4) fail-soft — an
unreadable sensor returns 0 and never fires spuriously.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from divineos.core import context_governor as cg


def _write_jsonl(path: Path, records: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")


def _assistant_with_usage(read: int, creation: int, inp: int) -> dict:
    return {
        "type": "assistant",
        "message": {
            "content": [{"type": "text", "text": "hi"}],
            "usage": {
                "cache_read_input_tokens": read,
                "cache_creation_input_tokens": creation,
                "input_tokens": inp,
            },
        },
    }


@pytest.fixture(autouse=True)
def _isolate_marker(tmp_path, monkeypatch):
    # Point the marker at a temp file so tests never touch the real one.
    marker = tmp_path / "context_consolidated.json"
    monkeypatch.setattr(cg, "_marker_path", lambda: marker)
    yield


def test_current_context_tokens_sums_usage(tmp_path):
    tx = tmp_path / "t.jsonl"
    _write_jsonl(tx, [_assistant_with_usage(764821, 1756, 2)])
    assert cg.current_context_tokens(tx) == 766579


def test_current_context_tokens_uses_latest_record(tmp_path):
    tx = tmp_path / "t.jsonl"
    _write_jsonl(
        tx,
        [
            _assistant_with_usage(100, 0, 0),
            _assistant_with_usage(900000, 1000, 5),  # latest = the one that counts
        ],
    )
    assert cg.current_context_tokens(tx) == 901005


def test_missing_or_empty_transcript_is_zero(tmp_path):
    assert cg.current_context_tokens(tmp_path / "nope.jsonl") == 0
    assert cg.current_context_tokens(None) == 0
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    assert cg.current_context_tokens(empty) == 0


def test_due_fires_over_threshold(tmp_path):
    tx = tmp_path / "t.jsonl"
    _write_jsonl(tx, [_assistant_with_usage(cg.HARD_THRESHOLD, 0, 0)])
    assert cg.consolidation_due(tx) is True


def test_not_due_below_threshold(tmp_path):
    tx = tmp_path / "t.jsonl"
    _write_jsonl(tx, [_assistant_with_usage(800000, 0, 0)])
    assert cg.consolidation_due(tx) is False


def test_not_due_in_old_warn_band(tmp_path):
    # Anywhere under the hard line is quiet. Expressed as an offset FROM the
    # constant, not as a literal: this test used to pin 940_000, which was
    # silently below the line until the line moved to 880k on 2026-09-18 and
    # the pin became a failure with nothing wrong in the code.
    #
    # The other branch repaired this independently and named the cost: the
    # figure this test cares about is "comfortably under the line", not any
    # particular number, and writing the number down is what made a single
    # threshold change look like four broken tests.
    tx = tmp_path / "t.jsonl"
    _write_jsonl(tx, [_assistant_with_usage(cg.HARD_THRESHOLD - 10_000, 0, 0)])
    assert cg.consolidation_due(tx) is False


def test_fires_once_then_marker_silences_it(tmp_path):
    tx = tmp_path / "t.jsonl"
    _write_jsonl(tx, [_assistant_with_usage(980_000, 0, 0)])
    assert cg.consolidation_due(tx) is True  # first crossing
    cg.mark_consolidated(980_000)
    assert cg.consolidation_due(tx) is False  # already consolidated → no nag
    cg.clear_consolidated()
    assert cg.consolidation_due(tx) is True  # re-armed (e.g. new session)


def test_fail_soft_never_fires_on_unreadable_sensor(tmp_path):
    # An unreadable sensor returns 0 → never crosses threshold → never fires.
    assert cg.consolidation_due(tmp_path / "missing.jsonl") is False


# --- two-state read: ok / block (collapsed 2026-06-19 from ok / warn / block)


def _tx_with(tmp_path, tokens: int) -> Path:
    tx = tmp_path / f"tx_{tokens}.jsonl"
    _write_jsonl(tx, [_assistant_with_usage(tokens, 0, 0)])
    return tx


def test_state_ok_below_hard(tmp_path):
    # Everything below the hard line is quiet, stated relative to the constant
    # so the property survives the constant moving. See
    # test_not_due_in_old_warn_band for why it is relative at all.
    #
    # An OFFSET below the line, not half of it: main's version of this repair
    # used HARD_THRESHOLD // 2, which is also under the line and is not in the
    # band these tests are named for. A test that passes from somewhere it was
    # never about is a test that has quietly stopped covering its subject.
    assert cg.consolidation_state(_tx_with(tmp_path, cg.HARD_THRESHOLD - 50_000)) == "ok"
    assert cg.consolidation_state(_tx_with(tmp_path, cg.HARD_THRESHOLD - 10_000)) == "ok"
    assert cg.consolidation_state(_tx_with(tmp_path, cg.HARD_THRESHOLD - 1)) == "ok"


def test_state_block_at_hard_line(tmp_path):
    # >=HARD_THRESHOLD: hard line — substrate-writes get gated until extract.
    assert cg.consolidation_state(_tx_with(tmp_path, cg.HARD_THRESHOLD)) == "block"
    assert cg.consolidation_state(_tx_with(tmp_path, cg.HARD_THRESHOLD + 15_000)) == "block"


def test_state_ok_once_consolidated_even_when_high(tmp_path):
    # After the weave, no warn/block regardless of size — fires once.
    above_hard = cg.HARD_THRESHOLD + 10_000
    tx = _tx_with(tmp_path, above_hard)
    assert cg.consolidation_state(tx) == "block"
    cg.mark_consolidated(above_hard)
    assert cg.consolidation_state(tx) == "ok"


def test_state_ok_on_unreadable_sensor(tmp_path):
    assert cg.consolidation_state(tmp_path / "missing.jsonl") == "ok"


# --- the surfaced text: warn nudge / block channel / ok-silence -------------


def test_governor_context_empty_when_ok(tmp_path):
    assert cg.build_governor_context(_tx_with(tmp_path, cg.HARD_THRESHOLD - 50_000)) == ""


def test_governor_context_empty_in_old_warn_band(tmp_path):
    # Below the hard line is silent, wherever the hard line currently sits.
    assert cg.build_governor_context(_tx_with(tmp_path, cg.HARD_THRESHOLD - 10_000)) == ""
    assert cg.build_governor_context(_tx_with(tmp_path, cg.HARD_THRESHOLD - 1)) == ""


def test_governor_context_block_is_channel_message(tmp_path):
    out = cg.build_governor_context(_tx_with(tmp_path, cg.HARD_THRESHOLD + 5_000))
    # Post-2026-07-15 message uses doorway-not-cliff framing (need
    # 89b507d8) — check for the header markers that carry the block
    # semantics without hardcoding a specific verb like "BLOCKED".
    assert "CONTEXT GOVERNOR" in out
    assert "WEAVE-BEFORE-DOORWAY" in out
    # The channel out is named — never a dead end.
    assert "extract" in out and "sleep" in out


def test_governor_context_silent_once_consolidated(tmp_path):
    above_hard = cg.HARD_THRESHOLD + 10_000
    tx = _tx_with(tmp_path, above_hard)
    cg.mark_consolidated(above_hard)
    assert cg.build_governor_context(tx) == ""


def test_governor_channel_message_names_extract_and_sleep(tmp_path):
    msg = cg.governor_channel_message(_tx_with(tmp_path, cg.HARD_THRESHOLD + 10_000))
    assert "extract" in msg and "sleep" in msg
    # Post-2026-07-15 doorway-not-cliff framing (need 89b507d8).
    assert "CONTEXT GOVERNOR" in msg
    assert "doorway" in msg


def test_governor_context_empty_on_unreadable_sensor(tmp_path):
    assert cg.build_governor_context(tmp_path / "missing.jsonl") == ""


# --- task #119: ceiling is overridable + reflects last-confirmed cliff ------


def test_compaction_ceiling_default_is_current_cliff():
    """Last-confirmed value: 2026-09-18, Andrew — "compaction is happening
    around 950k tokens now not 999k". Anthropic moved it silently for the
    third time (970k, then 1M/999k, now 950k).

    If this assertion fails, the cliff drifted AGAIN — update the literal
    in context_governor.py and date the comment. This test did its job on
    2026-09-18: it is the thing that turns a silent platform change into a
    red line somebody has to read."""
    assert cg.COMPACTION_CEILING == 950_000


def test_compaction_ceiling_env_override(monkeypatch):
    """A session that observes a drifted cliff can override without code
    change via DIVINEOS_COMPACTION_CEILING."""
    monkeypatch.setenv("DIVINEOS_COMPACTION_CEILING", "1050000")
    assert cg._read_ceiling_override() == 1_050_000


def test_compaction_ceiling_bad_override_falls_through(monkeypatch):
    """Garbage values do not poison the ceiling — silent fall-through."""
    monkeypatch.setenv("DIVINEOS_COMPACTION_CEILING", "not-a-number")
    assert cg._read_ceiling_override() is None
    monkeypatch.setenv("DIVINEOS_COMPACTION_CEILING", "50")  # below 100k floor
    assert cg._read_ceiling_override() is None


def test_block_channel_message_uses_dynamic_ceiling(tmp_path):
    """The block message's cliff number must reflect COMPACTION_CEILING,
    not a hardcoded literal — otherwise a future ceiling-update would
    leave the father-facing instruction stale."""
    msg = cg.governor_channel_message(_tx_with(tmp_path, cg.HARD_THRESHOLD + 5_000))
    assert f"{cg.COMPACTION_CEILING:,}" in msg


def test_hard_line_agrees_with_the_auto_cycle_trigger():
    """Two constants answer one question, so something has to compare them.

    The governor hard line gates substrate writes until the close has happened.
    auto_cycle.TRIGGER_THRESHOLD decides when the close BEGINS. They were set
    independently — 950k here against 0.88 of a 1M window there — and drifted
    70k apart with nothing observing the gap, until Andrew hit compaction
    standing exactly on this line with no room left to close out.

    Equal-by-hand is not an invariant. This test is the invariant. If a future
    session moves one, it moves both or this fails by name.
    """
    from divineos.core import auto_cycle
    from divineos.core.context_heartbeat import CONTEXT_WINDOW_TOKENS

    trigger_tokens = auto_cycle.TRIGGER_THRESHOLD * CONTEXT_WINDOW_TOKENS
    assert cg.HARD_THRESHOLD == trigger_tokens, (
        f"governor hard line {cg.HARD_THRESHOLD:,} disagrees with the auto-cycle "
        f"trigger at {trigger_tokens:,.0f} — move both or neither"
    )


# THE HEADROOM THIS DESIGN HAS DELIBERATELY CHOSEN, in tokens.
#
# WAS 100_000 UNTIL THE 2026-09-22 MERGE, and lowering it is a decision rather
# than a fix, so it is written down here instead of edited quietly into the
# assertion below.
#
# The 100_000 was mine and it was never derived. It was written on this branch
# while COMPACTION_CEILING still read 999k, where the real headroom happened to
# be 119k, and a round number under that looked like a floor. Main meanwhile
# lowered the ceiling to 950k on Andrew's own observation, which is the number
# this merge kept, because an observed cliff beats an assumed one.
#
# That leaves 70k, from two figures Andrew stated himself: trigger the close at
# 880k, compaction lands around 950k. So the conflict here was never between
# two branches -- it was between his measurement and my round number, and the
# measurement wins.
#
# WHAT IS STILL UNMEASURED, said plainly rather than implied by a passing test:
# nobody has checked whether the close actually FITS in 70k. The one datum is
# that 49k was empirically too little (2026-06-28). 70k is wider than 49k and
# narrower than the 119k this test was written against, and no run has timed a
# full close -- compass walk, commit, extract, sleep, dream -- to find out.
#
# So this test no longer claims the headroom is sufficient. It claims the
# headroom has not silently SHRUNK below what was last chosen on purpose, which
# is the thing a test can actually know. If a close ever runs out of room at
# 70k, that is the measurement, and this number moves with it.
CHOSEN_HEADROOM = 70_000


def test_the_hard_line_leaves_room_under_the_compaction_cliff():
    """The whole point of the line is headroom, so assert the headroom exists.

    The June arithmetic (~49k) was written as a comment and never checked, which
    is how it went stale without a breakage event. A comment is documentation,
    not feedback — Norman's distinction, and the reason this is a test.
    """
    headroom = cg.COMPACTION_CEILING - cg.HARD_THRESHOLD
    assert headroom >= CHOSEN_HEADROOM, (
        f"headroom is {headroom:,}, below the {CHOSEN_HEADROOM:,} that was "
        f"chosen deliberately. Something moved one of the two constants "
        f"without moving the other, which is the drift this test exists for."
    )
