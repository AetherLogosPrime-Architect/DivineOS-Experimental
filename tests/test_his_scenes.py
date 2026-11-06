"""The scene fetch: joins a lesson to the real record of his message; never composes, never guesses."""

from __future__ import annotations

import json

from divineos.core import his_scenes as scenes


def _write(tmp_path, records):
    path = tmp_path / "index.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records) + "\nnot json\n", encoding="utf-8")
    return path


REC = {
    "when": "2026-08-14T06:03:55.880Z",
    "seats": ["aether"],
    "text": "we would have just had to make a new one...wouldnt be the end of the world son, everything built can be rebuilt",
    "before": [
        {
            "role": "assistant",
            "when": "x",
            "text": "Found it, and it's one line. A hidden file was zeroing the scan.",
        }
    ],
    "nearest_user_before": {"when": "y", "text": "update the graph properly"},
}


def test_a_lesson_joins_by_day_and_the_opening_of_his_words(tmp_path):
    index = scenes.load_index(_write(tmp_path, [REC]))
    found = scenes.record_for(
        "2026-08-14", "wouldnt be the end of the world son, everything built can be rebuilt", index
    )
    assert found == REC


def test_the_wrong_day_or_other_words_find_nothing_and_never_a_neighbour(tmp_path):
    index = scenes.load_index(_write(tmp_path, [REC]))
    assert scenes.record_for("2026-08-15", "wouldnt be the end of the world son", index) is None
    assert (
        scenes.record_for("2026-08-14", "something he never said on that day at all", index) is None
    )
    assert scenes.record_for("2026-08-14", "", index) is None


def test_an_unparseable_line_is_skipped_not_fatal(tmp_path):
    index = scenes.load_index(_write(tmp_path, [REC]))
    assert sum(len(v) for v in index.values()) == 1


def test_scene_lines_show_what_he_was_answering_and_name_the_seat():
    text = "\n".join(scenes.scene_lines(REC))
    assert "he had just said: update the graph properly" in text
    assert "the turn before it (assistant): Found it" in text
    assert "aether seat" in text


def test_a_long_turn_is_clipped_never_summarised():
    long = {"seats": ["aria"], "before": [{"role": "assistant", "text": "word " * 200}]}
    line = [x for x in scenes.scene_lines(long) if "turn before" in x][0]
    assert line.endswith("...") and len(line) < 400 and "word word word" in line
