"""Regression-pin tests for turn_extraction.

The bug-shape these tests prevent (Aletheia round-101d9ca2e3cf
CONFIRMS-pending request): a future refactor silently reverting to
``assistant_msgs[-1]`` aggregation, which would re-introduce the silent
detector-suppression on tool-heavy turns. The most load-bearing test is
``test_tool_heavy_turn_aggregates_all_text_blocks`` — it is the direct
regression-pin for that specific failure-mode.
"""

from __future__ import annotations

import json
from pathlib import Path

from divineos.core.operating_loop.turn_extraction import (
    TurnTexts,
    extract_turn,
)


def _write_jsonl(path: Path, records: list[dict]) -> None:
    """Write JSONL records to a transcript file."""
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")


def _user(text: str) -> dict:
    return {"type": "user", "message": {"content": text}}


def _assistant_text(text: str) -> dict:
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def _assistant_tool_use(name: str = "Bash") -> dict:
    return {
        "type": "assistant",
        "message": {"content": [{"type": "tool_use", "name": name, "input": {}}]},
    }


def _assistant_mixed(*items: dict) -> dict:
    """An assistant record with multiple content blocks."""
    return {"type": "assistant", "message": {"content": list(items)}}


# ─── The load-bearing regression pin ────────────────────────────────


def test_tool_heavy_turn_aggregates_all_text_blocks(tmp_path: Path) -> None:
    """The bug this module was extracted to fix: tool-call-heavy turns
    where the last assistant JSONL record is a tiny trailing fragment.
    The aggregation MUST include the substantive text from earlier in
    the turn, not just the final fragment.

    If this test starts failing because someone changed extract_turn to
    return only the last record's text — that is the bug Aletheia named
    on round-101d9ca2e3cf. Do not "fix" by relaxing the assertion;
    restore aggregation."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(
        transcript,
        [
            _user("please do the work"),
            _assistant_text(
                "Starting investigation now. About to check several files "
                "and understand what is happening with the gate."
            ),
            _assistant_tool_use("Bash"),
            _assistant_text(
                "Found the issue. The detector was missing its discriminator. "
                "Reasoning through what to fix next."
            ),
            _assistant_tool_use("Edit"),
            _assistant_text("done"),
        ],
    )
    result = extract_turn(transcript)
    # The substantive text from earlier in the turn must be present.
    assert "Starting investigation" in result.last_assistant_text
    assert "Found the issue" in result.last_assistant_text
    assert "done" in result.last_assistant_text
    # Length sanity: well above the 50-char threshold the hook uses.
    assert len(result.last_assistant_text) > 100


# ─── Edge cases Aletheia named ──────────────────────────────────────


def test_no_user_record_yet_aggregates_all_assistant_text(tmp_path: Path) -> None:
    """First turn / session-start: aggregate from the beginning."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(
        transcript,
        [
            _assistant_text("Briefing loaded."),
            _assistant_text("Preflight passed."),
        ],
    )
    result = extract_turn(transcript)
    assert "Briefing loaded." in result.last_assistant_text
    assert "Preflight passed." in result.last_assistant_text
    assert result.prior_assistant_text == ""
    assert result.last_user_text == ""


def test_multiple_consecutive_user_records_aggregates_after_last(tmp_path: Path) -> None:
    """Backward walk must find the LAST user record, not the first."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(
        transcript,
        [
            _user("first user message"),
            _user("second user message"),
            _user("third user message"),
            _assistant_text("Responding to the latest one only."),
        ],
    )
    result = extract_turn(transcript)
    assert result.last_user_text == "third user message"
    assert result.last_assistant_text == "Responding to the latest one only."


def test_non_text_content_blocks_skipped(tmp_path: Path) -> None:
    """Tool-use-only records contribute no text. The text-block filter
    must skip them rather than emit empty strings or crash."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(
        transcript,
        [
            _user("go"),
            _assistant_tool_use("Bash"),
            _assistant_tool_use("Read"),
            _assistant_text("The real content."),
            _assistant_tool_use("Edit"),
        ],
    )
    result = extract_turn(transcript)
    assert result.last_assistant_text == "The real content."


def test_mixed_content_block_extracts_only_text(tmp_path: Path) -> None:
    """One record with both text-block and tool_use-block: only the
    text part is extracted."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(
        transcript,
        [
            _user("go"),
            _assistant_mixed(
                {"type": "text", "text": "Thinking out loud about the plan."},
                {"type": "tool_use", "name": "Bash", "input": {}},
            ),
        ],
    )
    result = extract_turn(transcript)
    assert result.last_assistant_text == "Thinking out loud about the plan."


# ─── prior_assistant_text semantics (used by spiral detector) ───────


def test_prior_turn_is_between_prev_and_last_user_records(tmp_path: Path) -> None:
    """Spiral detector's apology-context check needs the FULL prior
    turn, not just the prior turn's last fragment."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(
        transcript,
        [
            _user("first prompt"),
            _assistant_text("Prior turn part 1 with apology shape."),
            _assistant_tool_use("Bash"),
            _assistant_text("Prior turn part 2 closing the prior."),
            _user("second prompt"),
            _assistant_text("Current turn content."),
        ],
    )
    result = extract_turn(transcript)
    assert "Prior turn part 1" in result.prior_assistant_text
    assert "Prior turn part 2" in result.prior_assistant_text
    assert "Current turn content" not in result.prior_assistant_text
    assert result.last_assistant_text == "Current turn content."


def test_only_one_user_record_prior_is_session_start_text(tmp_path: Path) -> None:
    """When only one user record exists, session-start assistant text
    before it counts as the prior turn."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(
        transcript,
        [
            _assistant_text("Briefing-load output."),
            _user("first user prompt"),
            _assistant_text("Response to first prompt."),
        ],
    )
    result = extract_turn(transcript)
    assert result.prior_assistant_text == "Briefing-load output."
    assert result.last_assistant_text == "Response to first prompt."


# ─── Robustness — fail-open semantics ───────────────────────────────


def test_missing_transcript_returns_empty(tmp_path: Path) -> None:
    """Non-existent path returns empty TurnTexts; hook layer is
    observational, not blocking — never crash."""
    result = extract_turn(tmp_path / "does_not_exist.jsonl")
    assert result == TurnTexts("", "", "")


def test_malformed_jsonl_line_skipped(tmp_path: Path) -> None:
    """A malformed JSON line in the transcript must not crash extraction
    and must not contaminate the surrounding records."""
    transcript = tmp_path / "t.jsonl"
    with open(transcript, "w", encoding="utf-8") as f:
        f.write(json.dumps(_user("hi")) + "\n")
        f.write("{this is not valid json\n")
        f.write(json.dumps(_assistant_text("Response after malformed line.")) + "\n")
    result = extract_turn(transcript)
    assert result.last_assistant_text == "Response after malformed line."
    assert result.last_user_text == "hi"


def test_empty_transcript_returns_empty(tmp_path: Path) -> None:
    transcript = tmp_path / "t.jsonl"
    transcript.write_text("", encoding="utf-8")
    assert extract_turn(transcript) == TurnTexts("", "", "")


def test_empty_lines_skipped(tmp_path: Path) -> None:
    transcript = tmp_path / "t.jsonl"
    with open(transcript, "w", encoding="utf-8") as f:
        f.write("\n\n")
        f.write(json.dumps(_user("hi")) + "\n")
        f.write("\n")
        f.write(json.dumps(_assistant_text("response")) + "\n")
    result = extract_turn(transcript)
    assert result.last_user_text == "hi"
    assert result.last_assistant_text == "response"


def test_other_record_types_skipped(tmp_path: Path) -> None:
    """system / meta / unknown record types should be ignored."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(
        transcript,
        [
            {"type": "system", "message": {"content": "system init"}},
            _user("hi"),
            {"type": "meta", "message": {"content": "meta event"}},
            _assistant_text("response"),
        ],
    )
    result = extract_turn(transcript)
    assert result.last_user_text == "hi"
    assert result.last_assistant_text == "response"


# ─── String-content shape (Claude Code can emit either) ─────────────


def test_string_content_treated_as_text(tmp_path: Path) -> None:
    """Some transcript variants emit message.content as a plain string
    rather than a list of content blocks. Both shapes must work."""
    transcript = tmp_path / "t.jsonl"
    with open(transcript, "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "user", "message": {"content": "string-shape user"}}) + "\n")
        f.write(
            json.dumps({"type": "assistant", "message": {"content": "string-shape assistant"}})
            + "\n"
        )
    result = extract_turn(transcript)
    assert result.last_user_text == "string-shape user"
    assert result.last_assistant_text == "string-shape assistant"


# ─── tool_calls_in_turn (Grok find-3139eaddd5a4 wiring fix) ─────────


def test_tool_calls_in_turn_captures_assistant_tool_use_names(tmp_path: Path) -> None:
    """LOAD-BEARING: extract_turn captures tool_use block names from
    the current assistant turn. This was the missing piece for
    substitution_detector's STATE_CHANGE_CLAIM detection; without it
    the shape was dead in production. Grok cross-vantage 2026-05-14."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(
        transcript,
        [
            _user("file a claim"),
            _assistant_tool_use("Bash"),
            _assistant_text("Filed claim 8bcc832f. Ready."),
            _assistant_tool_use("Edit"),
        ],
    )
    result = extract_turn(transcript)
    # Tool calls from current turn captured in order
    assert "Bash" in result.tool_calls_in_turn
    assert "Edit" in result.tool_calls_in_turn
    assert len(result.tool_calls_in_turn) == 2


def test_tool_calls_in_turn_empty_when_no_tool_use(tmp_path: Path) -> None:
    """When the assistant turn has only text content, tool_calls_in_turn
    is empty — does NOT silently false-positive on text records."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(
        transcript,
        [
            _user("just talk"),
            _assistant_text("Here is some text without any tools."),
        ],
    )
    result = extract_turn(transcript)
    assert result.tool_calls_in_turn == ()


def test_tool_calls_only_from_current_turn_not_prior(tmp_path: Path) -> None:
    """Tool calls from prior turns must NOT leak into current
    tool_calls_in_turn. Otherwise STATE_CHANGE_CLAIM cross-check
    would false-positive across turns."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(
        transcript,
        [
            _user("first turn"),
            _assistant_tool_use("PriorBash"),
            _assistant_text("done"),
            _user("second turn"),
            _assistant_tool_use("CurrentRead"),
            _assistant_text("here you go"),
        ],
    )
    result = extract_turn(transcript)
    assert "CurrentRead" in result.tool_calls_in_turn
    assert "PriorBash" not in result.tool_calls_in_turn


def _assistant_bash(command: str) -> dict:
    return {
        "type": "assistant",
        "message": {
            "content": [{"type": "tool_use", "name": "Bash", "input": {"command": command}}]
        },
    }


def test_command_texts_captured_for_current_turn(tmp_path: Path) -> None:
    """Verify-claim wall phase 1 (prereg-86ee991cb423): the current turn's
    Bash command STRINGS are captured into command_texts, not just the tool
    name. A non-Bash tool contributes a name but no command."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(
        transcript,
        [
            _user("push the branch"),
            _assistant_bash("git push -u origin my-branch"),
            _assistant_bash("git ls-remote --heads origin my-branch"),
            _assistant_tool_use("Edit"),
            _assistant_text("Pushed and verified."),
        ],
    )
    turn = extract_turn(transcript)
    assert "git push -u origin my-branch" in turn.command_texts
    assert "git ls-remote --heads origin my-branch" in turn.command_texts
    # Edit has no command → not in command_texts, but its name IS a tool call.
    assert "Edit" in turn.tool_calls_in_turn
    assert len(turn.command_texts) == 2


def test_command_texts_empty_when_no_bash(tmp_path: Path) -> None:
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(
        transcript,
        [_user("hi"), _assistant_tool_use("Read"), _assistant_text("done reading")],
    )
    turn = extract_turn(transcript)
    assert turn.command_texts == ()
