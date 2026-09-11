"""Each test pins one way this half could quietly become decoration.

The five failures it has to survive: a mark with nothing at the other end,
a mark filed out of order, an unopened item reading as clean, an
unreadable record passing as satisfied, and a refusal message that says
nothing a person could act on.
"""

from __future__ import annotations

import sys

import pytest

from divineos.core import station_marks as sm


@pytest.fixture(autouse=True)
def isolated_home(monkeypatch, tmp_path):
    monkeypatch.setattr(sm, "divineos_home", lambda: tmp_path)


_SUBSTANCE = (
    "the idea written out before any code exists, at enough length that it "
    "clears the floor a touched file would not"
)


def _artifact(tmp_path, name="draft.md", text=_SUBSTANCE):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_a_mark_pointing_at_nothing_is_refused(tmp_path):
    sm.open_item("item-1")
    with pytest.raises(sm.MarkRefused):
        sm.mark("item-1", "draft", str(tmp_path / "does-not-exist.md"))


def test_marks_are_refused_out_of_order(tmp_path):
    sm.open_item("item-1")
    with pytest.raises(sm.MarkRefused) as exc:
        sm.mark("item-1", "test", _artifact(tmp_path, "out.txt"))
    # The refusal names what is missing in words, not a station number.
    assert "draft" in str(exc.value) and "before any code" in str(exc.value)

    sm.mark("item-1", "draft", _artifact(tmp_path))
    with pytest.raises(sm.MarkRefused):
        sm.mark("item-1", "test", _artifact(tmp_path, "out.txt"))  # build still absent

    sm.mark("item-1", "build", _artifact(tmp_path, "edit.py"))
    # The test station takes a recorded run now rather than any file; the
    # attack test below is why.
    sm.mark("item-1", "test", str(sm.record_run("item-1", [sys.executable, "-c", "pass"])))
    assert sm.check("item-1", "test").state == sm.SATISFIED


def test_an_unopened_item_cannot_read_as_clean():
    for result in sm.check_all("never-opened"):
        assert result.state == sm.CANNOT_CHECK
    assert sm.blind_count("never-opened") == len(sm.STATIONS)
    # And the refusal text says could-not-look, never a silent pass.
    assert all("Could not look" in s for s in sm.unmet_sentences("never-opened"))


def test_a_vanished_artifact_reverts_to_missing(tmp_path):
    sm.open_item("item-1")
    path = tmp_path / "draft.md"
    path.write_text(_SUBSTANCE, encoding="utf-8")
    sm.mark("item-1", "draft", str(path))
    assert sm.check("item-1", "draft").state == sm.SATISFIED
    path.unlink()
    result = sm.check("item-1", "draft")
    assert result.state == sm.MISSING
    assert "gone" in result.why


def test_an_unreadable_record_is_not_a_pass(tmp_path):
    sm.open_item("item-1")
    sm.mark("item-1", "draft", _artifact(tmp_path))
    (tmp_path / "build_items" / "item-1" / "draft.json").write_text("{ not json", encoding="utf-8")
    result = sm.check("item-1", "draft")
    assert result.state == sm.CANNOT_CHECK
    assert "unreadable" in result.why


def test_unmet_sentences_are_readable_and_shrink_as_work_lands(tmp_path):
    sm.open_item("item-1")
    before = sm.unmet_sentences("item-1")
    assert len(before) == len(sm.STATIONS)
    assert all(s.endswith(".") and s[0].isupper() for s in before)
    assert not any(s.strip().isdigit() for s in before)

    sm.mark("item-1", "draft", _artifact(tmp_path))
    after = sm.unmet_sentences("item-1")
    assert len(after) == len(sm.STATIONS) - 1
    assert not any("before any code" in s for s in after)


def test_an_empty_artifact_is_refused_and_hollowing_one_out_revokes_the_pass(tmp_path):
    """The hole the second council pass found: with existence as the only
    requirement, one touched file was a free forgery of every station."""
    sm.open_item("item-1")
    empty = tmp_path / "touched.md"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(sm.MarkRefused) as exc:
        sm.mark("item-1", "draft", str(empty))
    assert "empty or near-empty" in str(exc.value)

    real = _artifact(tmp_path, "draft.md")
    sm.mark("item-1", "draft", real)
    assert sm.check("item-1", "draft").state == sm.SATISFIED

    # Honest once is not honest now.
    tmp_path.joinpath("draft.md").write_text("", encoding="utf-8")
    result = sm.check("item-1", "draft")
    assert result.state == sm.MISSING
    assert "now empty" in result.why


def test_an_empty_folder_does_not_pass_as_an_artifact(tmp_path):
    """The first thing that fell when I attacked my own half.

    The directory branch returned early meaning "a folder's substance lives in
    its contents", then never looked at the contents. Every other test here
    uses files, so only an attack could have surfaced it.
    """
    sm.open_item("item-1")
    empty = tmp_path / "hollow"
    empty.mkdir()
    with pytest.raises(sm.MarkRefused):
        sm.mark("item-1", "draft", str(empty))

    (empty / "real.md").write_text(_SUBSTANCE, encoding="utf-8")
    sm.mark("item-1", "draft", str(empty))
    assert sm.check("item-1", "draft").state == sm.SATISFIED


def test_one_file_cannot_stand_for_every_station(tmp_path):
    """I pointed all five at one junk file and the set went green in a
    thousandth of a second. Five stations are five different pieces of work."""
    sm.open_item("item-1")
    one = _artifact(tmp_path, "only.md")
    sm.mark("item-1", "draft", one)
    with pytest.raises(sm.MarkRefused) as exc:
        sm.mark("item-1", "build", one)
    assert "same artifact" in str(exc.value)


def test_the_test_station_refuses_output_that_was_never_run(tmp_path):
    """I typed 'passed' into a file and it counted as stored evidence that a
    command had run. The docstring said stored output rather than a claim about
    output; nothing enforced the difference until the attack found it."""
    sm.open_item("item-1")
    sm.mark("item-1", "draft", _artifact(tmp_path, "draft.md"))
    sm.mark("item-1", "build", _artifact(tmp_path, "edit.py"))

    invented = tmp_path / "invented.txt"
    # Long enough to clear the substance floor, so this pins the run-header
    # rule specifically rather than being refused for being thin.
    invented.write_text(
        "8 passed in 0.34s -- I typed every character of this by hand and no "
        "command was ever run at any point",
        encoding="utf-8",
    )
    with pytest.raises(sm.MarkRefused) as exc:
        sm.mark("item-1", "test", str(invented))
    assert "recorded run" in str(exc.value)

    real = sm.record_run("item-1", [sys.executable, "-c", "print('ran for real')"])
    sm.mark("item-1", "test", str(real))
    assert sm.check("item-1", "test").state == sm.SATISFIED
    body = real.read_text(encoding="utf-8")
    assert "exit: 0" in body and "ran for real" in body


def test_the_sabotage_station_takes_only_a_run_of_the_sabotage_tool(tmp_path):
    """Andrew taught this in August and I built the tool the same week, then
    did not run it on anything I built tonight and told him I was the wrong
    seat to test my own work. Lesson taught, tool built, tool unused. So the
    tool becomes a station, and deciding to break the code does not count as
    breaking the code."""
    sm.open_item("item-1")
    sm.mark("item-1", "draft", _artifact(tmp_path, "draft.md"))
    sm.mark("item-1", "build", _artifact(tmp_path, "edit.py"))
    sm.mark("item-1", "test", str(sm.record_run("item-1", [sys.executable, "-c", "pass"])))

    # A real recorded run, but of something that is not the sabotage tool.
    wrong = sm.record_run("item-1", [sys.executable, "-c", "print('not an attack')"])
    with pytest.raises(sm.MarkRefused) as exc:
        sm.mark("item-1", "sabotage", str(wrong))
    assert sm._SABOTAGE_TOOL in str(exc.value)

    attacked = sm.record_run("item-1", [sys.executable, "-c", "print('hollow_out.py ran')"])
    sm.mark("item-1", "sabotage", str(attacked))
    assert sm.check("item-1", "sabotage").state == sm.SATISFIED


def test_the_sabotage_comes_after_the_tests_and_before_the_second_look(tmp_path):
    """Ordering is not decorative: there is nothing to sabotage before tests
    exist, and little point re-walking the lenses over code whose tests have
    not been shown to test anything."""
    assert sm.STATIONS.index("sabotage") == sm.STATIONS.index("test") + 1
    assert sm.STATIONS.index("sabotage") < sm.STATIONS.index("second_council")

    sm.open_item("item-1")
    sm.mark("item-1", "draft", _artifact(tmp_path, "draft.md"))
    sm.mark("item-1", "build", _artifact(tmp_path, "edit.py"))
    sm.mark("item-1", "test", str(sm.record_run("item-1", [sys.executable, "-c", "pass"])))
    # With the tests recorded, the attack is now the earliest gap, and the
    # refusal names it in words rather than as a station number.
    with pytest.raises(sm.MarkRefused) as exc:
        sm.mark("item-1", "second_council", _artifact(tmp_path, "walk.txt"))
    assert "blanked the code" in str(exc.value)


def test_a_failing_run_is_recorded_as_faithfully_as_a_passing_one(tmp_path):
    """Hiding a red result would be the same fault one layer over."""
    sm.open_item("item-1")
    failed = sm.record_run("item-1", [sys.executable, "-c", "raise SystemExit(3)"])
    assert "exit: 3" in failed.read_text(encoding="utf-8")


def test_a_station_this_half_does_not_watch_says_so():
    sm.open_item("item-1")
    result = sm.check("item-1", "aletheia_audit")
    assert result.state == sm.CANNOT_CHECK
    assert "not watched by this half" in result.why
