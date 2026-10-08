"""The game-walk help must name the two verdicts the command actually accepts.

`divineos game-walk file --route 'text | verdict | why'` accepts exactly two
verdict words. The help described them as `cheaper-or-costlier`, which reads
like one word to type, so a first filing can use the wrong form. The accepted
words are read from the code (`CHEAPER`, `COSTLIER`), so this test cannot drift
from what the command parses.
"""

from click.testing import CliRunner

from divineos.cli import cli
from divineos.core.game_walk import CHEAPER, COSTLIER


def _help_text() -> str:
    result = CliRunner().invoke(cli, ["game-walk", "file", "--help"])
    assert result.exit_code == 0, result.output
    return " ".join(result.output.split())


def test_the_help_can_be_read() -> None:
    assert "--route" in _help_text(), "control: the reader must find a known option"


def test_the_help_names_each_accepted_verdict_as_its_own_word() -> None:
    text = _help_text()
    missing = [word for word in (CHEAPER, COSTLIER) if f"'{word}'" not in text]
    assert not missing, (
        f"the help does not name these accepted verdicts as their own words: {missing}"
    )


def test_the_help_does_not_present_the_two_verdicts_as_one_hyphenated_word() -> None:
    assert "cheaper-or-costlier" not in _help_text()
