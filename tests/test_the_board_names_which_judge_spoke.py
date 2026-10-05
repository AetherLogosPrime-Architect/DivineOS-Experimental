"""The board judges branches using whatever copy of itself is checked out.

Found 2026-09-12 by accident. From a branch rebuilt off main the board
reported SIX pieces of work READY; from the branch carrying that day's repairs
the same twelve at the same moment reported ZERO. Two opposite verdicts minutes
apart, and neither named which judge had spoken. I nearly carried the
flattering one into a reply.

THE LOAD-BEARING TEST IS THE BEHIND CASE, and it needs a test rather than a
demonstration. Walking onto an old branch does not exercise it: an old branch
predates the stamp entirely, so it prints no line at all -- which is itself
the limitation recorded in correction #658, a guard placed inside the artifact
it guards is absent exactly where the artifact is stale. The BEHIND path only
occurs once the stamp has landed and someone works from a post-landing branch
that has since fallen behind, a state that cannot be produced from here. An
untested branch of a warning is the painted door this house keeps finding, so
the three outcomes are exercised directly.

The first version said "differs from the shared one", which is symmetric and
reads as harmless. Behind is an older judge, and older judges are PERMISSIVE.

Companion to tests/test_build_flow_lens_counting.py, which pins what the
stations decide; this pins whether the board admits WHICH station code decided.
"""

from __future__ import annotations

import subprocess

from divineos.cli import build_flow_commands as bfc


class _Result:
    def __init__(self, returncode: int) -> None:
        self.returncode = returncode
        self.stdout = ""
        self.stderr = ""


def test_behind_is_named_as_the_dangerous_direction(monkeypatch):
    """The one that matters. An older judge returns permissive verdicts."""
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Result(0))
    said = bfc._judge_direction()
    assert "BEHIND" in said
    assert "PERMISSIVE" in said
    assert "unproven" in said


def test_ahead_is_not_treated_as_a_reason_to_distrust_the_reading(monkeypatch):
    """Ahead carries unlanded repairs -- a different situation entirely.

    The first version covered both cases with one word, which is how the
    dangerous one passed for the harmless one.
    """
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Result(1))
    said = bfc._judge_direction()
    assert "AHEAD" in said
    assert "BEHIND" not in said
    assert "PERMISSIVE" not in said


def test_a_git_that_will_not_answer_says_so_rather_than_guessing(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Result(129))
    said = bfc._judge_direction()
    assert "COULD NOT BE READ" in said
    assert "unverified" in said


def test_a_git_that_cannot_run_is_not_a_direction(monkeypatch):
    def _boom(*_a, **_k):
        raise OSError("git is gone")

    monkeypatch.setattr(subprocess, "run", _boom)
    said = bfc._judge_direction()
    assert "COULD NOT BE READ" in said
    assert "BEHIND" not in said
    assert "AHEAD" not in said
