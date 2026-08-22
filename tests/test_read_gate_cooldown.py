"""The read-gate's throttle, which stopped throttling and said nothing.

MEASURED 2026-08-20 from the gate's own clear-log, after Andrew asked why my
commands kept freezing: 95 fires in 24 hours across 86 distinct paths, and 95
of the 95 cleared with extent "inlined in full -- delivery is the read". Not
one clear came from an actual Read. Seven to nine blocked-and-retried commands
per hour, each injecting up to _INLINE_MAX_CHARS of exploration text.

``has_pending`` was written to prevent exactly that and states the invariant in
its own docstring: "at most one requirement per gate is ever live." It kept
returning correct answers the whole time. What changed underneath it is that
delivery now clears the requirement inside the same fire, so the pending list
is empty by the next turn and the surface arms a fresh match -- a different
path every time, which is also why the same-path guard never caught it.

Two correct changes composing into a defect neither contains:

  2026-08-16  inline-in-full        removed the cost of going to fetch the file
  2026-08-17  delivery-is-the-read  removed the redundant Read demand

Both right. Together they converted a once-per-gate blocker into a per-turn
one, and the guard against that outcome was already in the file, still passing
its tests, guarding nothing.

These tests drive the register -> fire -> clear -> re-register cycle. The
existing read-gate tests exercise arming and clearing separately -- vanished
targets, pytest scratch, inline-whole vs truncated -- and the defect exists
only in their composition, which is why a green suite carried it.
"""

from __future__ import annotations

import time

import pytest

from divineos.core import read_gate


@pytest.fixture
def isolated_gate(tmp_path, monkeypatch):
    """Point every piece of gate state at tmp_path.

    The module resolves STATE_DIR at import time, so redirecting DIVINEOS_HOME
    afterwards does nothing -- the constants are already bound. Patching them
    directly is the honest way to isolate. This matters more than usual here:
    the module's own docstring records a 2026-08-14 incident where tests wrote
    into the LIVE gate state and blocked the real workspace twice.
    """
    monkeypatch.setattr(read_gate, "STATE_DIR", tmp_path)
    monkeypatch.setattr(read_gate, "STATE_FILE", tmp_path / "pending.json")
    monkeypatch.setattr(read_gate, "COOLDOWN_FILE", tmp_path / "cooldown.json")
    monkeypatch.setattr(read_gate, "CLEAR_LOG", tmp_path / "clears.jsonl")
    monkeypatch.setattr(read_gate, "REARM_LOG", tmp_path / "rearms.jsonl")
    monkeypatch.setattr(read_gate, "SEEN_READS", tmp_path / "seen.json")

    # tmp_path IS pytest scratch, so require_read correctly refuses every
    # fixture built inside it -- the guard that exists because test files
    # armed the live gate. It is not the subject here and test_read_gate_
    # pytest_scratch.py already covers it against real inputs, so it is
    # stood down for these cases rather than worked around with a fake
    # directory layout that would misrepresent where the files live.
    monkeypatch.setattr(read_gate, "is_pytest_scratch", lambda _target: False)
    return tmp_path


def _entry(tmp_path, name: str) -> str:
    p = tmp_path / name
    p.write_text(f"# {name}\n\nshort enough to inline whole\n", encoding="utf-8")
    return str(p)


def test_the_surface_cannot_rearm_immediately_after_a_delivery(isolated_gate):
    """The loop itself: register, fire, clear, then try to arm a NEW path.

    A different path each turn is what 86-distinct-paths-in-a-day looks like
    from inside, and it walks straight past the same-path guard.
    """
    first = _entry(isolated_gate, "first.md")
    second = _entry(isolated_gate, "second.md")

    registered, why = read_gate.require_read("prior-writing", first, "top match")
    assert registered, why

    blocked, message = read_gate.gate_status()
    assert blocked
    assert "first.md" in message

    # Delivery in full clears it -- correct, and precisely why has_pending is
    # no longer able to throttle anything.
    assert not read_gate.has_pending("prior-writing")

    registered, why = read_gate.require_read("prior-writing", second, "next match")
    assert not registered, (
        "the gate armed a fresh requirement immediately after delivering one. "
        "That is the per-turn block: every command pays a fire, an injection of "
        "up to _INLINE_MAX_CHARS, and a forced retry."
    )
    assert "cooling down" in why


def test_the_gate_arms_again_once_the_quiet_period_passes(isolated_gate, monkeypatch):
    """A throttle that never releases is a disabled gate wearing a fix.

    This side fails worse than the defect: a gate that quietly stops firing
    forever is indistinguishable from a gate with nothing to report.
    """
    first = _entry(isolated_gate, "first.md")
    second = _entry(isolated_gate, "second.md")

    assert read_gate.require_read("prior-writing", first, "top match")[0]
    read_gate.gate_status()
    assert not read_gate.require_read("prior-writing", second, "next")[0]

    # Move the stamp out of the window rather than sleeping through it.
    stale = time.time() - (read_gate.GATE_COOLDOWN_SECONDS + 60)
    read_gate.COOLDOWN_FILE.write_text(f'{{"prior-writing": {stale}}}', encoding="utf-8")

    registered, why = read_gate.require_read("prior-writing", second, "next")
    assert registered, f"gate never re-armed: {why}"


def test_the_quiet_period_is_per_gate_not_global(isolated_gate):
    """One surface going quiet must not silence a different one.

    Keyed on gate_id because the path differs every time; keying it any wider
    would let the prior-writing surface mute gates unrelated to it.
    """
    first = _entry(isolated_gate, "first.md")
    other = _entry(isolated_gate, "other.md")

    assert read_gate.require_read("prior-writing", first, "top match")[0]
    read_gate.gate_status()

    registered, why = read_gate.require_read("some-other-gate", other, "unrelated")
    assert registered, f"an unrelated gate was silenced by prior-writing: {why}"


def test_unreadable_cooldown_state_fails_open(isolated_gate):
    """Bad state must make the gate MORE willing to fire, not less.

    A throttle that could jam itself shut would be the wall this module
    promises it is not.
    """
    assert read_gate.cooldown_remaining("prior-writing") == 0.0

    read_gate.COOLDOWN_FILE.write_text("{not json", encoding="utf-8")
    assert read_gate.cooldown_remaining("prior-writing") == 0.0

    read_gate.COOLDOWN_FILE.write_text('{"prior-writing": "yesterday"}', encoding="utf-8")
    assert read_gate.cooldown_remaining("prior-writing") == 0.0


def test_a_backwards_clock_does_not_wedge_the_gate_shut(isolated_gate):
    """A future timestamp must expire, not silence the gate for a day.

    One bad stamp -- a clock correction, a restored state file -- would
    otherwise mute the gate for an unbounded stretch with no symptom.
    """
    read_gate.COOLDOWN_FILE.write_text(
        f'{{"prior-writing": {time.time() + 86400}}}', encoding="utf-8"
    )
    assert read_gate.cooldown_remaining("prior-writing") == 0.0
