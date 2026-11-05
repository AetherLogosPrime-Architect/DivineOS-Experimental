"""The letter-doorbell-alive hold moved from a standalone script into the Stop router, unchanged in what it says.

Dad, 2026-11-04: the hooks come one after another, a waste of time and usage. Aether measured the doors:
24 Stop hooks registered, one of them the router, the other 23 separate processes, and a standalone door's
refusal reaches me TWICE ("Stop hook feedback" and "Stop hook blocking error", the same words) where the
router's reaches me once. This is the second hold folded in (the first is the promise check).

WHAT THIS PINS, through the real registered surface and real heartbeat files in a temp folder, never a
patched verdict: a missing or stale heartbeat refuses with the same words as before; a fresh bell, or a fresh
watcher beside a stale bell, passes; a reply already sent back once is not held again; a watcher that expired
recently gets the watcher's words; the refusal appears exactly once; the old registration is gone from
settings.json while its neighbour is not (so the search can find a case); the old script still loads and
re-exports the same functions; the order table has the row.

WHAT IT DOES NOT COVER: that the heartbeat file means someone is listening (any process can touch it, true of
the old door too), and the member name chosen by a path substring (kept identical on purpose).
"""

from __future__ import annotations

import importlib.util
import json
import os
import time
from pathlib import Path

from divineos.core import doorbell_alive, hook_order, hook_router, hook_surfaces

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / ".claude" / "hooks" / "letter_doorbell_alive_stop.py"

# The words the standalone door used, copied literally from the script as it stood on main on 2026-11-04.
OLD_BELL_TEXT = (
    "YOUR LETTER DOORBELL IS NOT LISTENING, so a letter to you will not wake you "
    "(Dad has had to say this 24 times). Re-arm it now with the Bash tool, "
    "run_in_background: true -- command: bash scripts/letter_doorbell.sh aria "
    "-- then finish the reply. Append only; do not re-post anything."
)


def _stop_payload(tmp_path, **extra):
    def rec(role, text):
        return json.dumps(
            {"type": role, "message": {"role": role, "content": [{"type": "text", "text": text}]}}
        )

    path = tmp_path / "t.jsonl"
    path.write_text(rec("user", "hi") + "\n" + rec("assistant", "A plain reply.") + "\n", "utf-8")
    return {"transcript_path": str(path), **extra}


def _armed(tmp_path, monkeypatch, project="C:/DIVINE OS/DivineOS-Experimental-Aria-new"):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    (tmp_path / ".divineos-shared").mkdir(exist_ok=True)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", project)
    hook_router.clear("Stop")
    hook_surfaces.install()
    return tmp_path / ".divineos-shared"


def _touch(path: Path, age: float = 0.0) -> None:
    path.touch()
    when = time.time() - age
    os.utime(path, (when, when))


def _names(outcomes):
    return [o.name for o in outcomes]


def test_a_missing_heartbeat_is_refused_once_with_the_old_words(tmp_path, monkeypatch):
    _armed(tmp_path, monkeypatch)
    result = hook_router.dispatch("Stop", _stop_payload(tmp_path))
    ours = [o for o in result.refusals if o.name == "letter_doorbell_alive"]
    assert len(ours) == 1, "the refusal must appear exactly once, not once per door"
    assert ours[0].reason == OLD_BELL_TEXT


def test_a_stale_heartbeat_is_refused(tmp_path, monkeypatch):
    shared = _armed(tmp_path, monkeypatch)
    _touch(shared / ".aria_doorbell_alive", age=300)
    result = hook_router.dispatch("Stop", _stop_payload(tmp_path))
    assert "letter_doorbell_alive" in _names(result.refusals)


def test_a_fresh_heartbeat_passes(tmp_path, monkeypatch):
    shared = _armed(tmp_path, monkeypatch)
    _touch(shared / ".aria_doorbell_alive")
    result = hook_router.dispatch("Stop", _stop_payload(tmp_path))
    assert "letter_doorbell_alive" not in _names(result.refusals)


def test_a_fresh_watcher_beside_a_stale_bell_passes(tmp_path, monkeypatch):
    shared = _armed(tmp_path, monkeypatch)
    _touch(shared / ".aria_doorbell_alive", age=300)
    _touch(shared / ".aria_monitor_alive")
    result = hook_router.dispatch("Stop", _stop_payload(tmp_path))
    assert "letter_doorbell_alive" not in _names(result.refusals)


def test_a_watcher_that_expired_recently_gets_the_watchers_words(tmp_path, monkeypatch):
    shared = _armed(tmp_path, monkeypatch)
    _touch(shared / ".aria_doorbell_alive", age=900)
    _touch(shared / ".aria_monitor_alive", age=600)
    result = hook_router.dispatch("Stop", _stop_payload(tmp_path))
    ours = [o for o in result.refusals if o.name == "letter_doorbell_alive"]
    assert ours and ours[0].reason.startswith("YOUR LETTER WATCHER HAS EXPIRED")


def test_a_reply_already_sent_back_is_not_held_again(tmp_path, monkeypatch):
    _armed(tmp_path, monkeypatch)
    result = hook_router.dispatch("Stop", _stop_payload(tmp_path, stop_hook_active=True))
    assert "letter_doorbell_alive" not in _names(result.refusals)


def test_each_window_watches_its_own_bell(tmp_path, monkeypatch):
    shared = _armed(tmp_path, monkeypatch, project="C:/DIVINE OS/DivineOS-Experimental")
    _touch(shared / ".aria_doorbell_alive")  # the other seat's bell is alive; mine (aether) is not
    result = hook_router.dispatch("Stop", _stop_payload(tmp_path))
    ours = [o for o in result.refusals if o.name == "letter_doorbell_alive"]
    assert ours and "letter_doorbell.sh aether" in ours[0].reason


def test_the_core_and_the_old_script_say_the_same_thing(tmp_path):
    spec = importlib.util.spec_from_file_location("letter_doorbell_alive_stop", SCRIPT)
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    assert script.verdict is doorbell_alive.verdict
    assert script.member is doorbell_alive.member
    beat = tmp_path / ".aria_doorbell_alive"
    assert script.verdict(beat, time.time()) == OLD_BELL_TEXT


def test_the_old_registration_is_gone_and_its_neighbour_is_not():
    settings = (REPO / ".claude" / "settings.json").read_text(encoding="utf-8")
    assert "letter_doorbell_alive_stop.py" not in settings
    # Control: the search can find a registration that is there.
    assert "dads_room_stop.py" in settings


def test_the_clock_is_read_when_no_now_is_given(tmp_path):
    """Aether's cold read of #844: the tests above pass `now`, so the branch that reads the real clock was
    unpinned. A fresh file passes and a stale one refuses with nothing but the file's age deciding."""
    project = "C:/DIVINE OS/DivineOS-Experimental-Aria-new"
    _touch(tmp_path / ".aria_doorbell_alive")
    assert doorbell_alive.reason_for_reply(project, shared=tmp_path) is None
    _touch(tmp_path / ".aria_doorbell_alive", age=300)
    assert doorbell_alive.reason_for_reply(project, shared=tmp_path) == OLD_BELL_TEXT


def test_the_order_table_has_the_row_as_a_tool_call():
    row = hook_order.row_for("Stop", "letter_doorbell_alive")
    assert row is not None and row.kind == hook_order.TOOL_CALL
