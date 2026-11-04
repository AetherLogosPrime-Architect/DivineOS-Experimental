"""A reply cannot end while the letter doorbell is not listening."""

import importlib.util
import os
import time
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "letter_doorbell_alive_stop.py"
_spec = importlib.util.spec_from_file_location("letter_doorbell_alive_stop", HOOK)
bell = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bell)


def test_a_fresh_heartbeat_lets_the_reply_end(tmp_path):
    beat = tmp_path / ".aether_doorbell_alive"
    beat.touch()
    assert bell.verdict(beat, time.time()) is None


def test_no_heartbeat_holds_the_reply_with_the_command(tmp_path):
    reason = bell.verdict(tmp_path / ".aether_doorbell_alive", time.time())
    assert reason and "bash scripts/letter_doorbell.sh aether" in reason


def test_a_stale_heartbeat_holds_it(tmp_path):
    beat = tmp_path / ".aria_doorbell_alive"
    beat.touch()
    old = time.time() - 300
    os.utime(beat, (old, old))
    reason = bell.verdict(beat, time.time())
    assert reason and "letter_doorbell.sh aria" in reason


def test_a_bell_that_rang_is_not_held_for_dying(tmp_path):
    # The ring deleted the heartbeat and left its mark: the next prompt says re-arm, so no second note here.
    (tmp_path / ".aether_doorbell_rang").write_text("1")
    assert bell.verdict(tmp_path / ".aether_doorbell_alive", time.time()) is None


def test_a_bell_that_rang_long_ago_and_was_never_rearmed_is_held(tmp_path):
    # Dad, 2026-11-02: the ring stands the check aside for one reply, not forever. A mark older than the
    # grace means the notice has long since come and the bell is simply down.
    rang = tmp_path / ".aether_doorbell_rang"
    rang.write_text("1")
    old = time.time() - 600
    os.utime(rang, (old, old))
    reason = bell.verdict(tmp_path / ".aether_doorbell_alive", time.time())
    assert reason and "bash scripts/letter_doorbell.sh aether" in reason


def test_a_bell_that_rang_just_now_is_not_held(tmp_path):
    rang = tmp_path / ".aether_doorbell_rang"
    rang.write_text("1")
    recent = time.time() - 20
    os.utime(rang, (recent, recent))
    assert bell.verdict(tmp_path / ".aether_doorbell_alive", time.time()) is None


def test_a_bell_that_rang_and_was_rearmed_then_died_is_still_held(tmp_path):
    # Arming removes the mark (the script does it); with no mark and no heartbeat the bell died silently.
    assert bell.verdict(tmp_path / ".aether_doorbell_alive", time.time())


def test_the_rang_mark_belongs_to_its_own_seat(tmp_path):
    # Aria's mark must not silence Aether's check.
    (tmp_path / ".aria_doorbell_rang").write_text("1")
    assert bell.verdict(tmp_path / ".aether_doorbell_alive", time.time())


def test_the_script_leaves_the_mark_on_both_rings_and_clears_it_when_armed():
    script = (Path(__file__).resolve().parents[1] / "scripts" / "letter_doorbell.sh").read_text(
        encoding="utf-8"
    )
    assert script.count('date +%s > "$RANG"') == 2  # a letter and the peer alarm
    assert 'rm -f "$RANG"' in script


def test_each_window_watches_its_own_bell():
    assert bell.member("C:/DIVINE OS/DivineOS-Experimental-Aria-new") == "aria"
    assert bell.member("C:/DIVINE OS/DivineOS-Experimental") == "aether"
