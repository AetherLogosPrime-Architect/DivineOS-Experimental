"""Each test pins one way this half could quietly become decoration.

The five failures it has to survive: a mark with nothing at the other end,
a mark filed out of order, an unopened item reading as clean, an
unreadable record passing as satisfied, and a refusal message that says
nothing a person could act on.
"""

from __future__ import annotations

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
    sm.mark("item-1", "test", _artifact(tmp_path, "out.txt"))
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


def test_a_station_this_half_does_not_watch_says_so():
    sm.open_item("item-1")
    result = sm.check("item-1", "aletheia_audit")
    assert result.state == sm.CANNOT_CHECK
    assert "not watched by this half" in result.why
