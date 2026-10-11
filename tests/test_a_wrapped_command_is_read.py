"""A command a shell is TOLD to run is read as a command, not skipped as a quoted string.

#619 made the council classifier read each segment's real head so words inside a quote
stop counting as the act. A side effect: ``bash -c "divineos prereg file x ..."`` has head
``bash`` and one quoted token, so the wrapped write scored zero and skipped the council
gate (found 2026-10-11 by the cloud helper's control, psf-9c6f5a9c, which sat red on a side
branch). Same line, same classifier, on main just before #619: fires. On main after: does not.

This is Aria's mutation family. Wrapped real writes must fire exactly as the plain form does;
wrapped looks and wrapped echoes of the words must stay quiet, so the repair cannot become a
hole in the other direction (fire on every ``-c``). The plain forms ride along as controls so a
loosened pattern cannot pass every row.
"""

from __future__ import annotations

import pytest

from divineos.core.command_parsing import shell_command_body
from divineos.core.gravity_classifier import score_substrate_modification

WRITE = "divineos prereg file x --claim y"


def _fires(command: str) -> bool:
    return score_substrate_modification("Bash", (), command).is_council_required


@pytest.mark.parametrize(
    "command",
    [
        WRITE,  # control: the plain form
        f'bash -c "{WRITE}"',
        f"bash -c '{WRITE}'",
        f'sh -c "{WRITE}"',
        f'zsh -c "{WRITE}"',
        f'dash -c "{WRITE}"',
        f'ksh -c "{WRITE}"',
        f'bash -lc "{WRITE}"',
        f'bash -ic "{WRITE}"',
        f'bash --login -c "{WRITE}"',
        f'bash --noprofile --norc -c "{WRITE}"',
        f'sudo bash -c "{WRITE}"',
        f'env VAR=1 bash -c "{WRITE}"',
        f'/bin/bash -c "{WRITE}"',
        f'"C:\\Git\\bin\\bash.exe" -c "{WRITE}"',  # quoted: the tokenizer keeps the backslashes
        f'C:/Git/bin/bash.exe -c "{WRITE}"',
        f'eval "{WRITE}"',
        f'bash -c "cd /tmp && {WRITE}"',
        "bash -c \"echo hi; divineos learn 'x'\"",
        f"bash -c \"bash -c '{WRITE}'\"",
        f"bash -c \"$(printf '{WRITE}')\"",
        'bash -c "divineos audit submit-round r --actor user"',
    ],
)
def test_a_real_write_inside_a_shell_string_fires_as_the_plain_form_does(command):
    assert _fires(command) is True, command


@pytest.mark.parametrize(
    "command",
    [
        'echo "divineos prereg file x --claim y"',  # words, no act
        "bash -c 'echo \"divineos audit list\"'",  # wrapped echo of the words
        f'bash -c "echo {WRITE}"',  # wrapped echo of a whole command line
        'bash -c "divineos prereg show x"',  # wrapped look
        'bash -c "divineos audit list"',  # wrapped look
        f'bash -c "{WRITE} --help"',  # wrapped help
        'bash -c "git status"',  # wrapped, unrelated
        "bash script.sh",  # a shell with no -c
        "bash -x script.sh",  # a flag that is not -c
        'git log --grep "divineos prereg"',  # words in a search pattern
    ],
)
def test_a_wrapped_look_or_an_echo_of_the_words_stays_quiet(command):
    assert _fires(command) is False, command


def test_an_unreadable_shell_string_falls_toward_firing():
    """The body cannot be split (an unbalanced quote), so the old text search decides, and it
    sees the verb. Unreadable means assume heavy, the direction the segment reader already uses."""
    assert _fires('bash -c "divineos prereg file x --claim \'y"') is True


@pytest.mark.parametrize(
    ("tokens", "expected"),
    [
        (["bash", "-c", "ls"], "ls"),
        (["sh", "-lc", "ls"], "ls"),
        (["bash", "--login", "-c", "ls"], "ls"),
        (["/usr/bin/zsh", "-ic", "ls"], "ls"),
        (["eval", "ls", "-la"], "ls -la"),
        (["bash", "script.sh"], None),
        (["bash", "-x", "script.sh"], None),
        (["bash", "-c"], None),
        (["python", "-c", "print(1)"], None),
        ([], None),
    ],
)
def test_the_shared_helper_names_the_body_a_shell_is_told_to_run(tokens, expected):
    assert shell_command_body(tokens) == expected
