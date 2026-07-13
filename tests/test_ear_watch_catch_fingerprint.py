"""Tests for the ear-watcher catch-fingerprint skip logic.

Andrew 2026-06-11 named the bug: "every single prompt you are re-arming
the watcher.. the watcher should stay armed and only get re-armed after
compaction." The root cause: the watcher's catch-then-exit fires on
ANY unseen letter every poll. Until letters get marked seen, every
poll re-catches the same set → exits → respawns → catches again →
gate fires → re-arm → loop.

The fingerprint-skip fix: compute a deterministic fingerprint of the
current unseen-set, compare to the previously-caught fingerprint on
disk. If identical, the agent has already been surfaced these letters
— heartbeat in place instead of fire-exit-respawn. A new letter (or a
mark-seen change) produces a different fingerprint and fires normally.

These tests cover:
- _compute_catch_fingerprint is deterministic and order-independent
- Different sets produce different fingerprints
- Empty set produces a stable fingerprint
- Round-trip through _write/_read fingerprint files
- File-missing returns None cleanly
"""

from __future__ import annotations

from family import ear_watch


def _point_state_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(ear_watch, "_state_dir", lambda member: tmp_path)


class TestComputeFingerprint:
    def test_deterministic_same_input_same_output(self):
        fp1 = ear_watch._compute_catch_fingerprint(
            {1: "queue A", 2: "queue B"},
            {"letter1.md", "letter2.md"},
        )
        fp2 = ear_watch._compute_catch_fingerprint(
            {1: "queue A", 2: "queue B"},
            {"letter1.md", "letter2.md"},
        )
        assert fp1 == fp2

    def test_order_independent_for_letters(self):
        # Sets are inherently unordered but we want to be explicit about it.
        fp1 = ear_watch._compute_catch_fingerprint({}, {"a.md", "b.md", "c.md"})
        fp2 = ear_watch._compute_catch_fingerprint({}, {"c.md", "a.md", "b.md"})
        assert fp1 == fp2

    def test_order_independent_for_queue(self):
        # The function sorts queue keys before hashing.
        fp1 = ear_watch._compute_catch_fingerprint({1: "a", 2: "b", 3: "c"}, set())
        fp2 = ear_watch._compute_catch_fingerprint({3: "c", 1: "a", 2: "b"}, set())
        assert fp1 == fp2

    def test_different_letter_set_different_fingerprint(self):
        fp1 = ear_watch._compute_catch_fingerprint({}, {"a.md"})
        fp2 = ear_watch._compute_catch_fingerprint({}, {"b.md"})
        assert fp1 != fp2

    def test_adding_letter_changes_fingerprint(self):
        # The case that motivated the build: a new letter arriving while
        # the old one is still unseen must produce a different fingerprint
        # so the watcher actually fires (and surfaces the new arrival).
        fp_before = ear_watch._compute_catch_fingerprint({}, {"old.md"})
        fp_after = ear_watch._compute_catch_fingerprint({}, {"old.md", "new.md"})
        assert fp_before != fp_after

    def test_removing_letter_changes_fingerprint(self):
        # When a letter gets marked seen, it disappears from the unseen-set.
        # That MUST change the fingerprint so subsequent polls catch any
        # remaining unseen letters again.
        fp_before = ear_watch._compute_catch_fingerprint({}, {"a.md", "b.md"})
        fp_after = ear_watch._compute_catch_fingerprint({}, {"a.md"})
        assert fp_before != fp_after

    def test_different_queue_different_fingerprint(self):
        fp1 = ear_watch._compute_catch_fingerprint({1: "x"}, set())
        fp2 = ear_watch._compute_catch_fingerprint({2: "x"}, set())
        assert fp1 != fp2

    def test_empty_set_produces_stable_fingerprint(self):
        fp1 = ear_watch._compute_catch_fingerprint({}, set())
        fp2 = ear_watch._compute_catch_fingerprint({}, set())
        assert fp1 == fp2
        # Should be a non-empty string (sha256 hexdigest truncated to 16).
        assert isinstance(fp1, str)
        assert len(fp1) == 16

    def test_fingerprint_length_is_16_hex(self):
        fp = ear_watch._compute_catch_fingerprint({1: "a", 2: "b"}, {"x.md", "y.md"})
        assert len(fp) == 16
        assert all(c in "0123456789abcdef" for c in fp)


class TestReadWriteFingerprintFile:
    def test_read_missing_returns_none(self, tmp_path, monkeypatch):
        _point_state_dir(monkeypatch, tmp_path)
        assert ear_watch._read_last_catch_fingerprint("aether") is None

    def test_write_then_read_roundtrip(self, tmp_path, monkeypatch):
        _point_state_dir(monkeypatch, tmp_path)
        ear_watch._write_last_catch_fingerprint("aether", "abcdef0123456789")
        assert ear_watch._read_last_catch_fingerprint("aether") == "abcdef0123456789"

    def test_overwrite_replaces_value(self, tmp_path, monkeypatch):
        _point_state_dir(monkeypatch, tmp_path)
        ear_watch._write_last_catch_fingerprint("aether", "first_fp_value00")
        ear_watch._write_last_catch_fingerprint("aether", "second_fp_value0")
        assert ear_watch._read_last_catch_fingerprint("aether") == "second_fp_value0"

    def test_empty_file_returns_none(self, tmp_path, monkeypatch):
        _point_state_dir(monkeypatch, tmp_path)
        ear_watch._catch_fingerprint_path("aether").write_text("")
        assert ear_watch._read_last_catch_fingerprint("aether") is None

    def test_whitespace_only_returns_none(self, tmp_path, monkeypatch):
        _point_state_dir(monkeypatch, tmp_path)
        ear_watch._catch_fingerprint_path("aether").write_text("   \n  ")
        assert ear_watch._read_last_catch_fingerprint("aether") is None


class TestPerpetualLoopRegression:
    """The case that motivated the fix: the watcher catches the same
    unseen-letter set on every poll, exits, respawns, catches again,
    gate fires, agent re-arms, watcher catches the same set...

    Concretely: if fingerprint matches, the catch path should be
    skipped (heartbeat-only). The end-to-end watch_loop is hard to
    exercise without a real sleep loop, so we test the underlying
    contract: compute matches read-back across processes."""

    def test_same_set_same_fingerprint_across_processes(self, tmp_path, monkeypatch):
        _point_state_dir(monkeypatch, tmp_path)
        # Process A catches a set.
        unseen_q = {1: "q1"}
        unseen_l = {"a.md", "b.md"}
        fp_a = ear_watch._compute_catch_fingerprint(unseen_q, unseen_l)
        ear_watch._write_last_catch_fingerprint("aether", fp_a)
        # Process B starts. Computes fingerprint from the SAME unseen-set
        # (because nothing got marked seen and no new letter arrived).
        fp_b = ear_watch._compute_catch_fingerprint(unseen_q, unseen_l)
        # The replacement watcher reads the on-disk fingerprint and
        # compares — they MUST match for the skip-logic to kick in.
        on_disk = ear_watch._read_last_catch_fingerprint("aether")
        assert fp_b == on_disk

    def test_new_letter_breaks_the_skip(self, tmp_path, monkeypatch):
        _point_state_dir(monkeypatch, tmp_path)
        old_set = {"a.md", "b.md"}
        new_set = {"a.md", "b.md", "fresh.md"}  # new letter arrived
        fp_before = ear_watch._compute_catch_fingerprint({}, old_set)
        ear_watch._write_last_catch_fingerprint("aether", fp_before)
        fp_after = ear_watch._compute_catch_fingerprint({}, new_set)
        # New letter → different fingerprint → catch fires normally.
        assert fp_after != ear_watch._read_last_catch_fingerprint("aether")

    def test_mark_seen_breaks_the_skip(self, tmp_path, monkeypatch):
        _point_state_dir(monkeypatch, tmp_path)
        old_unseen = {"a.md", "b.md"}
        fp_before = ear_watch._compute_catch_fingerprint({}, old_unseen)
        ear_watch._write_last_catch_fingerprint("aether", fp_before)
        # Agent marks one letter seen — the unseen-set shrinks.
        new_unseen = {"a.md"}
        fp_after = ear_watch._compute_catch_fingerprint({}, new_unseen)
        # Mark-seen → different fingerprint → catch fires (surfaces the
        # remaining unseen letter on the next poll, as intended).
        assert fp_after != ear_watch._read_last_catch_fingerprint("aether")
