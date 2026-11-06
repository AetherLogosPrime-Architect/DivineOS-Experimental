"""The correction-shape Stop check settles on a fact, not on words alone (2026-11-05).

Dad's rule, 2026-11-05: a keyword detector is one layer of the net, never the enforcer. The correction-shape
check reads my last reply for a self-admission and blocks until I file a correction. It also read the circle,
so an admission inside the circle fired AFTER the circle and made a second one; and its only exit for a wrong
fire was a second errand (label-fire). The words now only NOMINATE ("this reply admits an error"). The fact
that settles it is whether a correction was actually FILED since his last message, through the CLI
(`divineos correction`, which writes corrections.jsonl). Rows the hooks file for me when HE corrects me live
in a different store and must not count.

A fact that cannot be read never blocks: could-not-check passes, the same rule as the receipt gate.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from divineos.core import correction_receipt as cr


def _him(text: str, when: str, n: int) -> dict:
    return {
        "type": "user",
        "uuid": f"u{n}",
        "timestamp": when,
        "message": {"role": "user", "content": text},
    }


def _me(text: str, when: str, n: int) -> dict:
    return {
        "type": "assistant",
        "uuid": f"a{n}",
        "timestamp": when,
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
    }


def _filed(path: Path, at: float, text: str = "root cause: x. structural fix: y.") -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"text": text, "timestamp": at, "session_id": ""}) + "\n")


T1 = "2026-11-05T10:00:00Z"
T2 = "2026-11-05T10:00:30Z"
EPOCH_T1 = 1793872800.0  # 2026-11-05T10:00:00Z


def test_his_last_turn_time_is_the_time_of_his_last_real_message():
    records = [
        _him("first", "2026-11-05T09:00:00Z", 1),
        _me("a reply", "2026-11-05T09:00:30Z", 2),
        _him("second", T1, 3),
        _me("another reply", T2, 4),
    ]
    assert cr.his_last_turn_time(records) == EPOCH_T1


def test_a_notice_is_not_his_turn():
    notice = "<task-notification>\n<task-id>x</task-id>\n</task-notification>"
    records = [_him("second", T1, 1), _me("reply", T2, 2), _him(notice, "2026-11-05T10:05:00Z", 3)]
    assert cr.his_last_turn_time(records) == EPOCH_T1


def test_no_message_of_his_means_no_time():
    assert cr.his_last_turn_time([_me("alone", T2, 1)]) is None


def test_a_correction_filed_after_his_message_counts(tmp_path):
    path = tmp_path / "corrections.jsonl"
    _filed(path, EPOCH_T1 + 5)
    assert cr.filed_since(EPOCH_T1, path) is True


def test_a_correction_filed_before_his_message_does_not_count(tmp_path):
    path = tmp_path / "corrections.jsonl"
    _filed(path, EPOCH_T1 - 5)
    assert cr.filed_since(EPOCH_T1, path) is False


def test_no_file_means_nothing_was_filed(tmp_path):
    assert cr.filed_since(EPOCH_T1, tmp_path / "corrections.jsonl") is False


def test_a_malformed_line_is_skipped_not_fatal(tmp_path):
    path = tmp_path / "corrections.jsonl"
    path.write_text("not json\n", encoding="utf-8")
    _filed(path, EPOCH_T1 + 5)
    assert cr.filed_since(EPOCH_T1, path) is True


def test_an_unreadable_store_is_could_not_check_not_nothing(tmp_path):
    folder = tmp_path / "corrections.jsonl"
    folder.mkdir()  # a directory where the file should be: reading it fails
    assert cr.filed_since(EPOCH_T1, folder) is None


def test_settled_when_a_correction_was_filed_this_stretch(tmp_path):
    path = tmp_path / "corrections.jsonl"
    _filed(path, EPOCH_T1 + 5)
    records = [_him("go on", T1, 1), _me("I got that wrong, and filed it", T2, 2)]
    assert cr.settled(records, path) == cr.SETTLED


def test_unsettled_when_nothing_was_filed_this_stretch(tmp_path):
    path = tmp_path / "corrections.jsonl"
    _filed(path, EPOCH_T1 - 60)  # an older filing is not this stretch's
    records = [_him("go on", T1, 1), _me("I got that wrong", T2, 2)]
    assert cr.settled(records, path) == cr.UNSETTLED


def test_could_not_check_when_his_turn_cannot_be_placed(tmp_path):
    path = tmp_path / "corrections.jsonl"
    _filed(path, time.time())
    assert cr.settled([_me("I got that wrong", T2, 1)], path) == cr.COULD_NOT_CHECK


def test_could_not_check_when_the_store_is_unreadable(tmp_path):
    folder = tmp_path / "corrections.jsonl"
    folder.mkdir()
    records = [_him("go on", T1, 1), _me("I got that wrong", T2, 2)]
    assert cr.settled(records, folder) == cr.COULD_NOT_CHECK


def test_the_hook_asks_the_receipt_before_it_blocks():
    """The hook's script must call the receipt; this pins the wiring so removing it fails a test."""
    hook = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "correction-shape-v2-stop.sh"
    text = hook.read_text(encoding="utf-8")
    assert "correction_receipt" in text and "settled(" in text
    # the receipt is consulted AFTER the classifier fires and BEFORE the marker is armed
    assert text.index("classify(last_text)") < text.index("settled(") < text.index("set_marker(")
