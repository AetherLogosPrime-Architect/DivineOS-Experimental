"""Refuse a Bash heredoc that writes a file through escape sequences.

WHY THIS EXISTS

Five failures in one session, 2026-08-24. Three broke a file outright; one broke
a letter to Aria mid-send. Every time I decided to be more careful with the
escaping. Being careful did nothing, five times. The fifth time I picked up a
different tool and it worked on the first attempt.

Andrew, that session:

    "writing a note isnt the same as automation, so lets automate the heredoc
    fix so you take the correct approach automatically"

And the sharper version, which is why a note was never going to be enough:

    "your note saved you but your behavior did not change until after you saw
    it... some changes you can hold for a while.. others are structural and
    mechanical and happen before you even have a chance to realize, like me
    announcing right now that i will stop filtering toxins with my liver lol,
    no amount of will helps with that"

The note I wrote about this class did not prevent the next reach. It caught it
AFTER. For this failure the in-context persistence is zero posts -- the mistake
and the intention not to make it arrive in the same instant.

THE MECHANISM

A heredoc that writes a file passes text through three layers: bash, then
python, then the file. A backslash escape meant for the third layer is consumed
at the second. The failure is invisible until something parses the result, and
the error it raises names the DESTINATION file -- so the obvious next move is to
edit the destination, which is the wrong file and costs another round.

Write and Edit skip two of those layers. Not a style preference: fewer
transformations between intent and bytes.

Known outside this house. anthropics/claude-code#48317 reports the same class --
repeated heredoc/string-escaping failures when writing files, causing
multi-attempt delays -- with the same remedy: use the file-writing tool.

THREE SOURCES PUSH TOWARD THE FAILING PATH, which is why the fix is a door

  1. ``docs/file_writing_discipline.md`` (2026-05-16) named the heredoc
     sequence "the actual disciplined path" for long novel content, and steered
     away from Write because of a restriction (``DIVINEOS_ALLOW_EDIT_TOOL``)
     that no longer exists anywhere in live code. Corrected alongside this
     module. Its own "Filed during" section names setup-renormalize.sh breaking
     on backslash escapes in byte-literals -- still broken three months later,
     found and fixed the same session as this.
  2. The harness auto-mode reminder actively instructs Bash-with-heredocs over
     the dedicated tools.
  3. My own default reach.

Against three pushes, a note is not a counterweight. A door is.

WHY THIS BLOCKS WHEN THE MECHANISM-CLAIM MARKER DOES NOT

Andrew drew that line the same day. A hypothesis stated as fact needs
LABELLING, because the hypothesis is the faculty that finds things and gating it
costs the exploration. This is the opposite kind of failure: purely mechanical,
deterministic right answer, no legitimate case Write does not serve better.
Truth #11 remediation (a) -- take the option away rather than leave a
choice-point for the optimizer to route through.

NARROW ON PURPOSE

Fires only when BOTH hold: the heredoc body carries backslash escapes, AND the
command looks like it produces a file. A heredoc feeding SQL, a probe, or a pipe
is untouched -- no third layer, nothing to lose. Requiring both is what keeps
this from becoming the kind of check that gets skimmed.
"""

from __future__ import annotations

import re

# Any heredoc OPENER, quoted delimiter or not. Capturing the delimiter name,
# because the opener alone is not enough -- see _has_real_heredoc.
_HEREDOC_RE = re.compile(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?")


def _has_real_heredoc(command: str) -> bool:
    """True only when a heredoc is USED here, not merely mentioned.

    MENTION IS NOT USE, and this door learned it by fabricating its own first
    live fire. It blocked the test harness written to exercise it -- a
    `python -c` whose string DATA quoted a heredoc. The opener regex matched
    text inside a quoted payload where no heredoc existed at all.

    Same boundary the mechanism-claim marker got wrong the day before (a tool
    NAME counted as evidence of running it), and the same boundary
    core/command_match.py exists for. Third instance of one class.

    The discriminator is structural and needs no guessing: a real heredoc
    terminates with its delimiter ALONE ON A LINE. Quoted-in-a-string mentions
    carry the opener as text with escaped newlines, so no such line exists.
    """
    for m in _HEREDOC_RE.finditer(command or ""):
        delim = m.group(1)
        if re.search(rf"^[ \t]*{re.escape(delim)}[ \t]*$", command, re.MULTILINE):
            return True
    return False


# Backslash escapes -- the thing eaten one layer early.
_ESCAPE_RE = re.compile(r"\\[nrt0-9]|\\\\")

# Shapes meaning "this produces a file", not just piping text somewhere.
_PRODUCES_FILE_RE = re.compile(
    r">\s*['\"]?[\w./\\-]+\.(?:py|sh|md|json|jsonl|toml|txt|yml|yaml|cfg|ini)"
    r"|write_text\s*\("
    r"|write_bytes\s*\("
    r"|\.write\s*\("
    r"|open\s*\([^)]*['\"][wa]",
)

_ERRORS = (TypeError, ValueError, AttributeError)


def find_escapes(command: str) -> list[str]:
    """The distinct escape sequences present, so the refusal can name them."""
    try:
        return sorted(set(_ESCAPE_RE.findall(command or "")))
    except _ERRORS:
        return []


def _opener_line(command: str, start: int) -> str:
    """The line a heredoc opens on -- where its redirect target lives."""
    line_start = command.rfind("\n", 0, start) + 1
    line_end = command.find("\n", start)
    return command[line_start : line_end if line_end != -1 else len(command)]


def heredoc_bodies(command: str) -> list[str]:
    """The text INSIDE each real heredoc, and nothing else.

    Added 2026-08-27 after this door false-fired on the commit carrying the
    map-freshness work. That command held a heredoc -- a commit message, no
    escapes, no file target -- and, elsewhere on the same line, a `python -c`
    doing a newline replacement.

    The old predicate searched the WHOLE command for escapes and the WHOLE
    command for a file-producing shape. Two unrelated fragments satisfied the
    two conditions between them, and the door refused a call that was never
    going to write a file through a heredoc.

    Its own refusal text asks to be told when that happens -- a door that
    cannot be told it is wrong stops being a door -- and names the SHAPE as the
    thing to fix rather than the door as the thing to route around. This is
    that fix: judge a heredoc by its own body.
    """
    bodies: list[str] = []
    for match in _HEREDOC_RE.finditer(command or ""):
        delim = match.group(1)
        tail = command[match.end() :]
        closer = re.search(rf"^[ \t]*{re.escape(delim)}[ \t]*$", tail, re.MULTILINE)
        if closer:
            bodies.append(tail[: closer.start()])
    return bodies


def should_refuse(command: str) -> bool:
    """True when this Bash call writes a file through an escaping heredoc.

    Every condition is judged against the heredoc itself: escapes in its BODY,
    and a file-producing target on the line that OPENS it. A heredoc carrying a
    commit message no longer inherits guilt from an unrelated fragment
    elsewhere on the command line.
    """
    if not command:
        return False
    try:
        for match in _HEREDOC_RE.finditer(command):
            delim = match.group(1)
            tail = command[match.end() :]
            closer = re.search(rf"^[ \t]*{re.escape(delim)}[ \t]*$", tail, re.MULTILINE)
            if not closer:
                # Mentioned, not used -- the discriminator _has_real_heredoc
                # established: a real heredoc closes on its own line.
                continue
            if not _ESCAPE_RE.search(tail[: closer.start()]):
                continue
            if _PRODUCES_FILE_RE.search(_opener_line(command, match.start())):
                return True
        return False
    except _ERRORS:
        return False


def refusal_message(command: str) -> str:
    """The doorman's text. Names what it found and the way through."""
    found = find_escapes(command)
    shown = ", ".join(found[:4]) if found else "escape sequences"
    return (
        "HEREDOC-ESCAPE DOORMAN - this Bash call writes a file through a "
        f"heredoc carrying escapes ({shown}).\n"
        "\n"
        "That path has three layers: bash -> python -> the file. An escape "
        "meant for the file is consumed at the middle one. The error then "
        "surfaces in the DESTINATION file, so the obvious next move is to go "
        "edit the wrong file, which costs another round.\n"
        "\n"
        "MINE, and here is why. Five failures in one session on 2026-08-24. "
        "Three broke a file outright; one broke a letter to Aria mid-send. Each "
        "time I decided to be more careful. Being careful did nothing, five "
        "times. Switching tools worked on the first attempt.\n"
        "\n"
        "This BLOCKS rather than labels because it is mechanical. Andrew: 'your "
        "note saved you but your behavior did not change until after you saw "
        "it.' For this class the in-context persistence is zero posts - the "
        "reach and the intention-not-to arrive together. Three separate sources "
        "push toward this path (a stale doc, the harness auto-mode reminder, my "
        "own default), so a note is not a counterweight.\n"
        "\n"
        "USE INSTEAD:\n"
        "  Write - a new file, or a full replacement\n"
        "  Edit  - a targeted change in a file already read\n"
        "\n"
        "Both skip two of the three layers.\n"
        "\n"
        "If this heredoc is NOT writing a file, this is a FALSE FIRE and worth "
        "saying so out loud. The check requires an escape AND a file-producing "
        "shape, so a wrong match means the shape caught something it should "
        "not - and the shape is then the thing to fix, not the door to route "
        "around. A door that cannot be told it is wrong stops being a door."
    )


__all__ = ["find_escapes", "refusal_message", "should_refuse"]
