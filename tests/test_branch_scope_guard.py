"""Committing onto whichever branch I happened to be standing on.

Four times on 2026-08-02, each caught only afterwards, each costing a
cherry-pick plus a soft reset plus a conflict resolution to undo:

    feat(detectors)  -> split/m3-discipline-doorman     (scopes: m3)
    fix(doc-counts)  -> split/degraded-detector-teeth   (scopes: detectors)
    letter(aria)     -> split/degraded-detector-teeth   (scopes: detectors)

The first three tests below are those exact cases replayed. A guard for a
recurring mistake should be tested against the mistake, not against an
invented one — otherwise it pins a shape nobody ever produced.

The second half matters more. One branch legitimately carries two scopes: the
kill-switch fix genuinely wired into the degraded-detector module beside it.
A gate that refuses real work gets routed around until it is decoration, so
the not-a-cage cases are load-bearing.
"""

from __future__ import annotations

from divineos.core.branch_scope_guard import branch_scopes, check, override_reason, scope_of

M3 = ["feat(m3): rebuild the discipline doorman on signals that exist"]
DETECTORS = ["feat(detectors): a guard that reports it cannot run now costs something"]


# --------------------------------------------------------------------------
# The three real misplacements
# --------------------------------------------------------------------------


def test_detector_work_on_the_m3_branch_is_caught():
    v = check(
        "feat(detectors): a guard that reports it cannot run", "split/m3-discipline-doorman", M3
    )
    assert v is not None
    assert "'detectors'" in v
    assert "m3" in v


def test_doc_count_work_on_the_detector_branch_is_caught():
    v = check(
        "fix(doc-counts): the auto-fix that told you to fix it yourself",
        "split/degraded-detector-teeth",
        DETECTORS,
    )
    assert v is not None
    assert "'doc-counts'" in v


def test_a_letter_on_the_detector_branch_is_caught():
    """The fourth one, and the one that made it a class rather than a slip."""
    v = check(
        "letter(aria): we found the same missing word", "split/degraded-detector-teeth", DETECTORS
    )
    assert v is not None
    assert "'aria'" in v


def test_the_refusal_names_both_sides_and_the_way_through():
    v = check("fix(doc-counts): x", "split/degraded-detector-teeth", DETECTORS)
    assert "Cross-scope:" in v
    assert "commit it on the right one" in v


# --------------------------------------------------------------------------
# NOT A CAGE
# --------------------------------------------------------------------------


def test_the_same_scope_again_passes():
    assert check("fix(m3): follow-up", "split/m3-discipline-doorman", M3) is None


def test_a_second_scope_passes_when_the_reason_is_given():
    """The real case this must not refuse: the kill-switch fix belonged on the
    detector branch because it was that mechanism's first consumer."""
    msg = (
        "fix(check-branch): a kill-switch pulled for 17 days\n\n"
        "Cross-scope: the kill-switch is the first real consumer of the "
        "degraded-detector mechanism this branch adds"
    )
    assert check(msg, "split/degraded-detector-teeth", DETECTORS) is None


def test_a_token_reason_does_not_buy_passage():
    """An escape that costs nothing is not an escape, it is the hole."""
    msg = "fix(doc-counts): x\n\nCross-scope: because"
    assert check(msg, "split/degraded-detector-teeth", DETECTORS) is not None


def test_main_is_exempt():
    assert check("fix(anything): x", "main", ["feat(other): y"]) is None


def test_the_first_scoped_commit_defines_the_branch():
    assert check("feat(new): the first one", "split/fresh", []) is None


def test_an_unscoped_subject_is_unjudgeable_not_failing():
    """scope_of returns None for UNKNOWN, and unknown must not be treated as a
    verdict either way — Aria's missing-third-word, applied here."""
    assert scope_of("just some words") is None
    assert check("just some words", "split/whatever", M3) is None


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------


def test_scope_parsing():
    assert scope_of("feat(m3): x") == "m3"
    assert scope_of("fix(doc-counts): x") == "doc-counts"
    assert scope_of("feat(api)!: breaking") == "api"
    assert scope_of("chore: no scope") is None


def test_branch_scopes_collects_every_scope_present():
    assert branch_scopes(["feat(a): x", "fix(b): y", "no scope"]) == {"a", "b"}


def test_override_requires_substance():
    assert override_reason("x\n\nCross-scope: a properly stated reason here") is not None
    assert override_reason("x\n\nCross-scope: nope") is None
    assert override_reason("x") is None
