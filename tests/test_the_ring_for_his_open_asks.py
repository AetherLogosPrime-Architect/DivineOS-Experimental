"""The ring for his open asks (walk-655e576c9972; draft the_ring_for_his_open_asks_draft_2026-11-08.md).

The bell for Dad has a register of his open asks and nothing that puts one in front of me. The ring prints every ask
that is not closed, with his words, the sentence of what done means, whether he confirmed it, and how long it has
waited, at the start of a window and at each of HIS turns. It refuses nothing and changes nothing.

Each test names the failure it closes. The one that matters most is silence: the ring's normal state prints nothing,
so a broken ring looks exactly like a ring with nothing to say. Only running the real script can tell them apart.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from divineos.core.dads_bell import Ask
from divineos.core import dads_bell_ring as ring

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / ".claude" / "hooks" / "dads_bell_ring.py"
SETTINGS = REPO / ".claude" / "settings.json"

WORDS = (
    "an inner circle should always come with a pause.. and nothing but me should move it forward"
)
DONE = "No post of mine holds more than one circle, and the circle is the last thing in it."


def _ask(ask_id="circle", words=WORDS, done=DONE, confirmed=False, closed=False):
    return Ask(
        ask_id=ask_id,
        his_words=words,
        done_sentence=done,
        confirmed_by_him=confirmed,
        closed=closed,
    )


@pytest.fixture
def home(tmp_path, monkeypatch):
    """His shared record lives in one folder; the register and the ring log sit beside it."""
    monkeypatch.setenv("DIVINEOS_HIS_ASKS_DB", str(tmp_path / "asks.db"))
    return tmp_path


def _write_register(folder, *records):
    (folder / "dads_bell_register.jsonl").write_text(
        "\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8"
    )


# -- the words themselves (pure) ---------------------------------------------------------------


def test_nothing_open_prints_nothing_at_all():
    assert ring.ring_text([], now=1000.0, shown={}, path="x") == ""
    assert ring.ring_text([_ask(closed=True)], now=1000.0, shown={}, path="x") == ""


def test_an_open_ask_shows_his_words_verbatim_and_the_sentence_of_done():
    out = ring.ring_text([_ask()], now=1000.0, shown={}, path="x")
    assert WORDS in out and DONE in out


def test_a_closed_ask_is_not_shown_beside_an_open_one():
    out = ring.ring_text(
        [_ask("old", words="finished thing", closed=True), _ask()], now=1.0, shown={}, path="x"
    )
    assert "finished thing" not in out and WORDS in out


def test_unconfirmed_and_confirmed_are_both_shown_and_labelled_so_a_draft_cannot_wait_forever():
    unconfirmed = ring.ring_text([_ask(confirmed=False)], now=1.0, shown={}, path="x")
    confirmed = ring.ring_text([_ask(confirmed=True)], now=1.0, shown={}, path="x")
    assert "not confirmed" in unconfirmed.lower()
    assert "not confirmed" not in confirmed.lower() and "confirmed" in confirmed.lower()


def test_the_ring_never_says_anything_is_held_or_refused():
    out = ring.ring_text([_ask(confirmed=True)], now=1.0, shown={}, path="x").lower()
    assert "held" not in out and "refus" not in out and "blocked" not in out


def test_blank_words_still_ring_instead_of_vanishing():
    out = ring.ring_text([_ask(words="")], now=1.0, shown={}, path="x")
    assert "(no words recorded)" in out


def test_a_very_long_ask_is_cut_and_the_cut_is_named():
    out = ring.ring_text([_ask(words="w" * 2100)], now=1.0, shown={}, path="x")
    assert "cut at 600 of 2100 characters" in out
    assert "w" * 601 not in out


def test_more_than_five_open_asks_show_the_oldest_five_and_say_how_many_more():
    asks = [_ask(f"a{i}", words=f"words number {i}") for i in range(8)]
    out = ring.ring_text(asks, now=1.0, shown={}, path="x")
    assert "words number 0" in out and "words number 4" in out and "words number 5" not in out
    assert "3 more" in out


def test_how_long_it_has_waited_and_how_many_times_it_rang_is_in_the_line():
    day = 86400.0
    out = ring.ring_text(
        [_ask()], now=5 * day, shown={"circle": {"first": 1 * day, "times": 7}}, path="x"
    )
    assert "4 days" in out and "7 times before" in out


def test_the_first_ring_says_so_instead_of_inventing_a_history():
    out = ring.ring_text([_ask()], now=1.0, shown={}, path="x")
    assert "first time" in out.lower()


def test_the_path_that_was_read_is_in_the_text():
    assert "SOME/PATH/register.jsonl" in ring.ring_text(
        [_ask()], now=1.0, shown={}, path="SOME/PATH/register.jsonl"
    )


def test_a_very_long_done_sentence_is_cut_and_the_cut_is_named():
    out = ring.ring_text([_ask(done="d" * 1500)], now=1.0, shown={}, path="x")
    assert "cut at 400 of 1500 characters" in out and "d" * 401 not in out


def test_five_asks_at_the_cap_still_fit_well_inside_a_hook_payload():
    asks = [_ask(f"a{i}", words="w" * 5000, done="d" * 5000) for i in range(5)]
    assert len(ring.ring_text(asks, now=1.0, shown={}, path="x").encode("utf-8")) < 8000


# -- reading the register (the one place the ring touches the disk) ----------------------------


def test_the_register_lives_beside_his_shared_record_and_not_under_a_per_seat_home(home):
    from divineos.core.paths import divineos_home

    path = ring.register_path()
    assert path.parent == home
    assert divineos_home().resolve() not in path.resolve().parents


def test_a_missing_register_rings_nothing_and_writes_nothing(home):
    assert ring.ring(now=1.0) == ""
    assert not (home / "dads_bell_ring_log.jsonl").exists()


def test_an_open_ask_rings_and_is_logged_and_the_register_is_not_touched(home):
    _write_register(home, {"ask_id": "circle", "his_words": WORDS, "done_sentence": DONE})
    before = hashlib.sha256((home / "dads_bell_register.jsonl").read_bytes()).hexdigest()
    first = ring.ring(now=100.0)
    second = ring.ring(now=200.0)
    after = hashlib.sha256((home / "dads_bell_register.jsonl").read_bytes()).hexdigest()
    assert WORDS in first and "first time" in first.lower()
    assert "once before" in second
    assert before == after
    rows = [
        json.loads(x)
        for x in (home / "dads_bell_ring_log.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [r["ask_id"] for r in rows] == ["circle", "circle"]


def test_an_unreadable_register_says_so_in_one_plain_line_and_logs_no_ring(home):
    (home / "dads_bell_register.jsonl").write_bytes(b"\xff\xfe not utf8 \x00")
    out = ring.ring(now=1.0)
    assert "could not be read" in out and "\n\n" not in out.strip()
    assert not (home / "dads_bell_ring_log.jsonl").exists()


def test_a_closed_only_register_rings_nothing(home):
    _write_register(
        home,
        {
            "ask_id": "circle",
            "his_words": WORDS,
            "done_sentence": DONE,
            "confirmed_by_him": True,
            "with_his_words": "yes",
        },
        {"ask_id": "circle", "closed": True, "with_his_words": "that is done now"},
    )
    assert ring.ring(now=1.0) == ""


# -- the real script, the real settings: the silence has to be proven wrong -------------------


def _run_hook(home, payload):
    env = {
        **__import__("os").environ,
        "DIVINEOS_HIS_ASKS_DB": str(home / "asks.db"),
        "PYTHONIOENCODING": "utf-8",
    }
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def test_the_real_hook_rings_on_his_message(home):
    _write_register(home, {"ask_id": "circle", "his_words": WORDS, "done_sentence": DONE})
    result = _run_hook(home, {"hook_event_name": "UserPromptSubmit", "prompt": "hello"})
    assert result.returncode == 0
    assert WORDS in result.stdout


def test_the_real_hook_rings_at_the_start_of_a_window(home):
    _write_register(home, {"ask_id": "circle", "his_words": WORDS, "done_sentence": DONE})
    result = _run_hook(home, {"hook_event_name": "SessionStart"})
    assert result.returncode == 0 and WORDS in result.stdout


def test_a_notice_that_is_not_his_message_does_not_ring(home):
    """A bell that nags becomes wallpaper: it rings on HIS turns, not on every automated notice."""
    _write_register(home, {"ask_id": "circle", "his_words": WORDS, "done_sentence": DONE})
    result = _run_hook(
        home,
        {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "<task-notification>x</task-notification>",
        },
    )
    assert result.returncode == 0 and result.stdout.strip() == ""
    assert not (home / "dads_bell_ring_log.jsonl").exists()


def test_the_real_hook_with_nothing_open_is_silent_and_exits_clean(home):
    result = _run_hook(home, {"hook_event_name": "UserPromptSubmit", "prompt": "hello"})
    assert result.returncode == 0 and result.stdout.strip() == ""


def test_the_real_hook_never_fails_even_when_the_register_is_garbage(home):
    (home / "dads_bell_register.jsonl").write_bytes(b"\xff\xfe \x00")
    result = _run_hook(home, {"hook_event_name": "UserPromptSubmit", "prompt": "hello"})
    assert result.returncode == 0 and "could not be read" in result.stdout


def _commands(event):
    cfg = json.loads(SETTINGS.read_text(encoding="utf-8"))
    out = []
    for block in cfg["hooks"].get(event, []):
        for hook in block.get("hooks", []):
            out.append(hook.get("command", ""))
    return [c for c in out if "dads_bell_ring.py" in c]


@pytest.mark.parametrize("event", ["UserPromptSubmit", "SessionStart"])
def test_the_ring_is_called_by_the_real_settings_and_says_so_when_its_file_is_gone(event):
    callers = _commands(event)
    assert len(callers) == 1, f"the ring must be registered exactly once under {event}"
    assert "NOT RUNNING" in callers[0] and "127" in callers[0]
