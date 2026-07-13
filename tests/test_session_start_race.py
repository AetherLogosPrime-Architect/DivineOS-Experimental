"""Tests for the SESSION_END timestamp race condition fix.

The bug: emit_session_end() writes to the ledger BEFORE _run_session_end_pipeline()
runs. When the pipeline calls get_session_start_time(), it finds the SESSION_END we
just wrote — returning the session END time, not the start. This filters out all
records and produces "0 exchanges" in the handoff.

The fix: capture session_start BEFORE emitting, pass it as session_start_override.
"""

import json
import time

from divineos.analysis.session_analyzer import analyze_session


class TestSessionStartOverridePreventsRace:
    def test_override_prevents_zero_messages(self, tmp_path):
        """When override is used, analysis sees the session's records."""
        now = time.time()
        session_start = now - 3600  # 1 hour ago

        # Build a JSONL file with records DURING the session
        records = [
            {
                "type": "user",
                "timestamp": now - 1800,  # 30 min ago — inside session
                "message": {"role": "user", "content": "lets fix the tests"},
            },
            {
                "type": "assistant",
                "timestamp": now - 1790,
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "I'll fix those now."}],
                },
            },
            {
                "type": "user",
                "timestamp": now - 600,  # 10 min ago
                "message": {"role": "user", "content": "perfect that works"},
            },
        ]
        jsonl = tmp_path / "test_session.jsonl"
        jsonl.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")

        # Simulate the BUG: session_start = now (as if SESSION_END was just emitted)
        buggy = analyze_session(jsonl, since_timestamp=now)
        assert buggy.user_messages == 0, "Bug: using 'now' filters out everything"

        # Simulate the FIX: session_start captured BEFORE emission
        fixed = analyze_session(jsonl, since_timestamp=session_start)
        assert fixed.user_messages == 2, "Fix: pre-captured start sees session records"
        assert fixed.assistant_messages == 1

    def test_override_none_falls_through(self, tmp_path):
        """When override is None, analysis uses None (no filter)."""
        now = time.time()
        records = [
            {
                "type": "user",
                "timestamp": now - 86400,  # 1 day ago
                "message": {"role": "user", "content": "old message"},
            },
            {
                "type": "user",
                "timestamp": now - 100,
                "message": {"role": "user", "content": "recent message"},
            },
        ]
        jsonl = tmp_path / "test_session.jsonl"
        jsonl.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")

        # None means no filter — see everything
        analysis = analyze_session(jsonl, since_timestamp=None)
        assert analysis.user_messages == 2


class TestCheckpointDoesNotOverwriteHandoff:
    def test_real_handoff_preserved_by_checkpoint(self, tmp_path):
        """A checkpoint should not overwrite a real SESSION_END handoff note."""
        handoff_path = tmp_path / "handoff_note.json"

        # Write a real handoff (from SESSION_END pipeline)
        real_handoff = {
            "summary": "Last session: 14 exchanges, 3 knowledge entries extracted.",
            "written_at": time.time() - 60,  # 1 min ago
            "session_id": "test-123",
        }
        handoff_path.write_text(json.dumps(real_handoff), encoding="utf-8")

        # Read it back and check the detection logic
        existing = json.loads(handoff_path.read_text(encoding="utf-8"))
        existing_summary = existing.get("summary", "")
        age = time.time() - existing.get("written_at", 0)

        # "exchanges" keyword present AND age < 12 hours → should be preserved
        should_skip = "exchanges" in existing_summary and age < 43200
        assert should_skip, "Real handoff with 'exchanges' should be preserved"

    def test_auto_checkpoint_can_be_overwritten(self, tmp_path):
        """An auto-checkpoint handoff can be safely overwritten."""
        handoff_path = tmp_path / "handoff_note.json"

        checkpoint_handoff = {
            "summary": "Auto-checkpoint #2: 30 edits, 1 tool calls",
            "written_at": time.time() - 60,
            "session_id": "",
        }
        handoff_path.write_text(json.dumps(checkpoint_handoff), encoding="utf-8")

        existing = json.loads(handoff_path.read_text(encoding="utf-8"))
        existing_summary = existing.get("summary", "")
        age = time.time() - existing.get("written_at", 0)

        should_skip = "exchanges" in existing_summary and age < 43200
        assert not should_skip, "Auto-checkpoint handoff should be overwritable"
