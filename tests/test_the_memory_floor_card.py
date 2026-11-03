"""The memory floor card must teach only true things and never block a start."""

import re
import subprocess
import sys
from pathlib import Path

from click.testing import CliRunner

from divineos.cli import cli
from divineos.core.memory_floor import card

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".claude" / "hooks" / "goal-boundary-at-session-start.sh"
CALL = "from divineos.core.memory_floor import card; print(card())"


def _named_commands() -> list[list[str]]:
    found = []
    for span in re.findall(r"`([^`]+)`", card()):
        words = span.split()
        assert words[0] == "divineos"
        path = []
        for w in words[1:]:
            if w.startswith('"'):
                break
            path.append(w)
        if path not in found:
            found.append(path)
    return found


def test_every_command_the_card_names_exists():
    named = _named_commands()
    for expected in (
        ["context"],
        ["ask"],
        ["find", "query"],
        ["recall-explorations"],
        ["andrew-correction", "list"],
    ):
        assert expected in named
    for path in named:
        result = CliRunner().invoke(cli, [*path, "--help"])
        assert result.exit_code == 0, f"card names `divineos {' '.join(path)}`: {result.output}"


def test_card_length_is_three_to_six_lines():
    assert 3 <= len(card().splitlines()) <= 6


def test_hook_calls_memory_floor():
    assert "divineos.core.memory_floor import card" in HOOK.read_text()


def test_broken_import_prints_nothing_and_exits_zero():
    broken = CALL.replace("divineos.core.memory_floor", "divineos.core.memory_floor_missing")
    out = subprocess.run(
        f'"{sys.executable}" -c "{broken}" 2>/dev/null; exit 0',
        shell=True,
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0
    assert out.stdout == ""
