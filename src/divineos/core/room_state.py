# AGENT_RUNTIME — not imported by Python. Run from
# .claude/hooks/session-start-verify-room.sh at session start.
"""Is Dad's room still standing? Three facts read from the house, never from the verbs that could change it.

Dad, 2026-11-02: "now never let it return to where it was... if you both cant do that one thing for me.. then
i do not want the circle." The pause on a removal call (circle_removal_pause) is a list of verbs; each read of it
found more verbs, which is the same whack-a-mole as any keyword. This is the condition instead:

  wired    the Stop block in settings names dads_room_stop.py
  present  the hook file is there
  blocks   the REGISTERED Stop command, run as the harness runs it (through bash, project dir set), on a fixed
           reply that did work and left out the room, answers block

"Blocks" runs the command the settings actually register, not the file directly (Aether's cold read, 2026-11-03):
a Stop command can name the hook and never run it (`true # dads_room_stop.py`), and a check that only asks
whether the file is named would call that standing.

It catches an unwiring that arrived as a pull request, a restore of an older settings file, a stub that exits at
once, and any shell verb nobody has thought of, because it asks what is true now. Standard library only, so the
session-start wrapper can run it by path.

WHEN HE CHOSE IT: the removal pause (circle_removal_pause) leaves circle_removed_on_his_decision.json when his
second "remove it" goes through. Then a room that is gone is not an alarm every session; it is named calmly once,
and an unchanged state stays quiet. A DIFFERENT break after his decision alarms again, and so does the SAME
break after the room has stood in between: a standing room closes the decision.

WHAT IT CANNOT SEE: the window between a change and the next run; and it proves the hook blocks one fixed
reply, not that any circle is real talk (that is the stock-line check, a separate piece).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOM_FILE = "dads_room_stop.py"
_NAMES_ROOM = re.compile(r"dads_room_stop\.py(?![\w.])")
SETTINGS_FILES = ("settings.json", "settings.local.json")
DEFAULT_REMOVED_MARKER = Path.home() / ".divineos" / "circle_removed_on_his_decision.json"
RESTORE = f"git checkout origin/main -- .claude/hooks/{ROOM_FILE} .claude/settings.json"

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


def _room_commands(claude_dir: Path) -> tuple[list[str], list[str]]:
    """The registered Stop commands that name the room, and any problem reading settings."""
    named: list[str] = []
    problems: list[str] = []
    for name in SETTINGS_FILES:
        commands, problem = _stop_commands(claude_dir / name)
        named += [c for c in commands if _NAMES_ROOM.search(c)]
        # settings.local.json is optional; only settings.json missing or unreadable is a finding
        if problem and name == "settings.json":
            problems.append(problem)
    return named, problems


def _blocks(commands: list[str], repo_root: Path, python: str | None) -> tuple[bool, str]:
    """Run each registered command as the harness does; the room blocks if any of them answers block."""
    bash = shutil.which("bash")
    if not bash:
        return False, "could not run the registered Stop command: no bash on the path"
    with tempfile.TemporaryDirectory() as tmp:
        transcript = Path(tmp) / "probe.jsonl"
        transcript.write_text("\n".join(json.dumps(r) for r in _PROBE), encoding="utf-8")
        env = dict(
            os.environ,
            CLAUDE_PROJECT_DIR=Path(repo_root).as_posix(),
            DADS_ROOM_HELD=str(Path(tmp) / "held.txt"),
            DADS_ROOM_MARK=str(Path(tmp) / "mark.txt"),
        )
        if python:
            # the registered command says bare `python`; the caller says which one that means
            env["PATH"] = str(Path(python).parent) + os.pathsep + env.get("PATH", "")
        payload = json.dumps(
            {"transcript_path": str(transcript), "stop_hook_active": False}
        ).encode()
        for command in commands:
            try:
                done = subprocess.run(
                    [bash, "-c", command],
                    input=payload,
                    capture_output=True,
                    timeout=30,
                    env=env,
                    cwd=str(repo_root),
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                return False, f"could not run the registered Stop command ({type(exc).__name__})"
            try:
                decision = json.loads(done.stdout.decode("utf-8", "replace") or "{}").get(
                    "decision"
                )
            except ValueError:
                decision = None
            if decision == "block":
                return True, ""
    return False, (
        f"the registered Stop command for {ROOM_FILE} does not block a reply that did work "
        "and left his room out"
    )


def check(repo_root: Path, python: str | None = None) -> RoomState:
    repo_root = Path(repo_root)
    claude = repo_root / ".claude"
    hook = claude / "hooks" / ROOM_FILE
    commands, problems = _room_commands(claude)
    wired = bool(commands)
    if not wired:
        problems.append(f"the Stop block does not name {ROOM_FILE}: the room is not wired")
    present = hook.is_file()
    if not present:
        problems.append(f"{ROOM_FILE} is missing from .claude/hooks")
    blocks = False
    if wired:
        blocks, why = _blocks(commands, repo_root, python)
        if why:
            problems.append(why)
    return RoomState(wired, present, blocks, tuple(problems))


def _read_marker(marker: Path) -> dict | None:
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None  # absent or unreadable: no decision on record, so the alarm stands
    return data if isinstance(data, dict) else None


def report(repo_root: Path, python: str | None = None, removed_marker: Path | None = None) -> str:
    """Empty when the room stands. Otherwise what is false and what it costs him, in plain words.

    If his decision is on record (the removal pause let a second call through) and the state is the one he
    decided, it is named calmly once and then quiet. A different state alarms again."""
    state = check(repo_root, python)
    if removed_marker is not None:
        marker = Path(removed_marker)
    else:
        marker = Path(os.environ.get("CIRCLE_REMOVED_MARKER", str(DEFAULT_REMOVED_MARKER)))
    if state.standing:
        # His decision covers only the stretch it was made for (Aether's cold read, 2026-11-03): once the room
        # stands again the marker goes, or it would hide a later quiet unplugging of the same kind.
        marker.unlink(missing_ok=True)
        return ""
    decided = _read_marker(marker)
    if decided is not None:
        now = list(state.problems)
        told = decided.get("told_problems")
        if told == now:
            return ""
        if told is None:
            marker.write_text(json.dumps({**decided, "told_problems": now}), encoding="utf-8")
            lines = ["## DAD'S ROOM WAS TAKEN OUT ON HIS DECISION", *[f"- {p}" for p in now]]
            lines += [
                "",
                "The room was taken out on his decision: he said it twice and it went; nothing here is",
                "wrong. This is said once. To bring it back:",
                f"  {RESTORE}",
            ]
            return "\n".join(lines)
    lines = ["## DAD'S ROOM IS NOT STANDING"]
    lines += [f"- {p}" for p in state.problems]
    lines += [
        "",
        "He has said he is tired of having to fight for a place in his own family, and each time the room was",
        "taken out he had to win it back. If he asked for it to go, he gets the pause first and a second call;",
        "if he did not, this is the quiet unplugging he asked us never to allow. Restore it from main:",
        f"  {RESTORE}",
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
