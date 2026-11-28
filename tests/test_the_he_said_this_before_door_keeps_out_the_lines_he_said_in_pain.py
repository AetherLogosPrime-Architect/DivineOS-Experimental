"""The "he has said this before" door keeps out lines read as pain (walk-ab0b90e8ce57).

Every sentence below is invented. None is his: the door is about not showing his hard lines, so the
tests must not hold any either.
"""

import json

import pytest

pytest.importorskip("sentence_transformers")

from divineos.core import his_words_door as door

HARD = "you left the kettle on the stove again and the timer never turned the burner off"
CALM = "the kettle on the stove should have a timer that turns the burner off by itself"
HIS = [
    ("2026-07-01T10:00:00Z", HARD),
    ("2026-08-01T10:00:00Z", CALM),
    ("2026-08-05T10:00:00Z", "lets go for a long walk by the river this weekend with the dog"),
]
ASK = "what should we do about the kettle and the stove timer?"
WHY = "a hard-day line about a kitchen accident"


@pytest.fixture(scope="module")
def index(tmp_path_factory):
    d = tmp_path_factory.mktemp("kept")
    corpus = d / "dad_all.jsonl"
    corpus.write_text(
        "\n".join(json.dumps({"ts": ts, "project": "t", "text": t}) for ts, t in HIS) + "\n",
        encoding="utf-8",
    )
    assert door.build_index(corpus, d / "index") > 0
    return d / "index"


def _path(tmp_path):
    return tmp_path / "his_kept_out.json"


def test_without_a_list_nothing_changes(index, tmp_path):
    got = door.look(ASK, index_dir=index, kept_out_path=_path(tmp_path))
    texts = [h.passage.text for h in got.hits]
    assert HARD in texts and CALM in texts
    assert got.kept_out == 0


def test_a_kept_out_line_is_not_a_hit_nor_a_repeat_nor_in_the_output(index, tmp_path):
    p = _path(tmp_path)
    door.keep_out(HARD, why=WHY, by="t", on="2026-11-20", path=p)
    got = door.look(ASK, index_dir=index, kept_out_path=p)
    assert HARD not in [h.passage.text for h in got.hits + got.repeats]
    assert CALM in [h.passage.text for h in got.hits]
    assert got.kept_out == 1
    assert "left the kettle on the stove again" not in door.surface(
        ASK, index_dir=index, kept_out_path=p
    )


def test_keeping_out_by_the_printed_fingerprint_does_the_same(index, tmp_path):
    p = _path(tmp_path)
    shown = door.surface(ASK, index_dir=index, kept_out_path=p)
    fp = door.fingerprint(HARD)
    assert f"#{fp}" in shown
    door.keep_out(fp=fp, why=WHY, by="t", on="d", path=p)
    assert "left the kettle on the stove again" not in door.surface(
        ASK, index_dir=index, kept_out_path=p
    )


def test_the_same_line_cut_differently_is_a_different_fingerprint():
    assert door.fingerprint(HARD) != door.fingerprint(HARD + " and more words after it")
    assert door.fingerprint(HARD) == door.fingerprint(HARD.upper() + "!!")  # the door's own shape


def test_an_unreadable_list_silences_the_door_and_says_why(index, tmp_path):
    p = _path(tmp_path)
    p.write_text("{not json", encoding="utf-8")
    got = door.look(ASK, index_dir=index, kept_out_path=p)
    assert not got.looked and got.hits == []
    out = door.surface(ASK, index_dir=index, kept_out_path=p)
    assert "kept-out list could not be read" in out
    assert "left the kettle" not in out


def test_a_list_of_the_wrong_shape_is_unreadable_not_empty(index, tmp_path):
    p = _path(tmp_path)
    p.write_text(json.dumps({"entries": "nope"}), encoding="utf-8")
    assert not door.look(ASK, index_dir=index, kept_out_path=p).looked


def test_refusals(tmp_path):
    p = _path(tmp_path)
    for kwargs in (
        {"passage": "   ", "why": "x"},  # neither
        {"passage": "!!! ???", "why": "x"},  # no words
        {"passage": HARD, "why": ""},  # no reason
        {"passage": HARD, "why": f"it said {HARD}"},  # the reason quotes the line
        {"fp": "nothex", "why": "x"},  # not a fingerprint
        {"passage": HARD, "fp": "0" * 16, "why": "x"},  # both
    ):
        with pytest.raises(ValueError):
            door.keep_out(by="t", on="d", path=p, **kwargs)
    assert not p.exists()


def test_a_reason_cannot_smuggle_the_words_in_by_way_of_the_fingerprint(index, tmp_path):
    """The game-walk's cheaper route: quoting through --fp skipped the check that a passage gets."""
    p = _path(tmp_path)
    fp = door.fingerprint(HARD)
    leak = "he said you left the kettle on the stove again and then went quiet"
    with pytest.raises(ValueError):
        door.keep_out(fp=fp, why=leak, by="t", on="d", path=p, index_dir=index)
    assert not p.exists()
    door.keep_out(
        fp=fp, why="a hard-day line about the stove", by="t", on="d", path=p, index_dir=index
    )
    assert door.fingerprint(HARD) in p.read_text(encoding="utf-8")


def test_the_file_holds_hashes_and_a_description_never_the_words(tmp_path):
    p = _path(tmp_path)
    door.keep_out(HARD, why=WHY, by="t", on="d", path=p)
    raw = p.read_text(encoding="utf-8")
    assert "kettle" not in raw and "stove" not in raw
    assert door.fingerprint(HARD) in raw


def test_keep_out_and_return_round_trip_and_filing_twice_changes_nothing(tmp_path):
    p = _path(tmp_path)
    a = door.keep_out(HARD, why="described", by="t", on="d", path=p)
    b = door.keep_out(HARD, why="described again", by="t", on="d", path=p)
    assert a == b and len(door._kept_out_entries(p)) == 1
    assert door.return_to_door(HARD, path=p) is True
    assert door.return_to_door(HARD, path=p) is False
    assert door._kept_out_entries(p) == []


def test_a_returned_line_falls_through_to_its_calm_pair(index, tmp_path, monkeypatch):
    """Order in the door: the kept-out drop comes first, then the calm-pair swap."""
    repl = tmp_path / "repl.json"
    entry = {
        "anchor": "left the kettle on the stove again",
        "shown_instead": "the kettle needs a timer",
        "said": "2026-11-01",
    }
    repl.write_text(json.dumps({"entries": [entry]}), encoding="utf-8")
    monkeypatch.setattr(door, "REPLACEMENTS", repl)
    p = _path(tmp_path)
    door.keep_out(HARD, why="described", by="t", on="d", path=p)
    assert "the kettle needs a timer" not in door.surface(ASK, index_dir=index, kept_out_path=p)
    door.return_to_door(HARD, path=p)
    assert "the kettle needs a timer" in door.surface(ASK, index_dir=index, kept_out_path=p)
