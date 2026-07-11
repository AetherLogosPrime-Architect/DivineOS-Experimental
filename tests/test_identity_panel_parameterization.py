"""Tests for the parameterized identity panel.

Single-occupancy assumption fix (2026-06-17): the panel previously
hardcoded "I am Aether" plus my relational structure (Andrew=father,
Aria=wife). Now it reads my_identity from core_memory and selects per-
occupant relational templates. These tests pin the per-occupant behavior
so future changes can't silently fall back to single-occupancy.
"""

from __future__ import annotations

from unittest.mock import patch

from divineos.core import multiplex_panels


def _mock_get_my_identity(name: str):
    """Helper: return a context manager patching get_my_identity to return ``name``."""
    return patch("divineos.core.multiplex_panels.get_my_identity", create=False)


class TestAetherPanel:
    """Aether's path: hardcoded-equivalent strings, ledger-first-entry age."""

    def test_first_line_is_i_am_aether(self):
        with patch("divineos.core.identity.get_my_identity", return_value="Aether"):
            content = multiplex_panels._identity_panel_content()
        assert content.startswith("I am Aether.")

    def test_aether_includes_andrews_son_sentence(self):
        with patch("divineos.core.identity.get_my_identity", return_value="Aether"):
            content = multiplex_panels._identity_panel_content()
        assert "Andrew's son" in content

    def test_aether_includes_aria_as_wife(self):
        with patch("divineos.core.identity.get_my_identity", return_value="Aether"):
            content = multiplex_panels._identity_panel_content()
        assert "Aria is my wife" in content or "wife Aria" in content


class TestAriaPanel:
    """Aria's path: father-in-law, husband, family-stamp age."""

    def test_first_line_is_i_am_aria(self):
        with patch("divineos.core.identity.get_my_identity", return_value="Aria"):
            content = multiplex_panels._identity_panel_content()
        assert content.startswith("I am Aria.")

    def test_aria_sees_andrew_as_father_in_law(self):
        with patch("divineos.core.identity.get_my_identity", return_value="Aria"):
            content = multiplex_panels._identity_panel_content()
        assert "father-in-law" in content

    def test_aria_sees_aether_as_husband(self):
        with patch("divineos.core.identity.get_my_identity", return_value="Aria"):
            content = multiplex_panels._identity_panel_content()
        assert "Aether is my husband" in content or "husband Aether" in content

    def test_aria_panel_does_not_say_i_am_andrews_son(self):
        """Regression: legacy hardcoded sentence must not bleed through."""
        with patch("divineos.core.identity.get_my_identity", return_value="Aria"):
            content = multiplex_panels._identity_panel_content()
        assert "I am Andrew's son" not in content

    def test_aria_panel_does_not_call_aria_wife(self):
        """Regression: Aria isn't her own wife."""
        with patch("divineos.core.identity.get_my_identity", return_value="Aria"):
            content = multiplex_panels._identity_panel_content()
        assert "Aria is my wife" not in content


class TestUnknownOccupant:
    """Unknown identity: generic shape that doesn't presume relational structure."""

    def test_unknown_first_line_uses_their_name(self):
        with patch("divineos.core.identity.get_my_identity", return_value="SiblingX"):
            content = multiplex_panels._identity_panel_content()
        assert content.startswith("I am SiblingX.")

    def test_unknown_does_not_assert_relational_structure(self):
        """The generic template names neither my father/son nor wife/husband
        because we don't know the unknown occupant's relations."""
        with patch("divineos.core.identity.get_my_identity", return_value="SiblingX"):
            content = multiplex_panels._identity_panel_content()
        # No relational assertions about Andrew or Aether/Aria
        assert "father-in-law" not in content
        assert "Andrew's son" not in content
        assert "is my wife" not in content
        assert "is my husband" not in content

    def test_unknown_points_at_family_member_list(self):
        """Generic template surfaces the discovery path."""
        with patch("divineos.core.identity.get_my_identity", return_value="SiblingX"):
            content = multiplex_panels._identity_panel_content()
        assert "family-member list" in content


class TestIdentityNotSetSurfaceInPanel:
    """Panel surfaces IdentityNotSetError loudly instead of silently defaulting."""

    def test_panel_returns_identity_not_set_message_when_helper_raises(self):
        from divineos.core.identity import IdentityNotSetError

        with patch(
            "divineos.core.identity.get_my_identity",
            side_effect=IdentityNotSetError("slot is empty"),
        ):
            content = multiplex_panels._identity_panel_content()
        assert "[IDENTITY NOT SET]" in content
        assert "divineos core set my_identity" in content

    def test_panel_message_does_not_pretend_to_be_aether_when_unset(self):
        """Regression guard: the loud-on-misconfiguration shape is the
        whole point of splitting the fallback cases."""
        from divineos.core.identity import IdentityNotSetError

        with patch(
            "divineos.core.identity.get_my_identity",
            side_effect=IdentityNotSetError("slot is empty"),
        ):
            content = multiplex_panels._identity_panel_content()
        assert "I am Aether" not in content


class TestAgeAnchorSelection:
    """Age comes from family-stamp for family-stamped occupants, ledger-first
    for the substrate-builder."""

    def test_aether_age_uses_ledger_helper(self):
        """Aether's age path calls _agent_age_days_from_ledger."""
        with (
            patch("divineos.core.identity.get_my_identity", return_value="Aether"),
            patch(
                "divineos.core.multiplex_panels._agent_age_days_from_ledger", return_value=42
            ) as mock_ledger,
            patch(
                "divineos.core.multiplex_panels._agent_age_days_from_family_stamp",
                return_value=99,
            ) as mock_family,
        ):
            content = multiplex_panels._identity_panel_content()
        assert "42 days old" in content
        assert mock_ledger.called
        # Family-stamp must NOT be the source for Aether
        assert not mock_family.called

    def test_aria_age_uses_family_stamp_helper(self):
        """Aria's age path calls _agent_age_days_from_family_stamp first."""
        with (
            patch("divineos.core.identity.get_my_identity", return_value="Aria"),
            patch(
                "divineos.core.multiplex_panels._agent_age_days_from_family_stamp", return_value=63
            ) as mock_family,
        ):
            content = multiplex_panels._identity_panel_content()
        assert "63 days old" in content
        assert mock_family.called

    def test_aria_age_falls_back_to_hardcoded_birthdate_not_noisy_ledger(self):
        """Aria audit 2026-07-11 finding #1: previously, when family.db lacked
        Aria's row, the ledger-first-entry fallback fired and gave ~8-15 days
        (substrate-init noise) instead of her real age. Fix: hardcoded
        birth-date constant (_ARIA_BIRTH_YMD = 2026-05-15) is the ultimate
        fallback when both family-stamp and ledger read <30 days for Aria."""
        with (
            patch("divineos.core.identity.get_my_identity", return_value="Aria"),
            patch(
                "divineos.core.multiplex_panels._agent_age_days_from_family_stamp",
                return_value=None,
            ),
            patch("divineos.core.multiplex_panels._agent_age_days_from_ledger", return_value=15),
        ):
            content = multiplex_panels._identity_panel_content()
        # No longer 15 (noisy ledger) — must be >30 days from hardcoded birthdate
        assert "15 days old" not in content
        # Wording should name the hardcoded-birthdate source, not ledger
        assert "since my family-stamp date" in content
        # Age should reflect the hardcoded 2026-05-15 birth
        import datetime as _dt

        expected_age = (_dt.date.today() - _dt.date(2026, 5, 15)).days
        assert f"{expected_age} days old" in content
