"""A bare name under the word `dark` can only be read one way.

2026-09-19: the register printed `dark: <name>` and nothing else. I read that
as a finding and reported three guards to Andrew as switched off, then opened
them and found all three deliberate, each with a dated reason in its own first
lines. The reason existed the whole time and was discarded at the boundary.

Both directions pinned. Surfacing reasons must not quiet the case that has
none — that one is the actual finding and has to get louder once its
neighbours carry text.
"""

from __future__ import annotations

import pytest

from scripts.generate_automation_register import HOOKS_DIR, declared_off_reason


@pytest.fixture
def hook(tmp_path):
    def write(body: str):
        p = tmp_path / "some-hook.sh"
        p.write_text(body, encoding="utf-8")
        return p

    return write


def test_a_declared_reason_comes_back_as_its_own_words(hook):
    p = hook("#!/bin/bash\n# INTENTIONALLY UNWIRED 2026-09-03, waiting on the opt-in.\n")
    got = declared_off_reason(p)
    assert got.readable
    assert got.text is not None
    assert "INTENTIONALLY UNWIRED" in got.text
    assert "opt-in" in got.text, "the reason itself travels, not a flag"


def test_superseded_counts_as_a_reason(hook):
    p = hook("#!/bin/bash\n# SUPERSEDED by the router; logic moved.\n")
    assert "SUPERSEDED" in (declared_off_reason(p).text or "")


def test_a_hook_declaring_nothing_returns_none(hook):
    """The case that matters. Silence here is the finding, not a pass."""
    p = hook("#!/bin/bash\n# PreToolUse hook that does a thing.\necho hi\n")
    got = declared_off_reason(p)
    assert got.text is None
    assert got.readable, "a readable file that declares nothing is the finding"


def test_an_unreadable_file_is_unknown_rather_than_a_silent_guard(tmp_path):
    """This test used to assert the two answers were the same answer.

    It read ``is None`` and passed, which is how a cannot-read came to print
    as NO REASON DECLARED -- the loudest line this register has, raised on no
    evidence at all. The test pinned the collapse instead of catching it, the
    same way the correction-rate test pinned a verdict of healthy on no data.
    """
    got = declared_off_reason(tmp_path / "nope.sh")
    assert got.text is None
    assert not got.readable, "cannot-read must be distinguishable from declares-nothing"


def test_a_reason_buried_past_the_header_is_not_counted(hook):
    """Declared means declared where a reader lands, not anywhere in the file."""
    p = hook("#!/bin/bash\n" + "# filler\n" * 30 + "# INTENTIONALLY UNWIRED far below\n")
    assert declared_off_reason(p).text is None


def test_the_long_reason_is_truncated_rather_than_flooding_the_line(hook):
    p = hook("#!/bin/bash\n# SUPERSEDED " + ("x" * 400) + "\n")
    got = declared_off_reason(p).text or ""
    assert len(got) <= 120


def test_every_currently_dark_hook_in_the_tree_declares_something():
    """Live check: if this ever fails, a real unexplained dark hook has appeared.

    That is a finding rather than a broken test -- the failure means someone
    switched something off without saying why, which is exactly what the
    register now makes visible.
    """
    from scripts.generate_automation_register import collect

    silent = [
        r["name"]
        for r in collect()
        if not r["wired"] and declared_off_reason(HOOKS_DIR / r["name"]).text is None
    ]
    assert silent == [], f"dark with no declared reason: {silent}"
