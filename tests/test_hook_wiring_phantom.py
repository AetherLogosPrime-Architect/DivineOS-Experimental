"""A registration pointing at a deleted file must not read as a live gate.

WHY THIS EXISTS. ``require-monitors-armed.sh`` was deleted on 2026-08-23 when
the delivery cluster was retired -- it reported the letter monitor armed
unconditionally, so it was a gate that lied and removing it was correct. Merge
#438 then landed a branch older than that deletion, and its ``settings.json``
brought the registration back without the file. Every Bash tool call in this
tree spent the next day running ``bash .claude/hooks/require-monitors-armed.sh``
and collecting exit 127: no gate, no error anyone read, no complaint.

The existing check walked one direction only -- disk to registry, "is this file
wired?" -- so nothing looked the other way. The retirement commit had verified
the reverse property BY HAND and closed with "Every registered hook now
resolves to a file that exists", which was true when written and had no way to
stay true.

That is why the regression test at the bottom matters more than the unit tests
above it. A resurrection is not an authorship: nobody decided to register a
deleted hook, so no amount of remembering would have caught it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_hook_wiring import phantoms  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def _settings(tmp_path: Path, *commands: str) -> Path:
    path = tmp_path / "settings.json"
    payload = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [{"type": "command", "command": c} for c in commands],
                }
            ]
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_registration_without_a_file_is_reported(tmp_path):
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    (hooks / "real.sh").write_text("#!/bin/bash\n", encoding="utf-8")
    settings = _settings(
        tmp_path,
        "bash .claude/hooks/real.sh",
        "bash .claude/hooks/deleted.sh",
    )

    found, error = phantoms(hooks, settings)

    assert error is None
    assert found == ["deleted.sh"]


def test_all_files_present_reports_nothing(tmp_path):
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    for name in ("one.sh", "two.py"):
        (hooks / name).write_text("#\n", encoding="utf-8")
    settings = _settings(
        tmp_path,
        "bash .claude/hooks/one.sh",
        "python .claude/hooks/two.py",
    )

    assert phantoms(hooks, settings) == ([], None)


def test_windows_separators_resolve(tmp_path):
    """Registrations are written with either slash. Both must be seen."""
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    settings = _settings(tmp_path, r"bash .claude\hooks\gone.sh")

    found, error = phantoms(hooks, settings)

    assert error is None
    assert found == ["gone.sh"]


@pytest.mark.parametrize("body", ["{not json", ""])
def test_unreadable_settings_is_an_error_not_an_empty_answer(tmp_path, body):
    """Could-not-look must never render as looked-and-found-nothing.

    This is the whole class the phantom check belongs to, so the check itself
    is not allowed to have it.
    """
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    settings = tmp_path / "settings.json"
    settings.write_text(body, encoding="utf-8")

    found, error = phantoms(hooks, settings)

    assert found == []
    assert error is not None and "cannot read" in error


def test_missing_settings_file_is_an_error(tmp_path):
    hooks = tmp_path / "hooks"
    hooks.mkdir()

    found, error = phantoms(hooks, settings=tmp_path / "absent.json")

    assert found == []
    assert error is not None


def test_this_checkout_has_no_phantom_registrations():
    """The regression guard. This is the one that would have caught #438."""
    found, error = phantoms(REPO / ".claude" / "hooks", REPO / ".claude" / "settings.json")

    assert error is None, error
    assert found == [], (
        f"registered with no file on disk: {found}. Every matching tool call runs "
        "bash against a path that does not exist and collects exit 127 -- no gate "
        "runs and nothing says so. Remove the registration, or restore the file if "
        "the deletion was the mistake."
    )
