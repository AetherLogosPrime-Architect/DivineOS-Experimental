"""Tests for the multi-party-review gate (scripts/check_multi_party_review.py).

Falsifiability (per pre-reg):
  - No guardrail files staged -> gate passes regardless of trailer.
  - Guardrail files staged + no trailer -> block.
  - Trailer present + round does not exist -> block.
  - Round too old -> block.
  - Round missing diff-hash or wrong hash -> block.
  - Round has only user CONFIRMS -> block (needs AI too).
  - Round has only AI CONFIRMS -> block (needs user too).
  - Round has 'claude' bare as AI actor -> block (must be disambiguated).
  - Happy path: user CONFIRMS + grok CONFIRMS + valid hash + fresh -> pass.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch


def _load_module():
    """Load scripts/check_multi_party_review.py as a module — not on sys.path."""
    path = Path(__file__).resolve().parent.parent / "scripts" / "check_multi_party_review.py"
    spec = importlib.util.spec_from_file_location("check_multi_party_review", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_multi_party_review"] = mod
    spec.loader.exec_module(mod)
    return mod


mpr = _load_module()


class _FakeRound:
    def __init__(self, focus: str, created_at: float):
        self.focus = focus
        self.notes = ""
        self.created_at = created_at


class _FakeFinding:
    def __init__(self, actor: str, stance: str = "CONFIRMS"):
        self.actor = actor

        class _Stance:
            def __init__(self, v):
                self.value = v

        self.review_stance = _Stance(stance)


class TestNoGuardrailsStaged:
    def test_empty_staged_passes(self) -> None:
        with patch.object(mpr, "_staged_files", return_value=[]):
            ok, _ = mpr.validate("any message")
        assert ok is True

    def test_non_guardrail_files_pass(self) -> None:
        with patch.object(
            mpr,
            "_staged_files",
            return_value=["src/divineos/cli/_helpers.py", "tests/test_x.py"],
        ):
            with patch.object(
                mpr, "_load_guardrail_set", return_value={"src/divineos/core/compliance_audit.py"}
            ):
                ok, _ = mpr.validate("no trailer needed")
        assert ok is True


class TestTrailerMissing:
    def test_staged_guardrail_without_trailer_blocks(self) -> None:
        guardrail = "src/divineos/core/compliance_audit.py"
        with patch.object(mpr, "_staged_files", return_value=[guardrail]):
            with patch.object(mpr, "_load_guardrail_set", return_value={guardrail}):
                with patch.object(mpr, "_staged_diff_hash", return_value="abc"):
                    ok, msg = mpr.validate("routine commit message, no trailer")
        assert ok is False
        assert "External-Review" in msg
        assert guardrail in msg


class TestRoundNotFound:
    def test_trailer_references_missing_round_blocks(self) -> None:
        guardrail = "src/divineos/core/compliance_audit.py"
        with patch.object(mpr, "_staged_files", return_value=[guardrail]):
            with patch.object(mpr, "_load_guardrail_set", return_value={guardrail}):
                with patch.object(mpr, "_staged_diff_hash", return_value="abc"):
                    with patch.object(mpr, "_fetch_round_and_findings", return_value=(None, [])):
                        ok, msg = mpr.validate("commit\n\nExternal-Review: round-ghost")
        assert ok is False
        assert "round-ghost" in msg
        assert "not found" in msg.lower()


class TestStaleRound:
    def test_round_older_than_window_blocks(self) -> None:
        guardrail = "src/divineos/core/compliance_audit.py"
        now = 1_700_000_000.0
        # Round created 30 days ago, window is 7 days.
        old_ts = now - 30 * 86400
        diff_hash = "a" * 64
        rnd = _FakeRound(focus=f"test round  diff-hash: {diff_hash}", created_at=old_ts)
        findings = [_FakeFinding("user"), _FakeFinding("grok")]
        with patch.object(mpr, "_staged_files", return_value=[guardrail]):
            with patch.object(mpr, "_load_guardrail_set", return_value={guardrail}):
                with patch.object(mpr, "_staged_diff_hash", return_value=diff_hash):
                    with patch.object(
                        mpr, "_fetch_round_and_findings", return_value=(rnd, findings)
                    ):
                        ok, msg = mpr.validate("commit\n\nExternal-Review: round-stale", now=now)
        assert ok is False
        assert "days old" in msg


class TestDiffHashBinding:
    def test_round_missing_hash_blocks(self) -> None:
        guardrail = "src/divineos/core/compliance_audit.py"
        now = 1_700_000_000.0
        rnd = _FakeRound(focus="test round without hash", created_at=now - 3600)
        findings = [_FakeFinding("user"), _FakeFinding("grok")]
        with patch.object(mpr, "_staged_files", return_value=[guardrail]):
            with patch.object(mpr, "_load_guardrail_set", return_value={guardrail}):
                with patch.object(mpr, "_staged_diff_hash", return_value="a" * 64):
                    with patch.object(
                        mpr, "_fetch_round_and_findings", return_value=(rnd, findings)
                    ):
                        ok, msg = mpr.validate("commit\n\nExternal-Review: round-nohash", now=now)
        assert ok is False
        assert "diff-hash" in msg

    def test_wrong_hash_blocks(self) -> None:
        guardrail = "src/divineos/core/compliance_audit.py"
        now = 1_700_000_000.0
        rnd = _FakeRound(focus=f"test round diff-hash: {'b' * 64}", created_at=now - 3600)
        findings = [_FakeFinding("user"), _FakeFinding("grok")]
        with patch.object(mpr, "_staged_files", return_value=[guardrail]):
            with patch.object(mpr, "_load_guardrail_set", return_value={guardrail}):
                with patch.object(mpr, "_staged_diff_hash", return_value="a" * 64):
                    with patch.object(
                        mpr, "_fetch_round_and_findings", return_value=(rnd, findings)
                    ):
                        ok, _ = mpr.validate("commit\n\nExternal-Review: round-wronghash", now=now)
        assert ok is False


class TestSingleActorBlocks:
    def test_user_alone_blocks(self) -> None:
        guardrail = "src/divineos/core/compliance_audit.py"
        now = 1_700_000_000.0
        diff_hash = "a" * 64
        rnd = _FakeRound(focus=f"diff-hash: {diff_hash}", created_at=now - 3600)
        findings = [_FakeFinding("user")]  # no AI
        with patch.object(mpr, "_staged_files", return_value=[guardrail]):
            with patch.object(mpr, "_load_guardrail_set", return_value={guardrail}):
                with patch.object(mpr, "_staged_diff_hash", return_value=diff_hash):
                    with patch.object(
                        mpr, "_fetch_round_and_findings", return_value=(rnd, findings)
                    ):
                        ok, msg = mpr.validate("commit\n\nExternal-Review: round-useronly", now=now)
        assert ok is False
        assert "external AI" in msg

    def test_ai_alone_blocks(self) -> None:
        guardrail = "src/divineos/core/compliance_audit.py"
        now = 1_700_000_000.0
        diff_hash = "a" * 64
        rnd = _FakeRound(focus=f"diff-hash: {diff_hash}", created_at=now - 3600)
        findings = [_FakeFinding("grok")]  # no user
        with patch.object(mpr, "_staged_files", return_value=[guardrail]):
            with patch.object(mpr, "_load_guardrail_set", return_value={guardrail}):
                with patch.object(mpr, "_staged_diff_hash", return_value=diff_hash):
                    with patch.object(
                        mpr, "_fetch_round_and_findings", return_value=(rnd, findings)
                    ):
                        ok, msg = mpr.validate("commit\n\nExternal-Review: round-aionly", now=now)
        assert ok is False
        assert "actor=user" in msg


class TestClaudeBareBlocked:
    def test_claude_bare_is_not_external_ai(self) -> None:
        assert mpr._is_external_ai_actor("claude") is False
        assert mpr._is_external_ai_actor("CLAUDE") is False

    def test_claude_bare_does_not_satisfy_ai_requirement(self) -> None:
        guardrail = "src/divineos/core/compliance_audit.py"
        now = 1_700_000_000.0
        diff_hash = "a" * 64
        rnd = _FakeRound(focus=f"diff-hash: {diff_hash}", created_at=now - 3600)
        # User CONFIRMS + bare 'claude' CONFIRMS — should block because
        # 'claude' is the running agent's name and is not accepted as external.
        findings = [_FakeFinding("user"), _FakeFinding("claude")]
        with patch.object(mpr, "_staged_files", return_value=[guardrail]):
            with patch.object(mpr, "_load_guardrail_set", return_value={guardrail}):
                with patch.object(mpr, "_staged_diff_hash", return_value=diff_hash):
                    with patch.object(
                        mpr, "_fetch_round_and_findings", return_value=(rnd, findings)
                    ):
                        ok, _ = mpr.validate("commit\n\nExternal-Review: round-bareclaude", now=now)
        assert ok is False


class TestDisambiguatedClaudeAccepted:
    def test_claude_opus_auditor_is_external_ai(self) -> None:
        assert mpr._is_external_ai_actor("claude-opus-auditor") is True

    def test_claude_sonnet_external_is_external_ai(self) -> None:
        assert mpr._is_external_ai_actor("claude-sonnet-external") is True

    def test_grok_is_external_ai(self) -> None:
        assert mpr._is_external_ai_actor("grok") is True

    def test_gemini_is_external_ai(self) -> None:
        assert mpr._is_external_ai_actor("gemini") is True


class TestHappyPath:
    def test_user_plus_grok_passes(self) -> None:
        guardrail = "src/divineos/core/compliance_audit.py"
        now = 1_700_000_000.0
        diff_hash = "a" * 64
        rnd = _FakeRound(
            focus=f"review of guardrail change; diff-hash: {diff_hash}",
            created_at=now - 3600,
        )
        findings = [_FakeFinding("user"), _FakeFinding("grok")]
        with patch.object(mpr, "_staged_files", return_value=[guardrail]):
            with patch.object(mpr, "_load_guardrail_set", return_value={guardrail}):
                with patch.object(mpr, "_staged_diff_hash", return_value=diff_hash):
                    with patch.object(
                        mpr, "_fetch_round_and_findings", return_value=(rnd, findings)
                    ):
                        ok, msg = mpr.validate("commit\n\nExternal-Review: round-happy", now=now)
        assert ok is True
        assert "passed" in msg.lower()

    def test_user_plus_claude_opus_external_passes(self) -> None:
        guardrail = "src/divineos/core/compliance_audit.py"
        now = 1_700_000_000.0
        diff_hash = "a" * 64
        rnd = _FakeRound(focus=f"review; diff-hash: {diff_hash}", created_at=now - 3600)
        findings = [_FakeFinding("user"), _FakeFinding("claude-opus-auditor")]
        with patch.object(mpr, "_staged_files", return_value=[guardrail]):
            with patch.object(mpr, "_load_guardrail_set", return_value={guardrail}):
                with patch.object(mpr, "_staged_diff_hash", return_value=diff_hash):
                    with patch.object(
                        mpr, "_fetch_round_and_findings", return_value=(rnd, findings)
                    ):
                        ok, _ = mpr.validate("commit\n\nExternal-Review: round-happyext", now=now)
        assert ok is True


class TestTrailerParsing:
    def test_trailer_on_own_line(self) -> None:
        assert (
            mpr._parse_trailer("subject\n\nbody text\n\nExternal-Review: round-abc") == "round-abc"
        )

    def test_trailer_case_insensitive(self) -> None:
        assert mpr._parse_trailer("subject\n\nexternal-review: round-xyz") == "round-xyz"

    def test_no_trailer(self) -> None:
        assert mpr._parse_trailer("nothing here") is None
