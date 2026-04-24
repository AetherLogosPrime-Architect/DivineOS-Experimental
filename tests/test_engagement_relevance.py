"""Tests for the engagement-relevance check (core/engagement_relevance.py).

Falsifiability:
  - Token extraction pulls identifiers from free text, filters stopwords.
  - Path tokens: directory + stem + underscore-split parts all contribute.
  - is_substantive returns False on empty, True when overlap exists.
  - mark_engaged with substantive query fully clears; shell query halves.

All pure-function tests avoid the ledger; the ledger-backed extractor
is exercised separately via a fresh DB fixture.
"""

from __future__ import annotations

import json
import os
import time

import pytest

from divineos.core.engagement_relevance import (
    extract_recent_keywords,
    is_substantive,
    _path_tokens,
    _tokenize,
)


class TestTokenize:
    def test_returns_lowercased_identifiers(self) -> None:
        assert _tokenize("Compass Rudder") == {"compass", "rudder"}

    def test_filters_stopwords(self) -> None:
        assert _tokenize("the and what but for") == set()

    def test_drops_too_short(self) -> None:
        # Tokens must be at least 2 chars (pattern requires >= 2).
        assert "a" not in _tokenize("a quick brown fox")
        assert "i" not in _tokenize("i see it")

    def test_empty_returns_empty(self) -> None:
        assert _tokenize("") == set()
        assert _tokenize(None) == set()  # type: ignore[arg-type]

    def test_identifier_chars_only(self) -> None:
        # Punctuation is not part of tokens.
        tokens = _tokenize("compass-rudder.py!")
        assert "compass" in tokens
        assert "rudder" in tokens
        assert "py" in tokens


class TestPathTokens:
    def test_path_contributes_all_parts(self) -> None:
        toks = _path_tokens("src/divineos/core/compass_rudder.py")
        assert "divineos" in toks
        assert "core" in toks
        assert "compass_rudder" in toks
        assert "compass" in toks
        assert "rudder" in toks

    def test_handles_windows_separators(self) -> None:
        toks = _path_tokens("src\\divineos\\x.py")
        assert "divineos" in toks
        assert "py" in toks

    def test_empty_path_returns_empty(self) -> None:
        assert _path_tokens("") == set()


class TestIsSubstantive:
    def test_empty_query_is_shell(self) -> None:
        assert is_substantive("", keywords={"anything"}) is False

    def test_overlap_is_substantive(self) -> None:
        assert is_substantive("about rudder gate", keywords={"rudder"}) is True

    def test_no_overlap_is_shell(self) -> None:
        assert is_substantive("random words", keywords={"compass", "rudder"}) is False

    def test_empty_keywords_is_substantive_lenient(self) -> None:
        # When the ledger is unavailable (keywords == empty), we don't
        # penalize — the fail-open policy.
        assert is_substantive("anything at all", keywords=set()) is True

    def test_only_stopwords_is_shell(self) -> None:
        # A command full of stopwords has no tokens to match.
        assert is_substantive("the and but for", keywords={"rudder"}) is False

    def test_case_insensitive(self) -> None:
        assert is_substantive("RUDDER GATE", keywords={"rudder"}) is True


class TestExtractRecentKeywords:
    """Ledger-backed extraction. Uses a tmp DB per test."""

    @pytest.fixture(autouse=True)
    def _fresh_db(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        from divineos.core.ledger import init_db

        init_db()
        try:
            yield
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def _log_tool_call(self, file_path: str) -> None:
        from divineos.core.ledger import get_connection

        conn = get_connection()
        payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": file_path}})
        conn.execute(
            "INSERT INTO system_events "
            "(event_id, timestamp, event_type, actor, payload, content_hash) "
            "VALUES (?, ?, 'TOOL_CALL', 'assistant', ?, 'h')",
            ("evt-" + str(time.time()), time.time(), payload),
        )
        conn.commit()
        conn.close()

    def test_empty_ledger_returns_empty(self) -> None:
        assert extract_recent_keywords() == set()

    def test_recent_tool_call_contributes_path_tokens(self) -> None:
        self._log_tool_call("src/divineos/core/compass_rudder.py")
        keywords = extract_recent_keywords()
        assert "compass_rudder" in keywords
        assert "rudder" in keywords
        assert "divineos" in keywords

    def test_stale_events_outside_window_are_ignored(self) -> None:
        # Log one event and then query with a window in the past.
        self._log_tool_call("src/old_stale.py")
        # A window from 2 hours in the future back 10 minutes should
        # exclude the "now" event.
        future = time.time() + 7200
        keywords = extract_recent_keywords(now=future)
        assert "old_stale" not in keywords


class TestMarkEngagedWithRelevance:
    """mark_engaged should treat shells differently from substantive queries."""

    @pytest.fixture(autouse=True)
    def _fresh_env(self, tmp_path, monkeypatch):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        # Redirect the HUD dir so the .session_engaged marker is isolated.
        hud_dir = tmp_path / "hud"
        hud_dir.mkdir()
        monkeypatch.setattr("divineos.core.hud_handoff._get_hud_dir", lambda: hud_dir)
        monkeypatch.setattr("divineos.core.hud_handoff._ensure_hud_dir", lambda: hud_dir)
        from divineos.core.ledger import init_db

        init_db()
        try:
            yield hud_dir
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def _seed_work(self) -> None:
        """Log a TOOL_CALL on compass_rudder.py so 'rudder' is a recent keyword."""
        from divineos.core.ledger import get_connection

        conn = get_connection()
        payload = json.dumps(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "src/divineos/core/compass_rudder.py"},
            }
        )
        conn.execute(
            "INSERT INTO system_events "
            "(event_id, timestamp, event_type, actor, payload, content_hash) "
            "VALUES (?, ?, 'TOOL_CALL', 'assistant', ?, 'h')",
            ("evt-seed", time.time(), payload),
        )
        conn.commit()
        conn.close()

    def _read_marker(self, hud_dir) -> dict:
        path = hud_dir / ".session_engaged"
        return json.loads(path.read_text(encoding="utf-8"))

    def _set_counter(self, hud_dir, code: int, deep: int = 0) -> None:
        path = hud_dir / ".session_engaged"
        path.write_text(
            json.dumps(
                {
                    "engaged_at": time.time(),
                    "code_actions_since": code,
                    "deep_actions_since": deep,
                }
            ),
            encoding="utf-8",
        )

    def test_substantive_deep_thinking_zeroes_counter(self, _fresh_env) -> None:
        from divineos.core.hud_handoff import mark_engaged

        self._seed_work()
        self._set_counter(_fresh_env, code=20, deep=25)
        mark_engaged(tool="ask", query="about the rudder")
        m = self._read_marker(_fresh_env)
        assert m["code_actions_since"] == 0
        assert m["deep_actions_since"] == 0
        assert m["engagement_substantive"] is True

    def test_shell_deep_thinking_halves_only(self, _fresh_env) -> None:
        """An ask with no overlap against recent work should NOT fully
        clear the deep counter. This is the un-gameable behavior."""
        from divineos.core.hud_handoff import mark_engaged

        self._seed_work()
        self._set_counter(_fresh_env, code=20, deep=25)
        mark_engaged(tool="ask", query="unrelated topic")
        m = self._read_marker(_fresh_env)
        assert m["code_actions_since"] == 10  # halved
        assert m["deep_actions_since"] == 25  # preserved, NOT zeroed
        assert m["engagement_substantive"] is False

    def test_substantive_light_thinking_halves(self, _fresh_env) -> None:
        """Light tools (decide/feel/context) halve even when substantive —
        they're not deep enough to fully clear."""
        from divineos.core.hud_handoff import mark_engaged

        self._seed_work()
        self._set_counter(_fresh_env, code=20, deep=5)
        mark_engaged(tool="decide", query="rudder calibration")
        m = self._read_marker(_fresh_env)
        assert m["code_actions_since"] == 10
        assert m["engagement_substantive"] is True

    def test_empty_query_is_shell(self, _fresh_env) -> None:
        from divineos.core.hud_handoff import mark_engaged

        self._seed_work()
        self._set_counter(_fresh_env, code=30, deep=30)
        mark_engaged(tool="ask", query="")
        m = self._read_marker(_fresh_env)
        assert m["engagement_substantive"] is False
        assert m["deep_actions_since"] == 30  # not zeroed by shell
