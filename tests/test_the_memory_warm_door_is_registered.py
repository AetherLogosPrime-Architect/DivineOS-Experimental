"""The saved-memory warm's door is registered for PostToolUse in the REAL settings file (the second commit).

Built-but-unwired is the failure Dad named: read the real settings, not a fixture. Kept apart from the module's
own tests so the registration, a guardrail-class file, is reviewed and reverted on its own.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_the_door_is_registered_for_posttooluse_in_the_real_settings_file() -> None:
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    groups = settings["hooks"]["PostToolUse"]
    mine = [
        (g.get("matcher", ""), h["command"])
        for g in groups
        for h in g["hooks"]
        if "memory_saved_warm.py" in h["command"]
    ]
    assert len(mine) == 1
    matcher, command = mine[0]
    assert all(tool in matcher for tool in ("Write", "Edit", "MultiEdit"))
    assert "NOT RUNNING" in command
    assert (ROOT / ".claude" / "hooks" / "memory_saved_warm.py").is_file()


def test_the_registration_is_one_small_entry_and_valid_json() -> None:
    """Said to Dad as 'one small entry': one group, one hook, a ten-second timeout, and the file still parses."""
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    groups = [
        g
        for g in settings["hooks"]["PostToolUse"]
        if any("memory_saved_warm.py" in h["command"] for h in g["hooks"])
    ]
    assert len(groups) == 1 and len(groups[0]["hooks"]) == 1
    assert groups[0]["hooks"][0]["timeout"] == 10
