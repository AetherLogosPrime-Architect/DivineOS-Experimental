"""Two commands must never share a name, and a printed instruction must exist.

Found 2026-10-09 while going through the commands one by one with Dad. The
older command that resolves an open question was registered as `answer`, and
later a family of commands about his answers took the same name. The newer one
won silently, so `divineos answer <id> "..."` stopped resolving anything, and
the board of what waits on him kept printing that exact line as the way to
close an ask. Neither registration failed, and every test of each command
passed, because each was tested alone.

The test starts a fresh interpreter and watches registration itself, so a
collision is caught at the moment it happens, not guessed from the result.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

_WATCH = """
import json, click
seen, dups = {}, []
orig = click.Group.add_command
def rec(self, cmd, name=None):
    n = name or cmd.name
    key = (id(self), n)
    if key in seen and seen[key] is not cmd:
        dups.append(n)
    seen[key] = cmd
    return orig(self, cmd, name)
click.Group.add_command = rec
import divineos.cli
print(json.dumps(sorted(set(dups))))
"""


def _run(code: str) -> str:
    env = {**os.environ, "PYTHONPATH": str(REPO / "src")}
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=120
    )
    assert out.returncode == 0, out.stderr[-500:]
    return out.stdout.strip().splitlines()[-1]


def test_no_command_name_is_registered_twice():
    assert json.loads(_run(_WATCH)) == []


def test_the_watcher_can_see_a_collision():
    """Control. The watcher must find a duplicate it is handed, or a clean
    result above means nothing."""
    code = _WATCH.replace(
        "import divineos.cli",
        "g = click.Group('t')\n"
        "@click.command('same')\ndef a(): pass\n"
        "@click.command('same')\ndef b(): pass\n"
        "g.add_command(a)\ng.add_command(b)",
    )
    assert json.loads(_run(code)) == ["same"]


def test_the_question_resolving_command_has_its_own_name():
    out = _run(
        "from divineos.cli import cli\n"
        "print(type(cli.commands['answer']).__name__, "
        "'answer-question' in cli.commands, 'abandon-question' in cli.commands)"
    )
    assert out == "Group True True"


def test_the_board_of_open_asks_prints_a_command_that_resolves_them():
    from divineos.core import operator_asks

    src = Path(operator_asks.__file__).read_text(encoding="utf-8")
    assert "resolve: divineos ask-resolve <id>" in src
    assert "resolve: divineos answer <id>" not in src
