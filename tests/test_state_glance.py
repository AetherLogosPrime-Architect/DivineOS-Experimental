"""The state before a substrate change is a glance, not a wall.

Andrew 2026-10-05: "compress it with a link to the rest so it can be seen and
looked at deeper when needed but doesnt clog you up or waste tokens".
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from divineos.core.state_glance import glance

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude" / "hooks" / "state-gravity-surface.sh"

WORKLIST = "## ANDREW'S CORRECTIONS — A WORKLIST\n\nTotal filed: 377  Open: 265\nmore lines\n"
TELEMETRY = "## GATE BYPASS TELEMETRY\n\n### Windowed\n(an aside)\n7 escape(s) this window\n"


def test_one_line_per_report_with_its_first_real_line():
    lines, _ = glance([WORKLIST, TELEMETRY], {})
    assert len(lines) == 2
    assert lines[0].startswith("- ANDREW'S CORRECTIONS") and "Total filed: 377" in lines[0]
    assert "7 escape(s)" in lines[1]  # skips sub-headings and asides


def test_first_sight_is_changed_and_a_repeat_is_not():
    _, seen = glance([WORKLIST], {})
    again, _ = glance([WORKLIST], seen)
    assert "[CHANGED]" in glance([WORKLIST], {})[0][0]
    assert "[CHANGED]" not in again[0]


def test_a_moved_report_is_marked_changed():
    _, seen = glance([WORKLIST], {})
    moved, _ = glance([WORKLIST.replace("265", "264")], seen)
    assert "[CHANGED]" in moved[0]


def test_a_fresh_correction_shows_in_his_words_not_just_a_new_total():
    # prereg-e1f0ea9f7175's embarrassing reading: the total ticks up and his
    # actual words hide behind it.
    _, seen = glance([WORKLIST], {})
    fresh = WORKLIST.replace("Open: 265", "Open: 266") + "#378 [0d] this is wallpaper isnt it\n"
    lines, _ = glance([fresh], seen)
    assert "[CHANGED]" in lines[0]
    assert any("this is wallpaper isnt it" in ln for ln in lines[1:])


def test_first_sight_does_not_dump_every_line():
    lines, _ = glance([WORKLIST], {})
    assert len(lines) == 1


def _bash() -> str:
    for candidate in (
        Path("C:/Program Files/Git/bin/bash.exe"),
        Path("/bin/bash"),
        Path("/usr/bin/bash"),
    ):
        if candidate.is_file():
            return str(candidate)
    pytest.fail("no usable bash found, so this went unchecked; saying so rather than skipping")
    raise AssertionError


def test_the_real_hook_emits_a_glance_and_keeps_the_whole_text(tmp_path):
    # The suite's home is a fresh empty store (conftest), where every report is
    # rightly silent and the hook prints nothing. So one real correction is
    # filed into THAT store through the real writer, never into his.
    from divineos.core.andrew_correction_tracker import file_correction

    file_correction("a test correction, filed into the suite's own empty store")
    payload = {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}
    env = dict(os.environ, DIVINEOS_STATE_GLANCE_DIR=str(tmp_path))
    done = subprocess.run(
        [_bash(), str(HOOK)],
        input=json.dumps(payload),
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    assert done.returncode == 0
    if not done.stdout.strip():
        pytest.fail(
            "the hook printed nothing for a commit; the gravity scorer or loaders did not run"
        )
    context = json.loads(done.stdout)["hookSpecificOutput"]["additionalContext"]
    assert context.startswith("## STATE"), context[:200]
    assert len(context) < 1500, f"the wall came back: {len(context)} chars"
    whole = tmp_path / f"{ROOT.name}.state.md"
    assert whole.exists() and str(whole) in context
    assert len(whole.read_text(encoding="utf-8")) > len(context)  # the rest is one link away
