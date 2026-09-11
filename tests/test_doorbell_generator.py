"""Nobody writes a bell, so nobody can put a brain in one.

Aria 2026-09-08, refusing the property check I had started: *"Do not police the
shape. Remove the authoring. ... You cannot put a brain in a file you did not
author."*

And the half that decides how these files behave when they break: *"At Stop,
the things behind the door are the refusals. A dead doorbell there produces a
reply that shipped because nothing was present to refuse it, and that looks
identical to a reply that passed every check."*

Every assertion that something is absent is paired with its control.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core import doorbell_generator as dg
from divineos.core.hook_router import EVENTS


def test_stop_is_the_only_door_that_refuses_when_the_os_will_not_load():
    """The asymmetry is the whole point, so it is asserted in both directions."""
    stop = dg.render("Stop")
    assert "sys.exit(2)" in stop
    assert "REFUSING" in stop
    for event in EVENTS:
        if event == "Stop":
            continue
        text = dg.render(event)
        assert "sys.exit(2)" not in text, f"{event} must fail soft"
        assert "sys.exit(0)" in text


def test_a_missing_repository_is_soft_even_on_the_closed_door():
    """The fresh-clone condition. Refusing there would wall someone out of
    their own checkout, which is a different failure than the one Stop guards."""
    preamble = dg.render("Stop").split("HOOK_JSON=")[0]
    assert "|| exit 0" in preamble
    assert "|| exit 2" not in preamble


@pytest.mark.parametrize("event", EVENTS)
def test_every_bell_says_absent_is_not_passing(event):
    text = dg.render(event)
    assert "NOT RUNNING" in text
    assert "not passing, absent" in text
    assert event in text


def _shell_statements(text: str) -> list[str]:
    """The shell lines of a bell, with comments and the embedded python removed."""
    out: list[str] = []
    in_python = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("HOOK_JSON=") and line.endswith('-c "'):
            in_python = True
            out.append(line)
            continue
        if in_python:
            if line == '"':
                in_python = False
            continue
        out.append(line)
    return out


@pytest.mark.parametrize("event", EVENTS)
def test_a_bell_carries_no_decision_of_its_own(event):
    """The property the generation exists to guarantee.

    Asserted as an EXACT LIST rather than by searching for branch words. My
    first version searched, extracted the embedded python by mistake, and
    matched the word "for" inside an English sentence -- which is the same
    keyword-detector weakness Aria named, reproduced in the test that was
    supposed to prove it gone.

    An exact list cannot be routed around: any new shell statement, however it
    is spelled, fails this. The four preamble lines are the only conditionals a
    bell is allowed, and each one gives up when the substrate is unreachable
    rather than deciding anything about the event.
    """
    assert _shell_statements(dg.render(event)) == [
        "set +e",
        # The trailing comment is required by the silent-swallow check, which
        # wants the reason on the same line as the suppression. Kept inside the
        # exact string rather than stripped, because stripping comments here
        # would reopen the hole this test exists to close.
        'REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0'
        "  # fail-soft: outside a git checkout there is no OS to route to, "
        "so the bell stays silent rather than guessing at a repo root",
        '[ -z "$REPO_ROOT" ] && exit 0',
        'source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0',
        'PYTHON_BIN="$(find_divineos_python)" || exit 0',
        "export PYTHONIOENCODING=utf-8",
        'HOOK_JSON="$(cat)" "$PYTHON_BIN" -c "',
        "exit $?",
    ]


def test_an_unknown_event_is_a_loud_error_not_a_silent_file():
    with pytest.raises(ValueError, match="unknown hook event"):
        dg.render("Whenever")
    assert dg.render("Stop")  # control: a real one still renders


def test_only_doors_with_surfaces_get_a_bell():
    """A bell for an empty door is a file connected to nothing -- the dark-hook
    shape the wiring checker exists to catch."""
    active = dg.active_events()
    assert active, "the roster failed to load; that is not the same as no surfaces"
    assert set(active) <= set(EVENTS)
    assert "Stop" in active and "UserPromptSubmit" in active


def test_writing_is_idempotent_and_reports_only_real_changes(tmp_path):
    (tmp_path / ".claude" / "hooks").mkdir(parents=True)
    assert dg.write_all(tmp_path), "the first write must create files"
    assert dg.write_all(tmp_path) == [], "a second write must change nothing"
    assert dg.drifted(tmp_path) == {}


def test_a_hand_edit_is_caught_and_a_missing_bell_is_caught(tmp_path):
    (tmp_path / ".claude" / "hooks").mkdir(parents=True)
    dg.write_all(tmp_path)
    assert dg.drifted(tmp_path) == {}  # control

    stop = dg.path_for("Stop", tmp_path)
    stop.write_text(dg.render("Stop") + "\n# one more line\n", encoding="utf-8")
    assert dg.drifted(tmp_path).get("Stop") == "hand-edited"

    stop.unlink()
    assert dg.drifted(tmp_path).get("Stop") == "missing"


def test_the_files_land_with_unix_line_endings(tmp_path):
    """Caught by shellcheck refusing the first generated batch: the default
    writer translated the newlines, and a naive comparison translated them
    straight back, so the drift check would have called them identical."""
    (tmp_path / ".claude" / "hooks").mkdir(parents=True)
    dg.write_all(tmp_path)
    raw = dg.path_for("Stop", tmp_path).read_bytes()
    assert b"\r\n" not in raw
    assert b"\n" in raw


def test_main_blocks_on_drift_and_allows_a_clean_tree(tmp_path):
    (tmp_path / ".claude" / "hooks").mkdir(parents=True)
    dg.write_all(tmp_path)
    assert dg.main(tmp_path) == 0

    dg.path_for("Stop", tmp_path).write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
    assert dg.main(tmp_path) == 1


def test_the_live_tree_matches_the_generator():
    """The instrument proved against the real repository, not only fixtures."""
    assert dg.drifted(Path(__file__).resolve().parents[1]) == {}
