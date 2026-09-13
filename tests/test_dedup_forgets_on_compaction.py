"""A suppression outlives the thing it points at, unless compaction clears it.

The dedup pointer's whole claim is that the full content is "byte-identical to
earlier this session" — which is only worth something while that earlier copy
is still in context. Compaction deletes it. Nothing forgot, so after every
compaction six primes went on being suppressed in favour of a pointer at
nothing.

Found 2026-09-08 by the circle-room gate firing on a post-compaction reply:
the circle-first prime had been reduced to a pointer, that emission was eaten
by the compaction, and the reply was composed with neither the prime nor its
residual anywhere in context.

These tests hold the repair rather than my memory of it. The last pair is the
important one — the OS function can be perfect and do nothing at all if the
door stops calling it, and that unwiring would be entirely silent.
"""

from __future__ import annotations

from pathlib import Path

from divineos.core import context_dedup

_HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "post-compact.sh"


class TestForgettingOnCompaction:
    def setup_method(self):
        context_dedup.clear()

    def teardown_method(self):
        context_dedup.clear()

    def test_a_repeat_is_suppressed_while_the_context_is_intact(self):
        """The control, and it comes first: if this ever fails, the test below
        passes for the wrong reason and proves nothing about compaction."""
        emit_first, _ = context_dedup.should_emit("t_prime", "BODY")
        emit_again, pointer = context_dedup.should_emit("t_prime", "BODY")
        assert emit_first is True
        assert emit_again is False
        assert pointer is not None

    def test_the_same_repeat_emits_in_full_after_a_compaction(self):
        context_dedup.should_emit("t_prime", "BODY")
        context_dedup.on_compaction()
        emit, pointer = context_dedup.should_emit("t_prime", "BODY")
        assert emit is True, "suppressed against a copy compaction already deleted"
        assert pointer is None

    def test_it_reports_how_many_it_forgot_rather_than_assuming(self):
        context_dedup.should_emit("one", "A")
        context_dedup.should_emit("two", "B")
        assert context_dedup.on_compaction() == 2

    def test_forgetting_nothing_is_not_an_error(self):
        """Compaction can land before any prime has emitted. That is a zero,
        not a failure, and it must not take the post-compaction reload with
        it."""
        assert context_dedup.on_compaction() == 0


class TestTheDoorStillRings:
    def test_the_compaction_door_calls_it(self):
        """The wiring, asserted. Everything above can be correct and idle if
        this call is dropped, and dropping it would produce no failure
        anywhere — only primes quietly missing from every post-compaction
        turn, which is precisely the defect that went unnoticed until a gate
        fired."""
        assert _HOOK.exists(), _HOOK
        assert "on_compaction" in _HOOK.read_text(encoding="utf-8")

    def test_the_guard_can_actually_fail(self):
        """Control for the assertion above: prove the file does not contain
        any plausible string we look for, or the check is vacuous."""
        assert "on_decompaction" not in _HOOK.read_text(encoding="utf-8")
