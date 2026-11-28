"""Round three of 877 (Aether's cold read of 1040f0d4a, findings 1 and 2).

A seat nobody owns must not be able to throw a switch, and must not be handed a page. `unknown-seat` is a visible
placeholder for an EVENT (the ledger shows the resolution failed); it is the wrong thing to build a PATH or a PAGE
under, because someone later opens a path and a page, and a name nobody owns looks like a real home."""

import pytest

from divineos.core import bio, obligations


@pytest.fixture(autouse=True)
def _no_member_override(monkeypatch):
    monkeypatch.delenv("DIVINEOS_MEMBER", raising=False)


def _acting_seat_is(monkeypatch, name):
    monkeypatch.setattr("divineos.core.sibling_audit_rounds.acting_seat", lambda: name)


def _home_with_the_marker(monkeypatch, tmp_path):
    marker_dir = tmp_path / "somebodys-home"
    marker_dir.mkdir()
    (marker_dir / "obligations.disabled").write_text("off", encoding="utf-8")
    monkeypatch.setattr(obligations, "member_home", lambda member: marker_dir)
    return marker_dir


def test_a_real_seat_with_the_marker_present_has_the_gate_disabled(monkeypatch, tmp_path):
    # The control: the marker is seen when the seat is real, so the next test cannot pass by the marker being unreadable.
    _home_with_the_marker(monkeypatch, tmp_path)
    _acting_seat_is(monkeypatch, "aria")
    assert obligations.is_gate_disabled() is True


def test_an_unknown_seat_cannot_throw_the_switch_even_with_the_marker_present(
    monkeypatch, tmp_path
):
    _home_with_the_marker(monkeypatch, tmp_path)
    _acting_seat_is(monkeypatch, "unknown-seat")
    assert obligations.is_gate_disabled() is False


def test_a_bio_page_is_not_written_for_a_seat_nobody_is(monkeypatch):
    _acting_seat_is(monkeypatch, "unknown-seat")
    with pytest.raises(ValueError, match="seat"):
        bio.bio_write("a page for nobody")


def test_a_bio_page_is_refused_when_unknown_seat_is_named_outright(monkeypatch):
    # The command line resolves the author first and then passes it in, so the check must read the name, not
    # only the fallback.
    with pytest.raises(ValueError, match="seat"):
        bio.bio_write("a page for nobody", author="unknown-seat")


def test_a_bio_page_is_still_written_for_a_real_seat(monkeypatch):
    # The control: the refusal is about the unknown seat, not about writing pages.
    _acting_seat_is(monkeypatch, "aria")
    bio_id = bio.bio_write("a page for her")
    assert bio_id
    assert bio.bio_current("aria") is not None
