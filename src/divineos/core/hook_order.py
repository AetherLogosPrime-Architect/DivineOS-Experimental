"""One table that orders every refusing hook surface, so a pile of notes becomes one voice.

Dad, 2026-11-04: the hooks are the biggest issue on his end. Aria's picture, his words
after: twenty people each handing over a sticky note, when it should be one person holding
twenty notes, all looked at until the list shrinks to what cannot be encoded.

THE FAULT THIS ANSWERS, seen on my own screen that morning: two or three Stop refusals arrive
in ONE message, concatenated in registration order, and nothing sequences them. One reply was
told to append only the room, do the step with a tool call, and append a summary, all at once.
Aria's freeze test found the same pile at PreToolUse: one hold names a remedy another refuses.

WHAT IS HERE. A row per surface: its event, its KIND of remedy, and a rank. The kind decides
first because that is what collided: a tool call goes before appended text, since the text can
be written in the same turn after it. Rank orders within a kind.

WHAT IT CANNOT DO. It does not repair a wrong note: an arbiter that orders false alarms serves
them politely. Surfaces outside the router (the standalone Stop commands) have no rows yet and
move in one at a time. A surface with no row is left exactly as it was and is reported by
``unlisted``; a test fails until it gets a row, so a new note cannot arrive unordered.
"""

from __future__ import annotations

from dataclasses import dataclass

# What the remedy IS. Order is the order they are asked in.
READ_LETTER = "read_letter"
WAIT = "wait"
TOOL_CALL = "tool_call"
APPEND_TEXT = "append_text"
OTHER = "other"
RECORD_ONLY = "record_only"

_KIND_ORDER = {
    k: i for i, k in enumerate((READ_LETTER, WAIT, TOOL_CALL, APPEND_TEXT, OTHER, RECORD_ONLY))
}


@dataclass(frozen=True)
class Row:
    name: str
    event: str
    kind: str
    rank: int


def _rows(event: str, kind: str, names: tuple[str, ...], start: int) -> list[Row]:
    return [Row(n, event, kind, start + i) for i, n in enumerate(names)]


ROWS: tuple[Row, ...] = tuple(
    # Stop: what the reply must do next, after it already reached him.
    _rows("Stop", TOOL_CALL, ("landed_claim", "waiting_claim"), 10)
    + _rows(
        "Stop",
        APPEND_TEXT,
        (
            "addressed_to_him",
            "voiced_family",
            "summary_room",
            "order_question",
            "no_fix_claim",
            "self_demotion_stop",
            "translation_floor",
            "repeated_reply",
            "his_standing_verdict",
        ),
        20,
    )
    + _rows("Stop", OTHER, ("close_reach", "compaction_reach"), 40)
    + _rows("Stop", RECORD_ONLY, ("hedge_audit", "theater_audit", "time_estimate"), 50)
    # PreToolUse: why this call was stopped. Reads first, then the rest.
    + _rows("PreToolUse", READ_LETTER, ("unread_letter",), 10)
    + _rows("PreToolUse", TOOL_CALL, ("require_briefing", "must_read", "degraded_detectors"), 20)
    + _rows(
        "PreToolUse",
        OTHER,
        (
            "his_words",
            "deletion_discipline",
            "no_verify_cost",
            "full_suite_by_hand",
            "compound_branch_change",
            "heredoc_escape",
            "cd_drift",
            "slashed_ref_path",
            "trial_in_days",
            "pr_merge_gate",
            "pr_merge_freshness",
            "pr_create_gate",
        ),
        30,
    )
)

_BY_KEY = {(r.event, r.name): r for r in ROWS}


def row_for(event: str, name: str) -> Row | None:
    return _BY_KEY.get((event, name))


def unlisted(event: str, names: list[str]) -> list[str]:
    """Names with no row for ``event``: notes nobody has ordered yet."""
    return [n for n in names if (event, n) not in _BY_KEY]


def _sort_key(event: str, item: tuple[str, str]) -> tuple[int, int]:
    row = row_for(event, item[0])
    if row is None:
        return (len(_KIND_ORDER), 0)
    return (_KIND_ORDER[row.kind], row.rank)


def first_and_rest(
    event: str, refusals: list[tuple[str, str]]
) -> tuple[tuple[str, str] | None, list[str]]:
    """The one refusal to say first, and the names of the others, in order.

    ``refusals`` are (surface name, reason). Surfaces with no row sort last.
    """
    if not refusals:
        return None, []
    ordered = sorted(refusals, key=lambda item: _sort_key(event, item))
    return ordered[0], [name for name, _ in ordered[1:]]
