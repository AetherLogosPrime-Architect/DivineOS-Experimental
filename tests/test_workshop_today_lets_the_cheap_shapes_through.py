"""Characterization: what the draft doorman does TODAY with tonight's shapes.

Station 5 before station 3, on purpose (Feathers and Popper in both walks for
docs/drafts/his_builds_get_the_full_workshop_draft_2026-09-30.md). These pin
current behaviour, not intended behaviour. Aria predicted that on tonight's
record the door as it stands catches 0 of 3 of the shapes that reached Andrew.
If any assertion here fails on first run, that prediction was wrong, and the
design rests on a false premise that has to be found before building on it.

Each test that pins a gap is marked GAP and flips when the build lands. A GAP
test going red is the build working. Update it then, and never before.
"""

from __future__ import annotations

from pathlib import Path

from divineos.core import work_item_doorman as doorman

ROOT = Path(__file__).resolve().parents[1]
HOME_MEMORY = Path.home() / ".claude" / "projects" / "some-project" / "memory"


def test_gap_the_note_path_is_not_the_doors_business() -> None:
    """GAP. Tonight's once-a-session note was written into the memory
    directory outside the repo, in our words, two minutes after he called the
    last one wallpaper. The door does not see that path at all."""
    note = HOME_MEMORY / "feedback_refuse_for_him_what_i_refuse_for_aria.md"
    assert doorman.needs_an_item([str(note)]) == ()
    decision = doorman.decide("Write", {"file_path": str(note), "content": "How to apply: ..."})
    assert decision.allows


def test_gap_the_in_repo_memory_folder_is_exempt_as_prose() -> None:
    """GAP. The repo's own memory/ folder is on the exempt list as prose,
    so a rule written there in our words opens no work either."""
    assert doorman.needs_an_item([str(ROOT / "memory" / "a_rule_about_him.md")]) == ()


def test_gap_no_station_asks_for_an_objection_or_his_words() -> None:
    """GAP. The marks required before an edit are these three. The
    self-answered rule had all three and was hollow: a yes in a letter and a
    walk in costume passed. Nothing asks for the other seat's objection, a
    search of his words, or a replay against the real record."""
    assert doorman.REQUIRED_BEFORE_BUILD == ("prior-art search", "rough draft", "council walk")


def test_gap_any_fresh_draft_satisfies_the_draft_mark(tmp_path, monkeypatch) -> None:
    """GAP. The draft mark is any file under docs/drafts newer than the item,
    with 64 bytes in it. It does not have to be about this work, so a draft
    for one thing opens the door for another."""
    unrelated = tmp_path / "some_other_idea_draft.md"
    unrelated.write_text("an unrelated idea, long enough to clear the content floor " * 2)
    monkeypatch.setattr(doorman, "DRAFTS_DIR", tmp_path)
    assert doorman._draft_mark(since=0.0)


def test_code_paths_are_still_held_today() -> None:
    """Not a gap, and pinned so the build cannot lose it: a code path in the
    repo still opens work."""
    assert doorman.needs_an_item([str(ROOT / "src" / "divineos" / "core" / "x.py")])
