"""Tests for context_meter — reads true context-window fullness from the
Claude Code transcript's per-turn token usage (governor step 2).
"""

import json

from divineos.core.context_meter import (
    COMPACTION_CEILING_TOKENS,
    ContextReading,
    format_reading,
    read_latest_context_tokens,
)


def _usage_line(input_tokens, cache_creation, cache_read, output_tokens):
    return json.dumps(
        {
            "type": "assistant",
            "message": {
                "usage": {
                    "input_tokens": input_tokens,
                    "cache_creation_input_tokens": cache_creation,
                    "cache_read_input_tokens": cache_read,
                    "output_tokens": output_tokens,
                }
            },
        }
    )


def _write_transcript(tmp_path, lines):
    f = tmp_path / "session.jsonl"
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f


class TestReadLatestContextTokens:
    def test_reads_latest_usage_block(self, tmp_path):
        # Two turns; the reading must reflect the LAST one (current fill).
        f = _write_transcript(
            tmp_path,
            [
                _usage_line(3, 100_000, 0, 200),
                '{"type":"user","message":{"content":"hi"}}',
                _usage_line(3, 50_000, 300_000, 500),
            ],
        )
        r = read_latest_context_tokens(f)
        assert r is not None
        # 3 + 50_000 + 300_000 = 350_003 (output_tokens 500 excluded)
        assert r.context_tokens == 350_003

    def test_excludes_output_tokens(self, tmp_path):
        f = _write_transcript(tmp_path, [_usage_line(10, 0, 0, 999_999)])
        r = read_latest_context_tokens(f)
        assert r is not None
        assert r.context_tokens == 10  # output_tokens must not count

    def test_over_threshold_flag(self, tmp_path):
        # 90% of a 1000-token ceiling, threshold 0.85 -> over.
        f = _write_transcript(tmp_path, [_usage_line(900, 0, 0, 0)])
        r = read_latest_context_tokens(f, ceiling=1000, fire_threshold=0.85)
        assert r is not None
        assert r.over_threshold is True
        assert abs(r.pct - 0.9) < 1e-9

    def test_under_threshold_flag(self, tmp_path):
        f = _write_transcript(tmp_path, [_usage_line(100, 0, 0, 0)])
        r = read_latest_context_tokens(f, ceiling=1000, fire_threshold=0.85)
        assert r is not None
        assert r.over_threshold is False

    def test_none_when_no_usage(self, tmp_path):
        f = _write_transcript(tmp_path, ['{"type":"user","message":{"content":"hi"}}'])
        assert read_latest_context_tokens(f) is None

    def test_none_when_file_missing(self, tmp_path):
        assert read_latest_context_tokens(tmp_path / "nope.jsonl") is None

    def test_skips_malformed_json_lines(self, tmp_path):
        f = _write_transcript(
            tmp_path,
            [
                "{not valid json at all",
                _usage_line(5, 5, 5, 1),
            ],
        )
        r = read_latest_context_tokens(f)
        assert r is not None
        assert r.context_tokens == 15

    def test_default_ceiling_is_compaction_ceiling(self, tmp_path):
        f = _write_transcript(tmp_path, [_usage_line(1, 0, 0, 0)])
        r = read_latest_context_tokens(f)
        assert r is not None
        assert r.ceiling == COMPACTION_CEILING_TOKENS


class TestFormatReading:
    def test_none_reads_as_no_signal(self):
        # A parse failure must read as "no signal", never as "0% / empty".
        msg = format_reading(None)
        assert "no signal" in msg
        assert "0%" not in msg

    def test_over_threshold_shows_flag(self):
        r = ContextReading(
            context_tokens=900, ceiling=1000, pct=0.9, over_threshold=True, source_line=3
        )
        assert "90%" in format_reading(r)
        assert "[!]" in format_reading(r)
