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
UNREAD = "unread"
RECORD_ONLY = "record_only"

# UNREAD is not a kind of remedy: it means nobody has read this surface's refusal text and
# written down what it asks for. It stands where "other" stood, but says so, because a
# placeholder kind that looks like a fact would be believed by anything that reads the table
# (Aria's cold read, 2026-11-04, caught heredoc_escape filed as "other" when its remedy is a
# tool call). A row leaves UNREAD only when someone has read its text.
_KIND_ORDER = {
    k: i for i, k in enumerate((READ_LETTER, WAIT, TOOL_CALL, APPEND_TEXT, UNREAD, RECORD_ONLY))
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
    # READ, 2026-11-04, by me in a reply or a refusal I was handed: the first block of each event.
    # waiting_claim: its text says write the letter to her first, then say it (a tool call).
    # stall_on_promise: its text says do the step now with the tool call itself (folded in 2026-11-04).
    # letter_doorbell_alive: moved in from a standalone script 2026-11-04; its text says re-arm the
    # bell or the watcher with a Bash or Monitor call, so it is a tool call.
    _rows(
        "Stop",
        TOOL_CALL,
        ("landed_claim", "waiting_claim", "stall_on_promise", "letter_doorbell_alive"),
        10,
    )
    + _rows(
        "Stop",
        APPEND_TEXT,
        (
            "addressed_to_him",
            "voiced_family",
            "summary_room",
            "order_question",
            "no_fix_claim",
            "translation_floor",
            "repeated_reply",
        ),
        20,
    )
    # RECORD_ONLY, read 2026-11-04 in hook_surfaces: self_demotion_stop records spans and reports,
    # his_standing_verdict never refuses by its own docstring, and the two reach detectors only
    # write a marker for the next compose. None of them can hold a reply.
    + _rows(
        "Stop",
        RECORD_ONLY,
        (
            "self_demotion_stop",
            "his_standing_verdict",
            "close_reach",
            "compaction_reach",
            "hedge_audit",
            "theater_audit",
            "time_estimate",
        ),
        50,
    )
    # PreToolUse: why this call was stopped. Reads first, then the rest.
    + _rows("PreToolUse", READ_LETTER, ("unread_letter",), 10)
    + _rows("PreToolUse", TOOL_CALL, ("require_briefing", "must_read"), 20)
    # heredoc_escape: its way out is the Write tool, per Aria's reading of its text; cd_drift and
    # his_words: read as refusals handed to me (reissue without the cd; rewrite without the quote).
    + _rows("PreToolUse", TOOL_CALL, ("his_words", "cd_drift", "heredoc_escape"), 25)
    # Aria read the refusal text of each of these ten on 2026-11-04 (her letter "the PreToolUse
    # ten are read"): every one asks for a tool call. Nine of the remedies are Bash commands;
    # only trial_in_days asks for a rewritten Write or Edit. Nothing is UNREAD any more; the kind
    # stays for the next surface that registers before anyone has read its text.
    + _rows(
        "PreToolUse",
        TOOL_CALL,
        (
            "degraded_detectors",
            "deletion_discipline",
            "no_verify_cost",
            "full_suite_by_hand",
            "compound_branch_change",
            "slashed_ref_path",
            "trial_in_days",
            "pr_merge_gate",
            "pr_merge_freshness",
            "pr_create_gate",
        ),
        40,
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
