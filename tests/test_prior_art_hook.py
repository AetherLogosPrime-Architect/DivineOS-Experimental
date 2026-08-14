"""The prior-art lookup must run without being asked, and never block.

Pins the two properties that make this a service rather than another gate:
it answers on its own, and it cannot interfere with the search that triggered
it. Both matter because the thing it replaces is not a missing tool -- the
tool was complete and unwired -- but a missing trigger.
"""

from __future__ import annotations

import io
import json

from divineos.hooks import prior_art_hook


class TestTermExtraction:
    def test_regex_metacharacters_do_not_hide_the_words(self):
        # The search that missed PR #409's fix looked like this. If the
        # metacharacters swallowed the words, the lookup would run on nothing.
        assert prior_art_hook.extract_terms("bypass.*telemetry") == ["bypass", "telemetry"]

    def test_generic_words_are_dropped(self):
        # A hit on "test" or "def" says nothing about whether work exists,
        # and reporting it teaches me to skim the surface.
        assert prior_art_hook.extract_terms("def test_") == []

    def test_short_fragments_are_ignored(self):
        assert prior_art_hook.extract_terms("a bc def") == []

    def test_terms_are_capped(self):
        # An unbounded pattern must not produce an unbounded report.
        terms = prior_art_hook.extract_terms("alpha beta gamma delta epsilon")
        assert len(terms) <= 2


class TestNeverBlocks:
    """Exit 0 on every path. A lookup that breaks a search is worse than the
    forgetting it replaces, and a nonzero exit from PreToolUse stops the tool.

    ``main()`` is driven directly rather than through a subprocess. A
    subprocess resolves ``divineos`` through whatever is pip-installed, which
    on this machine points at a different checkout entirely -- so the test
    would report on code other than the code under test. That exact confusion
    cost real time on 2026-08-14; verify the artifact, not a copy of it.
    """

    def _run(self, payload: str, monkeypatch, capsys) -> tuple[int, str]:
        monkeypatch.setattr("sys.stdin", io.StringIO(payload))
        code = prior_art_hook.main()
        return code, capsys.readouterr().out

    def test_malformed_payload_exits_zero(self, monkeypatch, capsys):
        assert self._run("not json at all", monkeypatch, capsys)[0] == 0

    def test_empty_payload_exits_zero(self, monkeypatch, capsys):
        assert self._run("", monkeypatch, capsys)[0] == 0

    def test_unrelated_tool_exits_zero_and_stays_silent(self, monkeypatch, capsys):
        payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": "x.py"}})
        code, out = self._run(payload, monkeypatch, capsys)
        assert code == 0
        assert out.strip() == ""

    def test_search_payload_exits_zero(self, monkeypatch, capsys):
        payload = json.dumps({"tool_name": "Grep", "tool_input": {"pattern": "bypass.*telemetry"}})
        assert self._run(payload, monkeypatch, capsys)[0] == 0

    def test_a_raising_lookup_still_exits_zero(self, monkeypatch, capsys):
        """The failure mode that would matter most: prior_art itself breaking."""

        def boom(_pattern):
            raise RuntimeError("lookup exploded")

        monkeypatch.setattr(prior_art_hook, "report_for", boom)
        payload = json.dumps({"tool_name": "Grep", "tool_input": {"pattern": "anything"}})
        assert self._run(payload, monkeypatch, capsys)[0] == 0


class TestReportContent:
    def test_no_hits_produces_no_surface(self):
        # Silence when there is nothing to say is what keeps this from
        # decaying into wallpaper -- the failure the 2026-07-15 design
        # sketch observed in the surfaces this one replaces.
        assert prior_art_hook.report_for("zzqqxx_nonexistent_term_zzqqxx") == ""

    def test_empty_pattern_produces_no_surface(self):
        assert prior_art_hook.report_for("") == ""
