"""Every PreToolUse group says which tools it watches.

A merge tool rebuilt the his-voice-ends-the-turn hook as a new group and kept
only its ``hooks`` key, so its ``"matcher": "*"`` was gone and the hook that
stops work when Andrew speaks mid-turn no longer matched every tool
(council-e67d2eb56f89). One hook's own wiring test caught it; this is the
rule for all of them. True of all 27 groups on main when written.
"""

from __future__ import annotations

import json
from pathlib import Path

SETTINGS = Path(__file__).resolve().parents[1] / ".claude" / "settings.json"


def test_no_pre_tool_use_group_is_missing_its_matcher():
    groups = json.loads(SETTINGS.read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
    assert groups, "no PreToolUse groups found; the probe is broken"
    missing = [
        [h.get("command", "")[-60:] for h in g.get("hooks", [])]
        for g in groups
        if "matcher" not in g
    ]
    assert not missing, f"PreToolUse groups with no matcher: {missing}"
