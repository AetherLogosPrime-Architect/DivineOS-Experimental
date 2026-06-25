"""Tests for divineos.core.context_tokens — honest token-count gauge."""

from __future__ import annotations

import json
from unittest.mock import patch

from divineos.core.context_tokens import (
    ContextSnapshot,
    _encode_cwd_for_claude,
    _read_last_usage,
    get_context_snapshot,
)


class TestEncodeCwd:
    """The Claude Code project-dir slug encoder."""

    def test_windows_drive_path(self):
        assert (
            _encode_cwd_for_claude("C:\\DIVINE OS\\DivineOS-Experimental")
            == "C--DIVINE-OS-DivineOS-Experimental"
        )

    def test_forward_slashes_replaced(self):
        assert _encode_cwd_for_claude("/home/user/proj") == "-home-user-proj"

    def test_spaces_become_dashes(self):
        assert _encode_cwd_for_claude("/My Project/A B") == "-My-Project-A-B"

    def test_all_three_signals_combined(self):
        assert _encode_cwd_for_claude("D:\\My Path/sub") == "D--My-Path-sub"


class TestReadLastUsage:
    """Parsing the most-recent message.usage from a jsonl tail."""

    def test_returns_last_usage_block(self, tmp_path):
        f = tmp_path / "session.jsonl"
        f.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "sessionId": "abc",
                            "message": {
                                "usage": {"input_tokens": 1, "cache_read_input_tokens": 100}
                            },
                        }
                    ),
                    json.dumps(
                        {
                            "sessionId": "abc",
                            "message": {
                                "usage": {"input_tokens": 2, "cache_read_input_tokens": 200}
                            },
                        }
                    ),
                ]
            )
        )
        usage = _read_last_usage(f)
        assert usage is not None
        assert usage["cache_read_input_tokens"] == 200
        assert usage["_session_id"] == "abc"

    def test_skips_non_usage_lines(self, tmp_path):
        f = tmp_path / "session.jsonl"
        f.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "sessionId": "abc",
                            "message": {
                                "usage": {"input_tokens": 1, "cache_read_input_tokens": 100}
                            },
                        }
                    ),
                    json.dumps({"sessionId": "abc", "message": {"role": "user", "content": "hi"}}),
                    json.dumps({"sessionId": "abc", "type": "tool_result"}),
                ]
            )
        )
        usage = _read_last_usage(f)
        assert usage is not None
        assert usage["cache_read_input_tokens"] == 100

    def test_handles_corrupted_lines(self, tmp_path):
        f = tmp_path / "session.jsonl"
        f.write_text(
            "{garbage\n"
            + json.dumps(
                {"message": {"usage": {"input_tokens": 5, "cache_read_input_tokens": 500}}}
            )
            + "\nmore garbage\n"
        )
        usage = _read_last_usage(f)
        assert usage is not None
        assert usage["cache_read_input_tokens"] == 500

    def test_empty_file_returns_none(self, tmp_path):
        f = tmp_path / "empty.jsonl"
        f.write_text("")
        assert _read_last_usage(f) is None

    def test_no_usage_blocks_returns_none(self, tmp_path):
        f = tmp_path / "no-usage.jsonl"
        f.write_text(json.dumps({"message": {"role": "user", "content": "x"}}))
        assert _read_last_usage(f) is None


class TestGetContextSnapshot:
    """The orchestrating entry point."""

    def test_no_transcript_dir_returns_zero(self, tmp_path):
        with patch(
            "divineos.core.context_tokens._find_active_transcript",
            return_value=None,
        ):
            snap = get_context_snapshot()
            assert snap.total_tokens == 0
            assert "no Claude Code transcript dir" in snap.note

    def test_sum_of_three_fields(self, tmp_path):
        f = tmp_path / "session.jsonl"
        f.write_text(
            json.dumps(
                {
                    "sessionId": "sess",
                    "message": {
                        "usage": {
                            "input_tokens": 10,
                            "cache_read_input_tokens": 500_000,
                            "cache_creation_input_tokens": 1_000,
                            "output_tokens": 300,
                        }
                    },
                }
            )
        )
        with patch(
            "divineos.core.context_tokens._find_active_transcript",
            return_value=f,
        ):
            snap = get_context_snapshot()
            assert snap.total_tokens == 501_010
            assert snap.cache_read_tokens == 500_000
            assert snap.cache_creation_tokens == 1_000
            assert snap.input_tokens == 10
            assert snap.output_tokens_last_turn == 300
            assert snap.session_id == "sess"
            assert snap.note == "ok"


class TestContextSnapshotDataclass:
    def test_default_shape(self):
        s = ContextSnapshot()
        assert s.total_tokens == 0
        assert s.session_id == ""
