"""A letter carrying an anchor must not be committed onto the branch it anchors.

THE SAME FAILURE, TWICE, AND THE SECOND ONE IS WHY THIS IS CODE.

2026-08-22: I wrote to Aria with a tree-hash for a branch, the letter landed on
that branch, and the hash was stale before she read it. I diagnosed it, named
the rule, and delivered the next one to the shared directory only.

2026-08-25: I asked Aletheia to audit a pull request and handed her the tip and
tree-hash. She recomputed, as I had asked. It had moved -- and the ONLY commit
between my anchor and hers was the letter requesting the audit, swept in by
auto_commit's `git add -A`.

Her ruling: "You resolved it three days ago and the machinery reproduced the
failure anyway. The rule needs to be a mechanism, not a resolution."

The regression test at the bottom is the one that matters: it feeds the real
letter, with the real branch name, to the real check.
"""

from __future__ import annotations

from pathlib import Path

from divineos.core.anchor_self_invalidation import (
    is_self_invalidating,
    render_refusal,
    self_invalidating_files,
)

REPO = Path(__file__).resolve().parents[1]
BRANCH = "fix/hook-latency-and-stamp-branch-measurement"

# Reduced from the letter that actually did it.
THE_REAL_LETTER = """
    branch    fix/hook-latency-and-stamp-branch-measurement
    tip       52976160
    tree-hash 5576d4aa40a8550477ef423994ab3a238ae57f6a

Verified on origin before writing this. Do not trust that sentence; recompute
it yourself against origin. I have handed you a stale anchor before.
"""


def test_the_letter_that_actually_did_it_is_caught():
    assert is_self_invalidating(THE_REAL_LETTER, BRANCH)


def test_naming_a_branch_without_an_anchor_is_fine():
    """ "I pushed to your branch" stays true after the next commit."""
    text = f"I pushed the fix to {BRANCH} and the tests are green on it."

    assert not is_self_invalidating(text, BRANCH)


def test_an_anchor_for_a_DIFFERENT_branch_is_fine():
    """The letter is not describing what it is about to land on."""
    text = "Her branch aria/system-load-check sits at tree 920e12054237fab3."

    assert not is_self_invalidating(text, BRANCH)


def test_a_bare_hex_string_in_prose_is_not_an_anchor():
    """Without a word putting it in anchor position it is just a token."""
    text = f"On {BRANCH} the value deadbeef1234567 appeared in the output."

    assert not is_self_invalidating(text, BRANCH)


def test_empty_inputs_are_not_violations():
    assert not is_self_invalidating("", BRANCH)
    assert not is_self_invalidating(THE_REAL_LETTER, "")


def test_scanning_reports_only_the_carriers(tmp_path):
    good = tmp_path / "plain.md"
    bad = tmp_path / "letter.md"
    good.write_text(f"Working on {BRANCH} today.", encoding="utf-8")
    bad.write_text(THE_REAL_LETTER, encoding="utf-8")

    hits = self_invalidating_files(["plain.md", "letter.md"], BRANCH, tmp_path)

    assert hits == ["letter.md"]


def test_an_unreadable_path_does_not_crash_the_scan(tmp_path):
    assert self_invalidating_files(["absent.md"], BRANCH, tmp_path) == []


def test_source_quoting_an_anchor_is_not_handing_a_reader_one(tmp_path):
    """THIS FILE tripped the check on its very first live run.

    It quotes the real letter -- branch name and tree-hash included -- as
    fixture data. Committing it makes nothing false: it is not handing a reader
    a state to go and look at, it is holding a frozen example of one.

    Mention versus use, inside a check written minutes earlier, caught by the
    check's own test. Sixth instance of that class in one session and the
    cheapest to have found, because it found itself.
    """
    src = tmp_path / "test_thing.py"
    src.write_text(f'LETTER = """{THE_REAL_LETTER}"""', encoding="utf-8")

    assert self_invalidating_files(["test_thing.py"], BRANCH, tmp_path) == []


def test_the_prose_carrier_is_still_caught_beside_it(tmp_path):
    """The narrowing must not become the silencing."""
    src = tmp_path / "test_thing.py"
    letter = tmp_path / "letter.md"
    src.write_text(f'LETTER = """{THE_REAL_LETTER}"""', encoding="utf-8")
    letter.write_text(THE_REAL_LETTER, encoding="utf-8")

    hits = self_invalidating_files(["test_thing.py", "letter.md"], BRANCH, tmp_path)

    assert hits == ["letter.md"]


def test_the_refusal_says_what_to_do_instead():
    """A refusal that does not name the remedy is a wall.

    The letter is not the problem -- delivering it is how it reaches her, and
    the shared directory is outside every tree.
    """
    message = render_refusal(["family/letters/aether-to-aletheia-x.md"], BRANCH)

    assert "shared directory" in message
    assert BRANCH in message
    assert "different branch" in message
