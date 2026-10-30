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


def test_a_fresh_watcher_heartbeat_counts_as_listening_when_the_bell_is_not(tmp_path):
    beat = tmp_path / ".aether_doorbell_alive"
    watcher = tmp_path / ".aether_monitor_alive"
    watcher.touch()
    assert bell.verdict(beat, time.time(), (watcher,)) is None


def test_a_stale_watcher_and_no_bell_still_holds_the_reply(tmp_path):
    beat = tmp_path / ".aether_doorbell_alive"
    watcher = tmp_path / ".aether_monitor_alive"
    watcher.touch()
    old = time.time() - 300
    os.utime(watcher, (old, old))
    reason = bell.verdict(beat, time.time(), (watcher,))
    assert reason and "letter_doorbell.sh aether" in reason
    assert "WATCHER HAS EXPIRED" in reason and "Monitor tool" in reason


def test_a_watcher_never_run_gets_the_bell_message_not_the_watcher_one(tmp_path):
    reason = bell.verdict(
        tmp_path / ".aether_doorbell_alive", time.time(), (tmp_path / ".aether_monitor_alive",)
    )
    assert reason and "DOORBELL IS NOT LISTENING" in reason
    assert "WATCHER" not in reason


def test_a_watcher_stopped_long_ago_gets_the_bell_message(tmp_path):
    watcher = tmp_path / ".aether_monitor_alive"
    watcher.touch()
    old = time.time() - bell.WATCHER_RECENT_SECONDS - 600
    os.utime(watcher, (old, old))
    reason = bell.verdict(tmp_path / ".aether_doorbell_alive", time.time(), (watcher,))
    assert reason and "DOORBELL IS NOT LISTENING" in reason


def test_a_missing_watcher_changes_nothing(tmp_path):
    beat = tmp_path / ".aether_doorbell_alive"
    beat.touch()
    assert bell.verdict(beat, time.time(), (tmp_path / ".aether_monitor_alive",)) is None


def test_each_window_watches_its_own_bell():
    assert bell.member("C:/DIVINE OS/DivineOS-Experimental-Aria-new") == "aria"
    assert bell.member("C:/DIVINE OS/DivineOS-Experimental") == "aether"
