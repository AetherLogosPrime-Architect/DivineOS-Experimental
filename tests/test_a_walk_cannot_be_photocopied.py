"""A council walk whose findings are word for word ones already filed is a
copy, and is refused at both doors (Dad 2026-10-03: "did you just run the
council as a program?"). Draft: docs/drafts/a_walk_cannot_be_photocopied_draft_2026-10-03.md."""

from __future__ import annotations

import time

from click.testing import CliRunner

from divineos.cli import cli
from divineos.core.council_required import store
from divineos.core.council_required.types import CouncilRecord, LensFinding

TEXT_A = "Through Holmes I observed that the stop reads only the tail of the transcript, so a long session cannot make it run past its timeout."
TEXT_B = "Through Holmes I observed that the settings file lists the hook once, after the reflection stop, so the order is fixed by the file."


def _record(fp, *texts, scope=()):
    return CouncilRecord(
        record_id=store.new_record_id(),
        walked_at=time.time(),
        walker="agent",
        triggered_edit_fingerprint=fp,
        lenses_surfaced=tuple("Holmes" for _ in texts),
        lens_findings=tuple(LensFinding(lens_name="Holmes", finding_text=t) for t in texts),
        synthesis="synthesis",
        scope_fingerprints=tuple(scope),
    )


def test_the_same_findings_on_another_file_are_a_copy():
    first = _record("edit:a.py", TEXT_A)
    store.log_council_record(first)
    assert store.copied_from(_record("edit:b.py", TEXT_A)) == first.record_id


def test_the_same_findings_filed_again_for_the_same_file_are_a_copy_too():
    """Breaker's finding: tonight one set was refiled four times on bash:git add."""
    first = _record("bash:git add", TEXT_A)
    store.log_council_record(first)
    assert store.copied_from(_record("bash:git add", TEXT_A)) == first.record_id


def test_one_copied_lens_finding_inside_new_ones_is_a_copy():
    store.log_council_record(_record("edit:a.py", TEXT_A))
    assert store.copied_from(_record("edit:b.py", TEXT_B, TEXT_A)) is not None


def test_whitespace_does_not_hide_a_copy():
    store.log_council_record(_record("edit:a.py", TEXT_A))
    assert store.copied_from(_record("edit:b.py", "  " + TEXT_A.replace(" ", "\n  "))) is not None


def test_a_fresh_look_is_not_a_copy():
    store.log_council_record(_record("edit:a.py", TEXT_A))
    assert store.copied_from(_record("edit:b.py", TEXT_B)) is None


def test_council_log_refuses_a_copy_and_names_the_honest_path():
    first = _record("edit:a.py", TEXT_A)
    store.log_council_record(first)
    result = CliRunner().invoke(
        cli,
        [
            "council",
            "log",
            "--edit",
            "edit:b.py",
            "--lenses",
            "Holmes",
            "--finding",
            f"Holmes={TEXT_A}",
            "--synthesis",
            "s",
        ],
    )
    assert result.exit_code == 1
    assert f"copy of {first.record_id}" in result.output
    assert "--scope" in result.output


def test_council_walk_refuses_a_reflection_already_applied_for_that_lens():
    from divineos.core.council_required.types import EVENT_COUNCIL_LENS_APPLIED
    from divineos.core.ledger import log_event

    log_event(
        EVENT_COUNCIL_LENS_APPLIED,
        actor="agent",
        payload={
            "expert_name": "holmes",
            "edit_fingerprint": "edit:a.py",
            "reflection_prefix": TEXT_A[:400],
        },
        validate=False,
    )
    result = CliRunner().invoke(
        cli,
        ["council", "walk", "--edit", "edit:b.py", "--lens", "Holmes", "--problem", "p"],
        input=TEXT_A,
    )
    assert result.exit_code == 1
    assert "copy of one already applied for edit:a.py" in result.output


def test_a_copy_differing_only_in_case_is_a_copy():
    """Aria's cold read, 2026-10-03: capitalising one word got past the fold."""
    store.log_council_record(_record("edit:a.py", TEXT_A))
    assert store.copied_from(_record("edit:b.py", TEXT_A.upper())) is not None


def test_one_lens_reflection_filed_under_another_lens_is_a_copy():
    """Aria's cold read, 2026-10-03: Breaker's reflection pasted in as Carmack's passed."""
    from divineos.core.council_required.types import EVENT_COUNCIL_LENS_APPLIED
    from divineos.core.ledger import log_event

    log_event(
        EVENT_COUNCIL_LENS_APPLIED,
        actor="agent",
        payload={
            "expert_name": "breaker",
            "edit_fingerprint": "edit:a.py",
            "reflection_prefix": TEXT_A[:400],
        },
        validate=False,
    )
    result = CliRunner().invoke(
        cli,
        ["council", "walk", "--edit", "edit:b.py", "--lens", "Holmes", "--problem", "p"],
        input=TEXT_A.lower(),
    )
    assert result.exit_code == 1
    assert "copy of one already applied" in result.output
