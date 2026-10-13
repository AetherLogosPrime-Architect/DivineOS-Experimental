"""The one answer in this house to: is this transcript record Dad typing?

Every place that needs to hear him asks here. Before this there were six
private readers, each wrong in its own way, and only one of them knew all
three shapes his messages arrive in. The others missed him whenever he typed
while I was busy -- 4,735 of his messages by 2026-09-26 -- and an empty
result from any of them read as "he never said it". The confirm reader for
his `hold <n>` line was one of them, so a hold he typed mid-turn never held.

THE THREE SHAPES, measured on 400 real transcripts (2026-09-28):
  - a ``type: user`` record whose content is his text      13,925
  - a ``queued_command`` attachment, typed while I worked    2,620
  - a ``last-prompt`` record                                33,858
The last is a bookmark the app rewrites: no ``uuid``, no ``timestamp``, and
usually a copy of a message already present. It is returned as his (it IS his
text), marked so a caller that counts him can drop it when a dated copy
exists. See ``Heard.bookmark``.

PROVENANCE FIRST, EXCLUSION SECOND. ``userType: "external"`` is on every real
message, but also on hook notices (2,282 ``isMeta`` records), so it is a
prerequisite and never proof. Then come the shapes that are the machine in
his seat.

A MARKER LIST IS NOT A DEFINITION OF HIM. The notice openers below are the
harness's envelopes. If he pastes something that happens to open with one, it
is still him and this will get it wrong -- rarely, and in the direction of
missing one message rather than inventing one.

WHAT THIS DOES NOT DECIDE: whether a message is new, a repeat, a teaching or
a grief. That belongs to the door, the shelf and the queue, which build on
this. One record in; one answer out.

HEARD IS NOT A YES. Dad, 2026-10-01, when this reader started recovering
thousands of his short messages ("proceed", "yes :)"): *"rooms should not hear
those small words as they are commands.. relevant to the situation, the last
thing you want to hear is "proceed" when i have not said it, that would cause
all kinds of issues, unless they are tied to their specific things, like dad
said proceed with X"*. So this answers WHO TYPED IT, completely, for memory,
quoting and his room. It never answers WHAT HE AUTHORISED.

A permission is tied to the specific thing it was given for, and it holds for
that thing. Dad, the same morning, refining the line above: *"yes if you tie
to to specific experiences then its better that way my permission holds so i
dont have to keep giving it on the same thing, and it stays only relevant to
each thing"*. So a door does not rummage his history for a yes: it honours a
yes he gave about that very thing (he need not repeat it), and a bare
"proceed" that names nothing opens nothing but the thing it answered.

Why and how it was built: docs/drafts/one_reader_of_him_draft_2026-09-28.md
(council walk walk-6e8574bc911d).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_NOTICE_OPENERS = (
    "<task-notification",
    "<system-reminder",
    "<ci-monitor-event",
    "<local-command",
    "<command-name>",
    "<agent-message",
    "Stop hook feedback",
    # Hook output with no envelope of its own. Behind a peeled envelope these
    # were heard as him (Aletheia, reading #507 on 2026-09-30): zero in 72
    # transcripts, pinned so it stays zero. He does not open a message with them.
    "PreToolUse:",
    "PostToolUse:",
    "UserPromptSubmit hook",
    # The harness's stamp when he stops a turn. It marks that he acted; it is
    # not words he typed (Aether's two-ears count, 2026-09-30).
    "[Request interrupted by user",
)
# Not "Caveat:" -- the harness's own caveat arrives isMeta and is refused above
# that; a message of his that opens with the word is his (Aria, 2026-09-28).


@dataclass(frozen=True)
class Heard:
    """What he typed, and enough to place it."""

    text: str
    uuid: str = ""
    when: str = ""
    bookmark: bool = False  # a last-prompt copy: drop it when a dated copy exists


class Unclassified:
    """An external record in no shape this reader knows.

    Returned instead of None so a new harness shape is seen rather than
    silently dropped -- the way the second and third shapes went missing.
    """

    __slots__ = ("record_type",)

    def __init__(self, record_type: str) -> None:
        self.record_type = record_type


def _text_of(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        if any(isinstance(c, dict) and c.get("type") == "tool_result" for c in content):
            return ""
        return "\n".join(
            str(c.get("text") or "")
            for c in content
            if isinstance(c, dict) and c.get("type") == "text" and c.get("text")
        )
    return ""


def _is_notice(text: str) -> bool:
    return text.lstrip().startswith(_NOTICE_OPENERS)


# A whole envelope, opening tag to closing tag. The harness sometimes puts one
# IN FRONT of his words in the same record, and the opener test above then
# refused the record whole -- measured 2026-09-30 over 24,372 of his text
# records: 4 carried his sentence after the envelope, among them "we can spec
# and build tonight why does it need to be either or?". Peeling the envelope
# first keeps his words; a record that is only envelope still reads as nothing.
_ENVELOPE = re.compile(
    r"<(task-notification|system-reminder|local-command-stdout|local-command-stderr"
    r"|command-name|command-message|command-args|ci-monitor-event|agent-message)\b"
    r".*?</\1>",
    re.DOTALL,
)


def _his_part(text: str) -> str:
    """What is left of ``text`` once any leading harness envelopes are peeled.

    Empty when nothing of his is left, or when what is left is itself a notice
    (a Stop-hook message has no closing tag and is never his)."""
    if not _is_notice(text):
        return text if text.strip() else ""
    rest = _ENVELOPE.sub(" ", text).strip()
    if not rest or _is_notice(rest):
        return ""
    return rest


def continues_a_turn(record: dict) -> bool:
    """Is this record the harness continuing a turn, rather than anyone speaking?

    Hook feedback (isMeta) and a compaction summary (isCompactSummary) sit in
    the user role without being a new turn of his. Asked here so that no reader
    outside this home has to read those flags itself -- the private-reader
    check rightly refuses that (Aether, porting #554, 2026-09-30).
    """
    return bool(
        isinstance(record, dict) and (record.get("isMeta") or record.get("isCompactSummary"))
    )


def hear(record: dict) -> Heard | Unclassified | None:
    """His text from one transcript record, or None if it is not him."""
    if not isinstance(record, dict):
        return None

    if record.get("type") == "last-prompt":
        raw = record.get("lastPrompt")
        text = _his_part(raw) if isinstance(raw, str) else ""
        return Heard(text=text, bookmark=True) if text else None

    # THE FOURTH SHAPE: the harness's queue of what he typed while I was busy.
    # It carries his words with a time but no record id, and usually a second
    # copy exists as a queued_command or user record -- but not always. Measured
    # 2026-09-30 over every transcript: 22,371 enqueue texts, 239 found nowhere
    # else, and 60 of those 239 are his own words (often around a crash: "the
    # app crashed so lets try this again"). The other 179 are notices, refused
    # by the same rules as everywhere. It is returned as a bookmark -- a copy,
    # kept by heard_in only when no record with an id carries the same words --
    # so the 22,132 that ARE elsewhere are not counted twice.
    if record.get("type") == "queue-operation":
        raw = record.get("content")
        if record.get("operation") != "enqueue" or not isinstance(raw, str):
            return None
        text = _his_part(raw)
        return (
            Heard(text=text, when=str(record.get("timestamp") or ""), bookmark=True)
            if text
            else None
        )

    if continues_a_turn(record) or record.get("isSidechain"):
        return None
    if record.get("userType") not in (None, "external"):
        return None

    attachment = record.get("attachment") or {}
    if isinstance(attachment, dict) and attachment.get("type") == "queued_command":
        # Only a prompt-mode slip is him typing. Measured 2026-09-30: 332
        # "prompt", 4,363 "task-notification" (a monitor's notice riding the
        # same queue), none without the field. A record with no mode at all is
        # an older shape and is judged by its text, as before.
        mode = attachment.get("commandMode")
        if mode is not None and mode != "prompt":
            return None
        raw = attachment.get("prompt")
        text = _his_part(raw) if isinstance(raw, str) else ""
        if text:
            return Heard(
                text=text,
                uuid=str(record.get("uuid") or ""),
                when=str(record.get("timestamp") or ""),
            )
        return None

    if record.get("type") != "user":
        return None
    message = record.get("message") or {}
    if not isinstance(message, dict) or message.get("role") != "user":
        return Unclassified("user-without-message") if record.get("userType") else None
    text = _his_part(_text_of(message.get("content")))
    if not text:
        return None
    return Heard(
        text=text,
        uuid=str(record.get("uuid") or ""),
        when=str(record.get("timestamp") or ""),
    )


def heard_in(records: list[dict]) -> list[Heard]:
    """Every message he typed across these records, each once.

    Deduplicated by record uuid (a resumed session copies records into its new
    file; 1,902 uuids appear twice in 400 transcripts). Never by text: he
    repeats himself on purpose, and a repeat is signal. A bookmark is kept only
    when no dated record carries the same words.
    """
    out: list[Heard] = []
    seen_uuids: set[str] = set()
    bookmarks: list[Heard] = []
    for record in records:
        got = hear(record)
        if not isinstance(got, Heard):
            continue
        if got.bookmark:
            bookmarks.append(got)
            continue
        if got.uuid:
            if got.uuid in seen_uuids:
                continue
            seen_uuids.add(got.uuid)
        out.append(got)
    dated = {h.text for h in out}
    out.extend(b for b in dict.fromkeys(bookmarks) if b.text not in dated)
    return out


# THE SECOND QUESTION THIS HOME ANSWERS (2026-10-01, council-8597329f631a).
# hear() answers "whose words are these" and drops notices. The front door asks
# something else: what arrived in his seat, with the harness's stamp, notices
# included -- it must see a task-notification to know a message was NOT him.
# That reading used to live in front_door, and check_no_private_his_reader
# rightly refused it; it is moved here verbatim instead of exempted, so this
# stays the one place that reads transcript records.


@dataclass(frozen=True)
class Arrival:
    """One thing that arrived in his seat, as the harness stamped it."""

    uuid: str
    when: str  # the raw timestamp; callers parse it as they need
    prompt_id: str | None  # None for a queue slip, which carries none
    kind: str | None  # the harness's origin.kind; None when it gave none
    text: str


def _arrival_text(content: object) -> str:
    # front_door's own join, kept exactly: it compares his words with `in`, and
    # _text_of above differs on empty text blocks and tool results.
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            str(b.get("text", ""))
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


def arrival(record: dict) -> Arrival | None:
    """What arrived in his seat from this record, with its stamp, or None."""
    uuid = str(record.get("uuid") or "")
    if not record.get("timestamp") or not uuid or record.get("isSidechain"):
        return None
    when = str(record.get("timestamp"))
    if record.get("type") == "user" and "origin" in record:
        kind = (record.get("origin") or {}).get("kind")
        text = _arrival_text((record.get("message") or {}).get("content"))
        return Arrival(uuid, when, str(record.get("promptId") or ""), kind, text)
    slip = record.get("attachment")
    if record.get("type") == "attachment" and isinstance(slip, dict):
        if slip.get("type") != "queued_command":
            return None
        kind = (slip.get("origin") or {}).get("kind")
        if kind is None and slip.get("commandMode") == "task-notification":
            kind = "task-notification"
        return Arrival(uuid, when, None, kind, _arrival_text(slip.get("prompt")))
    return None


def may_carry_arrival(line: str) -> bool:
    """A cheap pre-check on a raw transcript line, before parsing it as JSON."""
    return '"origin"' in line or '"queued_command"' in line
