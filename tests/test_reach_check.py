"""The doorman must refuse a disposition made without opening the artifact.

Andrew 2026-08-06: *"a forced thinking stage that asks you what you know and
if you have reached for it or applied it, with its own doorman to prove you
did."*

The load-bearing test in this file is `test_not_relevant_is_not_exempt`.
Every other refusal path is ordinary validation; that one is the design
decision, and if it ever gets relaxed the whole mechanism reverts to a report
that can be scrolled past.
"""

from __future__ import annotations

import pytest

from divineos.core import reach_check
from divineos.core.reach_check import ReachCheckError

GOOD_REASON = "read it end to end; it covers the case and I applied it here"


@pytest.fixture(autouse=True)
def _tables():
    reach_check.init_reach_tables()


def _item(artifact: str = "src/divineos/core/prior_art.py") -> reach_check.ReachItem:
    """One undisposed item, written directly so the test does not depend on
    what prior_art happens to find in this checkout."""
    import time
    import uuid

    from divineos.core.knowledge import _get_connection

    check_id = f"reach-test-{uuid.uuid4().hex[:8]}"
    item_id = f"ri-test-{uuid.uuid4().hex[:8]}"
    conn = _get_connection()
    conn.execute(
        "INSERT INTO reach_checks (check_id, symptom, opened_at) VALUES (?, ?, ?)",
        (check_id, "test symptom", time.time()),
    )
    conn.execute(
        "INSERT INTO reach_items (item_id, check_id, artifact, origin) VALUES (?, ?, ?, ?)",
        (item_id, check_id, artifact, "branch:test@abc123"),
    )
    conn.commit()
    return reach_check.ReachItem(item_id, check_id, artifact, "branch:test@abc123")


def test_disposition_refused_when_artifact_never_opened():
    item = _item()
    with pytest.raises(ReachCheckError) as exc:
        reach_check.dispose(item.item_id, reach_check.APPLIED, GOOD_REASON)
    assert "never opened" in str(exc.value)


def test_not_relevant_is_not_exempt():
    """The design decision. Judging relevance unread IS the failure mode.

    If this test is ever changed to allow not_relevant through without
    evidence, the mechanism no longer catches the class it was built for --
    every historical miss would have been waved off as not-relevant by
    someone who had not opened the file.
    """
    item = _item()
    with pytest.raises(ReachCheckError) as exc:
        reach_check.dispose(item.item_id, reach_check.NOT_RELEVANT, GOOD_REASON)
    assert "never opened" in str(exc.value)
    assert "not_relevant" in str(exc.value)


def test_read_tool_on_the_artifact_clears_the_doorman():
    item = _item()
    result = reach_check.dispose(
        item.item_id,
        reach_check.APPLIED,
        GOOD_REASON,
        tool_calls_in_turn=(("Read", "C:/repo/src/divineos/core/prior_art.py"),),
    )
    assert result.disposition == reach_check.APPLIED
    assert result.evidence == "tool:Read:prior_art.py"


def test_git_show_counts_as_reading():
    """Friction register G6: a file on an unmerged branch is read via git show,
    and a gate blind to that route demands a consult it cannot see."""
    item = _item()
    result = reach_check.dispose(
        item.item_id,
        reach_check.SUPERSEDED,
        GOOD_REASON,
        command_texts=("git show 1e260bab:src/divineos/core/prior_art.py",),
    )
    assert result.evidence == "cmd:prior_art.py"


def test_reading_a_different_file_does_not_clear_it():
    """Any-consult-counts is the shape of the verify-before-build gate. Here
    the evidence must name THIS artifact, or the check would pass on unrelated
    reading."""
    item = _item()
    with pytest.raises(ReachCheckError):
        reach_check.dispose(
            item.item_id,
            reach_check.APPLIED,
            GOOD_REASON,
            tool_calls_in_turn=(("Read", "C:/repo/src/divineos/core/holding.py"),),
        )


def test_cli_artifact_needs_the_command_run_not_a_file_read():
    item = _item(artifact="cli:reach")
    with pytest.raises(ReachCheckError):
        reach_check.dispose(item.item_id, reach_check.APPLIED, GOOD_REASON)
    result = reach_check.dispose(
        item.item_id,
        reach_check.APPLIED,
        GOOD_REASON,
        command_texts=("divineos reach status",),
    )
    assert result.evidence == "cmd:reach"


def test_empty_reason_refused():
    item = _item()
    with pytest.raises(ReachCheckError) as exc:
        reach_check.dispose(
            item.item_id,
            reach_check.APPLIED,
            "read it",
            tool_calls_in_turn=(("Read", "src/divineos/core/prior_art.py"),),
        )
    assert "at least" in str(exc.value)


def test_unknown_disposition_refused():
    item = _item()
    with pytest.raises(ReachCheckError):
        reach_check.dispose(
            item.item_id,
            "maybe_later",
            GOOD_REASON,
            tool_calls_in_turn=(("Read", "src/divineos/core/prior_art.py"),),
        )


def test_disposition_is_append_only():
    item = _item()
    evidence = (("Read", "src/divineos/core/prior_art.py"),)
    reach_check.dispose(item.item_id, reach_check.APPLIED, GOOD_REASON, tool_calls_in_turn=evidence)
    with pytest.raises(ReachCheckError) as exc:
        reach_check.dispose(
            item.item_id, reach_check.SUPERSEDED, GOOD_REASON, tool_calls_in_turn=evidence
        )
    assert "already disposed" in str(exc.value)


def test_gate_blocks_while_an_item_is_undisposed_and_names_it():
    item = _item(artifact="src/divineos/core/gate_test_artifact.py")
    blocked, message = reach_check.gate_status()
    assert blocked
    assert item.artifact in message

    reach_check.dispose(
        item.item_id,
        reach_check.NOT_RELEVANT,
        GOOD_REASON,
        tool_calls_in_turn=(("Read", item.artifact),),
    )
    _, after = reach_check.gate_status()
    assert item.artifact not in after


def test_check_with_no_prior_art_is_clear_not_blocking():
    """NOT FOUND is a real outcome. A symptom with no prior art must not
    manufacture a block -- that would train the gate into noise."""
    check = reach_check.open_check("zzqqxx-no-such-artifact-anywhere-zzqqxx")
    assert check.items == []
    assert check.clear


# ── LOADOUT axis (2026-08-06) ─────────────────────────────────────────
#
# Andrew: "the reach needs some tuning and better enforcement and should also
# be connected to the loadout or something and if stuff is missing from it add
# it to there."


def test_loadout_axis_finds_prose_the_code_axis_cannot():
    """The miss that prompted this: `reach open "emotion taxonomy"` returned
    NOT FOUND on the code axis while exploration/omni_mantra_walk/ held the
    exact derivation layer being asked about."""
    hits = reach_check.find_in_loadout("omni mantra")
    assert hits, "LOADOUT lists the omni_mantra_walk entries; the axis must see them"
    paths = [p for _label, p, _section in hits]
    assert any("omni_mantra_walk" in p for p in paths)
    sections = {s for _label, _p, s in hits}
    assert sections, "section must be carried through — it says what kind of artifact this is"


def test_slug_matching_is_separator_insensitive():
    assert reach_check.find_in_loadout("omni_mantra") == reach_check.find_in_loadout("omni-mantra")


def test_short_terms_do_not_match_everything():
    """A two-character term against a 2320-entry index would surface the whole
    substrate, which is the same over-fire the collapse threshold exists for."""
    assert reach_check.find_in_loadout("om") == []


def test_directory_collapse_folds_a_folder_into_one_item():
    surfaced = [(f"exploration/walk/{i:02d}_entry.md", "loadout:x") for i in range(9)]
    out = reach_check._collapse_by_directory(surfaced)
    assert len(out) == 1
    assert "exploration/walk/" in out[0][0]
    assert "9 matching files" in out[0][0]


def test_collapse_leaves_small_directories_alone():
    """Two hits are specific enough to act on; collapsing them would lose the
    filenames for no benefit."""
    surfaced = [("docs/a_thing.md", "loadout:x"), ("docs/b_thing.md", "loadout:x")]
    assert reach_check._collapse_by_directory(surfaced) == surfaced


def test_collapse_keeps_commits_first_and_uncollapsed():
    """Commit subjects are the axis that caught the freeze miss. They must not
    be folded into a directory, and must keep their leading position."""
    surfaced = [("commit:abc1234 fix(freeze): something", "unmerged-commit:branch")] + [
        (f"docs/x/{i}.md", "loadout:y") for i in range(8)
    ]
    out = reach_check._collapse_by_directory(surfaced)
    assert out[0][0].startswith("commit:")
    assert len(out) == 2


def test_cross_axis_duplicates_are_deduped():
    """A file in LOADOUT is usually also in the working tree. Listing it twice
    would demand two dispositions for one artifact."""
    surfaced = [("docs/thing.md", "loadout:docs"), ("docs/thing.md", "working-tree")]
    out = reach_check._collapse_by_directory(surfaced)
    assert len(out) == 1
    assert out[0][1] == "loadout:docs", "first axis wins; axis order is deliberate"


def test_loadout_gaps_reports_what_the_index_is_missing():
    gaps = reach_check.loadout_gaps(
        ["docs/definitely_not_in_the_index_zzqq.md", "commit:abc1234 subject"]
    )
    assert "docs/definitely_not_in_the_index_zzqq.md" in gaps
    assert not any(g.startswith("commit:") for g in gaps), "commits are not LOADOUT's job"
