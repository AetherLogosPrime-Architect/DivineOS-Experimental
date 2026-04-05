"""Tests for session quality trending."""

import os

from divineos.analysis.quality_trends import (
    SessionTrend,
    _extract_count,
    format_trend_summary,
    get_session_trend,
)
from divineos.core.knowledge import init_knowledge_table, store_knowledge
from divineos.core.ledger import init_db


class TestExtractCount:
    def test_extracts_corrections(self):
        content = "I was corrected 3 times and encouraged 1 time."
        assert _extract_count(content, "corrected") == 3

    def test_extracts_encouragements(self):
        content = "I was corrected 1 time and encouraged 5 times."
        assert _extract_count(content, "encouraged") == 5

    def test_zero_when_not_found(self):
        assert _extract_count("no counts here", "corrected") == 0


class TestFormatTrendSummary:
    def test_improving(self):
        trend = SessionTrend(
            direction="improving",
            sessions_analyzed=5,
            avg_corrections=1.2,
            avg_encouragements=3.0,
            detail="test",
        )
        text = format_trend_summary(trend)
        assert "[+]" in text
        assert "improving" in text

    def test_declining(self):
        trend = SessionTrend(
            direction="declining",
            sessions_analyzed=3,
            avg_corrections=4.0,
            avg_encouragements=0.5,
            detail="test",
        )
        text = format_trend_summary(trend)
        assert "[!]" in text
        assert "declining" in text

    def test_stable(self):
        trend = SessionTrend(
            direction="stable",
            sessions_analyzed=1,
            avg_corrections=1.0,
            avg_encouragements=1.0,
            detail="test",
        )
        text = format_trend_summary(trend)
        assert "[~]" in text


class TestGetSessionTrend:
    def test_no_episodes(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            trend = get_session_trend()
            assert trend.direction == "stable"
            assert trend.sessions_analyzed == 0
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_single_episode(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            store_knowledge(
                knowledge_type="EPISODE",
                content="I had 10 exchanges, made 50 tool calls. I was corrected 2 times and encouraged 3 times. 1 preferences noted, 0 context overflows (session abc123456789)",
                confidence=1.0,
            )

            trend = get_session_trend()
            assert trend.direction == "stable"
            assert trend.sessions_analyzed == 1
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_improving_trend(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            # Older sessions: many corrections
            for i in range(3):
                store_knowledge(
                    knowledge_type="EPISODE",
                    content=f"I had 10 exchanges, made 50 tool calls. I was corrected 5 times and encouraged 0 times. 0 preferences noted, 0 context overflows (session old{i}aaaaaa)",
                    confidence=1.0,
                )

            # Newer sessions: fewer corrections
            for i in range(3):
                store_knowledge(
                    knowledge_type="EPISODE",
                    content=f"I had 10 exchanges, made 50 tool calls. I was corrected 0 times and encouraged 3 times. 0 preferences noted, 0 context overflows (session new{i}aaaaaa)",
                    confidence=1.0,
                )

            trend = get_session_trend(n=6)
            assert trend.direction == "improving"
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_declining_trend(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            # Older sessions: few corrections
            for i in range(3):
                store_knowledge(
                    knowledge_type="EPISODE",
                    content=f"I had 10 exchanges, made 50 tool calls. I was corrected 0 times and encouraged 3 times. 0 preferences noted, 0 context overflows (session old{i}aaaaaa)",
                    confidence=1.0,
                )

            # Newer sessions: many corrections
            for i in range(3):
                store_knowledge(
                    knowledge_type="EPISODE",
                    content=f"I had 10 exchanges, made 50 tool calls. I was corrected 5 times and encouraged 0 times. 0 preferences noted, 0 context overflows (session new{i}aaaaaa)",
                    confidence=1.0,
                )

            trend = get_session_trend(n=6)
            assert trend.direction == "declining"
        finally:
            os.environ.pop("DIVINEOS_DB", None)
