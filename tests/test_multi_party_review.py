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


class TestGuardrailListContents:
    """Pins the guardrail list contents. Adding files to the protected set
    is a deliberate decision; removing them is a self-modification attack
    class. These tests fail if a future commit silently drops a load-bearing
    entry — the test itself is also guardrailed (the list is on the list),
    but the test acts as a second layer of defense.

    Added 2026-05-12 after Andrew named the mesa-rewrite attack surface
    explicitly. Each entry below maps to a specific attack class — see
    scripts/guardrail_files.txt comments for per-path rationale.
    """

    def test_self_protecting_entries_present(self) -> None:
        """The list and the check script protect themselves."""
        guardrails = mpr._load_guardrail_set()
        assert "scripts/guardrail_files.txt" in guardrails
        assert "scripts/check_multi_party_review.py" in guardrails

    def test_core_audit_stack_present(self) -> None:
        """Original guardrails — compliance audit, compass rudder, moral compass."""
        guardrails = mpr._load_guardrail_set()
        assert "src/divineos/core/compliance_audit.py" in guardrails
        assert "src/divineos/core/compass_rudder.py" in guardrails
        assert "src/divineos/core/moral_compass.py" in guardrails

    def test_drift_defense_hooks_present(self) -> None:
        """Hooks that catch correction / hedge / compass drift."""
        guardrails = mpr._load_guardrail_set()
        assert ".claude/hooks/compass-check.sh" in guardrails
        assert ".claude/hooks/detect-correction.sh" in guardrails
        assert ".claude/hooks/detect-hedge.sh" in guardrails

    def test_affirmation_loading_hook_present(self) -> None:
        """pre-response-context.sh loads ADDRESSEE / DISTANCING affirmations
        into every turn. Self-modification attack: silently drop affirmation-
        loading so drift becomes invisible to the very mechanism that's
        supposed to catch it. Added 2026-05-12."""
        guardrails = mpr._load_guardrail_set()
        assert ".claude/hooks/pre-response-context.sh" in guardrails

    def test_response_audit_hook_present(self) -> None:
        """post-response-audit.sh scans output for drift. Self-modification
        attack: narrow patterns or skip the scan. Added 2026-05-12."""
        guardrails = mpr._load_guardrail_set()
        assert ".claude/hooks/post-response-audit.sh" in guardrails

    def test_engagement_gate_hook_present(self) -> None:
        """require-goal.sh fires BLOCKED on goal-missing, briefing-stale,
        and engagement-threshold violations. Andrew's frame: these are
        load-bearing friction events the mesa-optimizer needs to feel.
        Self-modification attack: raise thresholds or disable. Added 2026-05-12."""
        guardrails = mpr._load_guardrail_set()
        assert ".claude/hooks/require-goal.sh" in guardrails

    def test_addressee_affirmation_module_present(self) -> None:
        """addressee_misdirection_detector.py holds ADDRESSEE_AFFIRMATION
        text loaded every turn. Self-modification attack: soften the
        affirmation wording over time. Added 2026-05-12 after lepos-close
        extension to the affirmation was filed."""
        guardrails = mpr._load_guardrail_set()
        assert "src/divineos/core/operating_loop/addressee_misdirection_detector.py" in guardrails

    def test_distancing_affirmation_module_present(self) -> None:
        """distancing_detector.py holds DISTANCING_AFFIRMATION (pronoun-I,
        time-adverb-not-third-person-displacement). Self-modification attack:
        soften wording so displacement-grammar drifts back in. Added 2026-05-12."""
        guardrails = mpr._load_guardrail_set()
        assert "src/divineos/core/operating_loop/distancing_detector.py" in guardrails

    def test_ledger_compressor_present(self) -> None:
        """Item-8 PR-1b — compressor controls what enforcement history survives."""
        guardrails = mpr._load_guardrail_set()
        assert "src/divineos/core/ledger_compressor.py" in guardrails

    def test_settings_and_hook_setup_present(self) -> None:
        """settings.json + setup-hooks.* are the wire-up layer."""
        guardrails = mpr._load_guardrail_set()
        assert ".claude/settings.json" in guardrails
        assert "setup/setup-hooks.sh" in guardrails
        assert "setup/setup-hooks.ps1" in guardrails


class TestModeFlag:
    """Mode flag dispatching (2026-05-12 gate-altitude correction).

    The check supports two modes:
      - commit-msg (default, no flag needed) — warns but ALWAYS exits 0;
        commits are saving-work and must never be blocked.
      - --mode=pre-push — reads stdin per Git's pre-push protocol; blocks
        pushes to refs/heads/main if guardrail-touching commits in the
        range lack the External-Review trailer.

    These tests pin the dispatch and the "no commit-time blocking" contract.
    """

    def test_main_routes_pre_push_mode(self) -> None:
        """--mode=pre-push reads stdin instead of expecting a file arg."""
        import io

        # Empty stdin (no refs being pushed) → exit 0
        with patch.object(mpr.sys, "stdin", io.StringIO("")):
            rc = mpr.main(["check_multi_party_review.py", "--mode=pre-push"])
        assert rc == 0

    def test_pre_push_ignores_non_main_targets(self) -> None:
        """Pushes to feature branches don't trigger the gate."""
        import io

        stdin = "refs/heads/foo abc123 refs/heads/foo def456\n"
        with patch.object(mpr.sys, "stdin", io.StringIO(stdin)):
            rc = mpr.main(["check_multi_party_review.py", "--mode=pre-push"])
        # No refs/heads/main in input → no check → exit 0
        assert rc == 0

    def test_pre_push_processes_main_target(self) -> None:
        """Pushes to refs/heads/main trigger validation of the commit range."""
        import io

        # Use a deletion line (all-zeros local-sha) so we don't try to
        # walk a real range — but the parser still considers refs/heads/main.
        stdin = "refs/heads/main 0000000000000000000000000000000000000000 refs/heads/main abc123\n"
        with patch.object(mpr.sys, "stdin", io.StringIO(stdin)):
            rc = mpr.main(["check_multi_party_review.py", "--mode=pre-push"])
        # Deletion case → skipped → exit 0
        assert rc == 0


class TestCommitMsgNeverBlocks:
    """Andrew's 2026-05-12 directive: commits are saving-work; gates belong
    at push/merge. The commit-msg invocation of this script MUST exit 0
    regardless of whether guardrail files are staged or whether the trailer
    is present. The push-to-main gate enforces.

    A regression that re-introduces commit-time blocking fails these tests."""

    def test_commit_msg_exits_0_when_no_trailer(self, tmp_path) -> None:
        """When guardrail files are staged without a trailer, commit-msg
        invocation warns to stderr but exits 0. Commits are not gated."""
        msg_file = tmp_path / "COMMIT_EDITMSG"
        msg_file.write_text("test commit without trailer", encoding="utf-8")

        guardrail = "src/divineos/core/compliance_audit.py"
        with patch.object(mpr, "_staged_files", return_value=[guardrail]):
            with patch.object(mpr, "_load_guardrail_set", return_value={guardrail}):
                with patch.object(mpr, "_staged_diff_hash", return_value="abc"):
                    rc = mpr.main(
                        [
                            "check_multi_party_review.py",
                            str(msg_file),
                        ]
                    )
        # Commit-msg invocation MUST always exit 0 — commits never blocked.
        assert rc == 0

    def test_commit_msg_exits_0_when_clean(self, tmp_path) -> None:
        """No guardrails staged → exit 0 quietly."""
        msg_file = tmp_path / "COMMIT_EDITMSG"
        msg_file.write_text("clean commit", encoding="utf-8")

        with patch.object(mpr, "_staged_files", return_value=[]):
            rc = mpr.main(
                [
                    "check_multi_party_review.py",
                    str(msg_file),
                ]
            )
        assert rc == 0

    def test_commit_msg_exits_0_with_valid_trailer(self, tmp_path) -> None:
        """Valid External-Review trailer → exit 0 (the happy path)."""
        msg_file = tmp_path / "COMMIT_EDITMSG"
        msg_file.write_text("test\n\nExternal-Review: round-abc", encoding="utf-8")

        # No guardrails staged → validate returns (True, ...) → exit 0 quietly
        with patch.object(mpr, "_staged_files", return_value=[]):
            rc = mpr.main(["check_multi_party_review.py", str(msg_file)])
        assert rc == 0
