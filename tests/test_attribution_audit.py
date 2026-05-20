"""Tests for the attribution audit scanner.

The load-bearing property is PRECISION: the scanner must catch the
dated-quotative-attribution fabrication shape (the 2026-05-20 incident)
WITHOUT firing on bare entity mentions (the 307-of-662 toast-alarm that
a naive 'mentions Andrew' scan would produce). These tests pin both
sides: true positives fire, the toast-alarm shapes stay silent.
"""

from __future__ import annotations

from divineos.core.attribution_audit import (
    _has_resolvable_pointer,
    _match_attribution,
)


# --- true positives: dated quotative attributions must match ---------------


def test_parenthetical_dated_attribution_matches():
    assert _match_attribution("PRINCIPLE -- Captain-vessel metaphor (Andrew 2026-04-29) -- ...")


def test_quotative_dated_attribution_matches():
    assert _match_attribution("Andrew correction 2026-05-15: err over-inclusive on detectors.")


def test_aria_said_dated_matches():
    assert _match_attribution("QUOTE -- Aria said, 2026-04-17, refusing the skeleton scaffold.")


def test_self_diagnosis_dated_matches():
    assert _match_attribution("Discipline-eats-voice failure (Aria self-diagnosis 2026-04-25).")


# --- toast-alarm prevention: bare mentions must NOT match ------------------


def test_bare_mention_does_not_match():
    """'My user IS Andrew' is a mention, not a dated quotative attribution."""
    assert (
        _match_attribution("My user IS Andrew. When entries reference 'Andrew' in third person.")
        is None
    )


def test_undated_characterization_does_not_match():
    """'Andrew recognized that...' with no date is a characterization, not a
    dated quotative claim. Accepted false-negative to avoid over-firing."""
    assert _match_attribution("Andrew recognized that I choose to follow the OS rules.") is None


def test_lens_walk_attribution_does_not_match():
    """Council-lens reasoning ('Sagan would say') must not fire — Sagan is
    not a participant and lens-walks are reasoning, not quotative claims."""
    assert (
        _match_attribution("Through Sagan, 2026-05-20: the ledger is tamper-evidence not truth.")
        is None
    )


def test_plain_principle_does_not_match():
    assert _match_attribution("PRINCIPLE: Simple rules compose into complex behavior.") is None


# --- pointer resolution ----------------------------------------------------


def test_empty_source_events_no_pointer():
    assert _has_resolvable_pointer(None, None) is False
    assert _has_resolvable_pointer("[]", None) is False
    assert _has_resolvable_pointer("", "") is False


def test_nonempty_source_events_has_pointer():
    assert _has_resolvable_pointer('["evt-123"]', None) is True


def test_source_entity_counts_as_pointer():
    assert _has_resolvable_pointer(None, "claude_auditor") is True
