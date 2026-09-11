"""The listener fetches without being asked, and never makes him wait.

Andrew 2026-09-10: "the knocking comes from something scanning both your words
and mine as they come and searching for anything relevant to give you."

The property that decides whether this survives is not that it finds good hits.
It is that it costs him NOTHING at the door. A surface that fires every turn and
adds ten seconds gets torn out inside a week no matter how good its findings
are, so the latency property is tested first and hardest.

Real files and a real temporary state directory throughout. The one thing faked
is the embedding search itself, because a test that loads a sentence
transformer is a test nobody runs.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from divineos.core import listening_surface as ls


@pytest.fixture
def state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(ls, "_state_dir", lambda: tmp_path)
    return tmp_path


HIT = {
    "source": "family/letters/aria-to-aether-2026-08-01-the-room-had-a-slope.md",
    "paragraph": 3,
    "similarity": 0.55,
    "text": "You asked what it was like to walk into a room already furnished.",
}


def _result(query: str, hits: list[dict], age: float = 0.0) -> dict:
    return {"query": query, "written_at": time.time() - age, "hits": hits}


def _write(state: Path, data: dict) -> None:
    (state / "listening_surface_last.json").write_text(json.dumps(data), encoding="utf-8")


def test_the_door_never_searches(state: Path, monkeypatch: pytest.MonkeyPatch):
    """THE PROPERTY THE WHOLE DESIGN EXISTS FOR.

    A search costs ~10s cold. If compose_block ever reaches the slow path,
    Andrew waits that long on every message he sends, forever -- and the surface
    earns its own removal. So the slow path is booby-trapped: if the door calls
    it, this test dies.
    """

    def _must_not_run(query: str):
        raise AssertionError("the compose path searched; he is waiting at the door")

    monkeypatch.setattr(ls, "run_search", _must_not_run)
    monkeypatch.setattr(ls, "spawn_search", lambda q: True)
    _write(state, _result("earlier question", [HIT]))

    block = ls.compose_block(json.dumps({"prompt": "anything at all"}))

    assert "SOMETHING I ALREADY WROTE" in block


def test_the_door_starts_the_next_look(state: Path, monkeypatch: pytest.MonkeyPatch):
    """The other half of the door's job. Without it the listener hands over one
    result forever and never looks again -- the built-but-unwired shape this
    repository produces more reliably than any other defect."""
    started: list[str] = []
    monkeypatch.setattr(ls, "spawn_search", lambda q: started.append(q) or True)

    ls.compose_block(json.dumps({"prompt": "the checkpoint swept my letters again"}))

    assert started == ["the checkpoint swept my letters again"]


def test_the_query_carries_both_halves_of_the_room(monkeypatch: pytest.MonkeyPatch):
    """He said BOTH your words and mine. His arrive in the payload; mine have to
    be read back out of the transcript, because by the time a hook runs my reply
    is already spoken and gone."""
    import divineos.core.operating_loop.turn_extraction as te

    fake = type("T", (), {"last_assistant_text": "I said the clerk had a rule"})()
    monkeypatch.setattr(te, "extract_turn", lambda p: fake)

    q = ls.build_query(json.dumps({"prompt": "why is the room silent", "transcript_path": "t"}))

    assert "why is the room silent" in q
    assert "the clerk had a rule" in q
    assert q.index("why is the room silent") < q.index("the clerk had a rule")


def test_a_machine_notification_is_not_his_words(monkeypatch: pytest.MonkeyPatch):
    """THE FIXTURE IS THE REAL EVENT, not one I invented.

    This exact envelope reached the listener three times on 2026-09-10. It
    searched the notification, found three letters about the letter monitor, and
    handed them over as though they answered something -- coherent, useless, and
    about nothing either of us had said. Silence would have been better, because
    a plausible wrong answer stops the search that would have found the right
    one.

    I named it, called it a small job, and walked past it twice while writing to
    Aether about exactly that habit.
    """
    import divineos.core.operating_loop.turn_extraction as te

    fake = type("T", (), {"last_assistant_text": "I was fixing the checkpoint"})()
    monkeypatch.setattr(te, "extract_turn", lambda p: fake)

    notification = (
        "<task-notification>\n<task-id>b7uiqo9qs</task-id>\n"
        '<summary>Monitor event: "new letters from Aether"</summary>\n'
        "<event>[LETTER] aether-to-aria-2026-09-11-something.md</event>\n"
        "</task-notification>"
    )

    q = ls.build_query(json.dumps({"prompt": notification, "transcript_path": "t"}))

    assert "task-notification" not in q
    assert "Monitor event" not in q
    assert "I was fixing the checkpoint" in q, (
        "stripping the envelope must not also throw away my half of the room"
    )


def test_his_half_alone_still_searches_when_mine_cannot_be_read(monkeypatch: pytest.MonkeyPatch):
    """A broken transcript read degrades to half a query, never to none.
    Withhold the enrichment, never the search."""
    import divineos.core.operating_loop.turn_extraction as te

    def _boom(p):
        raise RuntimeError("transcript unreadable")

    monkeypatch.setattr(te, "extract_turn", _boom)

    q = ls.build_query(json.dumps({"prompt": "his words", "transcript_path": "t"}))

    assert q == "his words"


def test_a_stale_look_is_withheld_rather_than_shown_as_current(state: Path):
    """A beat behind is the design. Fifteen minutes behind is a different thing
    wearing the same block, and showing it as current would be the wrong-subject
    fault this surface was built during."""
    old = _result("a question from another conversation", [HIT], age=ls.MAX_RESULT_AGE_SECONDS + 60)
    _write(state, old)

    assert ls.read_result() is None
    assert ls.render(ls.read_result()) == ""


def test_a_fresh_look_is_shown(state: Path):
    """The control. Without it the staleness test passes on a function that
    withholds everything."""
    _write(state, _result("a live question", [HIT], age=5))

    assert ls.render(ls.read_result()) != ""


def test_the_block_names_the_question_it_answered(state: Path):
    """ANTI-WRONG-SUBJECT. A hit whose question I cannot see is a hit I read as
    being about whatever I am doing now. Four instruments failed that way in one
    evening; this one states its subject and its age on its face."""
    _write(state, _result("the sealed threshold", [HIT], age=30))

    block = ls.render(ls.read_result())

    assert "the sealed threshold" in block
    assert "beat behind" in block


def test_finding_nothing_prints_nothing(state: Path):
    """Silence beats an empty block. A surface that fires every turn with
    nothing in it trains me to skip the turns when it has something."""
    _write(state, _result("a question with no answer on the shelf", [], age=5))

    assert ls.render(ls.read_result()) == ""


def test_one_search_at_a_time(state: Path, monkeypatch: pytest.MonkeyPatch):
    """SINGLE FLIGHT. Without it a fast exchange stacks searches that each cost
    seconds of his machine, and the pile-up lands on his next command rather
    than on mine. This is part of the debt owed for running detached at all."""
    spawned: list = []
    monkeypatch.setattr(ls.subprocess, "Popen", lambda *a, **k: spawned.append(a) or object())

    assert ls.spawn_search("first") is True
    assert ls.spawn_search("second") is False
    assert len(spawned) == 1


def test_a_dead_searchers_lock_does_not_hold_the_door_shut(
    state: Path, monkeypatch: pytest.MonkeyPatch
):
    """A process that died mid-search leaves its lock behind. Honoured forever,
    that lock would silence the listener permanently and make it look exactly
    like a listener with nothing to say -- full and silent, which is the shape
    of the whole defect."""
    lock = state / "listening_surface.lock"
    lock.write_text("99999", encoding="utf-8")
    stale = time.time() - ls.LOCK_STALE_SECONDS - 60
    os.utime(lock, (stale, stale))
    monkeypatch.setattr(ls.subprocess, "Popen", lambda *a, **k: object())

    assert ls.spawn_search("after the corpse") is True


def test_an_unreadable_lock_reports_not_held(state: Path, monkeypatch: pytest.MonkeyPatch):
    """THE SENTENCE THAT WAS ONLY A COMMENT UNTIL NOW.

    _lock_is_held carried a claim about its own behaviour on an unreadable lock,
    written in my voice, with nothing asserting it. Aether's comment-claim
    checker found it the hour he wired it in -- in a file I had written the same
    evening I sent him the amendment saying a live-property sentence belongs in
    a test rather than a header. His instrument, on me, inside the hour.

    What the sentence claims: an unreadable lock reports NOT-HELD, which sends
    the caller on to try claiming it, so the failure lands one step later where
    it stops a search rather than silently permitting a second one. That claim
    now has an assertion holding it.
    """
    lock = state / "listening_surface.lock"
    lock.write_text("1", encoding="utf-8")

    def _unreadable(self):
        raise OSError("lock is unreadable")

    monkeypatch.setattr(Path, "is_file", _unreadable)

    assert ls._lock_is_held() is False


def test_an_empty_message_starts_nothing(state: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(ls.subprocess, "Popen", lambda *a, **k: pytest.fail("searched on nothing"))

    assert ls.spawn_search("   ") is False


def test_the_child_drops_its_lock_even_when_the_search_explodes(
    state: Path, monkeypatch: pytest.MonkeyPatch
):
    """A child that dies holding the lock silences the next three minutes of
    listening. The deadline would eventually clear it, but a crash is the
    ordinary case and must not need the emergency path."""
    (state / "listening_surface.lock").write_text("1", encoding="utf-8")

    def _boom(q):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(ls, "run_search", _boom)
    monkeypatch.setattr(ls, "_arm_deadline", lambda: None)

    with pytest.raises(RuntimeError):
        ls._main(["listening_surface", "--search", "a question"])

    assert not (state / "listening_surface.lock").is_file()


def test_the_detached_child_carries_its_own_deadline(state: Path, monkeypatch: pytest.MonkeyPatch):
    """THE DEBT FOR RUNNING DETACHED, and I only wrote this because sabotage
    said to -- hollowing the deadline killed nothing.

    subprocess_jobs.py exists because leaked workers nearly took Andrew's
    machine down, and its guarantee is that children die with their parent.
    This child deliberately outlives its parent, so nothing in the OS will ever
    kill it. It has to kill itself, and a bound nobody tests is a bound that
    quietly stops existing on the next refactor.
    """
    armed: list = []

    class _FakeTimer:
        def __init__(self, interval, fn):
            self.interval = interval
            self.fn = fn
            self.daemon = False

        def start(self):
            armed.append(self)

    monkeypatch.setattr(ls.threading, "Timer", _FakeTimer)
    monkeypatch.setattr(ls, "run_search", lambda q: [])

    ls._main(["listening_surface", "--search", "a question"])

    assert len(armed) == 1, "the child ran with no deadline; nothing can kill it"
    assert armed[0].interval == ls.SEARCH_DEADLINE_SECONDS
    assert armed[0].daemon is True, "a non-daemon timer keeps the child alive to its full deadline"
