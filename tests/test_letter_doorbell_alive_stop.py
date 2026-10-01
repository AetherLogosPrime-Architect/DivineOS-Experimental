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


def test_each_window_watches_its_own_bell():
    assert bell.member("C:/DIVINE OS/DivineOS-Experimental-Aria-new") == "aria"
    assert bell.member("C:/DIVINE OS/DivineOS-Experimental") == "aether"
