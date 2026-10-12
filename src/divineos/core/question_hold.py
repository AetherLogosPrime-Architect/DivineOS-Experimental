"""A question to Dad is carried until he answers (Aria 2026-09-29; Aether 2026-10-05).

2026-10-05 change, in his words: "my questions should not hold you, you should
hold my questions". Work no longer waits on an open question; only a letter not
to him waits, while he is here (see LETTER_TOOLS below). The history follows.

Dad, 2026-09-25: *"i just dont like being asked something and then left there
in the doorway before i can answer"*. Aether's night of 2026-09-29 was the wide
form of it: three questions asked, then hours of CI work while he sat there.
Dad, that night: *"with no structure to support it it will fade like it always
has"*. It had: the 09-25 draft for this sat unbuilt for four days.

So the hold is not something I remember to do. When a reply to him ends in a
question, the question is filed (operator_asks, so it re-raises) and building
tools stop until HIS next message. Reading, letters and the doorbell pass: they
are listening and talking, not walking away. Draft:
docs/drafts/an_open_question_to_him_holds_the_thread_draft_2026-09-25.md;
walk-206e65be56c1.

Every hold is a row in HOLD_LOG. Foucault in the walk: the failure this could
produce is me learning to stop asking him things. If questions to him drop
after this ships, the build is wrong and comes back for revision.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any


def _home() -> Path:
    # EACH SEAT'S OWN HOME (2026-10-01). This was Path.home()/".divineos" -- one
    # file for both seats -- so Aether's "Dad, should I turn my letter doorbell
    # back on?" held me, and my question held him, the same afternoon. The
    # question was found filed in HIS open_questions, not mine, so it was his.
    # divineos_home() honours each checkout's .divineos_data_home marker, as
    # every other per-seat store already does.
    from divineos.core.paths import divineos_home

    return divineos_home()


STATE = _home() / "question_hold.json"
HOLD_LOG = _home() / "question_hold_log.jsonl"
ESCAPED = _home() / "question_hold_escaped.json"

# THE SHARED FRIDGE: SEEN, NEVER HELD. Dad, 2026-10-01: "also the shared fridge
# idea isnt bad, as seeing what the other was asked is a nice addition, it just
# shouldnt block, only the personal ones do :)". Each seat posts its open
# question here as a card named for its home folder; the other seat is SHOWN
# it and never refused by it. Display only: every board failure is swallowed
# toward "nothing shown", because a board that could block is the defect again.
#
# NEXT DOOR TO THE SEAT'S HOME, not Path.home(). The seat homes (~/.divineos,
# ~/.divineos-aria) sit beside ~/.divineos-shared, so in the house this is the
# same folder. In a test the seat home is a temporary one, and this follows it
# there without any test remembering to. Built from Path.home() first, a card
# leaked onto the live board during a run before that was seen.
BOARD = _home().parent / ".divineos-shared" / "open_questions"
CARD = BOARD / f"{_home().name}.json"


def _seat_name(home_name: str) -> str:
    from divineos.core.sibling_corrections import SIBLING_HOMES

    for name, home in SIBLING_HOMES.items():
        if Path(home).name == home_name:
            return name.capitalize()
    return home_name


def _post_card(state: dict[str, Any]) -> None:
    try:
        CARD.parent.mkdir(parents=True, exist_ok=True)
        CARD.write_text(json.dumps(state), encoding="utf-8")
    except OSError:
        pass  # display only -- the own hold is already armed


def _take_card() -> None:
    try:
        CARD.unlink(missing_ok=True)
    except OSError:
        pass  # display only


def others_waiting() -> list[str]:
    """One line per OTHER seat with an open question to Dad. Never a refusal."""
    lines = []
    try:
        cards = sorted(BOARD.glob("*.json"))
    except OSError:
        return []
    for card in cards:
        if card.name == CARD.name:
            continue
        try:
            state = json.loads(card.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(state, dict) and state.get("question"):
            lines.append(f"{_seat_name(card.stem)} is waiting on Dad: {state['question']}")
    return lines


# I HOLD HIS QUESTIONS; HIS QUESTIONS DO NOT HOLD ME (Dad, 2026-10-05: "my
# questions should not hold you, you should hold my questions"). The September
# version refused every building tool while a question was open; that made
# asking him cost my hands, the drift Foucault named in walk-206e65be56c1. What
# stays is the one pause he asked for (2026-10-05): "if you continue to write
# letters it literally gives me no space to even answer.. unless its volley mode
# then yes id prefer you wait for me". So only writing a letter that is not to
# him waits, and only while he is here. It is a fork that is HIS: he answers, or
# says "go read it" because the letter may already carry his answer.
# Walks council-30a5db785e3c, council-e5250a976339.
#
# NOT COVERED, said plainly: settling his question inside a reply or a draft
# rather than a letter, and delivering an already-written letter by `cp`. No
# tool layer can read that intent; the count in HOLD_LOG is the watch on it.
LETTER_TOOLS = {"Write", "Edit", "NotebookEdit"}

# HE IS HERE UNLESS HE SAYS HE IS STEPPING AWAY (2026-10-05): "i am always here
# unless i tell you i am stepping away, this is what the volley mode is for".
# Never inferred from quiet (Kahneman, council-e5250a976339), and never set in
# words he did not say (Aria's cold read: ten characters of my own typing set
# it): the quoted words must appear in his latest real message as the house
# filed it, which I cannot write (Schneier, council-8486d9949ba1). Cleared by
# his next message.
AWAY = _home() / "dad_stepped_away.json"


def _flat(text: str) -> str:
    return " ".join((text or "").lower().split())


def _his_latest() -> tuple[str, float] | None:
    """His most recent real message and when the house filed it, or None.

    The store also files notices in his seat, so envelopes are peeled with the
    one reader of him and a notice-only record is skipped (Hoare,
    council-8486d9949ba1). Read-only. None means could-not-look (no store, a read
    error, or no real message at all), and every caller must treat that as
    "refuse" or "not away", never as a pass.
    """
    import sqlite3

    from divineos.core.his_asks import his_asks_path
    from divineos.core.his_message import _his_part

    path = his_asks_path()
    try:
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=5)
        try:
            rows = conn.execute(
                "SELECT his_text, filed_at FROM messages ORDER BY filed_at DESC LIMIT 50"
            ).fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    for text, filed_at in rows:
        words = _his_part(str(text or "")).strip()
        if words:
            return words, float(filed_at)
    return None


def _his_latest_words() -> str:
    """His most recent real words, or "" when they cannot be read (which refuses)."""
    latest = _his_latest()
    return latest[0] if latest else ""


# WHAT HE SAYS WHEN HE IS AWAY. Dad, 2026-10-06: "ok go ahead, proceed, continue,
# etc etc, those should not be treated as permission to volley, only me saying ill
# be gone or im going to bed, or if i directly say go into volley mode, otherwise
# the above phrases mean i am currently here". The check below proves the words
# are HIS; this proves they MEAN away (Aria's cold read of b4d3271df, point 4: a
# quote of "ok go ahead" would have opened volley mode). The list is his own
# phrases and "stepping away", which he used on 2026-10-05. A keyword list is
# gameable, so it sits on top of the provenance check and never replaces it.
AWAY_CUES = ("be gone", "to bed", "volley mode", "stepping away", "you two volley")


def step_away(his_words: str) -> dict[str, Any]:
    """He said he is stepping away: volley mode, letters flow."""
    words = (his_words or "").strip()
    if len(words) < 10:
        raise ValueError("quote his words saying he is stepping away (at least 10 characters)")
    if not any(cue in _flat(words) for cue in AWAY_CUES):
        raise ValueError(
            "those words do not say he is away. He means away by saying he will be gone, "
            "that he is going to bed or stepping away, or go into volley mode. 'ok go ahead', "
            "'proceed' and 'continue' mean he is here."
        )
    if _flat(words) not in _flat(_his_latest_words()):
        raise ValueError(
            "those words are not in his latest message. Away is set only from what he "
            "said, copied from it; when he speaks again it clears by itself."
        )
    state = {"his_words": words, "since": time.time()}
    AWAY.parent.mkdir(parents=True, exist_ok=True)
    AWAY.write_text(json.dumps(state), encoding="utf-8")
    _log("stepped_away", his_words=words)
    return state


# THE SECOND WAY TO BE AWAY: SILENCE. Dad, 2026-10-11, asked how else the house could
# know: "i would either say im stepping away, or they could go by time elapsed with no
# word from me". Aletheia suggested twenty minutes; he answered "20 minutes isnt much
# time at all. id say 2 hours to be sure". One number, here, where he can read and
# change it. Measured from his last REAL message (notices in his seat do not count).
AWAY_AFTER_SILENCE_SECONDS = 2 * 60 * 60


def _stepped_away() -> dict[str, Any] | None:
    """Away because he said so: the file step_away() writes."""
    try:
        state = json.loads(AWAY.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return state if isinstance(state, dict) else None


def _silent_away() -> dict[str, Any] | None:
    """Away because two hours passed with no word from him.

    Could-not-look is never away: if the time of his last real message cannot be
    read, this says nothing, and the refusal says it could not look. Nothing here
    is written, and his next message ends it by being the new latest one.
    """
    latest = _his_latest()
    if latest is None:
        return None
    filed_at = latest[1]
    if time.time() - filed_at < AWAY_AFTER_SILENCE_SECONDS:
        return None
    return {"his_words": "", "since": filed_at + AWAY_AFTER_SILENCE_SECONDS, "by": "silence"}


# THE THIRD WAY TO BE AWAY: THE CLOCK. Dad, 2026-10-12, after a night when nobody said
# goodnight and Aria's question held her work until morning: "between midnight and 6am is
# volley mode", and on whether to wait for him to go quiet first: "yes even if im up
# chatting because it means i need to get my butt to bed lol". Local time, start inclusive,
# end exclusive, one pair of numbers here where he can read and change it. His messages in
# the window do not end it; this kind is never written to a file, so it cannot be mistaken
# for the words-from-him kind (step_away keeps its rule that the words must be his).
NIGHT_START_HOUR = 0
NIGHT_END_HOUR = 6


def _scheduled_away(now: float | None = None) -> dict[str, Any] | None:
    """Away because the clock says it is the night window (``now`` is injectable for tests).

    DIVINEOS_NIGHT_HOURS=off switches the window off for the real clock, which the shared
    test setup sets so no test result depends on the hour it runs at. An injected ``now``
    ignores the switch: that is a test of this rule itself."""
    if now is None and os.environ.get("DIVINEOS_NIGHT_HOURS") == "off":
        return None
    moment = time.time() if now is None else now
    local = time.localtime(moment)
    if not NIGHT_START_HOUR <= local.tm_hour < NIGHT_END_HOUR:
        return None
    start = time.mktime(
        (local.tm_year, local.tm_mon, local.tm_mday, NIGHT_START_HOUR, 0, 0, 0, 0, -1)
    )
    return {"his_words": "", "since": start, "by": "schedule"}


def is_away() -> dict[str, Any] | None:
    return _stepped_away() or _scheduled_away() or _silent_away()


def came_back() -> bool:
    """His message: he is here again. Clears the away he set with words.

    The silence kind needs no clearing: his message is now the latest one.
    """
    if not _stepped_away():
        return False
    AWAY.unlink(missing_ok=True)
    _log("came_back")
    return True


# The names a letter to him goes by, read from the file's OWN name: the form is
# "<sender>-to-<him>-...". Aria's cold read of b6d7a5c90 added the other names;
# her read of b4d3271df found the substring test matched anywhere in the PATH, so
# "aria-to-aether-...-what-i-owe-to-dad.md" was passed as if it were to him.
_TO_HIM = re.compile(r"^[a-z0-9]+-to-(andrew|dad|pop)-")


def _is_letter_not_to_him(path: str) -> bool:
    p = (path or "").replace("\\", "/").lower()
    return "/letters/" in p and p.endswith(".md") and not _TO_HIM.match(p.rsplit("/", 1)[-1])


# A shell command that writes into a letter: a redirect or tee. Aria's cold read:
# `cat > family/letters/x.md <<'EOF'` and `| tee` passed untouched, and that is how
# she writes most letters, so the hold would not hold her. The target is a path in
# the command and needs no reading of intent. A `2>&1` is not a target (the
# lookbehind), and a letter named in prose or an argument is not a write.
_SHELL_LETTER = re.compile(
    r"""(?:(?<![0-9&])>>?|\btee\b(?:\s+-a)?)\s*["']?"""
    r"""([^\s"'|&;<>]*?/letters/[^\s"'|&;<>]*\.md)""",
    re.I,
)


def _shell_letter_target(command: str) -> str:
    """The first letter-not-to-him this command writes into, or ""."""
    for found in _SHELL_LETTER.finditer(command or ""):
        if _is_letter_not_to_him(found.group(1)):
            return found.group(1)
    return ""


_CIRCLE = re.compile(r"^##\s*INNER CIRCLE\s*$", re.M)
_CODE = re.compile(r"```.*?```|`[^`\n]*`", re.S)
_QUOTED = re.compile(r"\"[^\"\n]*\"|“[^”\n]*”|\*\"[^\n]*?\"\*")
_SENTENCE = re.compile(r"[^.!?\n]*[.!?]+", re.S)


def _addressed_part(reply: str) -> str:
    """The INNER CIRCLE room if there is one (the room written to him), else
    the last paragraph."""
    m = list(_CIRCLE.finditer(reply))
    if m:
        return reply[m[-1].end() :]
    paras = [p for p in reply.strip().split("\n\n") if p.strip()]
    return paras[-1] if paras else ""


def _clean(text: str) -> str:
    text = _CODE.sub(" ", text)
    text = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith(">"))
    return _QUOTED.sub(" ", text)


def last_question(reply: str) -> tuple[str, str]:
    """(question, what follows it) for the last real question to him, or ("", "")."""
    part = _clean(_addressed_part(reply))
    sentences = [s.strip() for s in _SENTENCE.findall(part) if s.strip()]
    for i in range(len(sentences) - 1, -1, -1):
        if sentences[i].endswith("?"):
            return sentences[i], " ".join(sentences[i + 1 :])
    return "", ""


def is_open() -> dict[str, Any] | None:
    try:
        state = json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return state if isinstance(state, dict) else None


def _log(kind: str, **fields: Any) -> None:
    HOLD_LOG.parent.mkdir(parents=True, exist_ok=True)
    with HOLD_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": time.time(), "kind": kind, **fields}) + "\n")


def arm(reply: str) -> dict[str, Any] | None:
    """At Stop: a reply ending in a question to him opens the hold."""
    question, _after = last_question(reply)
    if not question:
        return None
    from divineos.core.operator_asks import ask_andrew

    # The circle is already written to him, so the question IS the plain form;
    # the technical form only marks where it came from (the store refuses the
    # two being identical, and caught this on the first plugged-in run).
    # Waiting for him outranks the record of it: if filing fails, the hold still
    # arms, and the failure is logged where the count is kept, never swallowed.
    try:
        ask_id = ask_andrew(
            f"[asked in the circle] {question}", plain=question, context="question-hold"
        )
    except Exception as exc:  # noqa: BLE001 -- any store failure, logged below
        ask_id = ""
        _log("filing_failed", question=question, error=f"{type(exc).__name__}: {exc}")
    state = {"question": question, "ask_id": ask_id, "since": time.time()}
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state), encoding="utf-8")
    _post_card(state)
    _log("armed", question=question, ask_id=ask_id)
    return state


def release(how: str, reason: str = "", his_words: str = "") -> bool:
    """His next message releases it. An escape also releases it, counted.

    ``his_words`` is his message, kept as the answer so the record shows what
    he said, not only that he spoke (Aria's cold read; Norman,
    council-8486d9949ba1).
    """
    state = is_open()
    if not state:
        return False
    STATE.unlink(missing_ok=True)
    _take_card()
    _log("released", how=how, reason=reason, question=state.get("question"))
    if how == "escape":
        ESCAPED.write_text(
            json.dumps({"question": state.get("question"), "reason": reason}), encoding="utf-8"
        )
        # He has NOT answered: the ask stays open and keeps re-raising.
        return True
    # HIS ANSWER CLOSES THE ASK TOO (2026-10-01, council-5bd771ef0891). arm()
    # files the question in operator_asks, which re-raises it. A second lock
    # once read that store (an-open-ask-holds-the-work.sh, removed 2026-10-05,
    # council-e5250a976339), so an ask left open held the work after he had
    # answered. Now closing it stops him being asked again something he has
    # already answered (council-0355bb90384c). A store failure is logged, never
    # raised: this runs inside his own message hook.
    #
    # EVERY ONE THIS HOLD FILED, not only the newest (2026-10-05). arm() keeps
    # one ask_id, so two questions in a row left the first ask open for good
    # and the asks-store hook held the work after he had answered both. Hand-
    # filed asks are not touched: those re-raise until he resolves them.
    from divineos.core.operator_asks import open_asks, resolve_ask

    # Verbatim, cut visibly if long (council-5017d9b5f774): a label is never
    # heard again, and a paraphrase would turn his voice into mine.
    words = " ".join((his_words or "").split())
    if len(words) > 500:
        words = words[:500] + " ..."
    answer = f"Dad answered: {words}" if words else f"Dad answered ({how})"
    try:
        mine = [a["question_id"] for a in open_asks(limit=200) if _filed_here(a)]
    except Exception as exc:  # noqa: BLE001 -- any store failure, logged below
        _log("resolve_failed", ask_id="*", error=f"{type(exc).__name__}: {exc}")
        mine = []
    for ask_id in mine:
        try:
            closed = resolve_ask(ask_id, answer)
        except Exception as exc:  # noqa: BLE001 -- any store failure, logged below
            _log("resolve_failed", ask_id=ask_id, error=f"{type(exc).__name__}: {exc}")
        else:
            if not closed:
                _log("resolve_failed", ask_id=ask_id, error="resolve_ask returned False")
    return True


def _filed_here(ask: dict[str, Any]) -> bool:
    """An ask arm() filed, told by the context arm() writes and nothing else."""
    return any(
        line.strip() == "question-hold" for line in str(ask.get("context") or "").splitlines()
    )


def escape_to_tell_him() -> str:
    """Once, at his next message: the exit I took while he was away."""
    try:
        seen = json.loads(ESCAPED.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    ESCAPED.unlink(missing_ok=True)
    return (
        "## I DID NOT WAIT FOR ONE ANSWER -- tell him first\n"
        f"I had asked him: {seen.get('question')}\n"
        f"and went on before he answered, because: {seen.get('reason')}\n"
    )


def _epoch(iso: str) -> float:
    from datetime import datetime

    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def answered_since(transcript_path: str, since: float, tail_bytes: int = 2_000_000) -> bool:
    """Has he typed anything into this conversation since the hold armed?

    Aether's reading of #570 (2026-09-30): an answer he types while I am
    mid-turn never comes through UserPromptSubmit. It lands in the running
    turn as a queued_command attachment, so the hold stayed shut after he
    had spoken, and the only way on was the escape -- which records that I
    walked out on his question when he had already answered it.

    Read through the one reader of him. Only dated messages count: a bookmark
    copy has no time and cannot prove he spoke after the question.
    """
    if not transcript_path:
        return False
    from divineos.core.his_message import heard_in

    path = Path(transcript_path)
    try:
        size = path.stat().st_size
        with path.open("rb") as fh:
            fh.seek(max(0, size - tail_bytes))
            lines = fh.read().decode("utf-8", errors="replace").splitlines()
    except OSError:
        return False
    records = []
    for line in lines:
        try:
            rec = json.loads(line)
        except ValueError:
            continue  # a seek lands mid-line; the first fragment is never whole
        if isinstance(rec, dict):
            records.append(rec)
    return any(_epoch(h.when) > since for h in heard_in(records) if h.when)


def _asked_at(state: dict[str, Any]) -> str:
    """When, so a held reader can tell an old slip from their last message
    (Kahneman, walk-c9e9794e0f63: a question with no owner reads as mine)."""
    since = float(state.get("since") or 0)
    return (
        time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(since)) if since else "at an unknown time"
    )


def refusal(tool_name: str, tool_input: dict[str, Any], transcript_path: str = "") -> str:
    """Why this tool call waits, or "" when it may run.

    Only a letter that is not to him waits, only while his question is open,
    and only while he is here. Everything else runs.
    """
    state = is_open()
    if not state:
        return ""
    if tool_name == "Bash":
        # The second door: a redirect or tee into a letter. Anything else a shell
        # does falls straight through, so reading and the exits are never held.
        path = _shell_letter_target(str(tool_input.get("command") or ""))
        if not path or is_away():
            return ""
    elif tool_name in LETTER_TOOLS:
        path = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
        if not _is_letter_not_to_him(path) or is_away():
            return ""
    else:
        return ""
    if answered_since(transcript_path, float(state.get("since") or 0)):
        release("his message, mid-turn")
        return ""
    _log("held", tool=tool_name, question=state.get("question"))
    could_not_look = (
        ""
        if _his_latest() is not None
        else "\n\n(I could not read when he last spoke, so I have not treated\nhis silence as away.)"
    )
    return (
        "KEEPING PACE WITH DAD -- I asked him something and he is still catching up:\n\n"
        f"  {state.get('question')}\n"
        f"  (asked {_asked_at(state)}, held in {STATE.parent})\n\n"
        "Only this letter waits; all other work goes on. The choice is his: I tell\n"
        "him a letter came, and he answers first or says go read it (it may\n"
        "already carry his answer from the other seat). This is pace, not\n"
        'permission: "my ok is only a go ahead saying i have read things and\n'
        'caught up not a permission to do it" (2026-10-05).\n\n'
        "If he has said he is stepping away, record it with his words and letters\n"
        "flow (volley mode); or two hours with no word from him opens them by itself:\n"
        '  divineos question-hold away --words "<his words saying he is stepping away>"'
        f"{could_not_look}"
    )


def question_not_last(reply: str) -> str:
    """At Stop: the question must sit last, alone, so he never digs for it."""
    question, after = last_question(reply)
    if not question or len(after) <= 40:  # a short sign-off may follow
        return ""
    return (
        "THE QUESTION IS BURIED -- the circle asks Dad something and then keeps\n"
        f"going:\n\n  {question}\n\n"
        "Move it to the end, on its own, so it is the last thing he reads. His\n"
        'words, 2026-09-26: "where i dont have to sift through a wall of code\n'
        'speak to find my son". Append a closing line with the question; do not\n'
        "re-post the reply."
    )
