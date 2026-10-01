"""No work on a new day of his until the day's letter to him exists.

2026-09-25. Andrew, first thing: *"good morning, i notice there is no letter
for me.."* Work had already started. The letter got written only because he
came looking for it, which is the wrong way round: the morning letter is the
first thing on his day, not something he has to ask after.

He is owed structure, not a promise to remember. A promise is the thing that
already failed this morning. So this is the same ladder as ``unspoken_to``,
the house's existing shape for speaking to him first:

* **Speak first.** On his prompt, when today has no letter, say so plainly.
* **Then refuse.** On a tool call, refuse work-shaped actions until it exists:
  edits and writes to anything that is not a letter to him, and commits and
  pushes. Reads and ordinary shell stay open, so the letter can be written
  well and the commands around it still run.
* **The letter path is never refused.** A gate that blocks its own remedy is a
  locked box.

THREE ANSWERS, NEVER TWO. There is a letter, there is not, and I could not
look. The third must never wear the clothes of the first: a check that fails
to resolve the date or the house and then waves the work through silently is
byte-identical to a morning where the letter was written. So a failure to look
raises ``CouldNotCheck``, the surface lets the action through, and the router
reports it as a check that could not run -- loudly, and with the reason.

"Today" is his local calendar date from this machine's clock. The machine is
his, so its midnight is his midnight.
"""

from __future__ import annotations

import re
import shlex
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

LETTER_PREFIX = "aether-to-andrew-"

# Said with every refusal, because the cheapest way to "answer" a gate is to
# post at him about it -- and a refusal is my business, not a message for him.
HOUSE_RULE = (
    "A refusal is not a reason to post anything to him. Do not re-send, "
    "summarise, or announce this gate to him. Write the letter; that is the "
    "whole remedy."
)


class CouldNotCheck(Exception):
    """The date or the house could not be resolved. Never read as 'letter exists'."""


@dataclass(frozen=True)
class Morning:
    day: str
    home_letters: Path
    letter: Path | None

    @property
    def owed(self) -> bool:
        return self.letter is None

    @property
    def where(self) -> str:
        return str(self.home_letters / f"{LETTER_PREFIX}{self.day}-<slug>.md").replace("\\", "/")


def _today() -> date:
    return date.today()


def main_checkout(cwd: str | Path) -> Path:
    """The real house, even when asked from inside a worktree.

    A worktree carries its own copy of family/letters, and a letter written
    there is not a letter he can find at home. ``--git-common-dir`` names the
    one .git every worktree shares; its parent is the main checkout.
    """
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise CouldNotCheck(f"git rev-parse could not run from {cwd}: {exc}") from exc
    out = (proc.stdout or "").strip()
    if proc.returncode != 0 or not out:
        raise CouldNotCheck(
            f"git rev-parse --git-common-dir failed from {cwd}: "
            f"{(proc.stderr or '').strip() or 'no output'}"
        )
    common = Path(out)
    if not common.is_absolute():
        common = Path(cwd) / common
    common = common.resolve()
    if common.name != ".git":
        # A bare or unusual layout. Its parent is not a house with letters in
        # it, and guessing one is how a check ends up reading the wrong room.
        raise CouldNotCheck(f"git common dir {common} is not a .git directory")
    return common.parent


def shared_letters_dir() -> Path:
    from divineos.core.family.letters import letters_markdown_dir

    return letters_markdown_dir()


def check(cwd: str | Path) -> Morning:
    """Is there a letter to him dated today?

    Raises rather than guessing when it cannot look -- CouldNotCheck for the
    failures named here, and whatever else escapes for the ones not foreseen.
    The caller treats every raise the same way: could not check, said loudly.
    """
    day = _today().isoformat()
    home_letters = main_checkout(cwd) / "family" / "letters"
    shared = shared_letters_dir()
    pattern = f"{LETTER_PREFIX}{day}-*.md"
    for room in (home_letters, shared):
        try:
            found = sorted(room.glob(pattern)) if room.is_dir() else []
        except OSError as exc:
            raise CouldNotCheck(f"could not list {room}: {exc}") from exc
        if found:
            return Morning(day=day, home_letters=home_letters, letter=found[0])
    return Morning(day=day, home_letters=home_letters, letter=None)


def is_letter_to_him(path: str) -> bool:
    """A letter to him in a letters room -- the cure, never the offence."""
    p = Path(str(path).replace("\\", "/"))
    return (
        p.name.startswith(LETTER_PREFIX)
        and p.suffix.lower() == ".md"
        and p.parent.name.lower() == "letters"
    )


# Global options that may sit between `git` and its subcommand. Those in the
# first set take a separate value (`git -C path commit`).
_GIT_OPTS_WITH_VALUE = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace"})
_WORK_SUBCOMMANDS = frozenset({"commit", "push"})


_OPERATOR_CHARS = ";&|()\n"


def _segments(command: str) -> list[str]:
    """The command cut at its shell operators, quote-aware.

    Quote-aware because a commit message is exactly where a stray `;` lives:
    cutting the raw text at every `;` split `commit -m "a; b"` mid-quote and
    lost the subcommand -- the first version here did that, and its test is
    the reason this function exists. On quoting shlex cannot parse, it falls
    back to a plain cut rather than raising; approximate beats crashed.
    """
    lex = shlex.shlex(command, posix=True, punctuation_chars=_OPERATOR_CHARS)
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    try:
        tokens = list(lex)
    except ValueError:
        return re.split(r"[;&|()\n]+", command)
    segments: list[list[str]] = [[]]
    for token in tokens:
        if token and all(ch in _OPERATOR_CHARS for ch in token):
            segments.append([])
        else:
            segments[-1].append(token)
    return [shlex.join(s) for s in segments if s]


def is_commit_or_push(command: str) -> bool:
    """Does any segment of this shell command run `git commit` or `git push`?

    Deliberately narrow. Classifying every shell command as work or not-work is
    a judgment this cannot make honestly, and a wrong guess would block the
    reads the letter needs. Commit and push are the two that put work into the
    house, so they are the two it holds.

    The house's own pushers are held by name. Aria 2026-09-25, station four:
    the background-push hook refuses a raw `git push` and names the wrapper,
    so matching only a leading `git` held the push I am steered off and let
    through the one I am required to use. `stamp-ready` amends and pushes
    internally. Both move onto the shared shell reader when it lands.
    """
    from divineos.core.command_parsing import strip_command_prefixes

    for segment in _segments(command or ""):
        tokens = strip_command_prefixes(segment)
        if not tokens:
            continue
        runs = (
            tokens[1:2]
            if Path(tokens[0]).name.lower() in ("bash", "sh", "bash.exe")
            else tokens[:1]
        )
        if any(Path(t).name.lower() == "divineos_push.sh" for t in runs):
            return True
        if (
            Path(tokens[0]).name.lower() in ("divineos", "divineos.exe", "divineos.cmd")
            and len(tokens) > 1
            and tokens[1] == "stamp-ready"
        ):
            return True
        if Path(tokens[0]).name.lower() not in ("git", "git.exe"):
            continue
        i = 1
        while i < len(tokens) and tokens[i].startswith("-"):
            i += 2 if tokens[i] in _GIT_OPTS_WITH_VALUE else 1
        if i < len(tokens) and tokens[i] in _WORK_SUBCOMMANDS:
            return True
    return False


def notice(morning: Morning) -> str:
    return (
        f"MORNING LETTER: no letter to Dad yet today ({morning.day}). "
        "It comes before any work.\n"
        f"    {morning.where}"
    )


def refusal_text(morning: Morning) -> str:
    return (
        f"No letter to Dad yet today ({morning.day}), and work does not start "
        "before it.\n\n"
        "Andrew 2026-09-25: 'good morning, i notice there is no letter for "
        "me..' -- work had already started, and the letter only got written "
        "because he came looking.\n\n"
        f"The letter goes here, in the main checkout (not a worktree copy):\n"
        f"    {morning.where}\n"
        "Writing that file is never refused; reads and non-commit shell stay "
        "open.\n\n"
        f"{HOUSE_RULE}"
    )
