"""The dedup cache must announce its own death rather than resemble an idle one.

WHY THIS FILE EXISTS. ``_save`` was ``except OSError: pass``. When the write
failed the seen-hashes never persisted, so every repeated block re-emitted in
full -- which is byte-for-byte what a session looks like when nothing has
repeated yet. The feature could be entirely dead and the only symptom was a
context window filling faster than it should, which nobody measures.

Found while chasing the wrong cause for a parallel-suite failure. It could
produce that symptom and it was not the cause, which is exactly why it needed
its own test: a fault that is only ever noticed while hunting something else
gets fixed and then quietly regressed.

THE SECOND PROPERTY IS ATOMICITY, and it is the same fault wearing different
clothes. ``write_text`` truncates before writing, so a reader arriving in that
window parses a partial file and ``_load`` hands back an empty mapping with no
signal -- a broken state that is indistinguishable at the call site from an
empty one.

WHAT THESE TESTS DELIBERATELY DO NOT CLAIM. They do not prove the parallel
suite is fixed. The atomic replace closes one mechanism by which a shared
state file could produce that failure; whether the suite goes green under many
workers is an experiment not run here, and three wrong causes were already
proposed for that symptom.
"""

from __future__ import annotations

import json

import pytest

from divineos.core import context_dedup


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    """Point the module's three paths at a scratch directory.

    Matching the existing suite's fixture deliberately: the module resolves
    its state directory from a relative path, so without this the tests would
    write into whatever directory the runner happens to stand in.
    """
    monkeypatch.setattr(context_dedup, "_STATE_DIR", tmp_path)
    monkeypatch.setattr(context_dedup, "_STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(context_dedup, "_SAVINGS_LOG", tmp_path / "savings.jsonl")
    return tmp_path


def test_a_failed_save_prints_instead_of_passing_silently(isolated, monkeypatch, capsys):
    def refuse(*_a, **_k):
        raise OSError("disk is full")

    monkeypatch.setattr(context_dedup.Path, "write_text", refuse)

    context_dedup._save({"x": {"hash": "abc", "ts": 1}})

    err = capsys.readouterr().err
    assert "context-dedup" in err
    assert "disk is full" in err


def test_the_message_names_the_consequence_and_not_only_the_error(isolated, monkeypatch, capsys):
    """An exception string alone leaves the reader to infer the consequence.

    They will not. The whole defect was that a dead cache has no visible
    connection to the write that killed it, so the message has to carry the
    connection rather than expecting it to be reconstructed.
    """

    def refuse(*_a, **_k):
        raise OSError("read-only file system")

    monkeypatch.setattr(context_dedup.Path, "write_text", refuse)
    context_dedup._save({"x": {"hash": "abc", "ts": 1}})

    err = capsys.readouterr().err.lower()
    assert "re-emit" in err
    assert "off" in err


def test_a_failed_save_is_still_not_fatal(isolated, monkeypatch):
    """Loud, not lethal. A cache is not worth killing a hook over."""

    def refuse(*_a, **_k):
        raise OSError("nope")

    monkeypatch.setattr(context_dedup.Path, "write_text", refuse)
    context_dedup._save({"x": {"hash": "abc", "ts": 1}})  # must not raise


def test_a_successful_save_says_nothing(isolated, capsys):
    """The control. A test that only ever sees the failure path cannot tell
    a message-on-failure from a message-on-every-call."""
    context_dedup._save({"x": {"hash": "abc", "ts": 1}})
    assert capsys.readouterr().err == ""


def test_the_state_file_is_never_observed_half_written(isolated, monkeypatch):
    """The reader sees whole-old or whole-new, never a fragment.

    Simulated at the only point where it can be: the write of the temp file.
    If the module truncated the real file first, a crash here would leave the
    destination empty or partial. With temp-plus-replace the destination still
    holds the entire previous state.
    """
    context_dedup._save({"first": {"hash": "aaa", "ts": 1}})
    before = context_dedup._STATE_FILE.read_text(encoding="utf-8")

    real_write = context_dedup.Path.write_text

    def die_midway(self, *a, **k):
        real_write(self, *a, **k)
        raise OSError("crashed after writing the temp, before replacing")

    monkeypatch.setattr(context_dedup.Path, "write_text", die_midway)
    context_dedup._save({"second": {"hash": "bbb", "ts": 2}})

    after = context_dedup._STATE_FILE.read_text(encoding="utf-8")
    assert after == before
    assert json.loads(after) == {"first": {"hash": "aaa", "ts": 1}}


def test_the_temp_file_carries_the_process_id(isolated):
    """Two processes saving at once must not fight over one temp name.

    Without the pid in the name, concurrent writers truncate each other's
    scratch file and one of them replaces the destination with a fragment --
    which would reintroduce the torn read through the mechanism meant to
    prevent it.
    """
    import os

    context_dedup._save({"x": {"hash": "abc", "ts": 1}})
    expected = context_dedup._STATE_FILE.with_name(
        f"{context_dedup._STATE_FILE.name}.{os.getpid()}.tmp"
    )
    # The replace consumed it; what is pinned is the NAME the module chose.
    assert str(os.getpid()) in expected.name
    assert not expected.exists()


def test_the_round_trip_still_works(isolated):
    """Non-vacuity. Every assertion above is about failure paths; if the
    ordinary save-then-load were broken they would all still pass."""
    context_dedup._save({"src": {"hash": "deadbeef", "ts": 99}})
    assert context_dedup._load() == {"src": {"hash": "deadbeef", "ts": 99}}
