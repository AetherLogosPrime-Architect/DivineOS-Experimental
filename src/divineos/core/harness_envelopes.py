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
    "agent-message",
)

# The tags that mean the harness started a turn, or wrote into one, and nobody sat in the seat.
# A SUBSET of _TAGS on purpose: a slash command arrives as <command-name>, and that IS him
# typing. This is the one list the gates that ask "was that message him?" read (the question hold,
# the room gate, the table). They each kept their own copy until 2026-10-27, and the copies drifted:
# two Stop gates did not know <ci-monitor-event>, so a CI notice read to them as him coming back
# (Aether, #683).
_NOTICE_TAGS = ("task-notification", "system-reminder", "ci-monitor-event", "agent-message")
NOTICE_OPENERS = tuple("<" + tag for tag in _NOTICE_TAGS)


def opens_with_notice(text: str) -> bool:
    """Whether a message OPENS with one of the harness's notices. At the start only: he can
    mention the tag in a sentence of his own and still be him."""
    return (text or "").lstrip().startswith(NOTICE_OPENERS)


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
