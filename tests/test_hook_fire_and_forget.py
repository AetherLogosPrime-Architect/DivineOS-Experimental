"""Tests for PostToolUse fire-and-forget of divineos extract/checkpoint.

Before: the PostToolUse hook called ``subprocess.run(["divineos", "extract"])``
synchronously, blocking the hook for 30–60s when the write-threshold was
crossed. This produced the dominant source of felt latency in long sessions.

After: the same calls use ``subprocess.Popen`` without ``.wait()``, returning
in ~100ms. The extract marker is written BEFORE firing so idempotency holds
even if the background subprocess never completes.

Falsifiability:
  - ``_fire_and_forget`` invokes Popen, not run.
  - ``_auto_run_extract`` writes the marker before firing.
  - ``_auto_run_extract`` does not block on completion.
  - ``_run_checkpoint`` does not block on completion.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from divineos.hooks import post_tool_use_checkpoint


class TestFireAndForget:
    def test_uses_popen_not_run(self) -> None:
        """Regression guard: the helper must use Popen, not run."""
        with patch("divineos.hooks.post_tool_use_checkpoint.subprocess") as mock_sp:
            mock_sp.Popen = MagicMock()
            mock_sp.DEVNULL = -3
            post_tool_use_checkpoint._fire_and_forget(["divineos", "extract"])
            assert mock_sp.Popen.called, "fire_and_forget must call Popen"
            assert not getattr(mock_sp, "run", MagicMock()).called, (
                "fire_and_forget must NOT call subprocess.run (would block)"
            )

    def test_passes_command_through(self) -> None:
        with patch("divineos.hooks.post_tool_use_checkpoint.subprocess") as mock_sp:
            mock_sp.Popen = MagicMock()
            mock_sp.DEVNULL = -3
            post_tool_use_checkpoint._fire_and_forget(["divineos", "checkpoint"])
            args, _ = mock_sp.Popen.call_args
            assert args[0] == ["divineos", "checkpoint"]

    def test_passes_env_through(self) -> None:
        with patch("divineos.hooks.post_tool_use_checkpoint.subprocess") as mock_sp:
            mock_sp.Popen = MagicMock()
            mock_sp.DEVNULL = -3
            custom_env = {"DIVINEOS_EXTRACT_TRIGGER": "hook"}
            post_tool_use_checkpoint._fire_and_forget(["divineos", "extract"], env=custom_env)
            _, kwargs = mock_sp.Popen.call_args
            assert kwargs.get("env") == custom_env

    def test_swallows_subprocess_errors(self) -> None:
        """OSError from spawn should not propagate (fail-open)."""
        import subprocess

        with patch.object(
            post_tool_use_checkpoint.subprocess,
            "Popen",
            side_effect=OSError("spawn failed"),
        ):
            # Should not raise
            post_tool_use_checkpoint._fire_and_forget(["divineos", "checkpoint"])
        _ = subprocess  # silence unused


class TestAutoRunExtractAsync:
    def test_writes_marker_before_firing(self, tmp_path: Path) -> None:
        """Marker must be set BEFORE the subprocess is spawned, so repeated
        hook firings don't all spawn extract. Idempotency-before-latency."""
        marker_path = tmp_path / "auto_session_end_emitted"
        call_order: list[str] = []

        def fake_write_marker(**_kwargs) -> None:
            call_order.append("marker")

        def fake_popen(*_args, **_kwargs) -> MagicMock:
            call_order.append("popen")
            return MagicMock()

        with (
            patch.object(post_tool_use_checkpoint, "_auto_emitted_path", return_value=marker_path),
            patch(
                "divineos.core.extract_marker.write_marker",
                side_effect=fake_write_marker,
            ),
            patch.object(post_tool_use_checkpoint.subprocess, "Popen", side_effect=fake_popen),
        ):
            post_tool_use_checkpoint._auto_run_extract()

        assert "marker" in call_order and "popen" in call_order
        assert call_order.index("marker") < call_order.index("popen"), (
            "marker must be written BEFORE spawning subprocess"
        )

    def test_marker_present_skips_fire(self, tmp_path: Path) -> None:
        """Existing marker → no fire (idempotency)."""
        marker_path = tmp_path / "auto_session_end_emitted"
        marker_path.write_text("1", encoding="utf-8")
        with (
            patch.object(post_tool_use_checkpoint, "_auto_emitted_path", return_value=marker_path),
            patch.object(post_tool_use_checkpoint.subprocess, "Popen") as mock_popen,
        ):
            post_tool_use_checkpoint._auto_run_extract()
        assert not mock_popen.called, "marker present should short-circuit"


class TestRunCheckpointAsync:
    def test_uses_fire_and_forget(self) -> None:
        with patch.object(post_tool_use_checkpoint, "_fire_and_forget") as mock_faf:
            post_tool_use_checkpoint._run_checkpoint()
            assert mock_faf.called
            args, _ = mock_faf.call_args
            assert args[0] == ["divineos", "checkpoint"]
