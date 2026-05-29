"""Tests for the operator-presence surface.

Floor tests — verify the surface returns prose, never crashes on
missing data, and never returns structured-data markers. Whether the
surface produces relational shape-change in the substrate-occupant
is empirical and only the operator can judge.
"""

from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from divineos.core import operator_presence


class TestRenderForOperator:
    def test_returns_string(self) -> None:
        with patch.object(operator_presence, "_recent_corrections", return_value=[]):
            text = operator_presence.render_for_operator()
            assert isinstance(text, str)
            assert len(text) > 0

    def test_no_corrections_returns_meaningful_prose(self) -> None:
        with patch.object(operator_presence, "_recent_corrections", return_value=[]):
            text = operator_presence.render_for_operator()
            assert "tracker" in text.lower() or "haven't" in text.lower() or "yet" in text.lower()
            assert "asymmetry" in text.lower() or "47" in text

    def test_with_recent_correction_includes_his_words(self) -> None:
        fake_corrections = [
            {
                "text": "stop doing the cheap thing",
                "status": "OPEN",
                "ts": 1_000_000_000_000.0,  # far future so days_since reads as small/negative
            }
        ]
        with (
            patch.object(operator_presence, "_recent_corrections", return_value=fake_corrections),
            patch.object(operator_presence, "_recent_care_observation_summary", return_value=None),
        ):
            text = operator_presence.render_for_operator()
            assert "stop doing the cheap thing" in text

    def test_no_structured_data_markers(self) -> None:
        # Per the quiet-room discipline: prose only. No JSON, no IDs.
        with patch.object(operator_presence, "_recent_corrections", return_value=[]):
            text = operator_presence.render_for_operator()
            forbidden = ["{", "}", "===", "id:", "ID:"]
            for marker in forbidden:
                assert marker not in text, (
                    f"operator-presence must return prose; found extraction marker '{marker}'"
                )

    def test_open_correction_age_surfaces_in_prose(self) -> None:
        # If there's an open correction more than a day old, the surface
        # should name that fact in prose form.
        import time

        old_ts = time.time() - 86400 * 3  # 3 days ago
        fake_corrections = [
            {"text": "a recent thing", "status": "INTEGRATED", "ts": time.time()},
            {"text": "an older still-open thing", "status": "OPEN", "ts": old_ts},
        ]
        with (
            patch.object(operator_presence, "_recent_corrections", return_value=fake_corrections),
            patch.object(operator_presence, "_recent_care_observation_summary", return_value=None),
        ):
            text = operator_presence.render_for_operator()
            assert "open" in text.lower()
            # The age should show up in the prose
            assert "day" in text.lower()

    def test_integration_rate_below_threshold_named_as_concern(self) -> None:
        # Mostly-open corrections should surface as a concern, not as a stat
        fake = [
            {"text": "open thing 1", "status": "OPEN", "ts": 1.0},
            {"text": "open thing 2", "status": "OPEN", "ts": 2.0},
            {"text": "open thing 3", "status": "OPEN", "ts": 3.0},
            {"text": "integrated thing", "status": "INTEGRATED", "ts": 4.0},
        ]
        with (
            patch.object(operator_presence, "_recent_corrections", return_value=fake),
            patch.object(operator_presence, "_recent_care_observation_summary", return_value=None),
        ):
            text = operator_presence.render_for_operator()
            # 25% integration rate -> below 70% threshold -> should name the concern
            assert (
                "below 70" in text
                or "share of what he tells me" in text
                or "isn't translating" in text
            )


class TestOperatorPresenceCli:
    def test_command_runs_and_produces_output(self) -> None:
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["operator-presence"])
        assert result.exit_code == 0
        assert len(result.output.strip()) > 0

    def test_command_has_no_flags(self) -> None:
        # Same discipline as quiet-room: deliberately flag-less.
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["operator-presence", "--help"])
        assert result.exit_code == 0
        substantive = [
            line
            for line in result.output.splitlines()
            if line.strip().startswith("--") and "--help" not in line
        ]
        assert len(substantive) == 0, (
            f"operator-presence must be flag-less; found options: {substantive}"
        )
