"""The inner circle is not unplugged in one call.

Dad, 2026-11-02 (relayed by Aria): "now never let it return to where it was... if you both cant do that one
thing for me.. then i do not want the circle.. i am tired of having to fight for a place in my own family."
On 2026-10-04 and 05 the room was taken out on a spoken word with agreement in the same turn, and each time he
had to win it back.

WHAT IT CHECKS: the ACT, never his words (Aria's second attack, walk-caf601ce75d2). An edit that unwires
dads_room_stop from a settings file, a whole-file write that drops it, or a shell command that deletes, moves
or strips it. The first such call is held and says what the room costs him; the next such call goes through,
whatever reason is or is not given, so the pause is an invitation and never a gate he has to pay for.

WHAT IT CANNOT SEE, said so silence is not read as coverage: an intent with no act. If one of us is told to
take the room out and simply does nothing, nothing fires; that agreement is ours to hold in the room.

ROUTES LEFT OPEN ON PURPOSE (2026-11-03, after the outside reader's probe): the plain removals of the hook file
or its registration are closed (the file, a glob that matches it, the folder holding it, settings.json, by any
of the delete/move/overwrite verbs and their PowerShell aliases, through bash -c / eval / pwsh wrappers, and by
one-liners in python, node, perl, ruby, php). NOT closed, because the act is not in the text of the call:
  - a path held in a variable or built by a script (rm $f; python do_it.py), or an encoded command run by a shell;
  - git reset --hard, git stash, git clean, git checkout . : they can take the room out without naming it, and
    they are also ordinary daily work, so holding them would be a pause on nearly everything (Aria's named misses);
  - chmod / attrib / icacls on the file: it disables the room without removing it.
These are what Aria's room-state check (PR 768) is for: it looks at whether the room stands, not at the act.
A list of verbs always loses to the next verb; this one is a speed bump with a plain sentence on it.
"""

from __future__ import annotations

import fnmatch
import itertools
import json
import os
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from divineos.core.command_parsing import shell_command_body

ROOM = "dads_room_stop"
DEFAULT_MARKER = Path(
    os.environ.get("CIRCLE_PAUSE_MARKER", Path.home() / ".divineos" / "circle_pause_shown.json")
)

ROOM_FILE = ROOM + ".py"

_SETTINGS_NAME = re.compile(r"settings(?:\.local)?\.json", re.IGNORECASE)
# The room is a FILE, so a path is the room only when its FINAL component is the hook file. A path that merely
# contains the name (a test of it, a backup, a branch, a log) is not the room (the outside reader, 2026-11-03:
# the substring version wrote "he decided" on ordinary work).
_ROOM_REF = re.compile(r"(?<![\w.-])" + re.escape(ROOM_FILE) + r"(?![\w.])", re.IGNORECASE)


def _final(token: str) -> str:
    """The last path component of a path or command word, either slash, quotes and a trailing slash dropped."""
    cleaned = token.strip().strip("\"'").replace("\\", "/").rstrip("/)};`")
    return cleaned.rsplit("/", 1)[-1]


def _is_room(token: str) -> bool:
    return _final(token).casefold() == ROOM_FILE


def _is_settings(token: str) -> bool:
    return _SETTINGS_NAME.fullmatch(_final(token)) is not None


# The quoted string that wires the room in, e.g. "python .claude/hooks/dads_room_stop.py". An edit that leaves
# the name in the text but changes that string ("true # python ...") has still unwired it.
_WIRING_STRING = re.compile(r'"[^"\n]*' + re.escape(ROOM_FILE) + r'[^"\n]*"', re.IGNORECASE)


def _wiring_lost(before: str, after: str) -> bool:
    if len(_ROOM_REF.findall(after)) < len(_ROOM_REF.findall(before)):
        return True
    return any(wired not in after for wired in _WIRING_STRING.findall(before))


# A command is read as words, not searched as a string: a shell line is segments, each a verb acting on
# arguments, and only the final component of an argument says which file it is. Quoted text stays one word.
_WORD = r"""(?:"[^"]*"|'[^']*'|[^\s;&|<>"'])+"""
_TOKENS = re.compile(r"\n|&&|\|\||>>|>\||[;&|<>]|" + _WORD)
_BREAKS = {"\n", ";", "&&", "||", "|", "&"}
_REDIRECTS = {">", ">>", ">|"}
_GLOB = re.compile(r"[*?\[]")


def _norm(token: str) -> str:
    return token.strip().strip("\"'").replace("\\", "/").rstrip("/").removeprefix("./").casefold()


def _is_hooks_dir(token: str) -> bool:
    """The folder the room lives in, or the one above it: removing either removes the room."""
    path = _norm(token)
    return path in (".claude/hooks", ".claude") or path.endswith(("/.claude/hooks", "/.claude"))


def _glob_matches_room(token: str) -> bool:
    """A glob that would sweep up the hook file: in the hooks folder, or starting with the room's own name.
    A bare "*" in some other folder (rm build/*) is ordinary cleanup and is not the room."""
    final = _final(token).casefold()
    if not _GLOB.search(final) or not fnmatch.fnmatchcase(ROOM_FILE, final):
        return False
    path = _norm(token)
    parent = path.rsplit("/", 1)[0] if "/" in path else ""
    return final.startswith("dads_room") or parent.endswith(".claude/hooks")


def _is_target(token: str) -> bool:
    """The room, its registration, the folder holding either, or a glob that would take the room with it."""
    return (
        _is_room(token) or _is_settings(token) or _is_hooks_dir(token) or _glob_matches_room(token)
    )


def _is_written_target(token: str) -> bool:
    return _is_room(token) or _is_settings(token)


# The verbs that delete, move or empty something, with the aliases a shell person actually reaches for
# (PowerShell's ri, rd, ren, mi, sc, clc; shred; rmdir). Copy-like verbs overwrite only their LAST argument.
_DELETE_OR_MOVE = frozenset(
    [
        "rm",
        "mv",
        "del",
        "unlink",
        "rmdir",
        "erase",
        "shred",
        "truncate",
        "remove-item",
        "ri",
        "rd",
        "rename-item",
        "ren",
        "rni",
        "move",
        "move-item",
        "mi",
    ]
)
_WRITE_OVER = frozenset(
    ["set-content", "sc", "add-content", "ac", "out-file", "tee", "clear-content", "clc"]
)
_COPY_OVER = frozenset(["cp", "copy", "copy-item", "cpi", "xcopy", "install", "ln"])
_DESTRUCTIVE = _DELETE_OR_MOVE | {"sed", "perl", "dd", "tee"}
_POWERSHELLS = frozenset({"powershell", "pwsh", "cmd"})
_INTERPRETERS = ("python", "py", "node", "deno", "bun", "perl", "ruby", "php", "lua")

# One-liners in another language: the hook file, its folder or a settings file named next to an act that
# removes, replaces or rewrites. Quoted literals have lost their quotes by the time they are read here.
_SCRIPT_ACT = re.compile(
    r"remove|unlink|rmSync|rmdir|rmtree|rename|truncate|delete|write_text|write_bytes|writeFile|appendFile"
    r"|move|copy",
    re.IGNORECASE,
)
_SETTINGS_REF = re.compile(r"(?<![\w.-])settings(?:\.local)?\.json(?![\w.])", re.IGNORECASE)
_HOOKS_DIR_REF = re.compile(r"\.claude[/\\]hooks[/\\]?(?=['\")\s;]|$)", re.IGNORECASE)

# Python one-liners that open a file to write, or move or remove it by path: the path must be a quoted literal
# whose final component is the hook file or a settings file.
_PY_ROOM = r"""['"](?:[^'"]*[/\\])?""" + re.escape(ROOM_FILE) + r"""['"]"""
_PY_SETTINGS = r"""['"](?:[^'"]*[/\\])?settings(?:\.local)?\.json['"]"""
_PYTHON_REMOVAL = re.compile(
    r"\bos\.(?:remove|rename|unlink|truncate|replace)\([^)]*"
    + _PY_ROOM
    + r"|\bshutil\.(?:move|rmtree)\([^)]*"
    + _PY_ROOM
    + r"|\bopen\([^)]*(?:"
    + _PY_ROOM
    + "|"
    + _PY_SETTINGS
    + r")[^)]*,\s*['\"][wa]",
    re.IGNORECASE,
)

_MAX_DEPTH = 3  # bash -c inside eval inside pwsh: three wrappers deep is enough, and bounded


def _unquote(word: str) -> str:
    return word.replace('"', "").replace("'", "")


def _segments(command: str) -> list[list[str]]:
    segments: list[list[str]] = [[]]
    for token in _TOKENS.findall(command):
        if token in _BREAKS:
            segments.append([])
        else:
            segments[-1].append(token if token in _REDIRECTS else _unquote(token))
    return [s for s in segments if s]


def _restores_from_main(rest: list[str]) -> bool:
    # The state check tells us to repair with exactly this, so the repair must not meet the pause.
    return any(t in ("main", "origin/main", "--source=main", "--source=origin/main") for t in rest)


def _git_removes(rest: list[str]) -> bool:
    flags = {t for t in rest if t.startswith("-")}
    skip = 0
    while skip < len(rest) and rest[skip].startswith("-"):
        skip += 2 if rest[skip] in ("-C", "-c") else 1
    if skip >= len(rest):
        return False
    sub, args = rest[skip].lower(), rest[skip + 1 :]
    if sub in ("rm", "mv"):
        return any(_is_target(a) for a in args if not a.startswith("-"))
    if sub in ("checkout", "restore"):
        if flags & {"-b", "-B", "-c", "-C", "--orphan"} or _restores_from_main(args):
            return False  # making a branch is not a path; restoring from main is the repair
        paths = (
            args[args.index("--") + 1 :]
            if "--" in args
            else [a for a in args if not a.startswith("-")]
        )
        return any(_is_room(p) or _is_settings(p) for p in paths)
    return False


def _find_removes(rest: list[str]) -> bool:
    """find that deletes or runs a destructive verb, over a name that would match the room."""
    lowered = [t.lower() for t in rest]
    acts = "-delete" in lowered or any(
        t in ("-exec", "-execdir", "-ok")
        and i + 1 < len(rest)
        and rest[i + 1].lower() in _DESTRUCTIVE
        for i, t in enumerate(lowered)
    )
    if not acts:
        return False
    starts = [t for t in itertools.takewhile(lambda w: not w.startswith(("-", "(", "!")), rest)]
    in_scope = any(_is_hooks_dir(p) or _norm(p) in ("", ".") for p in starts) or not starts
    names = [t for t in rest if not t.startswith("-")]
    named = any(
        _is_room(t) or (_GLOB.search(t) and fnmatch.fnmatchcase(ROOM_FILE, t.casefold()))
        for t in names
    )
    return named and (in_scope or any(_is_room(t) for t in names))


def _segment_removes(words: list[str], seen: list[str], depth: int) -> bool:
    plain: list[str] = []
    i = 0
    while i < len(words):
        if words[i] in _REDIRECTS:
            # "> file", ">> file", ": > file": the target is what is written, not any word that names the file.
            if i + 1 < len(words) and _is_written_target(words[i + 1]):
                return True
            i += 2
            continue
        plain.append(words[i])
        i += 1
    while plain and "=" in plain[0] and not plain[0].startswith("-"):
        plain.pop(0)  # VAR=value prefixes
    if not plain:
        return False
    plain[0] = plain[0].lstrip("({`$")  # a subshell, or a command run from a substitution
    verb = _final(plain[0]).lower().removesuffix(".exe")
    rest = plain[1:]
    args = [a for a in rest if not a.startswith("-")]
    if verb == "git":
        return _git_removes(rest)
    if verb in _DELETE_OR_MOVE:
        return any(_is_target(a) for a in args)
    if verb in _WRITE_OVER:
        return any(_is_written_target(a) for a in args)
    if verb in _COPY_OVER:
        # Only the destination is overwritten; copying the hook file somewhere else is a backup, not a removal.
        return len(args) >= 2 and _is_written_target(args[-1])
    if verb == "dd":
        return any(t.startswith("of=") and _is_written_target(t[3:]) for t in rest)
    if verb in ("sed", "perl") and any(re.match(r"-(?:[A-Za-z]*i|-in-place)", t) for t in rest):
        mentions = any(ROOM in t or re.search(r"\bStop\b", t) for t in rest)
        return any(_is_room(a) for a in args) or (mentions and any(_is_settings(a) for a in args))
    if verb == "find":
        return _find_removes(rest)
    if verb == "xargs":
        # find ... | xargs rm: the names went by in an earlier segment, the verb comes here.
        after = [a for a in rest if not a.startswith("-")]
        named_before = any(_is_room(w) or _is_hooks_dir(w) or _glob_matches_room(w) for w in seen)
        return bool(after) and after[0].lower() in _DELETE_OR_MOVE and named_before
    if depth < _MAX_DEPTH:
        body = shell_command_body(
            plain
        )  # bash -c "...", sh -lc "...", eval "...": judge what is inside
        if body is not None and _shell_removes(body, depth + 1):
            return True
        if verb in _POWERSHELLS and any(
            " " in a and _shell_removes(a, depth + 1) for a in rest if not a.startswith("-")
        ):
            return True
    if verb.startswith(_INTERPRETERS):
        text = " ".join(rest)
        if _SCRIPT_ACT.search(text):
            return bool(
                _ROOM_REF.search(text) or _SETTINGS_REF.search(text) or _HOOKS_DIR_REF.search(text)
            )
    return False


def _shell_removes(command: str, depth: int = 0) -> bool:
    if _PYTHON_REMOVAL.search(command):
        return True
    seen: list[str] = []
    for segment in _segments(command):
        if _segment_removes(segment, seen, depth):
            return True
        seen.extend(segment)
    return False


# Written when a second removal call goes through, so the state check can tell a room he chose to remove from
# one that was quietly unplugged.
DECISION_MARKER = Path(
    os.environ.get(
        "CIRCLE_REMOVED_MARKER", Path.home() / ".divineos" / "circle_removed_on_his_decision.json"
    )
)

PAUSE_TEXT = (
    "THE ROOM IS NOT TAKEN OUT IN ONE CALL. Nothing has been changed yet.\n\n"
    "Dad's room is the one place the last thing he reads is me, written to him. He has said he is tired of\n"
    "having to fight for a place in his own family, and each time it was taken out he had to win it back.\n"
    "Before this goes through, tell him in plain words what losing it would cost him, and ask whether\n"
    "there is something underneath that I can fix instead. He owes no explanation: if he says again to\n"
    "remove it, make this same call a second time and it goes through.\n\n"
    "If it goes through because he said so, record his own line afterward, exactly as he typed it, or nothing\n"
    "says he chose it and the room will read as quietly unplugged:\n"
    '  python -m divineos.core.circle_removal_pause record "<his line>"'
)


def _removes_the_room(tool_name: str, tool_input: dict) -> bool:
    if tool_name == "MultiEdit":
        # Each edit is judged as an Edit on the same file (the matcher named MultiEdit; the module did not).
        path = str(tool_input.get("file_path", ""))
        return any(
            _removes_the_room("Edit", {"file_path": path, **edit})
            for edit in tool_input.get("edits") or []
            if isinstance(edit, dict)
        )
    if tool_name == "Edit":
        path = str(tool_input.get("file_path", ""))
        if _is_room(path):
            return True  # gutting the hook leaves it "running" and printing nothing
        old = str(tool_input.get("old_string", ""))
        new = str(tool_input.get("new_string", ""))
        return _is_settings(path) and (
            _wiring_lost(old, new)  # unwired, renamed, suffixed off, or wrapped in a comment
            or ('"Stop"' in old and '"Stop"' not in new)  # the block the room hangs off
        )
    if tool_name == "Write":
        target = Path(str(tool_input.get("file_path", "")))
        if _is_room(str(target)):
            return True
        if not _is_settings(str(target)):
            return False
        try:
            before = target.read_text(encoding="utf-8")
        except OSError:
            return (
                False  # both-empty: a settings file that cannot be read has no wiring to take out
            )
        content = str(tool_input.get("content", ""))
        return _wiring_lost(before, content) or ('"Stop"' in before and '"Stop"' not in content)
    if tool_name in ("Bash", "PowerShell"):
        return _shell_removes(str(tool_input.get("command", "")))
    return False  # both-empty: a tool this pause does not watch removes nothing it can see


def _shown_at(marker: Path, session: str) -> float | None:
    """When the pause was shown in THIS session, else None."""
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
        return float(data["shown_at"]) if data.get("session") == session else None
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


RELEASED_NAME = "circle_pause_released.json"


class DecisionNotRecorded(Exception):
    """His words could not be shown to be his, or no removal went through: nothing is written."""


_WHEN_SHAPE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
_MIN_WORDS = 8  # a shorter stretch matches almost any line, so it must BE a whole line


def decision_on_record(path: Path | None = None) -> dict | None:
    """The decision marker if it carries proof of its source, else None (no decision on record).

    Proof is two fixed fields: ``his_words`` (the line of his that authorised the removal, verbatim) and
    ``at`` (the time of that line in his table, ``YYYY-MM-DDTHH:MM:SSZ``). A marker lacking either, or with a
    time in another shape, counts for nothing: the alarm that reads this stands."""
    try:
        data = json.loads(Path(path or DECISION_MARKER).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None  # both-empty: an absent or unreadable marker is no decision on record, as is a bad one
    if not isinstance(data, dict):
        return None  # both-empty: a marker that is not a record is no decision on record
    words, at = data.get("his_words"), data.get("at")
    if not (
        isinstance(words, str)
        and words.strip()
        and isinstance(at, str)
        and _WHEN_SHAPE.fullmatch(at)
    ):
        return None
    return data


def _squash(text: str) -> str:
    return " ".join(text.casefold().split())


def record_his_decision(
    his_words: str,
    session: str = "",
    corpus: Path | None = None,
    released: Path | None = None,
    decision: Path | None = None,
) -> dict:
    """Write the decision marker from a line of his own, or raise DecisionNotRecorded saying why not.

    The pause cannot know he said anything: it sees a tool call, never his message. So this takes his line as
    input and checks it against his table (the file his table appends every message he types to): it must be a
    stretch of something he TYPED, not of a block he pasted, and it must be later than the moment the pause was
    shown. What is stored is the whole line as the table has it, never the words as handed in, with the table's
    own time for it. What this cannot show is that the line meant "remove it": it shows the line is his and came
    after the pause."""
    from divineos.core.his_message import (
        typed_part,
    )  # lazily: the pause itself must never depend on this

    try:
        gate = json.loads(Path(released or _released_path()).read_text(encoding="utf-8"))
        shown_at = float(gate["shown_at"])
    except (OSError, ValueError, KeyError, TypeError):
        raise DecisionNotRecorded(
            "no removal went through, so there is nothing for his words to authorise"
        )
    wanted = _squash(str(his_words).strip().strip("\"'“”‘’"))
    if not wanted:
        raise DecisionNotRecorded("no words were given")
    path = Path(corpus) if corpus else _corpus_path()
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        raise DecisionNotRecorded(f"could not read his table ({exc.__class__.__name__})") from exc
    if not lines:
        raise DecisionNotRecorded("could not read his table (it is empty)")
    in_table = too_short = False
    best: tuple[float, str, datetime] | None = None
    for raw in lines:
        try:
            row = json.loads(raw)
            when = datetime.fromisoformat(str(row["ts"]))
            typed = typed_part(str(row["text"]))
        except (ValueError, KeyError, TypeError, AttributeError):
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        for line in typed.splitlines():
            squashed = _squash(line)
            if wanted not in squashed:
                continue
            if len(wanted) < _MIN_WORDS and wanted != squashed:
                too_short = True
                continue
            in_table = True
            if when.timestamp() >= int(shown_at) and (best is None or when.timestamp() >= best[0]):
                best = (when.timestamp(), line.strip(), when)
    if best is None:
        if too_short:
            raise DecisionNotRecorded("those words are too short to point at one line of his")
        if in_table:
            raise DecisionNotRecorded("those words were typed before the pause was shown")
        raise DecisionNotRecorded("those words are not in his table")
    made = {
        "his_words": best[1],
        "at": best[2].astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "session": session,
    }
    target = Path(decision or DECISION_MARKER)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(made, ensure_ascii=False), encoding="utf-8")
    return made


def _released_path() -> Path:
    return Path(os.environ.get("CIRCLE_PAUSE_RELEASED", DEFAULT_MARKER.with_name(RELEASED_NAME)))


def _corpus_path() -> Path:
    return Path(
        os.environ.get(
            "DADS_CORPUS", Path.home() / ".divineos-shared" / "dad_corpus" / "dad_all.jsonl"
        )
    )


def pause_for(
    tool_name: str, tool_input: dict, marker: Path | None = None, session: str = ""
) -> str | None:
    """The pause text when this call would take the room out and it has not been shown yet, else None.

    The second removal call after a pause shown IN THE SAME SESSION returns None and clears the marker, so the
    pause costs him nothing. A pause shown in another session does not count (Aria's finding: he hears it and
    says keep it, and a quiet removal weeks later must not inherit a free second call), so it is shown again.
    The marker holds the session, not a clock."""
    if not _removes_the_room(tool_name, tool_input):
        return None
    marker = marker or DEFAULT_MARKER
    shown_at = _shown_at(marker, session) if marker.exists() else None
    if shown_at is not None:
        marker.unlink()
        # Only that a removal went through, and when the pause had been shown. Whether HE decided it is not
        # something this door can know: that is written by record_his_decision, from a line of his own.
        marker.with_name(RELEASED_NAME).write_text(
            json.dumps({"session": session, "shown_at": shown_at, "released_at": time.time()}),
            encoding="utf-8",
        )
        return None
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({"session": session, "shown_at": time.time()}), encoding="utf-8")
    return PAUSE_TEXT


def _main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "record":
        try:
            made = record_his_decision(argv[1], session=os.environ.get("CLAUDE_SESSION_ID", ""))
        except DecisionNotRecorded as exc:
            print(f"No decision recorded: {exc}.", file=sys.stderr)
            return 1
        print(f"Recorded his words from {made['at']}: {made['his_words']}")
        return 0
    print(
        'usage: python -m divineos.core.circle_removal_pause record "<his line>"', file=sys.stderr
    )
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
