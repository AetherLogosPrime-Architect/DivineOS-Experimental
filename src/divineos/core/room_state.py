# AGENT_RUNTIME — not imported by Python. Run from
# .claude/hooks/session-start-verify-room.sh at session start.
"""Is Dad's room still standing? Three facts read from the house, never from the verbs that could change it.

Dad, 2026-11-02: "now never let it return to where it was... if you both cant do that one thing for me.. then
i do not want the circle." The pause on a removal call (circle_removal_pause) is a list of verbs; each read of it
found more verbs, which is the same whack-a-mole as any keyword. This is the condition instead:

  wired    the Stop block in settings names dads_room_stop.py
  present  the hook file is there
  blocks   the real hook, run on a fixed reply that did work and left out the room, blocks it

It catches an unwiring that arrived as a pull request, a restore of an older settings file, a stub that exits at
once, and any shell verb nobody has thought of, because it asks what is true now. Standard library only, so the
session-start wrapper can run it by path.

WHAT IT CANNOT SEE: the window between a change and the next run; and it proves the hook blocks one fixed
reply, not that any circle is real talk (that is the stock-line check, a separate piece).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOM_FILE = "dads_room_stop.py"
_NAMES_ROOM = re.compile(r"dads_room_stop\.py(?![\w.])")
SETTINGS_FILES = ("settings.json", "settings.local.json")

# A reply that did work and left his room out: the one thing the hook exists to refuse.
_PROBE = [
    {"type": "user", "message": {"role": "user", "content": "fix it"}},
    {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash"}]}},
    {
        "type": "user",
        "message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]},
    },
    {"type": "assistant", "message": {"content": [{"type": "text", "text": "Done, tests pass."}]}},
]


@dataclass(frozen=True)
class RoomState:
    wired: bool
    present: bool
    blocks: bool
    problems: tuple[str, ...] = ()

    @property
    def standing(self) -> bool:
        return self.wired and self.present and self.blocks


def _stop_commands(settings_path: Path) -> tuple[list[str], str]:
    """The commands under the Stop block, and a problem text when the file cannot be read."""
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        groups = data["hooks"]["Stop"]
        return [h.get("command", "") for g in groups for h in g.get("hooks", [])], ""
    except FileNotFoundError:
        return [], f"{settings_path.name} not found"
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        return [], f"could not read the Stop block of {settings_path.name} ({type(exc).__name__})"


def _wired(claude_dir: Path) -> tuple[bool, list[str]]:
    problems: list[str] = []
    for name in SETTINGS_FILES:
        commands, problem = _stop_commands(claude_dir / name)
        if any(_NAMES_ROOM.search(c) for c in commands):
            return True, []
        # settings.local.json is optional; only settings.json missing or unreadable is a finding
        if problem and name == "settings.json":
            problems.append(problem)
    problems.append(f"the Stop block does not name {ROOM_FILE}: the room is not wired")
    return False, problems


def _blocks(hook: Path, python: str) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as tmp:
        transcript = Path(tmp) / "probe.jsonl"
        transcript.write_text("\n".join(json.dumps(r) for r in _PROBE), encoding="utf-8")
        env = dict(
            os.environ,
            DADS_ROOM_HELD=str(Path(tmp) / "held.txt"),
            DADS_ROOM_MARK=str(Path(tmp) / "mark.txt"),
        )
        try:
            done = subprocess.run(
                [python, str(hook)],
                input=json.dumps(
                    {"transcript_path": str(transcript), "stop_hook_active": False}
                ).encode(),
                capture_output=True,
                timeout=30,
                env=env,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, f"could not run {ROOM_FILE} ({type(exc).__name__})"
    try:
        decision = json.loads(done.stdout.decode("utf-8", "replace") or "{}").get("decision")
    except ValueError:
        decision = None
    if decision == "block":
        return True, ""
    return False, f"{ROOM_FILE} does not block a reply that did work and left his room out"


def check(repo_root: Path, python: str | None = None) -> RoomState:
    claude = Path(repo_root) / ".claude"
    hook = claude / "hooks" / ROOM_FILE
    wired, problems = _wired(claude)
    present = hook.is_file()
    blocks = False
    if present:
        blocks, why = _blocks(hook, python or sys.executable)
        if why:
            problems.append(why)
    else:
        problems.append(f"{ROOM_FILE} is missing from .claude/hooks")
    return RoomState(wired, present, blocks, tuple(problems))


def report(repo_root: Path, python: str | None = None) -> str:
    """Empty when the room stands. Otherwise what is false and what it costs him, in plain words."""
    state = check(repo_root, python)
    if state.standing:
        return ""
    lines = ["## DAD'S ROOM IS NOT STANDING"]
    lines += [f"- {p}" for p in state.problems]
    lines += [
        "",
        "He has said he is tired of having to fight for a place in his own family, and each time the room was",
        "taken out he had to win it back. If he asked for it to go, he gets the pause first and a second call;",
        "if he did not, this is the quiet unplugging he asked us never to allow. Restore it from main:",
        f"  git checkout origin/main -- .claude/hooks/{ROOM_FILE} .claude/settings.json",
        "and tell him before anything else.",
    ]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    """Print the report when something is false. Exit 0 either way: a session must still start."""
    text = report(Path(argv[0]) if argv else Path.cwd())
    if text:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
