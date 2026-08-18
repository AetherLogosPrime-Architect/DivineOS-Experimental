"""Tests for divineos.core.context_tokens — honest token-count gauge."""

from __future__ import annotations

import json
import os
from unittest.mock import patch

from divineos.core.context_tokens import (
    ContextSnapshot,
    _encode_cwd_for_claude,
    _read_last_usage,
    find_active_transcript,
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
            "divineos.core.context_tokens.find_active_transcript",
            return_value=(None, False),
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
            "divineos.core.context_tokens.find_active_transcript",
            return_value=(f, True),
        ):
            snap = get_context_snapshot()
            assert snap.total_tokens == 501_010
            assert snap.cache_read_tokens == 500_000
            assert snap.cache_creation_tokens == 1_000
            assert snap.input_tokens == 10
            assert snap.output_tokens_last_turn == 300
            assert snap.session_id == "sess"
            assert snap.pinned is True
            assert snap.note == "ok"


def _usage_line(session_id: str, cache_read: int, timestamp: str = "") -> str:
    """One transcript row carrying a usage block, as Claude Code writes it."""
    return json.dumps(
        {
            "sessionId": session_id,
            "timestamp": timestamp,
            "message": {
                "usage": {
                    "input_tokens": 2,
                    "cache_read_input_tokens": cache_read,
                    "cache_creation_input_tokens": 0,
                }
            },
        }
    )


class TestWhoseNumberIsIt:
    """Regression for Andrew correction #452 (2026-08-18).

    The gauge answered "how full am I?" with another session's number.
    It mapped the shell's cwd to a project folder, took the newest file
    by mtime, and reported 961,358 tokens off a transcript abandoned
    sixty-nine days earlier while the live session held 439,200. The
    count was real; it belonged to a stranger.

    These tests build that exact shape: two project folders, an
    abandoned transcript with a huge count and the freshest mtime, and
    the asking session's own small one.
    """

    def _two_sessions(self, tmp_path):
        projects = tmp_path / "projects"
        mine = projects / "C--proj-worktree"
        theirs = projects / "C--proj"
        mine.mkdir(parents=True)
        theirs.mkdir(parents=True)

        live = mine / "live-session.jsonl"
        live.write_text(_usage_line("live-session", 439_198, "2026-08-18T16:03:38Z"))

        abandoned = theirs / "abandoned-session.jsonl"
        abandoned.write_text(_usage_line("abandoned-session", 959_220, "2026-06-10T19:04:01Z"))
        # The abandoned file wins any mtime race — that is the whole trap.
        os.utime(live, (1_000_000, 1_000_000))
        os.utime(abandoned, (2_000_000, 2_000_000))
        return projects, live, abandoned

    def test_session_id_beats_freshest_mtime(self, tmp_path):
        projects, live, abandoned = self._two_sessions(tmp_path)
        path, pinned = find_active_transcript(
            cwd="C:/proj/worktree",
            projects_dir=projects,
            session_id="live-session",
        )
        assert path == live, "resolved another session's transcript"
        assert pinned is True

    def test_session_id_wins_from_any_working_directory(self, tmp_path):
        """The failure needed only a `cd` — so cwd must not decide."""
        projects, live, _ = self._two_sessions(tmp_path)
        path, pinned = find_active_transcript(
            cwd="C:/proj",  # the folder holding the abandoned transcript
            projects_dir=projects,
            session_id="live-session",
        )
        assert path == live
        assert pinned is True

    def test_unknown_session_falls_back_but_says_so(self, tmp_path):
        projects, _, abandoned = self._two_sessions(tmp_path)
        path, pinned = find_active_transcript(
            cwd="C:/proj",
            projects_dir=projects,
            session_id="",
        )
        assert path == abandoned
        assert pinned is False, "a guess must not be labelled a measurement"

    def test_snapshot_marks_unpinned_reading(self, tmp_path):
        _, _, abandoned = self._two_sessions(tmp_path)
        with patch(
            "divineos.core.context_tokens.find_active_transcript",
            return_value=(abandoned, False),
        ):
            snap = get_context_snapshot()
        assert snap.total_tokens == 959_222
        assert snap.pinned is False
        assert "UNPINNED" in snap.note
        assert "2026-06-10T19:04:01Z" in snap.note, "the note must date the reading"

    def test_missing_transcript_for_known_session_falls_back_unpinned(self, tmp_path):
        """First turn of a session: env var set, file not written yet."""
        projects, _, abandoned = self._two_sessions(tmp_path)
        path, pinned = find_active_transcript(
            cwd="C:/proj",
            projects_dir=projects,
            session_id="session-with-no-file-yet",
        )
        assert path == abandoned
        assert pinned is False


class TestAutoCycleRefusesUnpinned:
    """The ritual is the one thing token count may decide — #452."""

    def test_unpinned_snapshot_reads_as_zero(self):
        from divineos.cli.auto_cycle_commands import _guess_context_pct

        loud = ContextSnapshot(total_tokens=961_358, pinned=False, note="UNPINNED — ...")
        with patch("divineos.core.context_tokens.get_context_snapshot", return_value=loud):
            assert _guess_context_pct() == 0.0

    def test_pinned_snapshot_is_spent(self):
        from divineos.cli.auto_cycle_commands import _guess_context_pct

        real = ContextSnapshot(total_tokens=920_000, pinned=True, note="ok")
        with patch("divineos.core.context_tokens.get_context_snapshot", return_value=real):
            assert _guess_context_pct() == 0.92


class TestContextSnapshotDataclass:
    def test_default_shape(self):
        s = ContextSnapshot()
        assert s.total_tokens == 0
        assert s.session_id == ""
