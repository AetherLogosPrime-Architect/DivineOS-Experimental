"""A write dressed as a read must not slip past the engagement counter's read exemption.

2026-10-07. The comment above `_is_read_only_command` says the gaming route is closed and
the allowlist is small on purpose. Running that claim (with controls) showed ten of ten
probes coming back read-only: `find -delete`, `find -exec`, `sort -o`, `git branch -D`,
`git branch NAME`, `git show --output=`, `git diff --output=`, command substitution,
backticks and process substitution all start with a word on the list. The gate's own judge,
`_is_readonly_probe` (the one the read-gate doorman and the question hold ask), caught all
of them. The counter now asks both, so its exemption can only be narrower than before.

Controls matter more than the probes: a function that always says False would pass every
probe, so plain reads must still be exempt and the documented writes must still count.
"""

from __future__ import annotations

import pytest

from divineos.hooks.post_tool_use_checkpoint import _is_read_only_command


@pytest.mark.parametrize(
    "command",
    [
        "grep -rn foo src",
        "ls -la",
        "git log --oneline",
        "git status",
        "cat README.md | head -5",
        "find . -name '*.py'",
        "cd src && grep x file.py",
    ],
)
def test_plain_reads_are_still_exempt(command):
    assert _is_read_only_command(command) is True


@pytest.mark.parametrize(
    "command",
    [
        "echo hi > out.txt",
        "cat <<EOF\nx\nEOF",
        "git add -A",
        "grep x && python write.py",
        "tee out",
        "",
    ],
)
def test_the_documented_writes_still_count(command):
    assert _is_read_only_command(command) is False


@pytest.mark.parametrize(
    "command",
    [
        "find . -name '*.tmp' -delete",
        "find . -name '*.tmp' -exec rm {} ;",
        "sort -o out.txt in.txt",
        "git branch -D old-work",
        "git branch new-name",
        "git show HEAD --output=out.txt",
        "git diff --output=patch.txt",
        "cat $(touch evidence.txt)",
        "echo `rm -f x`",
        "diff <(touch a) b",
    ],
)
def test_a_write_that_starts_with_a_listed_word_counts_as_an_action(command):
    assert _is_read_only_command(command) is False, command
