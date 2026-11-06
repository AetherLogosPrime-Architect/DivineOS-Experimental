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


def test_a_room_that_is_only_a_file_reference_is_not_printed_as_his_words():
    rec = {
        "seats": ["aether"],
        "before": [],
        "nearest_user_before": {
            "text": '@"C:\\Users\\aethe\\Downloads\\letter_aletheia_to_aria.md"'
        },
    }
    text = "\n".join(scenes.scene_lines(rec))
    assert "he had just attached a file" in text
    assert "Downloads" not in text and "he had just said" not in text


def test_our_text_pasted_under_a_lead_in_of_his_is_cut_not_labelled_as_his():
    ours = (
        "Five commits, four rounds, and Aether pointed me at the right things to attack. "
        "Let me pull the branch and go after the two that actually need adversarial eyes."
    )
    rec = {
        "seats": ["aether"],
        "before": [],
        "nearest_user_before": {"text": f"hmm.. should be there.. this is the letter\n\n{ours}"},
    }
    text = "\n".join(scenes.scene_lines(rec))
    assert "he had just said: hmm.. should be there.. this is the letter" in text
    assert "Five commits" not in text


def test_a_room_that_is_wholly_ours_is_dropped_so_the_label_never_sits_over_our_words():
    ours = "Done. The slot is replaced. The next message you send me will be the first composed with the new rule."
    rec = {"seats": ["aether"], "before": [], "nearest_user_before": {"text": ours}}
    assert "he had just said" not in "\n".join(scenes.scene_lines(rec))


def test_his_own_words_in_the_room_are_kept_whole():
    mine, only_a_file = scenes.his_part_of(
        "ok go ahead.. and use powershell if you cant get around it"
    )
    assert mine == "ok go ahead.. and use powershell if you cant get around it" and not only_a_file


def test_a_user_turn_before_that_is_only_a_file_reference_prints_no_path():
    rec = {
        "seats": ["aether"],
        "before": [{"role": "user", "text": '@"C:\\Users\\aethe\\Downloads\\letter_x.md"'}],
    }
    text = "\n".join(scenes.scene_lines(rec))
    assert "Downloads" not in text and "letter_x" not in text
    assert "he had attached a file" in text


def test_a_long_turn_is_clipped_never_summarised():
    long = {"seats": ["aria"], "before": [{"role": "assistant", "text": "word " * 200}]}
    line = [x for x in scenes.scene_lines(long) if "turn before" in x][0]
    assert line.endswith("...") and len(line) < 400 and "word word word" in line
