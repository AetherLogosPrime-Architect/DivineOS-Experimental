"""Audit rounds must travel with the repo, not sit on one hard drive.

THE PROBLEM (Andrew 2026-08-01). The audit store held 275 rounds and 637
findings; the repository held essentially none of it. GitHub only ever saw
the ``External-Review: round-abc123`` pointer — a reference number to a
filing cabinet it could not open. Every server-side check that wanted to
say anything about an audit was therefore blind, which is why one of them
failed 17 times in a row and the other had to report UNVERIFIABLE.

I had diagnosed that blindness precisely and then written a careful message
explaining it as permanent. Andrew: *"stop looking at barriers as stopping
points or walls we cannot get around."* The fix was already in the codebase
— ``prereg export`` has written pre-registrations into ``docs/`` all along.
Audit rounds simply never got pointed at the same trick.

These tests pin the two properties that make the export worth having: the
record must be COMPLETE (a review missing its actors and tiers is not a
review), and it must be READABLE BY CI (the point is a bare checkout with
no database).
"""

from __future__ import annotations

from divineos.core.watchmen.export import (
    exported_round_exists,
    export_rounds,
    find_unexported_rounds,
    format_round_markdown,
)
from divineos.core.watchmen.types import (
    AuditRound,
    Finding,
    FindingCategory,
    FindingStatus,
    ReviewStance,
    Severity,
    Tier,
)


def _round(rid: str = "round-abc123") -> AuditRound:
    return AuditRound(
        round_id=rid,
        created_at=1754000000.0,
        actor="aletheia",
        focus="merge-review gate coherence",
        expert_count=3,
        finding_count=1,
        notes="Cross-vantage review of the gate rewrite.",
        tier=Tier.STRONG,
    )


def _finding(fid: str = "find-001", **kw) -> Finding:
    base = dict(
        finding_id=fid,
        round_id="round-abc123",
        created_at=1754000100.0,
        actor="aletheia",
        severity=Severity.HIGH,
        category=FindingCategory.INTEGRITY,
        title="Gate reports absence when it means blindness",
        description="The lookup never ran; the verdict claimed it did.",
        recommendation="Distinguish unreadable from absent.",
        status=FindingStatus.OPEN,
        tier=Tier.STRONG,
    )
    base.update(kw)
    return Finding(**base)


# --------------------------------------------------------------------------
# Completeness — a review stripped of its provenance is not a review
# --------------------------------------------------------------------------


def test_export_carries_the_evidentiary_fields():
    """Actor, severity, tier and status are what make a finding checkable by
    someone who was not in the room. Losing them to keep the file tidy would
    export the shape of a review without its substance."""
    md = format_round_markdown(_round(), [_finding()])
    for expected in (
        "round-abc123",
        "aletheia",
        "HIGH",
        "INTEGRITY",
        "STRONG",
        "OPEN",
        "find-001",
    ):
        assert expected in md, expected


def test_export_carries_the_prose_a_human_actually_reads():
    md = format_round_markdown(_round(), [_finding()])
    assert "The lookup never ran" in md
    assert "Distinguish unreadable from absent." in md
    assert "Cross-vantage review of the gate rewrite." in md


def test_review_stance_and_target_survive_the_export():
    """A CONFIRMS from an external auditor is the highest-value record in the
    store. It is meaningless without knowing WHAT it confirms."""
    f = _finding(
        fid="find-002",
        reviewed_finding_id="find-001",
        review_stance=ReviewStance.CONFIRMS,
    )
    md = format_round_markdown(_round(), [f])
    assert "find-001" in md
    assert "CONFIRMS" in md.upper()


def test_empty_round_says_so_rather_than_looking_truncated():
    """A round with no findings and a round whose export broke look identical
    unless the file states which one it is."""
    md = format_round_markdown(_round(), [])
    assert "No findings were filed" in md


def test_file_states_that_the_store_is_not_the_repo():
    """Whoever reads this file cold should not assume it is live state."""
    md = format_round_markdown(_round(), [_finding()])
    assert "not committed" in md or "runtime state" in md


# --------------------------------------------------------------------------
# Readability by CI — the entire point
# --------------------------------------------------------------------------


def test_ci_can_confirm_a_round_with_no_database(tmp_path):
    """The load-bearing test. A bare checkout has files and no store; this is
    exactly the situation the check runs in on GitHub."""
    out = tmp_path / "audit_rounds"
    export_rounds([_round()], {"round-abc123": [_finding()]}, out_dir=str(out))
    assert exported_round_exists("round-abc123", out_dir=str(out)) is True


def test_unexported_round_is_not_confirmed(tmp_path):
    out = tmp_path / "audit_rounds"
    export_rounds([_round()], {"round-abc123": [_finding()]}, out_dir=str(out))
    assert exported_round_exists("round-never-filed", out_dir=str(out)) is False


def test_missing_directory_is_not_confirmation(tmp_path):
    assert exported_round_exists("round-abc123", out_dir=str(tmp_path / "nope")) is False


def test_round_id_is_never_treated_as_a_path(tmp_path):
    """A round id becomes a filename, so traversal must be refused rather than
    resolved. Nothing should be able to confirm a round by pointing at some
    other markdown file that happens to exist."""
    out = tmp_path / "audit_rounds"
    out.mkdir(parents=True)
    (tmp_path / "secret.md").write_text("not a round", encoding="utf-8")
    for hostile in ("../secret", "..\\secret", "/etc/passwd", ".", "", "   "):
        assert exported_round_exists(hostile, out_dir=str(out)) is False, hostile


def test_export_writes_one_file_per_round(tmp_path):
    out = tmp_path / "audit_rounds"
    rounds = [_round("round-a"), _round("round-b"), _round("round-c")]
    written = export_rounds(rounds, {}, out_dir=str(out))
    assert len(written) == 3
    assert {p.name for p in written} == {"round-a.md", "round-b.md", "round-c.md"}
    for rid in ("round-a", "round-b", "round-c"):
        assert exported_round_exists(rid, out_dir=str(out))


def test_export_is_idempotent(tmp_path):
    """Re-exporting must overwrite cleanly, so the command can be re-run after
    new findings land without producing duplicates or stale halves."""
    out = tmp_path / "audit_rounds"
    export_rounds([_round()], {"round-abc123": []}, out_dir=str(out))
    first = (out / "round-abc123.md").read_text(encoding="utf-8")
    assert "No findings were filed" in first

    export_rounds([_round()], {"round-abc123": [_finding()]}, out_dir=str(out))
    second = (out / "round-abc123.md").read_text(encoding="utf-8")
    assert "No findings were filed" not in second
    assert "find-001" in second


# --------------------------------------------------------------------------
# The store must survive reading its own history
# --------------------------------------------------------------------------


def test_case_drifted_enum_values_do_not_break_the_read():
    """Found by running the export over the real store: 6 findings hold
    'info' and some hold 'knowledge' against uppercase enums, so Severity()
    raised and ANY read touching those rows died — list_findings included.
    Six rows made whole rounds silently unreadable. Case is not meaning."""
    from divineos.core.watchmen.store import _coerce_enum

    assert _coerce_enum(Severity, "info", Severity.LOW) is Severity.INFO
    assert _coerce_enum(Severity, "INFO", Severity.LOW) is Severity.INFO
    assert _coerce_enum(FindingCategory, "knowledge", FindingCategory.OTHER) is (
        FindingCategory.KNOWLEDGE
    )


# --------------------------------------------------------------------------
# The consumer that breaks — Aria 2026-08-01
# --------------------------------------------------------------------------


def test_drift_between_store_and_export_is_detected(tmp_path):
    """Aria: 'a record nothing breaks over is a record nobody checks.' Without
    a consumer, the export could fall arbitrarily behind the store while CI
    reported every missing round as merely unverifiable and passed."""
    out = tmp_path / "audit_rounds"
    export_rounds([_round("round-a")], {}, out_dir=str(out))

    stale = find_unexported_rounds(["round-a", "round-b", "round-c"], out_dir=str(out))
    assert stale == ["round-b", "round-c"]


def test_no_drift_when_everything_is_exported(tmp_path):
    """The other direction. A check that always finds drift is as useless as
    one that never does — this session deleted several of the former."""
    out = tmp_path / "audit_rounds"
    export_rounds([_round("round-a"), _round("round-b")], {}, out_dir=str(out))
    assert find_unexported_rounds(["round-a", "round-b"], out_dir=str(out)) == []


def test_empty_store_reports_no_drift(tmp_path):
    """Nothing filed is not the same as something missing."""
    assert find_unexported_rounds([], out_dir=str(tmp_path)) == []


def test_missing_export_directory_reports_every_round_as_drift(tmp_path):
    """A deleted docs/audit_rounds must be loud, not silently 'fine'."""
    stale = find_unexported_rounds(["round-a", "round-b"], out_dir=str(tmp_path / "gone"))
    assert stale == ["round-a", "round-b"]


def test_unresolvable_value_degrades_one_field_not_the_whole_finding():
    """Losing a field's precision beats losing an audit record entirely."""
    from divineos.core.watchmen.store import _coerce_enum

    assert _coerce_enum(Severity, "banana", Severity.INFO) is Severity.INFO
    assert _coerce_enum(Severity, None, Severity.INFO) is Severity.INFO
    assert _coerce_enum(Severity, "", Severity.INFO) is Severity.INFO
