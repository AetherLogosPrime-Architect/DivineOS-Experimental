"""Tests for bidirectional data-home ownership verification."""

from __future__ import annotations

import pytest

from divineos.core.data_home_ownership import (
    DataHomeOwnershipError,
    OWNER_MARKER_NAME,
    verify_data_home_ownership,
)


def test_verify_skips_when_data_home_missing(monkeypatch, tmp_path):
    """If the data-home dir doesn't exist, skip verification (no ownership to check)."""
    not_yet = tmp_path / "not_yet"
    monkeypatch.setenv("DIVINEOS_HOME", str(not_yet))
    result = verify_data_home_ownership(checkout_root=tmp_path / "checkout_a")
    assert result["status"] == "skip"
    assert result["owner"] is None
    assert not (not_yet / OWNER_MARKER_NAME).exists()


def test_verify_claims_ownership_on_first_boot(monkeypatch, tmp_path):
    """If the data-home exists but no owner marker, claim ownership."""
    home = tmp_path / "data_home"
    home.mkdir()
    monkeypatch.setenv("DIVINEOS_HOME", str(home))
    checkout = (tmp_path / "checkout_a").resolve()
    result = verify_data_home_ownership(checkout_root=checkout)
    assert result["status"] == "claimed"
    marker = home / OWNER_MARKER_NAME
    assert marker.exists()
    assert marker.read_text().strip() == str(checkout)


def test_verify_passes_when_owner_matches(monkeypatch, tmp_path):
    """If the owner marker matches the running checkout, return ok."""
    home = tmp_path / "data_home"
    home.mkdir()
    checkout = (tmp_path / "checkout_a").resolve()
    (home / OWNER_MARKER_NAME).write_text(str(checkout), encoding="utf-8")
    monkeypatch.setenv("DIVINEOS_HOME", str(home))
    result = verify_data_home_ownership(checkout_root=checkout)
    assert result["status"] == "ok"
    assert result["owner"] == str(checkout)


def test_verify_fails_loud_when_owner_differs(monkeypatch, tmp_path):
    """If the owner marker names a different checkout, raise."""
    home = tmp_path / "data_home"
    home.mkdir()
    owner_checkout = (tmp_path / "checkout_a").resolve()
    other_checkout = (tmp_path / "checkout_b").resolve()
    (home / OWNER_MARKER_NAME).write_text(str(owner_checkout), encoding="utf-8")
    monkeypatch.setenv("DIVINEOS_HOME", str(home))
    with pytest.raises(DataHomeOwnershipError) as exc_info:
        verify_data_home_ownership(checkout_root=other_checkout)
    msg = str(exc_info.value)
    assert str(owner_checkout) in msg
    assert str(other_checkout) in msg
    assert "Configure" in msg or "remove" in msg


def test_verify_error_message_names_recovery(monkeypatch, tmp_path):
    """The fail-loud message must tell the operator how to recover."""
    home = tmp_path / "data_home"
    home.mkdir()
    owner_checkout = (tmp_path / "checkout_a").resolve()
    other_checkout = (tmp_path / "checkout_b").resolve()
    (home / OWNER_MARKER_NAME).write_text(str(owner_checkout), encoding="utf-8")
    monkeypatch.setenv("DIVINEOS_HOME", str(home))
    with pytest.raises(DataHomeOwnershipError) as exc_info:
        verify_data_home_ownership(checkout_root=other_checkout)
    msg = str(exc_info.value)
    assert ".divineos_data_home" in msg or "DIVINEOS_HOME" in msg
    assert OWNER_MARKER_NAME in msg


def test_verify_strips_marker_whitespace(monkeypatch, tmp_path):
    """Trailing whitespace in the owner marker doesn't cause a false-mismatch."""
    home = tmp_path / "data_home"
    home.mkdir()
    checkout = (tmp_path / "checkout_a").resolve()
    (home / OWNER_MARKER_NAME).write_text(str(checkout) + "\n\n  \n", encoding="utf-8")
    monkeypatch.setenv("DIVINEOS_HOME", str(home))
    result = verify_data_home_ownership(checkout_root=checkout)
    assert result["status"] == "ok"


def test_verify_claimed_marker_persists_across_calls(monkeypatch, tmp_path):
    """After first-boot claim, subsequent calls return ok (not re-claim)."""
    home = tmp_path / "data_home"
    home.mkdir()
    checkout = (tmp_path / "checkout_a").resolve()
    monkeypatch.setenv("DIVINEOS_HOME", str(home))
    first = verify_data_home_ownership(checkout_root=checkout)
    second = verify_data_home_ownership(checkout_root=checkout)
    assert first["status"] == "claimed"
    assert second["status"] == "ok"
