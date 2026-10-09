"""The places that tell you how to file a pre-registration must name every
option the command actually requires.

`divineos prereg file` refuses a first attempt that omits any required option.
Two places that teach the command left some out, so a first try copied from
them was refused for a reason the reminder never mentioned: the obligations
block message listed only `--claim` and `--falsifier`, and the prereg skill's
filing example left out `--embarrassing`.

The list of required options is read from the command itself, so this test
cannot drift from what the command enforces.
"""

from pathlib import Path

import click

from divineos.cli import cli
from divineos.core.obligations import format_block_message

REPO = Path(__file__).resolve().parent.parent


def _required_prereg_file_options() -> list[str]:
    cmd = cli.commands["prereg"].commands["file"]
    names = []
    for param in cmd.params:
        if isinstance(param, click.Option) and param.required:
            names.append(max(param.opts, key=len))
    return names


def test_the_command_has_required_options_to_check() -> None:
    required = _required_prereg_file_options()
    assert "--claim" in required, "control: the reader must find a known required option"
    assert len(required) >= 4


def test_obligations_reminder_names_every_required_option() -> None:
    message = format_block_message({"total": 0})
    reminder = [ln for ln in message.splitlines() if "divineos prereg file" in ln]
    assert reminder, "the block message should show how to file a pre-registration"
    missing = [opt for opt in _required_prereg_file_options() if opt not in reminder[0]]
    assert not missing, f"the reminder omits required option(s): {missing}"


def test_prereg_skill_example_names_every_required_option() -> None:
    skill = (REPO / ".claude" / "skills" / "prereg" / "SKILL.md").read_text(encoding="utf-8")
    block = skill.split("## Filing", 1)[1].split("```", 2)[1]
    missing = [opt for opt in _required_prereg_file_options() if opt not in block]
    assert not missing, f"the skill's filing example omits required option(s): {missing}"
