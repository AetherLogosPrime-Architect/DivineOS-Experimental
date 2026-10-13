"""A table child that wraps another hook wires the wrapper too.

The wiring check read only the last word of each child of Dad's table, so the
child "dedup-wrap.sh ear bash ear-surface.sh" counted the ear and called
dedup-wrap.sh DARK while it ran on every message (found merging main into
#560, 2026-10-01).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "check_hook_wiring", ROOT / "scripts" / "check_hook_wiring.py"
)
wiring = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wiring)


def _roster(tmp_path: Path, commands: list[str]) -> set[str]:
    (tmp_path / "dads_table_children.json").write_text(
        json.dumps([{"command": c} for c in commands]), encoding="utf-8"
    )
    return wiring._dads_table_roster(tmp_path)


def test_the_wrapper_and_the_wrapped_are_both_wired(tmp_path):
    got = _roster(
        tmp_path, ["bash .claude/hooks/dedup-wrap.sh ear bash .claude/hooks/ear-surface.sh"]
    )
    assert {"dedup-wrap.sh", "ear-surface.sh"} <= got


def test_a_bare_argument_word_is_not_a_hook(tmp_path):
    got = _roster(
        tmp_path, ["bash .claude/hooks/dedup-wrap.sh ear bash .claude/hooks/ear-surface.sh"]
    )
    assert "ear" not in got
    assert "bash" not in got


def test_the_live_table_leaves_no_child_dark():
    state, err = wiring.classify(ROOT / ".claude" / "hooks", ROOT / ".claude" / "settings.json")
    assert err is None
    assert "dedup-wrap.sh" not in state["DARK"]
