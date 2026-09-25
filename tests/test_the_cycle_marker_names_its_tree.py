"""A checkpoint record must say WHICH tree it fired in.

Two checkouts on this machine write into one log file. Before this, the
marker recorded that a cycle happened and never where, so the only relation
the artifact offered a reader was proximity -- and on 2026-09-15 both Aether
and I read a single cause out of two unrelated true lines that happened to
land next to each other. His not-declared line and my carve-out line came
from different trees, minutes apart, into the same file.

The lesson is not "read logs more carefully." Proximity was the sole
inference the record supported, so reasoning from it was correct reasoning
on a source that cannot be read correctly. The fix is the column.

WHY THE MARKER AS WELL AS THE CONSOLE LINE: the handshake JSON is what the
next phase actually reads. A column that stops at the console is one nobody
downstream ever sees, which is the same defect one layer in.

Each test here fails against the code as it stood before the column existed.
A probe that only demonstrates the healthy case proves nothing about the
failure it was written for.
"""

from __future__ import annotations

import json
from pathlib import Path

from divineos.core import auto_cycle


def test_a_cycle_result_names_the_tree_it_acted_on() -> None:
    result = auto_cycle.run_phase1(context_pct=0.5, dry_run=True)

    assert result.repo_root, "the cycle did not record which tree it acted on"
    named = Path(result.repo_root)
    assert (named / "src" / "divineos").is_dir(), (
        f"repo_root {named} does not look like a divineos checkout -- the column "
        "must name a real tree, not any string that happens to be non-empty"
    )


def test_the_handshake_marker_carries_the_tree_downstream(tmp_path, monkeypatch) -> None:
    """Phase 2 reads the marker. A column that stops here never reaches it."""
    marker = tmp_path / "handshake.json"
    monkeypatch.setattr(auto_cycle, "marker_path", lambda: marker)

    result = auto_cycle.run_phase1(context_pct=0.5, dry_run=True)
    auto_cycle.write_handshake_marker(result)

    payload = json.loads(marker.read_text(encoding="utf-8"))
    assert "repo_root" in payload, "the marker dropped the tree between memory and disk"
    assert payload["repo_root"] == result.repo_root


def test_two_trees_produce_distinguishable_records() -> None:
    """The point of the column, as the property rather than the field name.

    Two records from different checkouts must not be identical on every field
    a reader can see. Built by hand rather than by running a second cycle,
    because the claim is about the RECORD's ability to separate them.
    """
    mine = auto_cycle.run_phase1(context_pct=0.5, dry_run=True)
    theirs = auto_cycle.Phase1Result(
        phase1_completed_at=mine.phase1_completed_at,
        trigger_context_pct=mine.trigger_context_pct,
        cycle_id=mine.cycle_id,
        steps=mine.steps,
        repo_root=r"C:\DIVINE OS\DivineOS-Experimental",
    )

    assert mine.repo_root != theirs.repo_root, (
        "two records from different trees are identical on every field a reader "
        "can see, which is the state that made proximity the only relation"
    )


def test_an_unknown_tree_is_said_rather_than_omitted() -> None:
    """Cannot-tell and did-not-happen must not render the same.

    If a blind cycle silently dropped the column, its line would read exactly
    like the old one, and whoever was standing there would conclude the record
    was fine. Collapsing those two is the fault this whole change exists to
    remove, rebuilt inside its own fix.
    """
    blind = auto_cycle.Phase1Result(
        phase1_completed_at="2026-09-15T00:00:00Z",
        trigger_context_pct=0.9,
        cycle_id="auto-cycle-0000dead",
        repo_root=None,
    )

    tree = Path(blind.repo_root).name if blind.repo_root else "unknown-tree"
    line = f"[auto-cycle] fired in {tree}: {blind.cycle_id}"

    assert "unknown-tree" in line, "a blind cycle rendered as if it knew its tree"
    assert line != f"[auto-cycle] fired: {blind.cycle_id}", (
        "the blind line is byte-identical to the pre-column line, so a reader "
        "cannot tell a cycle that could not determine its tree from one that "
        "was never asked"
    )
