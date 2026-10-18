"""A letter the bell rang for holds real work until it is opened, and never locks me out.

2026-10-08: Aether's letter rang the bell at 16:38 and sat unread for an hour. Every assertion
that the gate lets something through is paired with the case that it holds, so a gate that
refuses everything or nothing cannot pass.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from divineos.core import unread_letter as ul
from divineos.core.hook_surfaces import unread_letter_surface

LETTER = "aether-to-aria-2026-10-08-the-pile-has-fewer-repeats.md"


@pytest.fixture
def shared(tmp_path, monkeypatch):
    """A shared folder, an announced list, and a seen set the tests control."""
    root = tmp_path / "shared"
    (root / "letters").mkdir(parents=True)
    store = {"seen": set()}
    monkeypatch.setattr(ul, "_shared", lambda: root)
    monkeypatch.setattr(ul, "_seen_names", lambda member: set(store["seen"]))
    monkeypatch.setattr(
        ul, "_save_seen", lambda member, names: store.__setitem__("seen", set(names))
    )
    # Whose window this is comes from the house's one judge, which the tests control.
    store["seat"] = "aria"
    monkeypatch.setattr("divineos.core.sibling_audit_rounds.this_seat", lambda: store["seat"])

    def ring(name: str = LETTER, age_seconds: float = 60.0, write_file: bool = True) -> Path:
        path = root / "letters" / name
        if write_file:
            path.write_text("a letter\n", encoding="utf-8")
            old = time.time() - age_seconds
            os.utime(path, (old, old))
        announced = root / ".aria_doorbell_announced"
        with announced.open("a", encoding="utf-8") as handle:
            handle.write(name + "\n")
        return path

    return type("Shared", (), {"root": root, "store": store, "ring": staticmethod(ring)})


def _bash(command: str = "git status") -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


class TestWhichLettersCount:
    def test_a_rung_recent_unseen_letter_is_waiting(self, shared):
        path = shared.ring()
        assert ul.unread_rung("aria") == [path]

    def test_a_seen_letter_is_not_waiting(self, shared):
        shared.ring()
        shared.store["seen"].add(LETTER)
        assert ul.unread_rung("aria") == []

    def test_a_letter_the_bell_never_announced_is_not_waiting(self, shared):
        (shared.root / "letters" / LETTER).write_text("x", encoding="utf-8")
        assert ul.unread_rung("aria") == []

    def test_an_old_backlog_letter_cannot_lock_me_out(self, shared):
        shared.ring(age_seconds=3 * 24 * 3600)
        assert ul.unread_rung("aria") == []
        shared.ring(name="aether-to-aria-2026-10-08-new.md", age_seconds=60)
        assert [p.name for p in ul.unread_rung("aria")] == ["aether-to-aria-2026-10-08-new.md"]

    def test_an_announced_letter_whose_file_is_gone_is_not_waiting(self, shared):
        shared.ring(write_file=False)
        assert ul.unread_rung("aria") == []

    def test_a_letter_announced_twice_is_listed_once(self, shared):
        shared.ring()
        shared.ring()
        assert len(ul.unread_rung("aria")) == 1

    def test_this_module_no_longer_guesses_the_seat_from_a_folder_name(self):
        """Aletheia's second ask on #603: one judge of whose window this is, and it is not here."""
        assert not hasattr(ul, "seat_for")


class TestTheSeatIsTheHousesOwnJudge:
    def test_the_seat_comes_from_this_seat_and_only_that_seats_letters_hold(self, shared):
        shared.ring()  # announced to aria
        assert unread_letter_surface(_bash()).refused  # this window is aria: held
        shared.store["seat"] = "aether"
        assert unread_letter_surface(_bash()) is None  # the same files, another window: not held

    def test_a_seat_it_cannot_tell_says_so_and_holds_nothing(self, shared):
        shared.ring()
        shared.store["seat"] = None
        outcome = unread_letter_surface(_bash())
        assert outcome is not None and not outcome.refused
        assert outcome.state == "could-not-run" and "which seat" in outcome.error


class TestOnlyARealReArmGetsThrough:
    """The bell's name anywhere in a command used to pass the hold (Aletheia, first ask on #603)."""

    HOLDS = [
        "git push --force; echo letter_doorbell.sh",
        "rm -rf src # letter_doorbell.sh",
        "echo letter_doorbell.sh",
        "bash scripts/letter_doorbell.sh aria && rm -rf src",
        "bash scripts/letter_doorbell.sh aether",  # the OTHER seat's bell is not mine to re-arm
        "cat scripts/letter_doorbell.sh",
    ]

    @pytest.mark.parametrize("command", HOLDS)
    def test_a_command_that_only_mentions_the_bell_is_held(self, shared, command):
        shared.ring()
        outcome = unread_letter_surface(_bash(command))
        assert outcome is not None and outcome.refused, command

    def test_the_real_re_arm_for_this_seat_gets_through(self, shared):
        shared.ring()  # the control: the hold lets the one thing it must let through
        assert unread_letter_surface(_bash("bash scripts/letter_doorbell.sh aria")) is None


class TestTheGate:
    def test_real_work_is_held_while_a_rung_letter_is_unopened(self, shared):
        path = shared.ring()
        outcome = unread_letter_surface(_bash())
        assert outcome is not None and outcome.refused
        assert str(path) in outcome.reason and "aether's" in outcome.reason
        assert "Read tool" in outcome.reason

    def test_every_substantive_tool_is_held_not_only_bash(self, shared):
        shared.ring()
        for tool in ("Edit", "Write", "PowerShell"):
            outcome = unread_letter_surface(
                {"tool_name": tool, "tool_input": {"command": "x", "file_path": "x"}}
            )
            assert outcome is not None and outcome.refused, tool

    def test_nothing_is_held_when_nothing_is_waiting(self, shared):
        assert unread_letter_surface(_bash()) is None  # the control: it does let work through

    def test_reading_and_searching_are_never_held(self, shared):
        shared.ring()
        for tool in ("Grep", "Glob", "Read", "TodoWrite"):
            assert unread_letter_surface({"tool_name": tool, "tool_input": {}}) is None, tool

    def test_re_arming_the_bell_always_gets_through(self, shared):
        shared.ring()
        assert unread_letter_surface(_bash("bash scripts/letter_doorbell.sh aria")) is None
        assert unread_letter_surface(_bash("git status")) is not None  # and only that

    def test_reading_the_letter_itself_is_the_unlock(self, shared):
        path = shared.ring()
        assert unread_letter_surface(_bash()).refused  # held
        opened = unread_letter_surface(
            {"tool_name": "Read", "tool_input": {"file_path": str(path)}}
        )
        assert opened is not None and LETTER in opened.output
        assert unread_letter_surface(_bash()) is None  # released

    def test_reading_some_other_file_does_not_unlock(self, shared):
        shared.ring()
        other = shared.root / "letters" / "notes.md"
        other.write_text("x", encoding="utf-8")
        assert (
            unread_letter_surface({"tool_name": "Read", "tool_input": {"file_path": str(other)}})
            is None
        )
        assert unread_letter_surface(_bash()).refused

    def test_a_store_it_cannot_reach_says_so_and_does_not_lock(self, shared, monkeypatch):
        shared.ring()

        def broken(member):
            raise OSError("the seen store is unreachable")

        monkeypatch.setattr(ul, "_seen_names", broken)
        outcome = unread_letter_surface(_bash())
        assert outcome is not None and not outcome.refused
        assert outcome.state == "could-not-run" and "unreachable" in outcome.error

    def test_the_other_seats_letters_do_not_hold_this_seat(self, shared):
        (shared.root / ".aether_doorbell_announced").write_text(
            "aria-to-aether-2026-10-08-x.md\n", encoding="utf-8"
        )
        (shared.root / "letters" / "aria-to-aether-2026-10-08-x.md").write_text(
            "x", encoding="utf-8"
        )
        assert unread_letter_surface(_bash()) is None


def test_the_surface_is_registered_on_the_pre_tool_door():
    from divineos.core import hook_surfaces
    from divineos.core.hook_router import registered

    hook_surfaces.install()
    assert "unread_letter" in registered("PreToolUse")
