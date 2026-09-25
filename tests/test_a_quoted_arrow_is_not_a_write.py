"""A quoted arrow is not a write, and nothing that writes becomes a read.

Aether, 2026-09-21: the read-only probe called ``git log --grep='a -> b'`` a
write, because it scanned for ``>`` without setting quoted text aside.
Reproduced 2026-09-25 on the gate as it stood on main.

Every command below uses a verb that IS on the probe list, so a refusal can
only come from the write detection. The first reproduction used ``grep``,
which is not on the list at all and was refused with or without an arrow; the
control test below exists so that mistake cannot recur silently.

The walk on the fix (walk-734fa481e6e2) found three ways a naive fix turns a
real write into a read. Each has a pin, and each fails if the fix is made the
naive way.
"""

from __future__ import annotations

import pytest

from divineos.core.command_parsing import blank_quoted_spans
from divineos.hooks.pre_tool_use_gate import _is_readonly_probe

# (read with a quoted arrow, the same read with the arrow removed)
QUOTED_ARROW_READS = [
    ("git log --grep='fixed > broken'", "git log --grep='fixed broken'"),
    ("git log --grep='a -> b'", "git log --grep='a b'"),
    ("git log --format='%h -> %s' -5", "git log --format='%h %s' -5"),
    ('git log --grep="value > threshold"', 'git log --grep="value threshold"'),
    # the self-referential case: searching the gate's history for the character
    # it misread
    (
        "git log -S'>' -- src/divineos/hooks/pre_tool_use_gate.py",
        "git log -S'x' -- src/divineos/hooks/pre_tool_use_gate.py",
    ),
    # a quoted --output is a search term, not a flag
    ("git log --grep='--output'", "git log --grep='output'"),
]

# Every one writes a file and must stay refused. All use probe verbs.
WRITES = [
    "git log > out.txt",
    "git diff --output=patch.diff",
    # a quoted arrow AND a real redirect
    "git log --grep='a > b' > out.txt",
    # Hoare: a quoted TARGET must not blank to nothing and read as /dev/null
    'git log > "log.txt"',
    "git log > 'log.txt'",
    # Aristotle: double quotes still expand, so this really writes f
    'git log --grep="$(echo x > f)"',
    'git log --grep="`echo x > f`"',
    # Schneier: an escaped quote is a literal character; the redirect is real
    'git log --grep=\\" > out.txt \\"',
    # ANSI-C quoting is not blanked; the redirect after it is real
    "git log --grep=$'a' > out.txt",
    # unterminated quote: nothing can be shown to be quoted
    "git log --grep='a > b",
]


@pytest.mark.parametrize("with_arrow,without", QUOTED_ARROW_READS)
def test_the_control_is_a_read_so_the_arrow_is_what_is_tested(with_arrow, without):
    assert _is_readonly_probe(without) is True


@pytest.mark.parametrize("with_arrow,without", QUOTED_ARROW_READS)
def test_a_quoted_arrow_is_a_read(with_arrow, without):
    assert _is_readonly_probe(with_arrow) is True


@pytest.mark.parametrize("cmd", WRITES)
def test_a_write_stays_refused(cmd):
    assert _is_readonly_probe(cmd) is False


class TestBlankQuotedSpans:
    def test_single_quoted_text_is_filled_to_the_same_length(self):
        out = blank_quoted_spans("git log --grep='a > b'")
        assert out is not None
        assert len(out) == len("git log --grep='a > b'")
        assert ">" not in out

    def test_a_filled_span_is_still_a_token(self):
        # Hoare's case: a quoted redirect target stays a target.
        out = blank_quoted_spans('git log > "log.txt"')
        assert out is not None
        assert out.split()[-1] not in ("", ">")

    def test_double_quotes_that_expand_are_left_as_shell(self):
        out = blank_quoted_spans('git log --grep="$(echo x > f)"')
        assert out is not None
        assert "echo x > f" in out

    @pytest.mark.parametrize(
        "text",
        [
            'git log --grep=\\" > out.txt \\"',  # escaped quote
            "git log --grep=$'a'",  # ANSI-C string
            "git log --grep='unterminated",  # unbalanced
        ],
    )
    def test_cannot_fill_safely_says_so(self, text):
        assert blank_quoted_spans(text) is None
