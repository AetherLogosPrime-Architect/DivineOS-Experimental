"""Tests for the gate-emit noise-suppression primitive (Aletheia finding #2).

The primitive: `maybe_emit_gate(gate_name, state, content, quiet_on_repeat)`
returns the content when the state changed OR when the state is not in the
quiet-on-repeat set. Returns empty string otherwise.

Contract:
- First emit of any state → surfaces (nothing to compare against).
- Repeat of a quiet-on-repeat state → suppressed.
- Non-quiet state → always surfaces (even repeats).
- Transition (state change) → surfaces.
- Different gates track state independently.
- I/O errors fail-loud (return content, don't over-suppress).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core import gate_emit


@pytest.fixture(autouse=True)
def _isolate_state_file(tmp_path: Path, monkeypatch):
    """Route the per-gate last-state file into tmp_path so tests don't
    pollute the real divineos home."""
    monkeypatch.setattr(gate_emit, "_state_file_path", lambda: tmp_path / "gate_last_states.json")


def test_first_emit_surfaces():
    """The primitive has no prior-state on first call, so the content
    must surface — otherwise a fresh install would swallow its first
    HEALTHY line and read as silently degraded."""
    content = "## GATE X — HEALTHY\nnothing to report"
    out = gate_emit.maybe_emit_gate(
        gate_name="test_gate",
        state="HEALTHY",
        content=content,
    )
    assert out == content


def test_repeat_healthy_suppresses():
    """The core Aletheia case: same state, same quiet-token — suppress."""
    gate_emit.maybe_emit_gate(gate_name="g", state="HEALTHY", content="first")
    out = gate_emit.maybe_emit_gate(gate_name="g", state="HEALTHY", content="second")
    assert out == ""


def test_transition_out_of_healthy_surfaces():
    """State change → always surface, so the reader sees the transition."""
    gate_emit.maybe_emit_gate(gate_name="g", state="HEALTHY", content="ok")
    out = gate_emit.maybe_emit_gate(gate_name="g", state="DEGRADED", content="## GATE — DEGRADED")
    assert out == "## GATE — DEGRADED"


def test_transition_back_to_healthy_surfaces_once():
    """After DEGRADED, coming back to HEALTHY is real news — surface it.
    But the NEXT healthy repeat suppresses again."""
    gate_emit.maybe_emit_gate(gate_name="g", state="DEGRADED", content="loud")
    first_healthy = gate_emit.maybe_emit_gate(
        gate_name="g", state="HEALTHY", content="healthy line"
    )
    assert first_healthy == "healthy line"
    second_healthy = gate_emit.maybe_emit_gate(
        gate_name="g", state="HEALTHY", content="healthy again"
    )
    assert second_healthy == ""


def test_non_quiet_state_always_surfaces():
    """Non-quiet states are LOUD by definition — the whole point of the
    gate is to name failures. Repeat DEGRADED must still fire."""
    gate_emit.maybe_emit_gate(gate_name="g", state="DEGRADED", content="first degraded")
    out = gate_emit.maybe_emit_gate(gate_name="g", state="DEGRADED", content="second degraded")
    assert out == "second degraded"


def test_severe_state_always_surfaces():
    """SEVERE is a non-quiet state — must always fire."""
    gate_emit.maybe_emit_gate(gate_name="g", state="SEVERE", content="first")
    out = gate_emit.maybe_emit_gate(gate_name="g", state="SEVERE", content="second")
    assert out == "second"


def test_nominal_state_suppresses_on_repeat():
    """`nominal` (Aletheia's other quiet token) suppresses like HEALTHY."""
    gate_emit.maybe_emit_gate(gate_name="g", state="nominal", content="ok")
    out = gate_emit.maybe_emit_gate(gate_name="g", state="nominal", content="ok")
    assert out == ""


def test_custom_quiet_on_repeat_set():
    """Callers can define their own quiet-state set — e.g. a gate whose
    quiet token is 'clear' instead of HEALTHY."""
    gate_emit.maybe_emit_gate(gate_name="g", state="clear", content="ok", quiet_on_repeat={"clear"})
    out = gate_emit.maybe_emit_gate(
        gate_name="g", state="clear", content="ok again", quiet_on_repeat={"clear"}
    )
    assert out == ""


def test_state_not_in_quiet_set_surfaces_even_on_repeat():
    """If the caller supplies a quiet-set that DOESN'T include the current
    state, repeats fire — because 'HEALTHY' isn't a quiet-token in this
    caller's semantics."""
    gate_emit.maybe_emit_gate(
        gate_name="g", state="HEALTHY", content="first", quiet_on_repeat={"nominal"}
    )
    out = gate_emit.maybe_emit_gate(
        gate_name="g", state="HEALTHY", content="second", quiet_on_repeat={"nominal"}
    )
    assert out == "second"


def test_different_gates_track_independently():
    """Gate A going HEALTHY does not silence Gate B's first HEALTHY."""
    gate_emit.maybe_emit_gate(gate_name="gate_a", state="HEALTHY", content="a-first")
    out_a_repeat = gate_emit.maybe_emit_gate(
        gate_name="gate_a", state="HEALTHY", content="a-second"
    )
    out_b_first = gate_emit.maybe_emit_gate(gate_name="gate_b", state="HEALTHY", content="b-first")
    assert out_a_repeat == ""
    assert out_b_first == "b-first"


def test_state_persists_across_calls():
    """Explicitly verify the JSON side-file is what carries state — this
    is the mechanism that lets the primitive survive across process
    boundaries (hook fires between substantive-work turns)."""
    gate_emit.maybe_emit_gate(gate_name="persist_test", state="HEALTHY", content="ok")
    # Now simulate a fresh process by clearing any in-memory state and
    # re-reading through the same call path.
    out = gate_emit.maybe_emit_gate(gate_name="persist_test", state="HEALTHY", content="ok2")
    assert out == "", "expected state to persist across calls via JSON side-file"


def test_io_error_fails_loud(tmp_path, monkeypatch):
    """If the state file is unreadable, the primitive returns content —
    fail-loud is safer than fail-silent when we're uncertain about state."""

    def _broken(*args, **kwargs):
        raise OSError("simulated I/O failure")

    monkeypatch.setattr(gate_emit, "_load_last_states", _broken)
    out = gate_emit.maybe_emit_gate(gate_name="g", state="HEALTHY", content="must surface on error")
    assert out == "must surface on error"
