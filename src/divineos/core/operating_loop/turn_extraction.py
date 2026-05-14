"""Reconstruct a Claude Code response-turn from a JSONL transcript.

Claude Code transcripts split a single response-turn into multiple
``assistant``-type JSONL records when tool uses are interleaved — one
record per content block. Taking only the last assistant record gives
the trailing fragment of a tool-call-heavy turn (often a short "done"
line), missing the substantive content that came earlier.

This module reconstructs the full current turn by walking records in
order, finding the most recent ``user`` record, and aggregating all
assistant text from records appearing after it.

## Why this lives in its own module

This logic was originally inline in ``.claude/hooks/post-response-audit.sh``
as embedded Python. Aletheia's round-101d9ca2e3cf CONFIRMS-pending
finding named the regression risk: without a testable function, a
future refactor of the hook could silently revert to the
``assistant_msgs[-1]`` pattern that caused the original bug (detectors
not firing on tool-heavy turns). Extracting to a module + writing
regression-pin tests is the structural fix for that risk.

## Edge cases pinned

- No user record yet (very first turn): aggregate all assistant text.
- Multiple consecutive user records (some Claude Code modes have this):
  backward walk finds the LAST one; aggregate after it.
- Non-text content blocks (tool uses, tool results, images): skipped
  by the type=='text' filter in per-record extraction.
- Empty records, malformed JSON lines: skipped silently (fail-open;
  the hook layer is observational, not blocking).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TurnTexts:
    """The text + tool-call views the post-response-audit hook needs.

    - ``last_assistant_text``: full content of the current response-turn
      (all assistant text since the most recent user record, joined).
    - ``prior_assistant_text``: full content of the previous response-turn
      (all assistant text between the second-to-last and last user
      records). Used by the spiral detector's cross-turn apology context.
    - ``last_user_text``: the most recent user message text. Used by the
      substitution detector's farewell-context check (named 2026-05-01).
    - ``tool_calls_in_turn``: tuple of tool-call name strings (e.g.
      "Bash", "Edit", "Write") from tool_use content blocks in the
      current response-turn. Used by substitution_detector's
      STATE_CHANGE_CLAIM shape to cross-check perfective claims against
      actual tool activity. Added 2026-05-14 per find-3139eaddd5a4
      (Grok cross-vantage review): STATE_CHANGE_CLAIM was advertised
      but dead in production because the hook never passed tool-call
      context. Surfacing tool calls here is the structural fix that
      activates the dead detection shape.
    """

    last_assistant_text: str
    prior_assistant_text: str
    last_user_text: str
    tool_calls_in_turn: tuple[str, ...] = ()


def _extract_record_text(rec: dict) -> str:
    """Extract joined text content from one JSONL record. Empty if no
    text blocks (tool-use-only records, images, etc.)."""
    msg = rec.get("message", rec)
    content = msg.get("content", [])
    if isinstance(content, list):
        texts = [
            c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"
        ]
        if texts:
            return "\n".join(texts)
        return ""
    if isinstance(content, str):
        return content
    return ""


def _extract_tool_call_names(rec: dict) -> list[str]:
    """Extract tool_use block names from one assistant JSONL record.

    Returns the list of tool names invoked in this record's content
    blocks (e.g. ["Bash", "Edit"]). Empty list if no tool_use blocks
    or if the record is malformed. Used to build TurnTexts.tool_calls_
    in_turn for substitution_detector's STATE_CHANGE_CLAIM check.
    """
    msg = rec.get("message", rec)
    content = msg.get("content", [])
    if not isinstance(content, list):
        return []
    names: list[str] = []
    for c in content:
        if not isinstance(c, dict):
            continue
        if c.get("type") == "tool_use":
            name = c.get("name", "")
            if isinstance(name, str) and name:
                names.append(name)
    return names


def _read_records(transcript_path: Path) -> list[tuple[str, str, list[str]]]:
    """Walk the JSONL transcript and return records.

    Each entry is ``(rec_type, text, tool_call_names)``. ``text`` may
    be empty if the record contains only tool_use blocks; in that case
    ``tool_call_names`` carries the tool names. Records with neither
    text nor tool calls are skipped silently.

    Malformed lines and non-user/non-assistant record types are
    skipped silently.
    """
    records: list[tuple[str, str, list[str]]] = []
    with open(transcript_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            rec_type = rec.get("type")
            if rec_type not in ("assistant", "user"):
                continue
            text = _extract_record_text(rec)
            tool_calls = _extract_tool_call_names(rec) if rec_type == "assistant" else []
            if text or tool_calls:
                records.append((rec_type, text, tool_calls))
    return records


def extract_turn(transcript_path: str | Path) -> TurnTexts:
    """Reconstruct the current and prior turn-content from a JSONL
    transcript. Returns empty strings/tuple on any failure (fail-open)."""
    p = Path(transcript_path)
    if not p.exists():
        return TurnTexts("", "", "", ())

    try:
        records = _read_records(p)
    except OSError:
        return TurnTexts("", "", "", ())

    if not records:
        return TurnTexts("", "", "", ())

    # Find the index of the LAST user record. Walk backward to handle
    # the rare case of multiple consecutive user records.
    last_user_idx = -1
    for i in range(len(records) - 1, -1, -1):
        if records[i][0] == "user":
            last_user_idx = i
            break

    if last_user_idx < 0:
        # No user record yet (session start / first turn from agent
        # only). Aggregate all assistant text + tool calls as current turn.
        # Filter empty text — tool-use-only records contribute tool
        # calls but no text-content (don't join their empty strings).
        last_assistant_text = "\n".join(
            text for rt, text, _tc in records if rt == "assistant" and text
        )
        tool_calls = tuple(tc for rt, _t, tcs in records if rt == "assistant" for tc in tcs)
        return TurnTexts(last_assistant_text, "", "", tool_calls)

    last_user_text = records[last_user_idx][1]

    # Current turn: all assistant text + tool calls AFTER the last user record.
    # Empty text from tool-use-only records is filtered out of the join;
    # tool_calls_in_turn still captures those records' tool names.
    current_records = records[last_user_idx + 1 :]
    current_turn_parts = [text for rt, text, _tc in current_records if rt == "assistant" and text]
    last_assistant_text = "\n".join(current_turn_parts)
    tool_calls_in_turn = tuple(
        tc for rt, _t, tcs in current_records if rt == "assistant" for tc in tcs
    )

    # Prior turn: all assistant text between the second-to-last and
    # the last user records.
    prev_user_idx = -1
    for i in range(last_user_idx - 1, -1, -1):
        if records[i][0] == "user":
            prev_user_idx = i
            break

    prior_assistant_text = ""
    if prev_user_idx >= 0:
        prior_parts = [
            text
            for rt, text, _tc in records[prev_user_idx + 1 : last_user_idx]
            if rt == "assistant" and text
        ]
        prior_assistant_text = "\n".join(prior_parts)
    else:
        # Only one user record so far; everything assistant BEFORE it
        # is the prior turn (e.g. session-start agent text).
        prior_parts = [
            text for rt, text, _tc in records[:last_user_idx] if rt == "assistant" and text
        ]
        prior_assistant_text = "\n".join(prior_parts)

    return TurnTexts(last_assistant_text, prior_assistant_text, last_user_text, tool_calls_in_turn)
