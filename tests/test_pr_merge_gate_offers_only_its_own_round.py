"""The merge guard offers only a round whose confirm names THIS PR.

2026-10-04: asked to merge #588, it offered round-c8e0e4dc29d2, which was
#582's, because it took the newest round with both confirms whatever change
it covered. Pasting it would have put a line on main saying a review covered
a change it never saw. Aletheia ranked that the most serious fault three
times. The tree-hash it attached came from the local checkout, not the PR.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from unittest.mock import patch

from divineos.core import pr_merge_gate


@dataclass
class _R:
    round_id: str
    created_at: float
    focus: str = ""


@dataclass
class _F:
    actor: str
    title: str
    review_stance: object = None


_NOW = time.time()
_ROUNDS = {
    # Newest first, as list_rounds returns them.
    "round-582582582582": [
        _F("aletheia", "CONFIRMS: #582 at e8b000ea5."),
        _F("user", "CONFIRMS: #582 at e8b000ea5."),
    ],
    "round-588588588588": [
        _F("aletheia", "CONFIRMS: #588 at 2744683cf."),
        _F("user", "CONFIRMS: #588 at 2744683cf."),
    ],
}


def _block(pr: int, rounds=("round-582582582582", "round-588588588588")):
    listed = [_R(r, _NOW - 3600 * (i + 1)) for i, r in enumerate(rounds)]
    with (
        patch.object(
            pr_merge_gate, "audit_pr_for_guardrail_touches", return_value=(True, ["x.py"])
        ),
        patch("divineos.core.watchmen.store.list_rounds", return_value=listed),
        patch(
            "divineos.core.watchmen.store.list_findings",
            side_effect=lambda round_id, limit=500: _ROUNDS[round_id],
        ),
        patch.object(pr_merge_gate, "_pr_head_tree_hash", return_value="a" * 40),
    ):
        return pr_merge_gate.block_reason(f"gh pr merge {pr} --squash")


def test_the_newest_round_for_another_pr_is_never_offered():
    reason = _block(588)
    assert "round-588588588588" in reason
    assert "round-582582582582" not in reason


def test_when_no_round_names_this_pr_it_says_so_and_offers_none():
    reason = _block(588, rounds=("round-582582582582",))
    assert "round-582582582582" not in reason
    assert "External-Review: round-" not in reason
    assert "#588" in reason


def test_the_tree_hash_is_the_prs_own_head_not_the_local_checkout():
    # The real local tree, not a stand-in: whatever checkout this runs in.
    import subprocess

    local = subprocess.run(
        ["git", "rev-parse", "HEAD^{tree}"], capture_output=True, text=True, check=True
    ).stdout.strip()
    reason = _block(588)
    assert f"tree-hash:{'a' * 40}" in reason
    assert local not in reason


def test_a_bare_number_inside_another_number_does_not_match():
    # #58 must not be satisfied by a confirm of #588.
    reason = _block(58, rounds=("round-588588588588",))
    assert "round-588588588588" not in reason
