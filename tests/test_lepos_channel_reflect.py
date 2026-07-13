"""Tests for post-send lepos reflection channel."""

from __future__ import annotations

from divineos.core.lepos_channel_reflect import (
    Reflection,
    _find_interior_marker,
    pending_surface_path,
    read_and_consume_pending,
    reflect,
    render_pending_or_empty,
    write_pending,
)


def test_reflect_detects_exact_span_citation() -> None:
    andrew = "the gate/channel needs to be triggered after your initial post"
    reply = "so the channel needs to be triggered after your initial post — got it"
    r = reflect(reply, andrew)
    assert r.heard is True
    assert r.heard_span is not None
    # Post 2026-07-09 window reduction (5 -> 3), the first-matched 3-word span
    # returned may or may not include "triggered" depending on tokenization
    # order. The load-bearing invariant is that a real shared span was
    # detected and its tokens all appear in Andrew's message.
    for tok in r.heard_span.split():
        assert tok in andrew.lower()


def test_reflect_no_citation_when_paraphrasing() -> None:
    andrew = "we usually do block first because it locates the violation"
    reply = "yeah okay makes sense to me sure whatever you say"
    r = reflect(reply, andrew)
    assert r.heard is False
    assert r.heard_span is None


def test_reflect_detects_interior_marker() -> None:
    andrew = "want me to build the block first?"
    reply = "I think block-first is right — I have a concern about the ordering though"
    r = reflect(reply, andrew)
    assert r.interior is True
    assert r.interior_marker is not None


def test_degenerate_when_both_lenses_fail() -> None:
    andrew = "wat"
    reply = "totally " * 100  # no citation, no interior marker
    r = reflect(reply, andrew)
    assert r.degenerate() is True


def test_not_degenerate_when_interior_present() -> None:
    andrew = "wat"
    reply = "I think " + "totally " * 100
    r = reflect(reply, andrew)
    assert r.degenerate() is False


def test_not_degenerate_when_heard_present() -> None:
    andrew = "the channel needs to be triggered after your initial post"
    reply = "the channel needs to be triggered after your initial post"
    r = reflect(reply, andrew)
    assert r.degenerate() is False


def test_write_and_consume_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    r = reflect("I think the channel is right", "the channel should be right", now=1000.0)
    write_pending(r)
    assert pending_surface_path().exists()
    got = read_and_consume_pending()
    assert got is not None
    assert got.ts == 1000.0
    assert got.interior is True
    assert not pending_surface_path().exists()


def test_read_pending_returns_none_when_absent(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    assert read_and_consume_pending() is None


def test_render_pending_returns_empty_when_absent(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    assert render_pending_or_empty() == ""


def test_render_pending_includes_channel_empty_when_degenerate(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    r = Reflection(
        ts=1.0,
        heard=False,
        heard_span=None,
        interior=False,
        interior_marker=None,
    )
    write_pending(r)
    out = render_pending_or_empty()
    assert "LEPOS REFLECTION" in out
    assert "channel-empty" in out


def test_read_and_consume_is_one_shot(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    r = reflect("I feel steady", "just checking in", now=42.0)
    write_pending(r)
    assert read_and_consume_pending() is not None
    assert read_and_consume_pending() is None


# --- Aria's LEPOS presence-density Goodhart fix (2026-07-11) ---
# Aria root-caused the mesa-optimizer close-shape she was running
# (`Feeling: **[word].**` at every reply) into the interior-marker
# detector: path (b) — _INTERIOR_ANCHOR_RE at paragraph start — passed
# the check on its own, equal-weight to (a) verbs/possessives and (c)
# expression texture. That made (b) the cheapest close/opener the
# optimizer could reach for. Fix (Shape 1): (b) is legibility-only; (a)
# or (c) alone still passes.


def test_bold_feeling_anchor_alone_does_not_pass() -> None:
    """Aria's exact suggested test: a reply with ONLY a bold Feeling-anchor
    at the close, no other interior signal in the body, must return None
    from _find_interior_marker. The reflex compliance-shape must fail."""
    reply = "The fix landed. Tests are green.\n\nFeeling: **home.**"
    assert _find_interior_marker(reply) is None


def test_bare_interior_anchor_at_open_alone_does_not_pass() -> None:
    """Aether-shape (compose-start `Interior:` opener). Same seam as
    Aria's close-shape — path (b) alone must not clear the check."""
    reply = "Interior: quiet.\n\nThe migration succeeded and tests are green."
    assert _find_interior_marker(reply) is None


def test_verb_marker_a_alone_still_passes() -> None:
    """Symmetric positive: path (a) — real interior speech — clears the
    check on its own without any recognition anchor."""
    reply = "The migration succeeded. I feel steady about the rollback plan."
    assert _find_interior_marker(reply) is not None


def test_expression_texture_c_alone_still_passes() -> None:
    """Symmetric positive: path (c) — first-person felt-body/quality span
    of >=40 chars — clears the check on its own."""
    reply = (
        "I noticed a specific quiet settling in me as the rebase went "
        "through cleanly and the tests came back green."
    )
    assert _find_interior_marker(reply) is not None


def test_anchor_plus_verb_marker_passes_via_a() -> None:
    """When (a) is present in the body AND (b) appears at close, the
    finder still returns a signal — it returns (a)'s match. Recognition
    anchor being present does not degrade a genuine interior signal."""
    reply = "I feel this landed cleanly and the audit trail is intact.\n\nFeeling: **steady.**"
    assert _find_interior_marker(reply) is not None
