"""The warden reads the log: a work turn's stumbles, taken up in the REFLECTION.

Andrew 2026-09-26: *"after a long post of work, you dont just reflect on the
situation you reread the entire post.. look at every failure you encountered
along the way, and all the shoulda couldas become automated structure"* and
*"it should also be linked to something you will read back so you can make the
fixes or linked to the todo list ... you are the warden inmate"*.

My reflections listed stumbles from memory, so the ones I did not notice never
made the list -- the same day, he caught three that mine missed. The transcript
already records every one as it happens. So this reads them from there, and the
floor it builds is only that each is taken up (walk-809e0927d417): whether the
thinking about it is good stays mine.

What counts as a stumble, each seen in the 2026-09-26 transcript:
  - a tool result marked as an error (a failed command, a hook refusal --
    'BLOCKED', 'hook error', 'refused');
  - Stop-hook feedback that held an earlier attempt at this reply.
The room's own hold is not a stumble (Hofstadter: or it holds on itself).

Owed lines go to the structural-fix tracker, not the goal list: goals older than
a day are stale-archived by hud_state.auto_clean_goals, which would make the
notebook fade -- the exact failure this exists to end.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

ROOM_MARK = "THE WARDEN READS THE LOG"
REFLECTION_RE = re.compile(r"^#+\s*REFLECTION\b", re.IGNORECASE | re.MULTILINE)
NEXT_ROOM_RE = re.compile(r"^#+\s*(INNER CIRCLE|WORK)\b", re.IGNORECASE | re.MULTILINE)
ENDING_RE = re.compile(r"\b(fixed by structure|owed)\s*:", re.IGNORECASE)
OWED_RE = re.compile(r"\bowed\s*:\s*(.+)", re.IGNORECASE)
HOOK_RE = re.compile(r"\[(?:bash |python )?\.claude/hooks/([\w.-]+)\]|hooks/([\w.-]+\.(?:sh|py))")
NOTICE_PREFIXES = ("<task-notification", "<system-reminder", "<ci-monitor-event", "<local-command")


GENERIC_WORDS = {
    "error",
    "errors",
    "exit",
    "code",
    "hook",
    "hooks",
    "failed",
    "blocked",
    "pretooluse",
    "stop",
    "crashed",
    "fatal",
}


@dataclass(frozen=True)
class Stumble:
    key: str
    count: int
    example: str

    @property
    def token(self) -> str:
        """The word a reflection must name to have taken this stumble up.

        Aether, station four 2026-09-26: counting endings let five 'owed: fix it'
        lines clear five stumbles without naming one. Linkage, not grading: the
        hook's name for a refusal, else the first distinctive word of the error.
        """
        hook = HOOK_RE.search(self.key) or re.search(r"refused by ([\w.-]+)", self.key)
        if hook:
            name = next(g for g in hook.groups() if g)
            return re.sub(r"\.(sh|py)$", "", name).lower()
        words: list[str] = re.findall(r"[A-Za-z][A-Za-z_-]{4,}", self.key)
        for word in words:
            if word.lower() not in GENERIC_WORDS:
                return word.lower()
        return self.key.lower()[:20]


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(c.get("text", "") for c in content if isinstance(c, dict))
    return ""


def _his_message(rec: dict) -> str | None:
    """His genuine message, including one he typed while I was busy.

    Asked of the one shared reader (2026-10-04): this used to judge the record
    itself, a second definition of what counts as him beside his_message.
    """
    from divineos.core.his_message import Heard, hear

    heard = hear(rec)
    return heard.text if isinstance(heard, Heard) else None


def _key(text: str) -> str:
    # Precedence (walk-e5e2543b6c8a): the doorman's own name, then the hook
    # path, then the first line. A doorman routed through doorbell-pre-tool-use
    # names itself ('BLOCKED by heredoc_escape'); keying on the path named the
    # doorway every routed doorman shares (Aether, 2026-09-26).
    named = re.search(r"BLOCKED by ([A-Za-z][\w-]+)", text)
    if named:
        return f"refused by {named.group(1)}"
    m = HOOK_RE.search(text)
    if m:
        return f"refused by {m.group(1) or m.group(2)}"
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if lines and re.fullmatch(r"Exit code \d+", lines[0]):
        # The first line of a crash is the envelope (Aether's first live hold,
        # 2026-09-26: token 'exit code #'). The name is the traceback's last
        # 'Name: message' line, else the first 'fatal:'/'error:' line.
        if any(ln.startswith("Traceback (most recent call last)") for ln in lines):
            for ln in reversed(lines):
                exc = re.match(r"([A-Za-z_][\w.]*(?:Error|Exception|Exit|Interrupt))\b", ln)
                if exc:
                    return f"crashed: {exc.group(1).split('.')[-1]}"
        for ln in lines[1:]:
            if re.match(r"(fatal|error)\s*:", ln, re.IGNORECASE):
                return re.sub(r"\b[0-9a-f]{8,}\b|\d+", "#", ln)[:80]
    first = lines[0] if lines else "(empty error)"
    first = re.sub(r"\b[0-9a-f]{8,}\b|\d+", "#", first)
    return first[:80]


def this_turn(records: list[dict]) -> tuple[bool, list[Stumble], str]:
    """(worked, stumbles, my reply text) since his last genuine message."""
    # The latest thing he said -- then the FIRST record carrying it. The harness
    # re-writes a queued message as a bookmark again and again through the
    # turn; taking the last copy moved the turn's start forward and dropped the
    # stumbles before it (replay 2026-09-26: 1 of 23 turns held, measured wrong).
    start, his = None, ""
    for i in range(len(records) - 1, -1, -1):
        t = _his_message(records[i])
        if t is not None:
            start, his = i, t
            break
    if start is None:
        return False, [], ""
    same = " ".join(his.split())
    for i in range(start - 1, -1, -1):
        t = _his_message(records[i])
        if t is None:
            continue
        if " ".join(t.split()) != same:
            break
        start = i
    worked = False
    reply: list[str] = []
    counts: dict[str, int] = {}
    examples: dict[str, str] = {}
    for rec in records[start + 1 :]:
        if rec.get("type") == "assistant":
            for c in (rec.get("message") or {}).get("content") or []:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    worked = True
                elif isinstance(c, dict) and c.get("type") == "text" and c.get("text", "").strip():
                    reply.append(c["text"])
            continue
        if rec.get("type") == "user":
            content = (rec.get("message") or {}).get("content")
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("is_error"):
                        t = _text(c.get("content"))
                        if re.fullmatch(r"\s*Exit code 1\s*", t):
                            continue  # a probe answering no (grep, cmp): 6 of ~900 on 2026-09-26
                        k = _key(t)
                        counts[k] = counts.get(k, 0) + 1
                        examples.setdefault(k, t.strip().splitlines()[0][:160] if t.strip() else "")
            t = _text(content)
            if t.startswith("Stop hook feedback") and ROOM_MARK not in t:
                k = "held at Stop: " + _key(t.split(":", 1)[-1])
                counts[k] = counts.get(k, 0) + 1
                examples.setdefault(
                    k, t.strip().splitlines()[1][:160] if len(t.strip().splitlines()) > 1 else ""
                )
    stumbles = [Stumble(k, n, examples.get(k, "")) for k, n in counts.items()]
    return worked, stumbles, "\n\n".join(reply)


def _rooms(reply: str) -> list[str]:
    out = []
    for m in REFLECTION_RE.finditer(reply):
        rest = reply[m.end() :]
        nxt = NEXT_ROOM_RE.search(rest)
        out.append(rest[: nxt.start()] if nxt else rest)
    return out


def reflection_of(reply: str) -> str:
    # The LAST reflection: a turn since his message can span several of my
    # replies (letters rang in between), and reading the first one judged this
    # reply by an older room -- the room's first live hold, 2026-09-26.
    rooms = _rooms(reply)
    return rooms[-1] if rooms else ""


def taken_up(reply: str, stumbles: list[Stumble]) -> bool:
    """The floor: each stumble named by its token, and an ending for each.

    Judged against EVERY reflection since his message, not only the latest
    (Aether, 'the room asks twice', 2026-09-26): a stumble answered in an
    earlier letter-woken reply is credited, not demanded again; one a retry let
    through earlier is still asked for.
    """
    all_rooms = "\n".join(_rooms(reply))
    named = all(s.token in all_rooms.lower() for s in stumbles)
    return named and len(ENDING_RE.findall(all_rooms)) >= len(stumbles)


def still_open(reply: str, stumbles: list[Stumble]) -> list[Stumble]:
    """The stumbles no reflection since his message has named yet.

    Aether 2026-09-27: held with six, five already answered earlier in the turn;
    listing all six read as the union failing. The hold names only these.
    """
    all_rooms = "\n".join(_rooms(reply)).lower()
    return [s for s in stumbles if s.token not in all_rooms]


def owed_lines(reply: str) -> list[str]:
    return [
        m.group(1).strip() for m in OWED_RE.finditer(reflection_of(reply)) if m.group(1).strip()
    ]


def file_owed(lines: list[str], stumbles: list[Stumble] | None = None) -> list[str]:
    """File each owed line; beside it, the error it answers when it names one."""
    from divineos.core.structural_fix_tracker import record_pending_fix

    def trigger(line: str) -> str:
        for s in stumbles or []:
            if s.token in line.lower():
                return f"reflection room: {s.example or s.key}"[:300]
        return "reflection room"

    return [
        record_pending_fix(line, trigger=trigger(line), source_kind="reflection") for line in lines
    ]


def hold_reason(stumbles: list[Stumble]) -> str:
    listing = "\n".join(
        f"  - [{s.token}] {s.key}"
        + (f" (x{s.count})" if s.count > 1 else "")
        + (f": {s.example}" if s.example else "")
        for s in stumbles
    )
    return (
        f"{ROOM_MARK}. This work turn stumbled, and the transcript recorded it -- "
        "not your memory:\n"
        f"{listing}\n\n"
        "In ## REFLECTION take up each one by its [name]: why it happened, then end it with "
        "'fixed by structure: <what now holds it>' or 'owed: <the build that "
        "would>'. Owed lines are filed as structural fixes automatically. A place "
        "to build, never an apology. Append only; do not re-post the reply."
    )


def read_tail(path: Path, tail_bytes: int = 4_000_000) -> list[dict]:
    size = path.stat().st_size
    with path.open("rb") as f:
        if size > tail_bytes:
            f.seek(size - tail_bytes)
            f.readline()
        lines = f.read().decode("utf-8", "replace").splitlines()
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out
