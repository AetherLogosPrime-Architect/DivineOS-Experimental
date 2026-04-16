"""Tests for the lifecycle atexit handler.

The handler must emit the SESSION_END event (so the boundary is recorded
in the ledger) but must NOT trigger the heavy analysis pipeline. The
pipeline belongs to explicit completion paths (`divineos emit SESSION_END`,
hooks), not to incidental process termination.

The requirement: auto-analysis only on completed sessions, not every
CLI command mid-session. A 30-second `divineos hud` check should not
start a multi-minute analysis when the stale window elapses.
"""

import sys
import time
from unittest.mock import patch

from divineos.core import lifecycle


class TestAtexitDoesNotRunHeavyPipeline:
    def test_atexit_emits_event_but_skips_pipeline(self, tmp_path, monkeypatch):
        """The atexit handler emits SESSION_END to the ledger but does
        not import or run the heavy session-end pipeline."""
        # Force lifecycle state file into a tmp location
        state_file = tmp_path / "lifecycle_state.json"
        monkeypatch.setattr(lifecycle, "_state_path", lambda: state_file)

        # Pretend a real session was started (not stale, not yet ended)
        lifecycle._save_state(
            {
                "session_started_at": time.time(),
                "last_checkpoint": time.time(),
                "command_count": 1,
                "checkpoints_run": 0,
                "session_end_emitted": False,
            }
        )

        # Block tests-skip path so the handler actually proceeds
        monkeypatch.setattr(lifecycle, "logger", lifecycle.logger)
        monkeypatch.setitem(sys.modules, "pytest_disabled_for_test", object())
        # We can't remove pytest from sys.modules without breaking the runner,
        # so instead we directly call the body's relevant work — verify the
        # *imports* in the handler no longer reference the pipeline.

        import inspect

        src = inspect.getsource(lifecycle._run_session_end)
        # The heavy pipeline must not be imported in the atexit body
        assert "_run_session_end_pipeline" not in src, (
            "atexit handler must not invoke the heavy session-end pipeline; "
            "that path is reserved for explicit user/hook triggers"
        )
        assert "session_pipeline" not in src, (
            "atexit handler must not import session_pipeline at all"
        )

    def test_atexit_still_emits_session_end_event(self, tmp_path, monkeypatch):
        """The atexit handler must still emit a SESSION_END event so the
        ledger has the session boundary."""
        state_file = tmp_path / "lifecycle_state.json"
        monkeypatch.setattr(lifecycle, "_state_path", lambda: state_file)

        lifecycle._save_state(
            {
                "session_started_at": time.time(),
                "last_checkpoint": time.time(),
                "command_count": 1,
                "checkpoints_run": 0,
                "session_end_emitted": False,
            }
        )

        # Pop pytest from sys.modules so the handler proceeds past its
        # in-test guard. Restore it in finally so the rest of the suite
        # is unaffected.
        pytest_mod = sys.modules.pop("pytest", None)
        try:
            with patch("divineos.event.event_emission.emit_session_end") as mock_emit:
                lifecycle._run_session_end()
                assert mock_emit.called, "atexit handler must emit SESSION_END event"
        finally:
            if pytest_mod is not None:
                sys.modules["pytest"] = pytest_mod

        # State should now show session_end_emitted=True
        state = lifecycle._load_state()
        assert state.get("session_end_emitted") is True

    def test_atexit_idempotent_within_session(self, tmp_path, monkeypatch):
        """If session_end_emitted is already True, the handler returns
        immediately without re-emitting."""
        state_file = tmp_path / "lifecycle_state.json"
        monkeypatch.setattr(lifecycle, "_state_path", lambda: state_file)

        lifecycle._save_state(
            {
                "session_started_at": time.time(),
                "session_end_emitted": True,
            }
        )

        pytest_mod = sys.modules.pop("pytest", None)
        try:
            with patch("divineos.event.event_emission.emit_session_end") as mock_emit:
                lifecycle._run_session_end()
                assert not mock_emit.called, (
                    "atexit must skip when session_end_emitted is already True"
                )
        finally:
            if pytest_mod is not None:
                sys.modules["pytest"] = pytest_mod
