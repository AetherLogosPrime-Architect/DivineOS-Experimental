"""The remedy-chain check refuses operator commands; it never crashes on them.

A clean merge kept two module-level ``_OPERATOR_CHARS`` in command_parsing --
#555's frozenset for _chain_links and main's str for the shell tokenizer. The
later binding won, so ``set(token) <= str`` raised on exactly the piped and
redirected commands the check exists to refuse (council-a8d569f767c2). Plain
commands never reach that comparison, which is why everything else stayed green.
"""

from __future__ import annotations

import pytest

from divineos.core import command_parsing as cp


@pytest.mark.parametrize(
    "command",
    [
        "divineos briefing | tee out.txt",
        "divineos briefing > out.txt",
        "divineos briefing & sleep 1",
        "(divineos briefing)",
    ],
)
def test_an_operator_in_the_chain_is_refused_not_raised(command):
    assert cp._chain_links(command) is None


def test_a_plain_chain_still_reads():
    assert cp._chain_links("cd /tmp && divineos briefing") is not None


def test_the_tokenizer_still_gets_its_string():
    # shlex needs a str for punctuation_chars; the set must not be handed to it.
    assert isinstance(cp._OPERATOR_CHARS, str)
    assert cp._shell_tokens("a | b") is not None
