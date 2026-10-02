"""What the harness wraps around his seat, in one place every reader of him uses.

Why it has to exist even after the harness's own stamp (Aria, measured
2026-09-24; Aether, second count the same day): the harness stamps some machine
notices as human. Across every transcript on this machine, six queue slips and
over a hundred turn records carry ``origin.kind == "human"`` and are nothing but
a ``<ci-monitor-event>`` block (two more are only a ``<system-reminder>``). The
stamp says who sat in the seat; the envelope says the words were not his.

ONE LIST, BECAUSE THERE WERE THREE. Searching before writing this found two
lists already, each missing what the other had: Aria's ``keeping_him._ENVELOPES``
(#507) knew the command blocks and not ``persisted-output``;
``correction_marker._HARNESS_ENVELOPE_RE`` knew ``persisted-output`` and an
unclosed envelope, and not the command blocks. The tags here are their union,
and an envelope that never closes is stripped to the end of the text as
``correction_marker`` already did. ``correction_marker`` reads this list now
(2026-09-24), which gave it the command blocks it lacked; Aria's
``keeping_him`` is still owed the same move.
"""

from __future__ import annotations

import re

_TAGS = (
    "task-notification",
    "system-reminder",
    "persisted-output",
    "ci-monitor-event",
    "local-command-stdout",
    "command-name",
    "command-message",
    "command-args",
)

# A block the harness wraps around a turn. A message that is only envelope is
# not him speaking -- it is the machine using his seat. An envelope with no
# closing tag runs to the end, because a truncated notice is still a notice.
_ENVELOPE = re.compile(
    r"<(" + "|".join(_TAGS) + r")\b[\s\S]*?(?:</\1>|\Z)",
    re.IGNORECASE,
)

# Openers belonging to the machine, not to him. Matched at the start only: he is
# perfectly capable of using the word "stop" in a sentence of his own, and a
# substring test would quietly eat it. (Aria, keeping_him.)
_MACHINE_OPENERS = (
    "stop hook feedback:",
    "userpromptsubmit hook",
    "pretooluse:",
    "posttooluse:",
    "caveat: the messages below",
    "this session is being continued from a previous conversation",
)


def remove_envelopes(text: str) -> str:
    """The text with the harness's wrappers cut out and its own lines kept, for
    readers that go on to read it line by line (blockquotes, fenced code)."""
    return _ENVELOPE.sub("", text or "")


def strip_envelopes(text: str) -> str:
    """His sentence with the harness's wrappers removed; empty when nothing is his."""
    return " ".join(_ENVELOPE.sub(" ", text or "").split()).strip()


def nothing_of_his(text: str) -> bool:
    """True when the words are only the machine's: all envelope, or a machine opener."""
    stripped = strip_envelopes(text)
    if not stripped:
        return True
    low = stripped.lower()
    return any(low.startswith(opener) for opener in _MACHINE_OPENERS)
