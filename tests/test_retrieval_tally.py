"""The retrieval tally, now inside the OS, and the end-of-reply door that calls it.

It had no tests while it lived in scripts/ behind an 84-line shell hook that swallowed
every error. Moved 2026-10-08. Each "nothing happened" assertion is paired with a control
that shows the same code does write a row when it should.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from divineos.core import retrieval_tally as rt
from divineos.core.hook_surfaces import _transcript_audit_surface

REPO = Path(__file__).resolve().parents[1]
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

LETTER = "family/letters/aria-to-aether-2026-10-08-thank-you-for-the-list.md"
EXPLORATION = "exploration/041_something_else_entirely.md"


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(rt, "_HOME", tmp_path)
    monkeypatch.setattr(rt, "_SURFACED_MARKER", tmp_path / "past_writing_surfaced.json")
    monkeypatch.setattr(rt, "_TALLY_LOG", tmp_path / "retrieval_tally.jsonl")
    return tmp_path


def _rows(home: Path) -> list[dict]:
    log = home / "retrieval_tally.jsonl"
    return (
        [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
        if log.exists()
        else []
    )


def test_no_marker_means_no_row(home):
    assert rt.check_reply("anything at all") is None
    assert _rows(home) == []


def test_a_cited_slug_counts_and_an_uncited_path_does_not(home):
    rt.record_surfaced([LETTER, EXPLORATION])
    row = rt.check_reply("I reread aria-to-aether-2026-10-08-thank-you-for-the-list and it holds.")
    assert row is not None and row["tally"] == "1/2"
    assert row["referenced"] == [LETTER]
    assert _rows(home) == [row]


def test_a_reply_citing_nothing_scores_zero_but_still_logs(home):
    rt.record_surfaced([LETTER])
    row = rt.check_reply("A reply about something unrelated.")
    assert row is not None and row["tally"] == "0/1"
    assert len(_rows(home)) == 1


def test_a_short_name_is_not_enough_to_count(home):
    rt.record_surfaced(["notes/a.md"])
    row = rt.check_reply("the a note")
    assert row is not None and row["referenced_count"] == 0


def test_the_backslash_form_of_a_path_counts(home):
    rt.record_surfaced([LETTER])
    row = rt.check_reply(LETTER.replace("/", "\\"))
    assert row is not None and row["referenced_count"] == 1


def test_summary_reads_what_check_reply_wrote(home):
    assert rt.summary()["turns"] == 0  # control: an empty log reads as empty
    rt.record_surfaced([LETTER, EXPLORATION])
    rt.check_reply("aria-to-aether-2026-10-08-thank-you-for-the-list")
    got = rt.summary()
    assert got["turns"] == 1 and got["surfaced_total"] == 2 and got["referenced_total"] == 1
    assert got["ratio"] == 0.5


def _transcript(tmp_path: Path, *assistant_blocks: str) -> str:
    records = [{"type": "user", "message": {"role": "user", "content": "go ahead"}}]
    for block in assistant_blocks:
        records.append(
            {
                "type": "assistant",
                "message": {"role": "assistant", "content": [{"type": "text", "text": block}]},
            }
        )
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return str(path)


def test_the_whole_reply_is_read_not_only_the_last_block(home, tmp_path):
    # the shell hook read only the last text block; a path cited early in the turn was missed
    rt.record_surfaced([LETTER])
    path = _transcript(
        tmp_path,
        "I reread aria-to-aether-2026-10-08-thank-you-for-the-list first.",
        "Now the closing line.",
    )
    row = rt.run_retrieval_tally(path)
    assert row is not None and row["referenced_count"] == 1


def test_an_unreadable_transcript_raises_instead_of_looking_empty(home, tmp_path):
    rt.record_surfaced([LETTER])
    with pytest.raises(OSError):
        rt.run_retrieval_tally(str(tmp_path / "does-not-exist.jsonl"))


def test_the_stop_door_row_logs_once_per_reply(home, tmp_path):
    rt.record_surfaced([LETTER])
    surface = _transcript_audit_surface(
        "retrieval_tally", "divineos.core.retrieval_tally", "run_retrieval_tally"
    )
    path = _transcript(tmp_path, "see aria-to-aether-2026-10-08-thank-you-for-the-list")
    outcome = surface({"transcript_path": path})
    assert outcome is not None and outcome.state == "nothing-to-say"
    assert len(_rows(home)) == 1


def test_the_stop_door_says_could_not_run_where_the_shell_hook_stayed_silent(home, tmp_path):
    surface = _transcript_audit_surface(
        "retrieval_tally", "divineos.core.retrieval_tally", "run_retrieval_tally"
    )
    outcome = surface({"transcript_path": str(tmp_path / "missing.jsonl")})
    assert outcome is not None and outcome.state == "could-not-run"
    assert "not a file" in outcome.error


def test_the_row_is_registered_on_the_stop_door():
    from divineos.core import hook_surfaces
    from divineos.core.hook_router import registered

    hook_surfaces.install()
    assert "retrieval_tally" in registered("Stop")


def test_the_old_script_only_forwards_and_still_answers(tmp_path):
    source = (REPO / "scripts" / "retrieval_tally.py").read_text(encoding="utf-8")
    assert "def " not in source  # it keeps no logic of its own
    env = {"PYTHONPATH": str(REPO / "src"), "USERPROFILE": str(tmp_path), "HOME": str(tmp_path)}
    done = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "retrieval_tally.py"), "summary", "--days", "3"],
        capture_output=True, text=True, env={**os.environ, **env}, creationflags=NO_WINDOW,
    )  # fmt: skip
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["turns"] == 0


def test_the_old_script_with_no_arguments_prints_its_usage(tmp_path):
    done = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "retrieval_tally.py")],
        capture_output=True, text=True, creationflags=NO_WINDOW,
        env={**os.environ, "PYTHONPATH": str(REPO / "src")},
    )  # fmt: skip
    assert done.returncode == 1 and "usage: retrieval_tally.py summary" in done.stdout
