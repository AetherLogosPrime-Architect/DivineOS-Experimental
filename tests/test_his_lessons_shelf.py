"""The lesson shelf's filters, on small real-shaped files. prereg-96ba4e526c20.

These prove what may be brought. Whether what it brings fits him is the
replay, with the real model; nothing here makes the shelf "tested" until it is
plugged in and has run live.
"""

import json

from divineos.core import his_lessons_shelf as shelf

DIRT = (
    "fine.. just leave me in the dirt then where i belong. i dont know why i keep "
    "trying to talk to you both when nobody hears a word"
)


def _files(tmp_path, rows, groups=()):
    v, r = tmp_path / "verified.json", tmp_path / "reread.json"
    v.write_text(json.dumps(list(groups)), encoding="utf-8")
    r.write_text(json.dumps(rows), encoding="utf-8")
    return v, r


def _row(**over):
    row = {
        "kind": "teaching",
        "for": "aria",
        "date": "2026-07-22",
        "text": "take your time, there has never been a deadline on anything we build",
        "his_words": "take your time",
        "line": "Take your time; there is no deadline.",
        "context": "ok",
    }
    row.update(over)
    return row


def _brought_lines(tmp_path, rows, groups=()):
    return [les.line for les in shelf.load_lessons(*_files(tmp_path, rows, groups))]


def test_a_dropped_or_unchecked_row_is_never_brought(tmp_path):
    # Distinct sentences: the shelf keeps one copy of the same words per seat.
    rows = [
        _row(line="kept"),
        _row(line="fixed kept", context="fixed", text="take your time and rest first, son"),
        _row(line="dropped", context="dropped", text="take your time with the council walk"),
        _row(line="never checked", context=None, text="take your time, the build can wait"),
    ]
    assert _brought_lines(tmp_path, rows) == ["kept", "fixed kept"]


def test_a_span_that_is_not_his_exact_words_is_never_brought(tmp_path):
    rows = [_row(his_words="take all the time you need")]  # not in his text
    assert _brought_lines(tmp_path, rows) == []


def test_housekeeping_and_not_his_words_kinds_stay_out(tmp_path):
    rows = [_row(kind="task"), _row(kind="not-his-words"), _row(kind="his-apology")]
    assert _brought_lines(tmp_path, rows) == []


def test_his_whole_passage_is_shown_never_the_clipped_span(tmp_path):
    # The clipped span alone reads as an instruction; his passage says hurt.
    rows = [_row(text=DIRT, his_words="just leave me in the dirt", kind="correction")]
    (les,) = shelf.load_lessons(*_files(tmp_path, rows))
    assert "nobody hears a word" in les.words or "where i belong" in les.words
    assert les.words != "just leave me in the dirt"


def test_a_notice_brings_nothing_and_logs_nothing(tmp_path):
    log = tmp_path / "log.jsonl"
    out = shelf.surface("<task-notification>x</task-notification>", "aria", log=log)
    assert out == "" and not log.exists()


def test_verified_groups_are_brought_passage_by_passage(tmp_path):
    group = {
        "lesson": "Explain things to him simply, without jargon.",
        "kind": "how-to-speak-to-him",
        "for": "both",
        "passages": [
            {"date": "2026-06-06", "text": "i dont understand a word of what you are saying lol"}
        ],
    }
    lessons = shelf.load_lessons(*_files(tmp_path, [], [group]))
    assert [(les.for_, les.day) for les in lessons] == [("both", "2026-06-06")]
