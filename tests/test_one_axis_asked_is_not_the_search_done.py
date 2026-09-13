"""A zero-item reach check is not a finished search until the prose axes ran.

THE INCIDENT, 2026-09-12. I opened a check on the checkpointer sweeping letters
onto code branches. It searched code, git history and the command registry,
surfaced one same-named command, and printed -- correctly, in its own words --
that the four PROSE surfaces were not queried, naming each with its command.

I disposed the one match and built a guard.

What the four would have said, asked afterwards: the semantic search returns at
the top a letter about a repair stranded on an unmerged branch. The knowledge
store returns AT FULL CONFIDENCE an entry I had written describing this exact
failure of this exact tool. And the machinery to do the job properly was already
on main -- built, tested, called by nothing.

THE DEFECT IS A MISSING WIRE, NOT A MISSING SENTENCE. ``satisfied_recently``
said in its comment that a zero-item check "means prior_art was asked and
answered empty". Asked on one axis. Three lines below, the CLI printed the four
it had not asked. Two mechanisms, two definitions of the word ASKED, nothing
able to read across the gap -- the same shape as a registry calling a
deliberately-wired module dark.

More prose could not have fixed it: the message was already honest, already
named the axes, already drew the not-found/not-checked distinction. I read it
and built anyway, twice. A well-made caveat reads as a matter already handled.

Per walk-c1935b1d6bb5, six lenses.
"""

from __future__ import annotations

import time

import pytest

from divineos.core import reach_check


def test_a_search_that_could_not_have_happened_yet_does_not_count(monkeypatch):
    """THE LOAD-BEARING ONE. An empty stream is a refusal, not a pass.

    WRITTEN AGAINST THE LIVE TRANSCRIPT FIRST, AND THAT WAS THE SAME DEFECT
    THIS FILE EXISTS TO FIX. It passed here and failed in the pre-push run,
    because a machine whose transcript cannot be read returns could-not-look
    rather than found-nothing -- which is the distinction the code is careful
    about and the test was not. I built a state-dependent check while fixing
    state-dependent checks, and the push gate caught it within the hour.

    The stream is supplied now, so this asserts the behaviour rather than the
    weather.
    """
    monkeypatch.setattr(
        reach_check, "action_stream_from_transcript", lambda window_seconds=0: ((), "")
    )
    ran, why_unknown = reach_check._prose_axis_run_since(time.time())
    assert ran is False
    assert why_unknown == "", "a readable transcript with no hits is not could-not-look"


def test_a_prose_search_that_did_run_counts(monkeypatch):
    """The probe must be able to find a case it should find.

    Asserted against a constructed stream rather than the live transcript, so
    the test says the same thing on a machine where I happen not to have run
    one recently.
    """
    monkeypatch.setattr(
        reach_check,
        "action_stream_from_transcript",
        lambda window_seconds=0: ((("Bash", 'divineos find query "something"'),), ""),
    )
    ran, why_unknown = reach_check._prose_axis_run_since(time.time() - 600)
    assert ran is True
    assert why_unknown == ""


def test_an_unreadable_transcript_is_its_own_answer(monkeypatch):
    """COULD-NOT-LOOK MUST NEVER COLLAPSE INTO SKIPPED.

    An unreadable transcript says nothing about what I ran. This gate has
    walled me in twice -- both instances are written into its own comments --
    so the unknown case falls back to satisfied AND says which question went
    unasked, rather than refusing on the strength of a missing file.
    """
    monkeypatch.setattr(
        reach_check,
        "action_stream_from_transcript",
        lambda window_seconds=0: ((), "transcript unreadable: boom"),
    )
    ran, why_unknown = reach_check._prose_axis_run_since(time.time() - 600)
    assert ran is False
    assert "unreadable" in why_unknown


def test_an_earlier_unrelated_search_does_not_satisfy_a_later_check(monkeypatch):
    """The window starts when the check opened.

    A prose search run before the check existed was asking about something
    else. Counting it would let one search satisfy every check that followed,
    which is the same everything-counts collapse this file exists to stop.
    """
    seen: dict[str, float] = {}

    def _record(window_seconds=0):
        seen["window"] = window_seconds
        return (), ""

    monkeypatch.setattr(reach_check, "action_stream_from_transcript", _record)
    opened = time.time() - 300
    reach_check._prose_axis_run_since(opened)
    assert seen["window"] == pytest.approx(300, abs=5), (
        "the window must start at the check's opening, not at a fixed default"
    )


def test_the_cure_is_not_behind_the_gate():
    """THE DEADLOCK GUARD, and it is the reason this change was safe to make.

    Two gates in this module's history refused the very command that would have
    cleared them, and both are written into its comments. This one tightens a
    gate, so the question is whether its remedy stays runnable while it is shut.

    The remedy is four read-only searches. The doorman guards writes into
    knowledge stores -- claim, learn, opinion, feel -- and nothing else, so the
    searches are reachable at any time. Pinned here rather than reasoned about
    once, because reasoning about it once is exactly what shipped both earlier
    deadlocks.
    """
    remedies = [cmd for cmd, _what in reach_check.prior_art.UNSEARCHED_SURFACES]
    assert remedies, "no remedy is named; the gate would refuse with no way out"
    guarded = ("claim", "learn", "opinion", "feel")
    for cmd in remedies:
        verb = cmd.split()[-1]
        assert verb not in guarded, (
            f"the remedy {cmd!r} is itself gated; that is the wall this module "
            "swore twice it would not rebuild"
        )
