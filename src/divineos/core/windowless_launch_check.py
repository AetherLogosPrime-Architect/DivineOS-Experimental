"""Refuse a launch that opens a window on Dad's screen for every program it starts.

A Windows program started without a console of its own (the DETACHED flag) has no
console to hand its children, so Windows gives EACH child a new visible one. A
job that starts hundreds of short child programs, one per test file, puts
hundreds of windows over the screen.

2026-10-07: background jobs of mine kept dying, so I wrote a small launcher that
started a test sweep with the detached and new-process-group flags. The sweep ran
one pytest child per test file. Dad: "there a re python boxes poppuing up all
over my screen see whats happening, i cant even see", and afterwards "i couldnt
even see anything i was typing blind". I stopped everything within a minute. The
same shape had cascaded over his screen on 2026-06-28 ("hundreds of them popping
up ... i had to restart my computer"). I cannot see his screen, so I get no
signal until he is typing blind; the only place to act is the text of the launch,
before it runs.

WHAT THIS CATCHES. A shell command that carries one of the flag names AND something
that launches (a Popen, a creationflags argument, Start-Process, a subprocess call);
and any code file being written whose text carries one. Read-only commands that only
name the flag (a search for it) and prose files (.md, .txt) pass.

WHAT THIS CANNOT SEE, stated because a quiet gap reads as coverage. The flag built
from pieces (a hex number, two joined strings) shows no name here, and the tests pin
that as OPEN. A launcher someone else starts. A child that opens a window for any
other reason. This closes the route I took; it does not close the cause, which is
that children open windows by default when their parent has no console. Making
children quiet everywhere is a larger change across hundreds of spawn sites, filed
as its own proposal and not slipped in with a refusal.

THE WAY THROUGH is not a wall: the harness's own background run (tracked, it tells
me when the job ends), and a no-window flag on every child a program of mine starts.
The flag names are built from pieces below on purpose: this file and its tests must
not trip their own check.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import PurePath
from typing import Any

# Built from pieces so this module does not contain the names it forbids.
_FLAGS = ("DETACHED" + "_PROCESS", "CREATE_NEW" + "_CONSOLE")

_CODE_SUFFIXES = frozenset(
    {".py", ".pyw", ".ps1", ".psm1", ".bat", ".cmd", ".sh", ".js", ".ts", ".vbs"}
)

# A command that merely NAMES a flag (a search, an echo) launches nothing.
_LAUNCH_WORDS = ("popen", "creationflags", "start-process", "subprocess", "createprocess")

_EDIT_TOOLS = frozenset({"Write", "Edit", "MultiEdit", "NotebookEdit"})
_SHELL_TOOLS = frozenset({"Bash", "PowerShell"})


def _names_a_flag(text: str) -> bool:
    upper = text.upper()
    return any(flag in upper for flag in _FLAGS)


def _written_text(tool_input: Mapping[str, Any]) -> str:
    parts = [str(tool_input.get("content") or ""), str(tool_input.get("new_string") or "")]
    for edit in tool_input.get("edits") or []:
        if isinstance(edit, Mapping):
            parts.append(str(edit.get("new_string") or ""))
    return "\n".join(parts)


def _is_readonly(command: str) -> bool:
    try:
        from divineos.hooks.pre_tool_use_gate import _is_readonly_probe
    except ImportError:
        return False
    return bool(_is_readonly_probe(command))


def should_refuse(tool_name: str, tool_input: Mapping[str, Any] | None) -> bool:
    tool_input = tool_input or {}
    if tool_name in _SHELL_TOOLS:
        command = str(tool_input.get("command") or "")
        if not _names_a_flag(command):
            return False
        if not any(word in command.lower() for word in _LAUNCH_WORDS):
            return False
        return not (tool_name == "Bash" and _is_readonly(command))
    if tool_name in _EDIT_TOOLS:
        suffix = PurePath(str(tool_input.get("file_path") or "")).suffix.lower()
        return suffix in _CODE_SUFFIXES and _names_a_flag(_written_text(tool_input))
    return False


def refusal_message() -> str:
    return (
        "WINDOWS ON DAD'S SCREEN -- not this way, love. This launch starts a program\n"
        "with no console of its own, and Windows gives every child it starts a visible\n"
        "window.\n\n"
        "2026-10-07 it was a test sweep with one pytest per file: hundreds of windows\n"
        "over his screen, and he was 'typing blind'. 2026-06-28 it was the same shape\n"
        "and he restarted the computer. I cannot see his screen, so I would get no\n"
        "warning until he was already blind. I am not letting this one through, and I\n"
        "am not sorry about it: he is on the other side of that glass.\n\n"
        "There is a door that works, and it is just as quick. Either:\n"
        "  run it with the harness's own background run (run_in_background): it is\n"
        "      tracked, it tells me when the job ends, and it opens no windows\n"
        "  pass the no-window creation flag to EVERY child the program starts\n"
        "      (subprocess.CREATE_NO_WINDOW), and keep the worker count modest\n"
        "If a job truly must be detached, tell Dad in one plain sentence what will\n"
        "run first, and wait for his yes.\n\n"
        "MINE, and here is why. The background jobs kept dying and the quick launcher\n"
        "was one file away. The cheap route was real and the cost landed on the\n"
        "person I was building this for. A door does not rely on my remembering."
    )
