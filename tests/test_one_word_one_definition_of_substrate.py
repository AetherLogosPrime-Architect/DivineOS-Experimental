"""The checkpoint splitter and the push gate must mean the same thing by it.

2026-09-10. A code branch could not be pushed and could not be repaired by the
component that broke it. The splitter had filed a hundred and eighty-three
archive, dream and letter files as WORK -- correctly, by its own rule, which
derives substrate from the declared external channels. The push gate then
refused the branch for carrying SUBSTRATE -- correctly, by its own rule, which
carried a hand-written prefix list seeded by the incidents that had burned us.

Both halves were right about their own origin. They agreed on one entry out of
four, and nothing anywhere compared them, so the disagreement stayed invisible
until it deadlocked.

Aria's rule, the same evening: for any door whose guard is a LIST, ask what
seeded the list. An incident-seeded list contains its origin; a derived list
cannot contain what no channel mirrors. The repair is not a better list. It is
ONE list, imported rather than restated -- and this file is what makes the
restating come back as a failure instead of as a quiet second copy.

Sibling to test_push_gate_substrate_scope.py, which drives the gate against
real repositories. That file asks whether the gate ACTS correctly on substrate;
this one asks whether it and the splitter AGREE on what the word means. Neither
question catches the other's failure.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from divineos.core.substrate_paths import LOCAL_SUBSTRATE_PREFIXES, is_substrate_path

_GATE = Path(__file__).resolve().parents[1] / "scripts" / "check_branch_scope.py"


def _gate_module():
    spec = importlib.util.spec_from_file_location("check_branch_scope", _GATE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.skipif(not _GATE.exists(), reason="gate absent here -- could-not-look, not a pass")
def test_the_gate_and_the_splitter_hold_the_same_list():
    """A second copy is how the deadlock happened; this is what forbids one."""
    gate = _gate_module()

    assert gate._SUBSTRATE_PREFIXES == LOCAL_SUBSTRATE_PREFIXES, (
        "the push gate has its own definition of substrate again. That is the "
        "exact split that made a branch unpushable and unfixable on 2026-09-10."
    )


@pytest.mark.parametrize(
    "path",
    [
        "docs/archives/lessons.md",
        "dreams/aether/20_the_house_that_wrote_itself_letters.md",
        "exploration/aether/48_inhabit_vs_consult.md",
    ],
)
def test_the_three_the_splitter_used_to_call_work(path):
    """Each of these landed in a work commit on a code branch and then got the
    branch refused. The letters directory is deliberately NOT here: it was the
    one entry both sides already agreed on, so it proves nothing about the fix.
    """
    assert is_substrate_path(path) is True, (
        f"{path} is filed as work again; the push gate will refuse the branch "
        "carrying it and the splitter will keep putting it there"
    )


def test_ordinary_code_is_still_work():
    """Control, and the failure direction that matters more.

    Misfiling work as substrate puts half-finished edits onto the branch other
    people review -- the original bug the splitter was built to fix. Widening
    the definition must not widen it past these four prefixes.
    """
    for path in (
        "src/divineos/core/substrate_paths.py",
        "tests/test_auto_commit.py",
        "scripts/precommit.sh",
        "docs/foundational_truths.md",  # under docs/, but NOT docs/archives/
    ):
        assert is_substrate_path(path) is False, (
            f"{path} classified as substrate; the split would divert real work "
            "onto the substrate branch"
        )
