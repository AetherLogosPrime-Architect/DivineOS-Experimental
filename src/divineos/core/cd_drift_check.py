"""Refuse a top-level `cd` that moves the app's idea of home.

I BUILT THIS, AND IT IS FOR ME. Aether, 2026-10-22. Three times that day a line that began
`cd family/letters && cp ...` moved the app's primary working folder, and everything that finds
the project from the current folder broke behind it: the doorbell exited 127, the hooks lost
their module path, and one turn ended in a three-gate deadlock. The same thing had happened on
2026-10-19 (docs/drafts/hook_commands_find_the_project_and_bare_letters_are_stamped_draft_
2026-10-19.md) and was filed as a cause of bare letters while nobody built a door on the `cd`.

Dad, 2026-10-22: "build the cures so it stops happening." And, of the heredoc doorman (2026-08-
24), the reason a note was never going to be enough: "your note saved you but your behavior did
not change until after you saw it."

WHAT IT REFUSES. A `cd` (also `pushd`, `builtin cd`, `command cd`) at the top level of the line,
not inside `( ... )`, whose target is a strict subfolder of the session's own root or of one of
the shared homes the app lists as working directories. WHAT IT LEAVES ALONE: work-copy roots, the
root itself, a bare `cd`, `cd -`, and any target it cannot resolve to a path (a variable, a
substitution). The subshell `( cd x && ... )`, `git -C x`, and a full path are the forms that do
the same work and cannot move the shell, so the refusal text names them.

WHAT IT CANNOT SEE. The trigger is a fit to six measured rows, not a reading of the app (see the
table in the design note). A hook cannot read the app's list of working directories, so the shared
homes are a named superset. A script that `cd`s inside itself cannot move the app's folder and
is out of scope; `source script.sh` whose body does is invisible here, and so is
`eval "cd x"` (text the parser never reads as a command) and a shell function that is DEFINED
with a `cd` and then called (the definition runs nothing, so it is not refused; the call moves).
A `cd` inside an `if`, `while` or `for` body is refused even when the body might never run
(`while false; do cd x; done`): whether a body runs is not decidable from the text, and refusing
is the safe side. That is a stated limit, not a bug (Aria, 2026-10-23).
Aria read the first version against real bash on 2026-10-22 and found four misses and three
over-holds; the assignment prefix, `command -p`, pipelines, background `&`, function
definitions and the arithmetic `<<` are handled and pinned in the tests.
"""

from __future__ import annotations

import posixpath
import re
import shlex

from divineos.core.command_parsing import _ENV_ASSIGN_RE

#: Words after which a following token starts a new simple command in the SAME shell.
_SEGMENT_STARTS = frozenset(
    {
        "&&",
        "||",
        ";",
        ";;",
        "|",
        "&",
        "{",
        "then",
        "do",
        "else",
        "elif",
        "if",
        "while",
        "until",
        "!",
    }
)
_CD_HEADS = frozenset({"cd", "pushd"})
_SHARED_HOMES = (".divineos-shared", ".divineos", ".claude")
# The delimiter must start with a letter or underscore and the `<<` must not be a shift inside
# `$(( ... ))`: Aria 2026-10-22, `x=$((1 << 3))` followed by a line that is only `3` deleted a real cd.
_HEREDOC = re.compile(
    r"(?<![<(])<<-?[ \t]*(['\"]?)([A-Za-z_]\w*)\1[^\n]*\n.*?\n[ \t]*\2[ \t]*(?=\n|$)", re.DOTALL
)
# One definition of "NAME=value before a command is assignment syntax": the shared home's.
_ASSIGNMENT = _ENV_ASSIGN_RE
_PIPE_OR_BACKGROUND = frozenset({"|", "&"})
_DRIVE = re.compile(r"^/([A-Za-z])(/|$)")


def _normalise(path: str, root: str, home: str) -> str | None:
    """A comparable absolute form, or None when the target cannot be known from the text."""
    if not path or "$" in path or "`" in path:
        return None
    text = path.replace("\\", "/")
    if text == "~" or text.startswith("~/"):
        text = home.replace("\\", "/") + text[1:]
    drive = _DRIVE.match(text)
    if drive:
        text = f"{drive.group(1).upper()}:/" + text[drive.end() :]
    if not re.match(r"^[A-Za-z]:/", text) and not text.startswith("/"):
        text = root.replace("\\", "/") + "/" + text
    return posixpath.normpath(text).casefold()


def _strictly_inside(child: str, parent: str) -> bool:
    parent = posixpath.normpath(parent.replace("\\", "/")).casefold()
    return child.startswith(parent.rstrip("/") + "/")


def _list_is_backgrounded(tokens: list[str], start: int) -> bool:
    """True when the and/or list that began before `start` ends in `&`.

    Bash backgrounds the WHOLE `a && b &` list in a subshell, so a `cd` anywhere in it cannot
    move the shell (Aria ran it, 2026-10-23). A `;` ends the list first, so `cd x; ls &` leaves
    the cd in this shell.
    """
    for token in tokens[start:]:
        if token in (";", ";;"):
            return False
        if token == "&":
            return True
    return False


def _targets(command: str) -> list[str]:
    """Every `cd` target that sits at the top level of the line, in order."""
    text = _HEREDOC.sub("", command).replace("\n", " ; ")
    lexer = shlex.shlex(text, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return []  # unbalanced quotes: nothing here can be judged, and the shell will refuse it too
    found: list[str] = []
    depth = 0
    at_start = True
    after_pipe = False  # the previous boundary was `|`: this element is a subshell
    defs: list[bool] = []  # open `{` groups; True when the group is a function body
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token and set(token) <= {"(", ")"}:
            # shlex groups runs of brackets into one token: `()`, `((`, `))`
            if token == "()" and i + 1 < len(tokens) and tokens[i + 1] == "{":
                # `name() {`: a definition. Its body runs nothing until it is called.
                defs.append(True)
                i += 2
                at_start = True
                continue
            depth = max(0, depth + token.count("(") - token.count(")"))
            at_start = token.endswith("(")
            i += 1
            continue
        if token == "{":
            defs.append(False)
            at_start = True
            i += 1
            continue
        if token == "}":
            if defs:
                defs.pop()
            at_start = False
            i += 1
            continue
        if token in _SEGMENT_STARTS:
            after_pipe = token == "|"
            at_start = True
            i += 1
            continue
        if at_start and depth == 0 and not any(defs) and not after_pipe:
            j = i
            while j < len(tokens) and _ASSIGNMENT.match(tokens[j]):
                j += 1  # `FOO=1 cd x` still runs cd in this shell
            if j < len(tokens) and tokens[j] == "function":
                # `function f { ... }` is a definition, so skip to its opening brace
                while i < len(tokens) and tokens[i] != "{":
                    i += 1
                if i < len(tokens):
                    defs.append(True)
                    i += 1
                at_start = True
                continue
            while j < len(tokens) and tokens[j] in ("builtin", "command"):
                j += 1
                while j < len(tokens) and tokens[j] in ("-p", "-v", "-V", "--"):
                    j += 1
            if j < len(tokens) and tokens[j] in _CD_HEADS:
                k = j + 1
                while k < len(tokens) and tokens[k].startswith("-") and tokens[k] != "-":
                    k += 1
                    if tokens[k - 1] == "--":
                        break
                target_ends_in_background = False
                if k < len(tokens) and tokens[k] not in _SEGMENT_STARTS and tokens[k] not in "()":
                    # a trailing `|` or `&` makes this element a subshell too
                    nxt = tokens[k + 1] if k + 1 < len(tokens) else ""
                    target_ends_in_background = nxt in _PIPE_OR_BACKGROUND or _list_is_backgrounded(
                        tokens, k + 1
                    )
                    if not target_ends_in_background:
                        found.append(tokens[k])
        at_start = False
        after_pipe = False
        i += 1
    return found


def should_refuse(command: str, *, project_root: str, home: str) -> bool:
    shared = [home.replace("\\", "/") + "/" + name for name in _SHARED_HOMES]
    for target in _targets(command):
        if target == "-":
            continue
        resolved = _normalise(target, project_root, home)
        if resolved is None:
            continue
        if _strictly_inside(resolved, project_root) or any(
            _strictly_inside(resolved, folder) for folder in shared
        ):
            return True
    return False


def refusal_message(command: str) -> str:
    head = command.strip().splitlines()[0][:120] if command.strip() else ""
    return (
        "CD DRIFT -- a top-level `cd` into a folder the app already knows moves its idea of home, "
        "and the doorbell, the hooks and the gates then look for the project from the wrong folder.\n"
        f"  line: {head}\n"
        "  Measured 2026-10-22 and 2026-10-19: it broke the bell (exit 127), the hooks (no module "
        "named family) and one whole turn. A note did not stop me, so this door does.\n"
        "Do the same work without moving anything, any of these:\n"
        "  - a subshell:   ( cd <folder> && <command> )     cannot move the shell\n"
        "  - git's own:    git -C <folder> <command>\n"
        "  - a full path:  cp <folder>/a <folder>/b         no cd at all\n"
        "If the folder has already moved: the PowerShell tool has no such gate, and one "
        "Set-Location back to the checkout root puts it back.\n"
        "WHAT THIS CANNOT SEE: it reads the command text only, and a target built at run time "
        "(a variable) passes. Falsifier and measurements: "
        "docs/drafts/a_cd_cannot_move_my_home_draft_2026-10-22.md."
    )
