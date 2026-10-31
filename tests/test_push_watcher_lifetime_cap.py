"""The watcher ends itself at a hard time limit even when its hook is alive and never reported gone.

Aletheia, 2026-10-23: if a background recorder cannot tell its parent is gone, every push leaves a watcher running for
ever, quietly. The zombie and recycled-number fixes close the known ways; this is the backstop for the ways nobody has
met. The REAL `run` is used on the REAL running test process as its "hook" (which stays alive for the whole test), with
the limit shortened to two seconds: if the cap did not work, this would not return.

WHAT THIS DOES NOT COVER: that four hours is the right cap. It is a number chosen because no push runs that long.
"""

import importlib.util
import json
import os
import sys
import threading
import time
from pathlib import Path

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "push_watcher.py"
_spec = importlib.util.spec_from_file_location("push_watcher_cap", _PATH)
pw = importlib.util.module_from_spec(_spec)
sys.modules["push_watcher_cap"] = pw
_spec.loader.exec_module(pw)


def test_the_watcher_ends_itself_at_the_cap_while_its_hook_is_alive(tmp_path, monkeypatch):
    monkeypatch.setattr(pw, "MAX_WATCH_SECONDS", 2.0)
    raw = tmp_path / "raw.jsonl"
    done = threading.Event()

    def go():
        pw.run(os.getpid(), raw)  # the hook is THIS process, alive for the whole test
        done.set()

    thread = threading.Thread(target=go, daemon=True)
    began = time.time()
    thread.start()
    assert done.wait(timeout=30), "the watcher did not end itself at its cap: that is the leak"
    assert time.time() - began < 30
    ticks = [json.loads(x) for x in raw.read_text().splitlines() if '"tick"' in x]
    assert ticks, "it should leave a final heartbeat so the report can say how many looks it took"
