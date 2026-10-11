"""Reproduction: the phantom-registration check never looks at Dad's table.

Rows: psf-ea025a21
Note (psf-ea025a21): "a test that every entry in Dad's table points to a script that really exists. Nothing catches this kind of crossing on its own today."

``scripts/check_hook_wiring.phantoms()`` reads ``settings.json`` only. Since the
per-message hooks moved into ``.claude/hooks/dads_table_children.json`` (#560), a
table entry that names a script that does not exist is run by bash against
nothing on every message and the check reports no problem.

Marked ``xfail(strict=True)``: passes quietly as an expected failure today and
turns into a real failure the day the check also reads the table, which forces
the marker out. Nothing here changes the checker.

What would make the reproduction test wrong: it builds a small temporary tree,
so it says nothing about how the real table is laid out beyond what the live
table control below reads. It asserts that the missing name appears in the
checker's first return value; a repair that reports the problem through a
different channel (a new function, a second return value) would fail it for
a reason that is not the problem, and the test should then be pointed at the
new channel.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from check_hook_wiring import phantoms  # noqa: E402 -- scripts/ is put on the path just above

_NAMED = re.compile(r"\.claude/hooks/([\w.-]+\.(?:sh|py))")


def _tree(
    tmp_path: Path, settings_commands: list[str], table_commands: list[str]
) -> tuple[Path, Path]:
    hooks = tmp_path / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "real.sh").write_text("#!/bin/bash\n", encoding="utf-8")
    (hooks / "dads_table_children.json").write_text(
        json.dumps([{"command": c, "timeout": 5} for c in table_commands]), encoding="utf-8"
    )
    settings = tmp_path / ".claude" / "settings.json"
    settings.write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Bash",
                            "hooks": [{"type": "command", "command": c} for c in settings_commands],
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    return hooks, settings


@pytest.mark.xfail(
    raises=AssertionError,
    strict=True,
    reason="reproduces: a Dad's-table entry naming a script that does not exist is not reported as a phantom",
)
def test_a_table_entry_with_no_script_is_reported_as_a_phantom(tmp_path: Path):
    hooks, settings = _tree(
        tmp_path,
        settings_commands=["bash .claude/hooks/real.sh"],
        table_commands=["bash .claude/hooks/real.sh", "bash .claude/hooks/no-such-table-child.sh"],
    )
    found, error = phantoms(hooks, settings)
    assert error is None, error
    assert "no-such-table-child.sh" in found, (
        f"a table entry pointing at a missing script was not reported; the check returned {found!r}"
    )


def test_control_a_missing_script_named_in_settings_is_reported(tmp_path: Path):
    """Control: the same checker does find a phantom when it is named in settings,
    so a clean report is not a dead instrument."""
    hooks, settings = _tree(
        tmp_path,
        settings_commands=[
            "bash .claude/hooks/real.sh",
            "bash .claude/hooks/no-such-settings-hook.sh",
        ],
        table_commands=["bash .claude/hooks/real.sh"],
    )
    found, error = phantoms(hooks, settings)
    assert error is None, error
    assert found == ["no-such-settings-hook.sh"]


def test_control_a_table_of_real_scripts_reports_nothing(tmp_path: Path):
    """Control: no false alarm. A table whose entries all exist must stay clean,
    so a repair that reports every table entry fails here."""
    hooks, settings = _tree(
        tmp_path,
        settings_commands=["bash .claude/hooks/real.sh"],
        table_commands=["bash .claude/hooks/real.sh"],
    )
    assert phantoms(hooks, settings) == ([], None)


def test_control_every_entry_in_the_live_table_names_a_real_script():
    """Control, and the note's own ask read literally: every entry in the real
    table points at a file that exists today.

    The extraction here is the test's own regex, independent of the checker, so
    it says what is true of the live table whether or not the checker looks.
    It passes today and keeps guarding after the checker is repaired.
    """
    hooks = REPO / ".claude" / "hooks"
    table = json.loads((hooks / "dads_table_children.json").read_text(encoding="utf-8"))
    assert table, "the live table is empty, so this control proves nothing"
    missing = sorted(
        {
            name
            for entry in table
            for name in _NAMED.findall(entry.get("command", ""))
            if not (hooks / name).exists()
        }
    )
    assert missing == [], f"table entries naming files that do not exist: {missing}"
