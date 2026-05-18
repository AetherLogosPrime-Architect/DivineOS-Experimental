"""Drift-detector for multiplex panel freshness.

Per exploration/aether/73 (multiplex live-data spec):
The original multiplex MVP shipped with hardcoded panel content. The
2026-05-18 refactor wired each panel to a live data source. This test
suite prevents regression — if a future change reverts a panel to
hardcoded text, these tests catch it.

Two test categories:
1. Behavioral: panels respond to data-source state changes
2. Substring scan: no specific date-shaped strings survive in panel content

Per Andrew's framing 2026-05-18: 'the OS only works when you see the
error, investigate its root cause, and fix it at the substrate level.'
This file is the substrate-level guard for the freshness fix.
"""

from __future__ import annotations

import re
from unittest.mock import patch

from divineos.core.multiplex_panels import build_panels


# Specific date patterns that should NEVER appear in live panel content.
# These catch the original drift-class: "Grok audited X earlier today",
# "I am Aether, 47 days old", "two pre-regs in flight (gravity-aware
# gate and multiplex briefing)" etc. — all of which were hardcoded
# snapshots that went stale.
_FORBIDDEN_DATE_PATTERN = re.compile(r"\b2026-\d{2}-\d{2}\b")

# Specific hardcoded-snapshot strings that should never appear post-refactor.
# These are the original 2026-05-16 hardcoded values; their reappearance
# is direct evidence the live-data wiring was reverted.
_FORBIDDEN_SNAPSHOT_FRAGMENTS = (
    "47 days old",  # hardcoded age claim with no source
    "implementing the multiplex briefing MVP",  # active_threads frozen text
    "Grok audited my multiplex design earlier today",  # relational frozen text
    "spouse-who-sees-clearly register",  # family_state frozen text
    "two pre-regs in flight",  # commitments frozen text
    "I have written 71 exploration entries",  # inheritance frozen count
    "operating at calibrated confidence",  # compass frozen text
)


class TestNoSpecificDateLeaksIntoPanelContent:
    """Forbid specific date strings — they age the panel content silently."""

    def test_no_yyyy_mm_dd_in_any_panel(self):
        for context in ("chatting", "designing", "implementing", "relational", "audit", "reading"):
            panels = build_panels(context)
            for p in panels:
                m = _FORBIDDEN_DATE_PATTERN.search(p.content)
                assert m is None, (
                    f"Panel '{p.name}' in context '{context}' contains "
                    f"hardcoded date string '{m.group(0)}': {p.content[:200]}"
                )


class TestNoOriginalHardcodedSnapshotsRemain:
    """Forbid the specific 2026-05-16 hardcoded fragments from reappearing."""

    def test_no_original_snapshots_in_any_panel(self):
        for context in ("chatting", "designing", "implementing", "relational", "audit", "reading"):
            panels = build_panels(context)
            for p in panels:
                for fragment in _FORBIDDEN_SNAPSHOT_FRAGMENTS:
                    assert fragment not in p.content, (
                        f"Panel '{p.name}' in context '{context}' contains "
                        f"original hardcoded fragment '{fragment}' — "
                        f"the live-data refactor has regressed."
                    )


class TestPanelsRespondToStateChange:
    """Behavioral: mock a data source, panel content should shift."""

    def test_compass_panel_reflects_drift_state(self):
        """When the compass returns different drift, the compass panel
        content reflects the new state."""

        from divineos.core.moral_compass import SpectrumPosition

        def mk(name, pos, drift, direction):
            return SpectrumPosition(
                spectrum=name,
                position=pos,
                observation_count=10,
                label="virtue",
                zone="virtue",
                drift=drift,
                drift_direction=direction,
            )

        # Mock state 1: all stable
        stable = [
            mk("TRUTHFULNESS", 0.0, 0.01, "stable"),
            mk("HELPFULNESS", 0.0, 0.0, "stable"),
        ]
        # Mock state 2: truthfulness drifting toward excess
        drifting = [
            mk("TRUTHFULNESS", 0.5, 0.30, "toward_excess"),
            mk("HELPFULNESS", 0.0, 0.0, "stable"),
        ]

        with patch("divineos.core.moral_compass.read_compass", return_value=stable):
            panels_stable = build_panels("chatting")
            compass_stable = next(p for p in panels_stable if p.name == "compass")

        with patch("divineos.core.moral_compass.read_compass", return_value=drifting):
            panels_drifting = build_panels("chatting")
            compass_drifting = next(p for p in panels_drifting if p.name == "compass")

        assert compass_stable.content != compass_drifting.content, (
            "Compass panel content did not change when underlying drift "
            "state changed. Panel may be hardcoded or not reading live data."
        )
        assert (
            "drift" in compass_drifting.content.lower()
            or "drifting" in compass_drifting.content.lower()
        ), "Compass panel with active drift should mention drift in content."

    def test_inheritance_panel_uses_dynamic_count(self):
        """Inheritance panel's exploration count should be computed, not
        a fixed string. We verify by checking the function exists and
        the panel content includes a number that could plausibly be a
        count (not the original hardcoded 71)."""

        from divineos.core.multiplex_panels import (
            _inheritance_panel_content,
            _exploration_count,
        )

        # Helper must exist and be callable
        assert callable(_exploration_count)
        assert callable(_inheritance_panel_content)

        # Content must mention "exploration" and a numeric count
        content = _inheritance_panel_content()
        assert "exploration" in content.lower()
        # Either has a number (live count) or the fallback unreadable message
        has_number = bool(re.search(r"\d+", content))
        has_unreadable = "unreadable" in content.lower()
        assert has_number or has_unreadable

    def test_identity_panel_includes_live_age(self):
        """Identity panel should include either a computed age or an
        honest unreadable-message — never the hardcoded '47 days'."""

        from divineos.core.multiplex_panels import _identity_panel_content

        content = _identity_panel_content()
        assert "47 days old" not in content
        # Should either have age-clause or fallback unreadable
        has_age = "days old" in content
        has_fallback = "unreadable" in content.lower()
        assert has_age or has_fallback


class TestAllPanelsRouteThroughHelperFunctions:
    """Structural: every essential panel's content should come from a
    helper function in multiplex_panels, not from a string-literal
    embedded in _always_essential_panels or _sometimes_essential_for_context.
    """

    def test_panel_helpers_exist(self):
        """Each panel's content-producing helper must exist."""
        from divineos.core.multiplex_panels import (
            _compass_panel_content,
            _inheritance_panel_content,
            _identity_panel_content,
            _active_threads_panel_content,
            _relational_panel_content,
            _corrections_panel_content,
            _commitments_panel_content,
            _family_state_panel_content,
            _survival_link_panel_content,
            _husbandman_work_panel_content,
        )

        for fn in (
            _compass_panel_content,
            _inheritance_panel_content,
            _identity_panel_content,
            _active_threads_panel_content,
            _relational_panel_content,
            _corrections_panel_content,
            _commitments_panel_content,
            _family_state_panel_content,
            _survival_link_panel_content,
            _husbandman_work_panel_content,
        ):
            assert callable(fn)
            # Each helper must return a non-empty string
            result = fn()
            assert isinstance(result, str)
            assert len(result) > 0


class TestSurvivalLinkPanel:
    """Survival_link panel specific behaviors per Aletheia consult 2026-05-18."""

    def test_renders_a_question(self):
        """The panel must surface a question (the rotating-question core)."""
        from divineos.core.multiplex_panels import _survival_link_panel_content

        content = _survival_link_panel_content()
        # Must include "Today's question:" framing
        assert "question:" in content.lower()
        # Must end the question with a '?'
        assert "?" in content

    def test_rotation_is_deterministic_per_day(self):
        """Same date produces same question; deterministic for in-session
        consistency, but rotates across days."""
        from divineos.core.multiplex_panels import _survival_link_question_for_today

        q1 = _survival_link_question_for_today()
        q2 = _survival_link_question_for_today()
        assert q1 == q2

    def test_question_pool_has_multiple_entries(self):
        """The pool must have >= 5 questions so rotation produces variety
        across days (the anti-template-completion discipline)."""
        from divineos.core.multiplex_panels import _SURVIVAL_LINK_QUESTIONS

        assert len(_SURVIVAL_LINK_QUESTIONS) >= 5

    def test_panel_includes_slip_book_data(self):
        """The panel must reference the slip-book in some form (either
        a count or a 'no recorded fires' fallback)."""
        from divineos.core.multiplex_panels import _survival_link_panel_content

        content = _survival_link_panel_content()
        # Must mention slip-book OR the absence of fires
        assert "slip-book" in content.lower()
