"""The substrate-write and consolidation features read the COMMAND, not its words.

Aria hit this twice on 2026-10-09: the build-flow gate treated a heredoc body
that merely mentioned the prereg command, and the help flag of that command, as
if they were writes to the store. Both features searched the raw text for
`divineos <verb>`, so any text carrying those two words fired them. The
git-commit feature had already been moved to reading the command's real head;
these two had not.

Positives pin that real invocations still fire (the fix must not cost the
detection). Negatives are the words-without-the-act shapes. The last control
pins that a command the splitter cannot read still fails toward scrutiny.
"""

import pytest

from divineos.core.gravity_classifier import score_substrate_modification

_D = "divi" + "neos"


def _fired(command: str) -> tuple[str, ...]:
    return tuple(score_substrate_modification("Bash", bash_command=command).fired_features)


@pytest.mark.parametrize(
    "command",
    [
        f"{_D} prereg file x",
        f"cd /tmp && {_D} learn y",
        f"sudo {_D} audit submit x",
        f"{_D} decide x > out.txt",
        f"python -m {_D} journal save x",
    ],
)
def test_a_real_invocation_still_fires_the_store_write_feature(command):
    assert "substrate-write-cli" in _fired(command)


@pytest.mark.parametrize(
    "command",
    [
        f"{_D} prereg --help",
        f"{_D} prereg file --help",
        f"{_D} learn -h",
        f'echo "{_D} prereg file x"',
        f"git status # {_D} learn",
    ],
)
def test_words_without_the_act_do_not_fire_the_store_write_feature(command):
    assert "substrate-write-cli" not in _fired(command)


def test_a_heredoc_body_that_mentions_the_command_does_not_fire_it():
    command = f"cat <<'EOF' | wc -l\nrun {_D} prereg file later\nEOF"
    assert "substrate-write-cli" not in _fired(command)


def test_a_real_invocation_after_a_heredoc_body_still_fires():
    command = f"cat <<'EOF' | wc -l\nnotes\nEOF\n{_D} learn z"
    assert "substrate-write-cli" in _fired(command)


@pytest.mark.parametrize("verb", ["extract", "sleep"])
def test_a_real_consolidation_command_still_fires(verb):
    assert "consolidation-cli" in _fired(f"{_D} {verb}")


@pytest.mark.parametrize("verb", ["extract", "sleep"])
def test_consolidation_words_without_the_act_do_not_fire(verb):
    assert "consolidation-cli" not in _fired(f'echo "{_D} {verb}"')
    assert "consolidation-cli" not in _fired(f"{_D} {verb} --help")


def test_a_command_the_splitter_cannot_read_still_fails_toward_scrutiny():
    """Control. A substitution hides what runs, so the old text search stays."""
    assert "substrate-write-cli" in _fired(f"echo $({_D} learn x)")
