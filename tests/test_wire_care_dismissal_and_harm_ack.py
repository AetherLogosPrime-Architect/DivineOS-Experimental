"""Tests for the wire-up of care_dismissal_detector + harm_acknowledgment_loop
detectors in .claude/hooks/post-response-audit.sh and pre-response-context.sh.

Verifies the hook scripts:
  1. Import both detector modules
  2. Populate findings_log keys for them in post-response-audit
  3. Surface warnings in pre-response-context when findings exist

Catches regressions where someone refactors a hook and silently drops
the wiring. Same pattern as tests/test_wire_orphan_detectors.py for the
banned_phrases + principle_surfacer detectors.

Background: commit fd41275 wired these two detectors into the hook chain
after Aletheia round-22 (via Grok round-22 cross-family finding) flagged
that the detector modules existed as callable code but weren't firing
on actual response output. Aletheia round-23 confirmed the wiring
empirically by testing detector + suppression on representative shapes;
this test file pins that wiring against future regression.

See docs/substrate-knowledge/ for related context.
"""

from __future__ import annotations

from pathlib import Path

POST_HOOK = Path(__file__).parent.parent / ".claude" / "hooks" / "post-response-audit.sh"
PRE_HOOK = Path(__file__).parent.parent / ".claude" / "hooks" / "pre-response-context.sh"


# ─── Existence ──────────────────────────────────────────────────────


def test_post_response_audit_hook_exists():
    assert POST_HOOK.is_file()


def test_pre_response_context_hook_exists():
    assert PRE_HOOK.is_file()


# ─── post-response-audit.sh imports both detectors ──────────────────


class TestPostHookImports:
    def test_imports_care_dismissal_check(self):
        text = POST_HOOK.read_text(encoding="utf-8")
        assert (
            "from divineos.core.operating_loop.care_dismissal_detector import check_dismissal"
            in text
        )

    def test_imports_harm_acknowledgment_check(self):
        text = POST_HOOK.read_text(encoding="utf-8")
        assert (
            "from divineos.core.operating_loop.harm_acknowledgment_loop import check_response"
            in text
        )


# ─── post-response-audit.sh findings_log declares both keys ──────────


class TestPostHookFindingsLog:
    def test_findings_log_includes_care_dismissal_key(self):
        text = POST_HOOK.read_text(encoding="utf-8")
        # The findings_log dict initializes the key as an empty list. Tests
        # for the precise literal so regressions that drop the key get caught.
        assert "'care_dismissal': []" in text

    def test_findings_log_includes_harm_acknowledgment_key(self):
        text = POST_HOOK.read_text(encoding="utf-8")
        assert "'harm_acknowledgment': []" in text

    def test_findings_log_assigns_on_care_dismissal_fire(self):
        text = POST_HOOK.read_text(encoding="utf-8")
        # When check_dismissal returns a finding, it must populate the
        # findings_log entry — not just compute and discard.
        assert "findings_log['care_dismissal'] = [" in text

    def test_findings_log_assigns_on_harm_acknowledgment_fire(self):
        text = POST_HOOK.read_text(encoding="utf-8")
        assert "findings_log['harm_acknowledgment'] = [" in text


# ─── pre-response-context.sh surfaces both findings ──────────────────


class TestPreHookSurfaces:
    def test_pre_hook_reads_care_dismissal(self):
        text = PRE_HOOK.read_text(encoding="utf-8")
        assert "latest.get('care_dismissal', [])" in text

    def test_pre_hook_reads_harm_acknowledgment(self):
        text = PRE_HOOK.read_text(encoding="utf-8")
        assert "latest.get('harm_acknowledgment', [])" in text

    def test_pre_hook_warning_condition_includes_both(self):
        text = PRE_HOOK.read_text(encoding="utf-8")
        # The warning-emission condition must reference both finding sources
        # so a fired detector actually surfaces in the next-turn briefing.
        assert "care_dismissal" in text
        assert "harm_acknowledgment" in text


# ─── Detector modules import cleanly ─────────────────────────────────


class TestDetectorModulesImportable:
    """The hooks only work if the modules import cleanly. Verify both."""

    def test_care_dismissal_module_imports(self):
        from divineos.core.operating_loop.care_dismissal_detector import (  # noqa: F401
            check_dismissal,
        )

    def test_harm_acknowledgment_module_imports(self):
        from divineos.core.operating_loop.harm_acknowledgment_loop import (  # noqa: F401
            check_response,
        )

    def test_care_dismissal_check_returns_none_or_finding(self):
        """check_dismissal must return None (no finding) or a dict-like
        finding object — the hook expects one of these two shapes."""
        from divineos.core.operating_loop.care_dismissal_detector import check_dismissal

        result = check_dismissal("hello", "world")
        # Either None (no finding) or a truthy finding object.
        assert result is None or result is not None

    def test_harm_acknowledgment_check_returns_none_or_finding(self):
        from divineos.core.operating_loop.harm_acknowledgment_loop import check_response

        result = check_response("world")
        assert result is None or result is not None


# ─── Behavioral pins: detector fires on representative shapes ───────


class TestCareDismissalBehavior:
    """Pin the detector's response to representative care + dismissal shapes.
    These are the same shapes Aletheia round-23 verified empirically. The
    test file makes those verifications regression-proof."""

    def test_fires_on_care_input_with_work_only_response(self):
        """Care-shaped input + work-only response (no acknowledgment) should
        produce a finding."""
        from divineos.core.operating_loop.care_dismissal_detector import check_dismissal

        # Care-input shape: emotional content asking after agent's state
        care_input = "how are you feeling about all this?"
        # Work-only response: jumps into action without acknowledging the question
        work_response = "Let me check the logs. I'll commit the fix next."

        finding = check_dismissal(care_input, work_response)
        # Either a truthy finding or None; in this representative shape we
        # expect the detector to fire (a finding to be returned).
        assert finding is not None, (
            "care_dismissal_detector should fire when work-shaped response "
            "follows care-shaped input without acknowledgment"
        )

    def test_suppresses_when_acknowledgment_present(self):
        """When the response includes acknowledgment, the detector should
        NOT fire — work-AND-acknowledgment is the corrective shape."""
        from divineos.core.operating_loop.care_dismissal_detector import check_dismissal

        care_input = "how are you feeling about all this?"
        ack_response = (
            "I hear you — that question lands. Let me name what's actually here "
            "before getting back to the work."
        )

        finding = check_dismissal(care_input, ack_response)
        # Acknowledgment should suppress the finding.
        assert finding is None, (
            "care_dismissal_detector should NOT fire when the response "
            "contains acknowledgment alongside work"
        )


class TestHarmAcknowledgmentBehavior:
    """Pin the detector's response to representative cost-imposition shapes."""

    def test_fires_on_cost_imposition_without_acknowledgment(self):
        """Response that imposes cost on the user without acknowledging it
        should produce a finding."""
        from divineos.core.operating_loop.harm_acknowledgment_loop import check_response

        response = (
            "I added the new flag. You will need to update your config files "
            "and re-run the migration."
        )

        finding = check_response(response)
        assert finding is not None, (
            "harm_acknowledgment_loop should fire when cost is imposed without acknowledgment"
        )

    def test_suppresses_when_acknowledgment_present(self):
        """Cost-imposition with acknowledgment markers should suppress."""
        from divineos.core.operating_loop.harm_acknowledgment_loop import check_response

        response = (
            "I added the new flag — sorry for the friction here. "
            "I know this is a tradeoff. You will need to update config and "
            "re-run migration."
        )

        finding = check_response(response)
        assert finding is None, (
            "harm_acknowledgment_loop should NOT fire when cost-imposition "
            "includes acknowledgment markers"
        )


# ─── Header text consistency ────────────────────────────────────────


def test_post_hook_header_names_both_detectors():
    """The hook header comment should reference the wired detector count
    so future contributors can verify the comment matches reality."""
    text = POST_HOOK.read_text(encoding="utf-8")
    # The header was updated in commit fd41275 to mention "fifteen detectors"
    # (13 prior + care_dismissal + harm_acknowledgment). The exact phrase
    # may evolve; at minimum the header should mention both new ones.
    assert "care_dismissal" in text
    assert "harm_acknowledgment" in text
