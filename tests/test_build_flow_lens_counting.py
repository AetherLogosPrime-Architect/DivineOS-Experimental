"""Station-2 lens counting: it must distinguish absent from unmeasurable.

Written 2026-08-07 after dogfooding `build-flow status` surfaced a defect
that reading the code had not. `_lenses_applied` searched council-walk
events for the BRANCH NAME, while a walk records an edit fingerprint
(`edit:<path>`) and never a branch. Measured at the time: 279
COUNCIL_LENS_APPLIED events in the ledger, zero containing any branch
name. Station 2 therefore reported `0/N lenses walked` for every PR,
always, and could not have reported anything else.

That is a false ACCUSATION rather than a false pass, and it is the worse
direction here: a station that can only fail teaches me to discount it,
and a discounted gate is a dead gate.

These tests exist because the module had none at all.
"""

from __future__ import annotations

import pytest

from divineos.cli.build_flow_commands import _lenses_applied


def _walk(path: str, expert: str) -> dict:
    """A COUNCIL_LENS_APPLIED row shaped like the real ledger writes it."""
    return {
        "event_id": f"{expert}-{path}",
        "event_type": "COUNCIL_LENS_APPLIED",
        "payload": {"edit_fingerprint": f"edit:{path}", "expert_name": expert},
    }


@pytest.fixture
def ledger(monkeypatch):
    """Install a fake ledger and hand back the mutable row list."""
    rows: list[dict] = []

    def fake_get_events(**_kwargs):
        return rows

    import divineos.core.ledger as ledger_mod

    monkeypatch.setattr(ledger_mod, "get_events", fake_get_events)
    return rows


def test_cannot_check_is_not_zero(ledger):
    """paths=None means gh could not say what changed.

    The whole reason Status carries three values. Returning 0 here renders
    the station as MISS, which asserts something the check never
    established.
    """
    assert _lenses_applied(None) is None


def test_genuinely_unwalked_file_is_zero(ledger):
    ledger.append(_walk("src/divineos/core/other.py", "Turing"))
    assert _lenses_applied(("src/divineos/core/untouched.py",)) == 0


def test_counts_walks_on_the_changed_files(ledger):
    """The regression this file exists for: match on path, not branch."""
    ledger.extend(
        [
            _walk("docs/spec.md", "Turing"),
            _walk("docs/spec.md", "Wayne"),
            _walk("docs/spec.md", "Norman"),
            _walk("docs/spec.md", "Pearl"),
        ]
    )
    assert _lenses_applied(("docs/spec.md",)) == 4


def test_distinct_lenses_not_walk_events(ledger):
    """Requirement is phrased 'needs N lenses'; count experts, not rows.

    Measured motivation: counting events gave one PR 68 against a
    requirement of 6, and 31 of those came from a single high-traffic file
    (.claude/settings.json) that nearly every PR touches. One expert
    applied 31 times to a shared file is not 31 perspectives on this work.
    """
    ledger.extend([_walk(".claude/settings.json", "Beer") for _ in range(31)])
    assert _lenses_applied((".claude/settings.json",)) == 1


def test_absolute_and_relative_paths_both_match(ledger):
    """Walks may record an absolute path; changed-files are repo-relative."""
    ledger.append(_walk("C:/repo/src/divineos/core/paths.py", "Knuth"))
    assert _lenses_applied(("src/divineos/core/paths.py",)) == 1


def test_rows_without_an_edit_fingerprint_are_ignored(ledger):
    ledger.append({"event_id": "x", "payload": {"expert_name": "Turing"}})
    assert _lenses_applied(("docs/spec.md",)) == 0


def test_empty_changed_set_is_zero_not_none(ledger):
    """A PR that changes nothing is measurable and genuinely has no walks."""
    ledger.append(_walk("docs/spec.md", "Turing"))
    assert _lenses_applied(()) == 0
