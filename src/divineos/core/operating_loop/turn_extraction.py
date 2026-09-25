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
    # Bash command STRINGS run in the current turn (the `command` input of
    # each Bash tool_use). Tool NAMES ("Bash") aren't enough for detectors
    # that need to know WHICH command ran — e.g. the unverified-claim
    # detector checking whether a verifying command (git ls-remote, pytest)
    # actually executed. Verify-claim wall phase 1 (prereg-86ee991cb423).
    command_texts: tuple[str, ...] = ()
    # The CLOSING message alone — the last assistant text block in the turn,
    # not the join of all of them.
    #
    # WHY IT IS SEPARATE, measured 2026-08-25. `last_assistant_text` is every
    # assistant text record since the last user record, joined. That is right
    # for the detectors that want the whole turn (spiral, substitution) and
    # wrong for the translate-first gate, which asks whether a REPLY TO ANDREW
    # is shaped like a document. In a long agentic turn the join sweeps in every
    # line of shop-floor narration written between tool calls — commit hashes,
    # counts, backticked filenames — which is the register Andrew has said is
    # CORRECT while working.
    #
    # The measurement: a closing message carrying ZERO document-marks by the
    # gate's own patterns was reported at 42. All 42 lived in the interstitial
    # narration. That is why the file's own comment says "every fire arrived as
    # a full rewrite" — the composer rewrites a closing message that was already
    # clean, because the marks are somewhere the rewrite cannot reach.
    final_assistant_text: str = ""


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


def _extract_bash_commands(rec: dict) -> list[str]:
    """Extract Bash command strings from tool_use blocks in one assistant
    record — the ``command`` input of each Bash tool_use. Empty list if
    none. Lets detectors check WHICH command ran (e.g. git ls-remote),
    not merely that "Bash" ran (verify-claim wall phase 1)."""
    msg = rec.get("message", rec)
    content = msg.get("content", [])
    if not isinstance(content, list):
        return []
    cmds: list[str] = []
    for c in content:
        if not isinstance(c, dict) or c.get("type") != "tool_use":
            continue
        if c.get("name") != "Bash":
            continue
        inp = c.get("input", {})
        if isinstance(inp, dict):
            cmd = inp.get("command", "")
            if isinstance(cmd, str) and cmd:
                cmds.append(cmd)
    return cmds


# Tail-read window. Every caller of this module wants RECENT turns —
# extract_turn wants the last user record and what follows it;
# recent_turns_text wants the last handful. Nobody wants turn 3 of 400.
#
# Reading the whole file was costing real time, not theoretical time.
# Eight hooks on UserPromptSubmit and ten on Stop funnel through here,
# and a live transcript reaches tens of megabytes: measured 2026-08-03 at
# 39 MB live, 64 MB for the largest archived session, 767 MB across one
# project's history. That is hundreds of megabytes of reads standing
# between the operator pressing enter and the turn starting — which is
# exactly where the freeze he has been living with appears, and why it
# worsens as a session grows and why Escape does nothing (blocked on I/O,
# not waiting on a socket).
#
# I had already hit this once and fixed it in ONE hook's inline reader,
# then never asked whether anything else did the same thing. Eighteen
# other readers did.
_TAIL_BYTES_START = 2_000_000
_TAIL_BYTES_MAX = 32_000_000
_MIN_RECORDS = 40


def _tail_chunks(path: Path, min_records: int):
    """Yield (text, is_whole_file) windows, smallest first.

    Small files yield once, whole. Large files yield a growing tail so a
    caller that did not find enough records can widen instead of silently
    getting less than the old whole-file read would have given it. The
    final yield is always the entire file, so this can never return fewer
    records than the previous implementation — it only avoids reading
    bytes nobody needed.
    """
    try:
        size = path.stat().st_size
    except OSError:
        return
    if size <= _TAIL_BYTES_START:
        yield path.read_text(encoding="utf-8", errors="replace"), True
        return
    window = _TAIL_BYTES_START
    while window < min(_TAIL_BYTES_MAX, size):
        with open(path, "rb") as fh:
            fh.seek(size - window)
            raw = fh.read()
        # The seek lands mid-line; that first fragment is not valid JSON.
        # Dropping it is correct, not lossy — the full line is still
        # present in any wider window.
        _, _, rest = raw.partition(b"\n")
        yield rest.decode("utf-8", errors="replace"), False
        window *= 4
    yield path.read_text(encoding="utf-8", errors="replace"), True


def _read_records(
    transcript_path: Path, min_records: int = _MIN_RECORDS
) -> list[tuple[str, str, list[str], list[str]]]:
    """Walk the JSONL transcript and return records.

    Each entry is ``(rec_type, text, tool_call_names, bash_commands)``.
    ``text`` may be empty if the record contains only tool_use blocks; in
    that case ``tool_call_names`` carries the tool names and
    ``bash_commands`` the Bash command strings. Records with neither text
    nor tool calls are skipped silently.

    Malformed lines and non-user/non-assistant record types are
    skipped silently.

    Reads from the END of the file, widening until ``min_records`` are
    found or the whole file has been read. See ``_tail_chunks``.
    """
    for chunk, is_whole_file in _tail_chunks(transcript_path, min_records):
        records = _parse_records(chunk)
        if len(records) >= min_records or is_whole_file:
            return records
    return []


def _parse_records(chunk: str) -> list[tuple[str, str, list[str], list[str]]]:
    """Parse JSONL text into records. Shared by whole-file and tail reads."""
    records: list[tuple[str, str, list[str], list[str]]] = []
    for line in chunk.split("\n"):
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
        is_assistant = rec_type == "assistant"
        tool_calls = _extract_tool_call_names(rec) if is_assistant else []
        commands = _extract_bash_commands(rec) if is_assistant else []
        if text or tool_calls:
            records.append((rec_type, text, tool_calls, commands))
    return records


def recent_turns_text(transcript_path: str | Path, max_turns: int = 6) -> str:
    """Return the concatenated text of the last ``max_turns`` conversation
    records (user + assistant), newest-last. Empty string on any failure.

    The exploration-recall surfacer was matching only the single latest
    prompt — which is often terse ("define real, I'll wait") and shares no
    surface words with the relevant entry's curated tags, so it stayed
    silent while prior writing on the exact topic sat unsurfaced (named
    2026-05-27). Matching the recent conversation window instead gives the
    tag-matcher the vocabulary that actually came up across the turns,
    without loosening the exact-tag precision. Fail-open: the surfacer is
    observational, never blocking.
    """
    p = Path(transcript_path)
    if not p.exists():
        return ""
    try:
        records = _read_records(p)
    except OSError:
        return ""
    texts = [text for (_rt, text, _tc, _cmd) in records if text]
    if not texts:
        return ""
    return "\n".join(texts[-max_turns:])


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
            text for rt, text, _tc, _cmd in records if rt == "assistant" and text
        )
        tool_calls = tuple(tc for rt, _t, tcs, _cmd in records if rt == "assistant" for tc in tcs)
        commands = tuple(cmd for rt, _t, _tc, cmds in records if rt == "assistant" for cmd in cmds)
        parts = [text for rt, text, _tc, _cmd in records if rt == "assistant" and text]
        return TurnTexts(
            last_assistant_text,
            "",
            "",
            tool_calls,
            commands,
            final_assistant_text=parts[-1] if parts else "",
        )

    last_user_text = records[last_user_idx][1]

    # Current turn: all assistant text + tool calls AFTER the last user record.
    # Empty text from tool-use-only records is filtered out of the join;
    # tool_calls_in_turn still captures those records' tool names.
    current_records = records[last_user_idx + 1 :]
    current_turn_parts = [
        text for rt, text, _tc, _cmd in current_records if rt == "assistant" and text
    ]
    last_assistant_text = "\n".join(current_turn_parts)
    tool_calls_in_turn = tuple(
        tc for rt, _t, tcs, _cmd in current_records if rt == "assistant" for tc in tcs
    )
    command_texts_in_turn = tuple(
        cmd for rt, _t, _tc, cmds in current_records if rt == "assistant" for cmd in cmds
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
            for rt, text, _tc, _cmd in records[prev_user_idx + 1 : last_user_idx]
            if rt == "assistant" and text
        ]
        prior_assistant_text = "\n".join(prior_parts)
    else:
        # Only one user record so far; everything assistant BEFORE it
        # is the prior turn (e.g. session-start agent text).
        prior_parts = [
            text for rt, text, _tc, _cmd in records[:last_user_idx] if rt == "assistant" and text
        ]
        prior_assistant_text = "\n".join(prior_parts)

    return TurnTexts(
        last_assistant_text,
        prior_assistant_text,
        last_user_text,
        tool_calls_in_turn,
        command_texts_in_turn,
        final_assistant_text=current_turn_parts[-1] if current_turn_parts else "",
    )
