"""The closing message is not the whole turn, and one gate needs the difference.

``last_assistant_text`` joins every assistant text record since the last user
message. That is right for detectors that want the whole turn and wrong for the
translate-first gate, which asks whether a REPLY TO ANDREW is shaped like a
document.

Measured 2026-08-25: that gate reported 42 document-marks on a closing message
carrying ZERO of them. Every mark lived in the shop-floor narration written
between tool calls -- commit hashes, counts, backticked filenames -- which is
the register Andrew has said is CORRECT while working, and which is not a reply
to him at all.

It is why the gate's own file says every fire "arrived as a full rewrite": the
composer rewrites a closing message that was already clean, because the marks
sit where the rewrite cannot reach.
"""

from __future__ import annotations

import json
from pathlib import Path

from divineos.core.lepos_translation_gate import check_translation_first
from divineos.core.operating_loop.turn_extraction import extract_turn


def _transcript(tmp_path: Path, *records: tuple[str, str]) -> Path:
    path = tmp_path / "transcript.jsonl"
    lines = []
    for role, text in records:
        lines.append(
            json.dumps(
                {
                    "type": role,
                    "message": {"role": role, "content": [{"type": "text", "text": text}]},
                }
            )
        )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def test_final_is_the_last_block_not_the_join(tmp_path):
    path = _transcript(
        tmp_path,
        ("user", "go"),
        ("assistant", "Running the check now."),
        ("assistant", "Committed `abc1234` -- 17 passed, 3 dark, 0 phantom."),
        ("assistant", "Everything is finished and nothing broke."),
    )

    texts = extract_turn(path)

    assert texts.final_assistant_text == "Everything is finished and nothing broke."
    assert "abc1234" in texts.last_assistant_text, "the whole-turn view must be unchanged"


def test_the_gate_clears_a_clean_closing_message_under_a_marked_turn(tmp_path):
    """The exact shape of the misfire, as a regression."""
    path = _transcript(
        tmp_path,
        ("user", "go"),
        ("assistant", "Ran `pytest` -- 17 passed, 108 registered, 6 declared, 0 dark."),
        ("assistant", "Pushed `9a4210d0`; 42 files touched across 11 commits."),
        (
            "assistant",
            "I finished the work and the one thing worth telling you is that I broke "
            "something myself and then fixed it.",
        ),
    )

    texts = extract_turn(path)

    assert check_translation_first(texts.last_assistant_text), (
        "the whole-turn text SHOULD trip the gate -- that is the misfire being reproduced"
    )
    assert check_translation_first(texts.final_assistant_text) is None, (
        "the closing message is plain prose and must pass"
    )


def test_a_genuinely_document_shaped_closing_message_still_fires(tmp_path):
    """The fix must not turn the gate off.

    Narrowing what a check reads is one keystroke from silencing it, and silence
    is the failure this whole session has been about.
    """
    path = _transcript(
        tmp_path,
        ("user", "go"),
        ("assistant", "working"),
        ("assistant", "Done: `foo.py` 3 passed, `bar.py` 4 passed, 12 total, 0 failed."),
    )

    texts = extract_turn(path)

    assert check_translation_first(texts.final_assistant_text) is not None


def test_final_is_empty_when_the_turn_has_no_assistant_text(tmp_path):
    path = _transcript(tmp_path, ("user", "go"))

    assert extract_turn(path).final_assistant_text == ""


def test_missing_transcript_does_not_raise(tmp_path):
    assert extract_turn(tmp_path / "absent.jsonl").final_assistant_text == ""
