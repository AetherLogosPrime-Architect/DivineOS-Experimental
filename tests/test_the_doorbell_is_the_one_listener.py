"""The doorbell is the one listener, and its guard is still on the door.

Dad, 2026-10-02: "yes get rid of the letter watch the doorbell has superceded
it so remove it from the system and put it in the archive". With the watch
and its mid-turn gate gone, the doorbell's Stop hook is the only thing that
refuses a reply while nothing is listening (Polya, council-9a5bea0ec8a6). If
that hook were unwired too, nothing would stop a silent week, so this pins it.

The retired names are checked against live wiring only; the archive and the
retired-rules record are allowed to name them, because that is what they are.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RETIRED = (
    "letter_monitor_v2",
    "letter_monitor_health",
    "letter-watch-must-be-armed",
    "letter-monitor-health-surface",
)


def _hook_commands() -> list[tuple[str, str]]:
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    found = []
    for event, groups in settings.get("hooks", {}).items():
        for group in groups:
            for hook in group.get("hooks", []):
                found.append((event, hook.get("command", "")))
    return found


def test_the_doorbell_guard_is_wired_at_stop() -> None:
    stops = [cmd for event, cmd in _hook_commands() if event == "Stop"]
    assert any("letter_doorbell_alive_stop.py" in cmd for cmd in stops), (
        "the doorbell's Stop guard is not wired -- with the watch retired, "
        "nothing would hold a reply while no bell is listening"
    )
    assert (ROOT / ".claude" / "hooks" / "letter_doorbell_alive_stop.py").is_file()
    assert (ROOT / "scripts" / "letter_doorbell.sh").is_file()


def test_no_hook_runs_the_retired_watch() -> None:
    commands = _hook_commands()
    assert commands, "no hooks read at all -- the probe is broken, not the house clean"
    hits = [(e, c) for e, c in commands for name in RETIRED if name in c]
    assert not hits, f"retired letter-watch pieces are still wired: {hits}"


def test_the_retired_files_are_in_the_archive_not_the_house() -> None:
    archive = ROOT / "archive" / "superseded"
    assert "letter_monitor_v2.py" in (archive / "LEDGER.md").read_text(encoding="utf-8")
    assert (archive / "scripts" / "letter_monitor_v2.py").is_file()
    assert not (ROOT / "scripts" / "letter_monitor_v2.py").exists()
    assert not (ROOT / ".claude" / "hooks" / "letter-watch-must-be-armed.sh").exists()
