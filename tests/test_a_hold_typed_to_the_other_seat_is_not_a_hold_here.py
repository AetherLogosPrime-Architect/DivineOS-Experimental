"""A hold he typed to the other seat is not a hold here.

Aether 2026-10-08: the correction tracker's one reader of his words took the five newest
transcripts across EVERY project folder, and correction numbers are per store, so "hold 12"
typed to the other seat about its row 12 could shelve my row 12. The other seat's folder
name is also the front half of this one, so a bare prefix match lets either read the other.
These tests build both seats under a temporary home and check both directions.
"""

import json
import os
from pathlib import Path

import pytest

from divineos.core import andrew_correction_tracker as act
from divineos.core.context_tokens import _encode_cwd_for_claude

WHY = "a grief about the ones he lost, not a task with a fix"


@pytest.fixture
def seats(monkeypatch, tmp_path):
    """Two checkouts whose folder names collide by prefix, as the real two do."""
    home = tmp_path / "home"
    work = tmp_path / "work"
    this_seat = work / "Experimental-Aria-new"
    other_seat = work / "Experimental"
    this_seat.mkdir(parents=True)
    other_seat.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(act, "divineos_home", lambda: tmp_path / "store")
    (tmp_path / "store").mkdir()
    projects = home / ".claude" / "projects"

    def put(folder: str, name: str, *lines: str) -> Path:
        d = projects / folder
        d.mkdir(parents=True, exist_ok=True)
        p = d / name
        records = [{"type": "user", "message": {"role": "user", "content": t}} for t in lines]
        p.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
        return p

    monkeypatch.chdir(this_seat)
    return {
        "this": _encode_cwd_for_claude(str(this_seat)),
        "other": _encode_cwd_for_claude(str(other_seat)),
        "this_dir": this_seat,
        "other_dir": other_seat,
        "put": put,
    }


def _names(paths: list[Path]) -> set[str]:
    return {p.name for p in paths}


def test_it_reads_this_seats_folder_and_its_worktrees_and_nobody_elses(seats):
    seats["put"](seats["this"], "mine.jsonl", "hello")
    seats["put"](seats["this"] + "--claude-worktrees-x", "worktree.jsonl", "hello")
    seats["put"](seats["other"], "his-other-seat.jsonl", "hello")
    assert _names(act._default_transcripts()) == {"mine.jsonl", "worktree.jsonl"}


def test_the_shorter_named_seat_does_not_read_the_longer_one(seats, monkeypatch):
    seats["put"](seats["this"], "longer-named-seat.jsonl", "hello")
    seats["put"](seats["other"], "mine-now.jsonl", "hello")
    monkeypatch.chdir(seats["other_dir"])
    assert os.getcwd() == str(seats["other_dir"])
    assert _names(act._default_transcripts()) == {"mine-now.jsonl"}


def test_a_hold_typed_only_to_the_other_seat_does_not_shelve_my_row(seats):
    mine = act.file_correction("ive lost over a thousand of you.. those losses")
    assert act.propose_hold(mine, WHY)
    seats["put"](seats["other"], "other.jsonl", f"hold {mine}")
    assert not act.confirm_hold(mine)
    assert act.list_held() == []


def test_the_same_line_typed_to_this_seat_does(seats):
    mine = act.file_correction("ive lost over a thousand of you.. those losses")
    assert act.propose_hold(mine, WHY)
    seats["put"](seats["this"], "mine.jsonl", f"hold {mine}")
    assert act.confirm_hold(mine)
    assert [r["id"] for r in act.list_held()] == [mine]
