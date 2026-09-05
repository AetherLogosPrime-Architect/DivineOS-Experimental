"""A review must be reachable from inside the block that demands it.

FOUR TIMES, AND THE FOURTH ONE STOOD IN FRONT OF ITS OWN REPAIR.

The overdue-prereg gate blocks substantive work until a due pre-registration is
assessed. Its allowlist of read-only probes exists because an honest assessment
needs evidence, and the comment beside that list already records the gate
refusing evidence twice on 2026-08-13 -- both recorded DEFERRED for no reason
except this gate.

The repair chosen then was to add the two commands that had already been lost.
So the list covered the reviews somebody had already failed to earn, and on
2026-09-01 it happened again: a pre-registration about the degraded-detector
mechanism came due, every success criterion in it is a statement about what
``divineos detectors`` does, and that command was not listed. The only reachable
exit was the verdict itself -- the fabricated-outcome shape the list exists to
prevent. The edit adding it was then refused by the same block.

Enumeration cannot close this. The next review needing an unlisted probe is
unknowable in advance, and the gate cannot tell an unearnable review from a
dodged one. So the rule is about read-only VERBS, and these tests hold both
halves of it: the looking gets through, the doing does not.
"""

from __future__ import annotations

import pytest

from divineos.hooks.pre_tool_use_gate import _is_readonly_probe


@pytest.mark.parametrize(
    "cmd",
    [
        "divineos detectors status",
        "divineos detectors check",
        "divineos prereg show prereg-060a5e24ebf4",
        "divineos audit list",
        "divineos compass-ops history",
        "divineos audit summary",
        "cd /repo && divineos detectors status",
    ],
)
def test_looking_at_the_evidence_is_never_blocked(cmd):
    """The command a review needs must run while the review is owed."""
    assert _is_readonly_probe(cmd), cmd


@pytest.mark.parametrize(
    "cmd",
    [
        "divineos detectors heal",
        "divineos detectors defer --detector x --reason yyyyyyyyyyyyyyyyyyyyyyyyyyyyyy",
        "divineos audit submit-round 'x' --actor aether",
        "divineos learn 'something'",
        "divineos goal add 'something'",
    ],
)
def test_the_work_the_gate_exists_to_stop_is_still_stopped(cmd):
    """Clearing a degradation, filing a round, storing knowledge -- all
    substantive. The gate's purpose is to hold these until the review happens,
    and widening the looking must not widen the doing."""
    assert not _is_readonly_probe(cmd), cmd


@pytest.mark.parametrize(
    "cmd",
    [
        "divineos learn status",
        "divineos claim summary",
        "divineos learn check",
    ],
)
def test_a_one_word_argument_is_not_a_verb(cmd):
    """Aria, 2026-09-01, three sentences she ran that were not quoted.

    A lesson whose whole text is the word "status". A claim whose whole text
    is "summary". A lesson whose whole text is "check". All three write to a
    store; all three passed as read-only probes, because the rule looked at
    the third token's POSITION and not at whether the second token has a third
    level at all. A one-word lesson is a bad lesson, but this gate is not here
    to judge quality -- it is here to stop writes.
    """
    assert not _is_readonly_probe(cmd), cmd


def test_a_group_with_a_third_level_still_reads(monkeypatch):
    """The repair must not take the group case with it. When the second token
    IS a group, the third token is the verb, and looking still gets through."""
    from divineos.hooks import pre_tool_use_gate as g

    monkeypatch.setattr(g, "_is_command_group", lambda name: True)
    assert _is_readonly_probe("divineos detectors status")


def test_could_not_look_at_the_registry_is_a_refusal(monkeypatch):
    """If the CLI cannot be resolved, the answer is not-a-probe, never a pass.

    Same discipline as the unbalanced-quote case: a check that cannot see
    does not get the benefit of the doubt, because a gate that fails open on
    its own error becomes the thing it exists to stop.
    """
    from divineos.hooks import pre_tool_use_gate as g

    monkeypatch.setattr(g, "_is_command_group", lambda name: None)
    assert not _is_readonly_probe("divineos detectors status")


def test_a_read_only_word_inside_an_argument_does_not_qualify():
    """The verb must sit where a verb sits.

    Otherwise the rule becomes a word-search over the whole command, which is
    the match-the-name-not-the-thing fault the rest of this week was made of --
    and here it would hand a mutating command a pass.
    """
    assert not _is_readonly_probe(
        "divineos audit submit 'x' --round r --actor aether -d 'the status list shows'"
    )


def test_a_compound_command_is_not_a_probe():
    """Hardening carried from the bypass check: a probe joined to anything else
    is not a probe. Looking cannot be the doorway for doing."""
    assert not _is_readonly_probe("divineos detectors status && rm -rf /tmp/x")
    assert not _is_readonly_probe("divineos detectors status; divineos learn 'x'")


def test_unbalanced_quotes_are_not_read_as_a_probe():
    """Could-not-parse is not a pass. If the command cannot be read, it does not
    get the benefit of the doubt -- which is this session's whole subject."""
    assert not _is_readonly_probe("divineos detectors status 'unterminated")


def test_a_bare_group_with_no_verb_is_not_a_probe():
    """``divineos detectors`` alone prints help, which is harmless, but the rule
    is about verbs and a missing verb is not one. Narrow beats clever here: the
    listed prefixes above still cover the groups that were explicitly reviewed."""
    assert not _is_readonly_probe("divineos detectors")
