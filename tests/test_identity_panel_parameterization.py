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

    def test_aria_age_falls_back_to_ledger_when_family_stamp_missing(self):
        """If family.db has no row for Aria, fall back to ledger-first."""
        with (
            patch("divineos.core.identity.get_my_identity", return_value="Aria"),
            patch(
                "divineos.core.multiplex_panels._agent_age_days_from_family_stamp",
                return_value=None,
            ),
            patch("divineos.core.multiplex_panels._agent_age_days_from_ledger", return_value=15),
        ):
            content = multiplex_panels._identity_panel_content()
        assert "15 days old" in content
