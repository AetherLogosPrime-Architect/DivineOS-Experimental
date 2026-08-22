"""A requirement whose file has vanished must not hold the door.

``require_read`` refuses a path that does not exist, "rather than creating a
block that nobody can clear" -- but it checks once, at arming. ``gate_status``
is what actually fires, and it never re-checked, so a requirement outlived its
file.

2026-08-14: the prior-writing index matched a pytest tmpdir, pytest cleaned it
up, and every Bash, Edit and Write afterwards demanded a file that no longer
existed. Read is exempt by design, so the prescribed cure ran and returned
"File does not exist" -- and with Edit and Write held too, the gate blocked the
repair of itself while an unfinished merge sat conflicted in another checkout.

The gate's own message promises this cannot happen: "A gate whose cure sits
behind itself is a wall." These tests hold it to that.

MAX_AGE_SECONDS would eventually have expired the entry, but three hours of a
frozen workspace is not a remedy -- and an aged-out block teaches the bypass
reflex, which is the thing this module exists to avoid.
"""

from __future__ import annotations

import json
import time

from divineos.core import read_gate


def _point_state_at(tmp_path, monkeypatch):
    state = tmp_path / "read_gate_pending.json"
    monkeypatch.setattr(read_gate, "STATE_DIR", tmp_path)
    monkeypatch.setattr(read_gate, "STATE_FILE", state)
    return state


def _entry(path, gate_id="prior-writing", reason="top prior-writing match"):
    return {
        "gate_id": gate_id,
        "path": str(path),
        "reason": reason,
        "registered_at": time.time(),
    }


def _arm(state, *entries):
    """Write requirements directly, bypassing require_read's existence check.

    Deliberate: the failure under test is a requirement that was VALID when
    armed and became unsatisfiable afterwards. Going through require_read
    cannot reproduce it, because require_read is the half that already works.
    """
    state.write_text(json.dumps(list(entries)), encoding="utf-8")


class TestVanishedTargetDoesNotBlock:
    def test_gate_opens_when_the_target_is_gone(self, tmp_path, monkeypatch):
        state = _point_state_at(tmp_path, monkeypatch)
        ghost = tmp_path / "popen-gw4" / "test_surface_fires_only_on_tag0" / "tagged.md"
        _arm(state, _entry(ghost))

        blocked, message = read_gate.gate_status()

        assert blocked is False, (
            "a file that cannot be opened is not a reading being avoided; "
            f"gate still blocked with: {message[:120]}"
        )

    def test_the_dead_requirement_is_removed_not_just_ignored(self, tmp_path, monkeypatch):
        """Otherwise it re-evaluates on every tool call until it ages out."""
        state = _point_state_at(tmp_path, monkeypatch)
        _arm(state, _entry(tmp_path / "gone.md"))

        read_gate.gate_status()

        assert json.loads(state.read_text(encoding="utf-8")) == []

    def test_a_live_requirement_still_blocks(self, tmp_path, monkeypatch):
        """The fix must not defang the gate for targets that DO exist."""
        state = _point_state_at(tmp_path, monkeypatch)
        real = tmp_path / "exploration_entry.md"
        real.write_text("something I wrote and have not opened", encoding="utf-8")
        _arm(state, _entry(real))

        blocked, message = read_gate.gate_status()

        assert blocked is True
        assert str(real) in message, "the gate must name the exact path"

    def test_a_dead_requirement_does_not_take_a_live_one_with_it(self, tmp_path, monkeypatch):
        """The live requirement must survive the dead one being pruned.

        The live file here is deliberately BIG. As of 2026-08-17 the gate
        clears a requirement it has inlined in full, so a small file would be
        gone from state by the end of gate_status() -- for a legitimate reason
        that has nothing to do with the vanished sibling, which would make this
        test's assertion unable to tell the two causes apart.

        A file past the inline cap stays required, so "still in state" once
        again means what this test needs it to mean. The behaviour under test
        is unchanged; only the fixture was made able to observe it.
        """
        state = _point_state_at(tmp_path, monkeypatch)
        real = tmp_path / "alive.md"
        real.write_text("still here\n" * 900, encoding="utf-8")  # past the inline cap
        _arm(
            state,
            _entry(tmp_path / "gone.md", gate_id="ghost", reason="vanished"),
            _entry(real, reason="real match"),
        )

        blocked, message = read_gate.gate_status()

        assert blocked is True
        assert str(real) in message
        assert "gone.md" not in message
        remaining = json.loads(state.read_text(encoding="utf-8"))
        assert [r["gate_id"] for r in remaining] == ["prior-writing"]

    def test_a_fully_inlined_file_needs_no_further_read(self, tmp_path, monkeypatch):
        """Delivery in full IS the read; demanding one afterwards is theatre.

        Andrew 2026-08-17: "if you read it twice it should NOT be asking for
        another read lol". The gate used to inline a whole file and then keep
        waiting for a Read tool call -- a call that by construction fetches
        nothing new, and is therefore guaranteed to be a skim. The gate
        manufactured the empty gesture it exists to prevent, then counted it as
        compliance.
        """
        state = _point_state_at(tmp_path, monkeypatch)
        small = tmp_path / "short.md"
        small.write_text("all of it fits\n" * 20, encoding="utf-8")
        _arm(state, _entry(small, reason="prior writing"))

        blocked, message = read_gate.gate_status()

        assert blocked is True, "it still interrupts — that is how the text arrives"
        assert "all of it fits" in message, "and the text is actually delivered"
        remaining = json.loads(state.read_text(encoding="utf-8"))
        assert remaining == [], "delivered in full, so nothing is still owed"

    def test_a_truncated_inline_still_owes_a_read(self, tmp_path, monkeypatch):
        """The dividing line is truncation, and the gate must see it.

        The entry that exposed the defect was 217 lines against a 220-line
        cap -- complete by three lines. Three longer and the inline would have
        been partial, and then the Read demand would have been correct, because
        there would genuinely have been more to fetch. Two regimes; the old
        code treated them alike.
        """
        state = _point_state_at(tmp_path, monkeypatch)
        big = tmp_path / "long.md"
        big.write_text("line\n" * 900, encoding="utf-8")
        _arm(state, _entry(big, reason="prior writing"))

        blocked, message = read_gate.gate_status()

        assert blocked is True
        assert "truncated" in message, "and it says so, rather than cutting silently"
        remaining = json.loads(state.read_text(encoding="utf-8"))
        assert [r["gate_id"] for r in remaining] == ["prior-writing"], (
            "part of it was withheld, so a Read is still genuinely owed"
        )
