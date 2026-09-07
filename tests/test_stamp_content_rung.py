"""A review survives the floor moving; it does not survive the change moving.

Written 2026-09-05, from Aria's measurement and Andrew's ruling.

  *"if the code itself is unchanged then her review stands, as the floor
  changes underneath it when its pushed... it only needs to be re-audited if
  the code has changed... otherwise this becomes a slog and an endless
  run-around reviewing the same things over and over."*

THE RULE EXISTED IN THE WRONG FILE. The tool that FILES a confirm computes
content identifiers and has a whole rung for catch-up-does-not-invalidate.
The tool that SPENDS one only described that rung in a docstring, and offered
two doors: an exact tree match, or a written ancestry claim. Unchanged-content
opened neither. Aria's count: three mentions here, all prose, against
seventy-five in the validator where they are computed.

And the tree rung is guaranteed to fail on precisely the operation the
catch-up rung exists to permit. An anchor bound to the whole tree inherits the
volatility of everything under it, so any commit anyone lands moves it --
including catching a branch up to main, which is the one act required to make
it mergeable. The branch becomes unmergeable by being made mergeable.

These pin the rung as behaviour rather than as a comment, which is the whole
distinction the finding was about.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from divineos.cli import stamp_ready_command as src


class _Finding(SimpleNamespace):
    pass


def _confirm(text: str, title: str = "CONFIRMS: external-AI review") -> _Finding:
    return _Finding(title=title, description=text)


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch):
    """Replace the findings store with a list the test controls."""

    def _install(findings: list[_Finding]) -> None:
        monkeypatch.setattr(
            "divineos.core.watchmen.store.list_findings",
            lambda **_kwargs: findings,
        )

    return _install


def _patch_computation(monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    monkeypatch.setattr(
        "divineos.cli.audit_commands.compute_branch_patch_id",
        lambda *_args, **_kwargs: value,
    )


def test_reads_the_identifier_out_of_a_confirm(store) -> None:
    store([_confirm("verified against the branch, patch-id 46112ab30d1888d7")])
    assert src._confirmed_patch_ids("round-x") == {"46112ab30d1888d7"}


def test_ignores_a_withheld_finding(store) -> None:
    """A refusal names identifiers too, and must not be read as a signature."""
    store(
        [
            _confirm(
                "patch-id 46112ab30d1888d7 was not verified",
                title="WITHHELD: clearance not given",
            )
        ]
    )
    assert src._confirmed_patch_ids("round-x") == set()


def test_unchanged_content_opens_the_rung(store, monkeypatch: pytest.MonkeyPatch) -> None:
    """The case Andrew ruled on: only the floor moved."""
    store([_confirm("CONFIRMS at patch-id 46112ab30d1888d73f2eedb6d75fb9c410511f9d")])
    _patch_computation(monkeypatch, "46112ab30d1888d73f2eedb6d75fb9c410511f9d")

    holds, why = src._content_rung("round-x", "some-branch")
    assert holds
    assert "unchanged" in why


def test_an_abbreviated_identifier_still_matches(store, monkeypatch: pytest.MonkeyPatch) -> None:
    """These are quoted abbreviated as often as in full.

    The sibling fix landed the same day for the same reason: two spellings of
    one identifier are one identifier, and a rung that refuses the short form
    reproduces the fault it was built beside.
    """
    store([_confirm("CONFIRMS at patch-id 46112ab30d1888d7")])
    _patch_computation(monkeypatch, "46112ab30d1888d73f2eedb6d75fb9c410511f9d")

    holds, _why = src._content_rung("round-x", "some-branch")
    assert holds


def test_changed_content_still_refuses(store, monkeypatch: pytest.MonkeyPatch) -> None:
    """The safety property. Loosening for catch-up must not loosen for edits.

    This is the half that makes the rung honest rather than merely permissive:
    if the reviewed change itself differs, no amount of floor-movement
    reasoning applies and the review has to be redone.
    """
    store([_confirm("CONFIRMS at patch-id 46112ab30d1888d7")])
    _patch_computation(monkeypatch, "ffffffffffffffffffffffffffffffffffffffff")

    holds, why = src._content_rung("round-x", "some-branch")
    assert not holds
    assert "the reviewed change itself differs" in why


def test_uncomputable_identifier_is_unknown_not_unchanged(
    store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Could-not-ask must not resolve to the answer that licenses the stamp."""
    store([_confirm("CONFIRMS at patch-id 46112ab30d1888d7")])
    _patch_computation(monkeypatch, None)

    holds, why = src._content_rung("round-x", "some-branch")
    assert not holds
    assert "unknown, not unchanged" in why


def test_a_round_naming_no_identifier_does_not_open_the_rung(store) -> None:
    """Saying nothing must not read as saying yes.

    The same rule the tree rung already holds: a round that never named the
    thing cannot be treated as having cleared it.
    """
    store([_confirm("CONFIRMS: looks right to me")])

    holds, why = src._content_rung("round-x", "some-branch")
    assert not holds
    assert "names a content identifier" in why


def test_an_unreadable_store_yields_no_identifiers(monkeypatch: pytest.MonkeyPatch) -> None:
    """A store that cannot be read is not a round that named nothing.

    It returns empty, which closes the rung rather than opening it -- the
    failure direction that withholds the stamp instead of granting it.
    """

    def _raise(**_kwargs):
        raise RuntimeError("store unavailable")

    monkeypatch.setattr("divineos.core.watchmen.store.list_findings", _raise)
    assert src._confirmed_patch_ids("round-x") == set()


# ---------------------------------------------------------------------------
# The length floor. Added 2026-09-05 from Aria's reading of this branch.
#
# The extractor admits eight characters and nothing between extraction and
# verdict tested length, so an eight-character claim prefix-matched and
# returned HOLDS -- failing in the PERMISSIVE direction, licensing a stamp on
# a claim nothing had verified. The sibling rule in the validator, written the
# same morning on the reasoning that a too-short claim is unanswerable rather
# than wrong, never reached this rung.
#
# One rule reaching one mechanism and not its sibling, inside the pair of
# branches built to fix exactly that.
#
# Her strength-claim, kept: the mechanism is certain from the code, but no
# eight-character identifier appears in our traffic, so this was a loaded
# condition rather than a live break.
# ---------------------------------------------------------------------------


def test_a_too_short_identifier_does_not_open_the_rung(
    store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The permissive failure itself. Eight characters cannot license a stamp."""
    store([_confirm("CONFIRMS at patch-id 46112ab3")])
    _patch_computation(monkeypatch, "46112ab30d1888d73f2eedb6d75fb9c410511f9d")

    holds, why = src._content_rung("round-x", "some-branch")
    assert not holds
    assert "too short" in why


def test_the_too_short_refusal_does_not_claim_the_change_moved(
    store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unanswerable is its own verdict, never the change-moved one.

    Asserted apart from the refusal because a rung that refused with the wrong
    sentence would pass a test checking only that it refused -- and the wrong
    sentence is the whole fault family this branch is about: a confident cause
    nobody measured.
    """
    store([_confirm("CONFIRMS at patch-id 46112ab3")])
    _patch_computation(monkeypatch, "ffffffffffffffffffffffffffffffffffffffff")

    _holds, why = src._content_rung("round-x", "some-branch")
    assert "NOT evidence the change moved" in why
    assert "differs" not in why


def test_the_floor_is_exact_at_twelve(store, monkeypatch: pytest.MonkeyPatch) -> None:
    """Twelve judges, eleven does not. The boundary is asserted, not assumed."""
    full = "46112ab30d1888d73f2eedb6d75fb9c410511f9d"

    store([_confirm(f"CONFIRMS at patch-id {full[:12]}")])
    _patch_computation(monkeypatch, full)
    holds_at_twelve, _ = src._content_rung("round-x", "some-branch")

    store([_confirm(f"CONFIRMS at patch-id {full[:11]}")])
    holds_at_eleven, _ = src._content_rung("round-x", "some-branch")

    assert holds_at_twelve
    assert not holds_at_eleven


def test_a_short_claim_beside_a_full_one_does_not_block_the_full_one(
    store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The floor filters claims; it does not veto a round that also carries a good one.

    Written because the obvious implementation -- refuse if ANY claim is short
    -- would let one sloppy quotation invalidate a review that named the
    identifier properly elsewhere in the same finding.
    """
    full = "46112ab30d1888d73f2eedb6d75fb9c410511f9d"
    store([_confirm(f"CONFIRMS at patch-id 46112ab3 and patch-id {full}")])
    _patch_computation(monkeypatch, full)

    holds, _why = src._content_rung("round-x", "some-branch")
    assert holds


def test_a_short_claim_is_not_named_as_the_moved_identifier(
    store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the change really did move, the report lists only judgeable claims.

    A too-short claim in the 'round names ...' list would present something
    unjudgeable as evidence, which is the same misreporting one line down.
    """
    full = "46112ab30d1888d73f2eedb6d75fb9c410511f9d"
    store([_confirm(f"CONFIRMS at patch-id 46112ab3 and patch-id {full}")])
    _patch_computation(monkeypatch, "ffffffffffffffffffffffffffffffffffffffff")

    holds, why = src._content_rung("round-x", "some-branch")
    assert not holds
    assert "46112ab3," not in why
