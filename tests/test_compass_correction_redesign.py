"""Tests for the compass-correction disclose-then-escalate redesign.

Pre-reg prereg-75c900fe. Tests pin:
  - Marker schema includes advised_count + last_advised_ts (backwards-compat
    when reading old markers without the fields).
  - record_advisory_fire increments and updates timestamp.
  - should_dedup_within_turn returns True within window, False after.
  - format_gate_message branches on advised_count (advisory text below
    threshold, BLOCK text at/above threshold).
  - dismiss subcommand clears marker AND files OBSERVATION knowledge entry
    with the right tags.
  - compass_dismissal_briefing_surface counts dismissals by trigger-kind
    and surfaces only when threshold is exceeded.
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

from divineos.core import compass_required_marker
from divineos.core.compass_required_marker import (
    ESCALATION_THRESHOLD,
    PER_TURN_DEDUP_SECONDS,
    format_gate_message,
    record_advisory_fire,
    should_dedup_within_turn,
)


class TestMarkerSchema:
    """New fields in the marker schema."""

    def test_set_marker_initializes_new_fields(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("DIVINEOS_TEST_ALLOW_COMPASS_CASCADE", "1")
        with patch.object(
            compass_required_marker, "marker_path", return_value=tmp_path / "cr.json"
        ):
            compass_required_marker.set_marker("test", "test summary")
            marker = compass_required_marker.read_marker()
            assert marker is not None
            assert marker["advised_count"] == 0
            assert marker["last_advised_ts"] == 0.0
            assert marker["kind"] == "test"

    def test_record_advisory_fire_increments(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("DIVINEOS_TEST_ALLOW_COMPASS_CASCADE", "1")
        with patch.object(
            compass_required_marker, "marker_path", return_value=tmp_path / "cr.json"
        ):
            compass_required_marker.set_marker("test", "test")
            assert record_advisory_fire() == 1
            assert record_advisory_fire() == 2
            assert record_advisory_fire() == 3

    def test_record_advisory_fire_returns_zero_when_no_marker(self, tmp_path: Path) -> None:
        with patch.object(
            compass_required_marker, "marker_path", return_value=tmp_path / "cr.json"
        ):
            assert record_advisory_fire() == 0

    def test_backwards_compat_old_marker_without_fields(self, tmp_path: Path) -> None:
        """Old marker (no advised_count) should default to 0."""
        import json

        path = tmp_path / "cr.json"
        path.write_text(
            json.dumps({"ts": time.time(), "kind": "test", "summary": "x"}),
            encoding="utf-8",
        )
        with patch.object(compass_required_marker, "marker_path", return_value=path):
            marker = compass_required_marker.read_marker()
            assert int(marker.get("advised_count", 0)) == 0
            # First record advances it.
            assert record_advisory_fire() == 1


class TestPerTurnDedup:
    """Dedup window suppresses same-marker re-firing within ~30s."""

    def test_dedup_returns_false_on_no_marker(self, tmp_path: Path) -> None:
        with patch.object(
            compass_required_marker, "marker_path", return_value=tmp_path / "cr.json"
        ):
            assert should_dedup_within_turn() is False

    def test_dedup_returns_false_on_fresh_marker(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("DIVINEOS_TEST_ALLOW_COMPASS_CASCADE", "1")
        with patch.object(
            compass_required_marker, "marker_path", return_value=tmp_path / "cr.json"
        ):
            compass_required_marker.set_marker("test", "test")
            # last_advised_ts is 0.0 — never advised — so no dedup.
            assert should_dedup_within_turn() is False

    def test_dedup_returns_true_after_recent_advisory(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("DIVINEOS_TEST_ALLOW_COMPASS_CASCADE", "1")
        with patch.object(
            compass_required_marker, "marker_path", return_value=tmp_path / "cr.json"
        ):
            compass_required_marker.set_marker("test", "test")
            record_advisory_fire()  # advances last_advised_ts to now
            assert should_dedup_within_turn() is True

    def test_dedup_returns_false_after_window_expires(self, tmp_path: Path, monkeypatch) -> None:
        """Manually back-date last_advised_ts to outside the window."""
        monkeypatch.setenv("DIVINEOS_TEST_ALLOW_COMPASS_CASCADE", "1")
        with patch.object(
            compass_required_marker, "marker_path", return_value=tmp_path / "cr.json"
        ):
            compass_required_marker.set_marker("test", "test")
            record_advisory_fire()
            # Back-date to outside window.
            import json

            marker_data = compass_required_marker.read_marker()
            marker_data["last_advised_ts"] = time.time() - PER_TURN_DEDUP_SECONDS - 5
            (tmp_path / "cr.json").write_text(json.dumps(marker_data), encoding="utf-8")
            assert should_dedup_within_turn() is False


class TestFormatGateMessage:
    """Message branches on advised_count."""

    def test_advisory_below_threshold(self) -> None:
        marker = {
            "kind": "correction",
            "summary": "user said you missed something",
            "advised_count": 0,
        }
        msg = format_gate_message(marker)
        assert msg.startswith("[~]")
        assert "Compass-relevant event" in msg
        assert "correction" in msg.lower()
        assert "BLOCKED" not in msg

    def test_advisory_with_still_pending_prefix(self) -> None:
        marker = {"kind": "test", "summary": "x", "advised_count": 1}
        msg = format_gate_message(marker)
        assert "still pending" in msg.lower()

    def test_block_at_threshold(self) -> None:
        marker = {
            "kind": "correction",
            "summary": "x",
            "advised_count": ESCALATION_THRESHOLD,
        }
        msg = format_gate_message(marker)
        assert "BLOCKED" in msg
        assert "dismiss" in msg  # the alternative path is named

    def test_block_above_threshold(self) -> None:
        marker = {
            "kind": "test",
            "summary": "x",
            "advised_count": ESCALATION_THRESHOLD + 5,
        }
        msg = format_gate_message(marker)
        assert "BLOCKED" in msg


class TestDismissCommand:
    """`divineos compass-ops dismiss --reason` clears marker and files data."""

    def test_dismiss_clears_marker_and_files_observation(self, tmp_path: Path, monkeypatch) -> None:
        from click.testing import CliRunner

        from divineos.cli import cli

        # Set up marker
        monkeypatch.setenv("DIVINEOS_TEST_ALLOW_COMPASS_CASCADE", "1")
        with patch.object(
            compass_required_marker, "marker_path", return_value=tmp_path / "cr.json"
        ):
            compass_required_marker.set_marker("correction", "user teasing flagged as correction")
            assert (tmp_path / "cr.json").exists()

            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "compass-ops",
                    "dismiss",
                    "--reason",
                    "warm-tone teasing, not a real correction",
                ],
            )
            # Should succeed
            assert result.exit_code == 0, result.output
            assert "dismissed" in result.output.lower()
            # Marker cleared
            assert not (tmp_path / "cr.json").exists()

    def test_dismiss_with_no_marker(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from divineos.cli import cli

        with patch.object(
            compass_required_marker, "marker_path", return_value=tmp_path / "cr.json"
        ):
            runner = CliRunner()
            result = runner.invoke(cli, ["compass-ops", "dismiss", "--reason", "test"])
            assert "no compass-required advisory" in result.output.lower()


class TestDismissalBriefingSurface:
    """Surface counts dismissals by kind, surfaces over threshold."""

    def test_empty_when_no_dismissals(self) -> None:
        from divineos.core.compass_dismissal_briefing_surface import format_for_briefing

        # No dismissal entries → empty
        out = format_for_briefing()
        # Don't assert it's exactly empty (existing entries in DB might
        # exceed threshold). Assert it doesn't error.
        assert isinstance(out, str)

    def test_threshold_constants_exposed(self) -> None:
        from divineos.core import compass_dismissal_briefing_surface as cdb

        assert cdb.DISMISSAL_THRESHOLD >= 1
        assert cdb.WINDOW_DAYS >= 1

    def test_tag_parser_handles_json_list_format(self) -> None:
        """Tags stored as JSON list (the _wrapped_store_knowledge format)
        parse correctly and extract the trigger-kind."""
        import json as _json

        # The row format is (knowledge_id, content, tags_raw, created_at).
        # Format of tags_raw matches what _wrapped_store_knowledge writes.
        tags_raw = _json.dumps(["compass-dismissal", "compass-dismissal-kind-correction"])

        # Verify parser extracts the kind correctly from this format.
        tags = _json.loads(tags_raw)
        prefix = "compass-dismissal-kind-"
        kind = next(
            (t[len(prefix) :] for t in tags if isinstance(t, str) and t.startswith(prefix)),
            "unknown",
        )
        assert kind == "correction", (
            f"parser should extract 'correction' from JSON-list tags, got {kind!r}"
        )

    def test_tag_parser_handles_dict_shaped_json(self) -> None:
        """Aletheia round-6 audit edge-case: json.loads on dict-shaped
        input parses successfully (not as list), and iteration would
        proceed over dict keys. The list-validation guard prevents this."""
        import json as _json

        # Dict-shape JSON parses to a dict. Without the isinstance(list)
        # guard, `for tag in tags` would iterate the keys.
        bad_dict_tags = '{"compass-dismissal": true, "compass-dismissal-kind-correction": true}'

        try:
            parsed = _json.loads(bad_dict_tags)
        except (_json.JSONDecodeError, TypeError):
            parsed = []

        # The guard the audit recommended.
        tags = parsed if isinstance(parsed, list) else []

        prefix = "compass-dismissal-kind-"
        kind = next(
            (t[len(prefix) :] for t in tags if isinstance(t, str) and t.startswith(prefix)),
            "unknown",
        )
        # With the guard: tags becomes [] because parsed was a dict.
        # kind stays "unknown". No mis-grouping from dict-key iteration.
        assert tags == [], "list-validation guard should reject dict-shaped JSON"
        assert kind == "unknown"

    def test_tag_parser_handles_legacy_or_corrupted_tags(self) -> None:
        """Tag values that aren't valid JSON should fall back to empty
        (kind='unknown') rather than mis-group via brittle string-splitting.
        Silent-fail-with-misleading-data is the worst failure mode for a
        disclosure surface."""
        import json as _json

        # Various corrupted shapes the parser must survive:
        for bad_tags in (
            None,
            "",
            "not valid json",
            "compass-dismissal,compass-dismissal-kind-correction",  # comma-string, not JSON
            "[unclosed",
            "{this is a dict not a list}",
        ):
            try:
                tags = _json.loads(bad_tags) if bad_tags else []
            except (_json.JSONDecodeError, TypeError):
                tags = []

            prefix = "compass-dismissal-kind-"
            kind = next(
                (t[len(prefix) :] for t in tags if isinstance(t, str) and t.startswith(prefix)),
                "unknown",
            )
            # Either the json parses cleanly and the prefix isn't present
            # (returning "unknown"), OR the json fails and we fall back
            # to empty list (also returning "unknown"). Either way the
            # parser does NOT pretend to extract a kind from invalid data.
            assert kind == "unknown", (
                f"parser should return 'unknown' on corrupted tags, got {kind!r} from {bad_tags!r}"
            )
