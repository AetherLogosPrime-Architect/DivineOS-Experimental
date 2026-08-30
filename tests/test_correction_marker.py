"""Tests for correction_marker — structural enforcement of `divineos learn`.

Falsifiability:
  - set_marker + read_marker round-trip preserves trigger + ts.
  - Missing marker reads as None.
  - Malformed JSON reads as None (fail-open).
  - clear_marker removes the file; subsequent read returns None.
  - format_gate_message always contains the trigger text (or preview).
  - Gate integration: when marker is present AND tool is not bypass,
    pre_tool_use_gate returns a deny decision.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from divineos.core import correction_marker
from divineos.core.correction_marker import classify_correction, strip_relayed


def should_mark(prompt: str) -> bool:
    """Test helper — formerly a backcompat wrapper in correction_marker.

    Removed from production 2026-06-04 (test-only, replaced everywhere by
    classify_correction). Kept in tests to avoid rewriting 20+ call sites
    that exercise the BLOCK/no-block distinction. Equivalent to the
    deleted wrapper: STRONG patterns block; WEAK patterns alone do not.

    Updated 2026-06-19 (prereg-897aade9ef38): classify_correction now
    returns CorrectionMatch | None (evidence-bearing). Read .verdict.
    """
    result = classify_correction(prompt)
    return result is not None and result.verdict == "block"


def verdict_of(
    prompt: str,
    prior_text: str = "",
    prior_calls: tuple[str, ...] = (),
) -> str | None:
    """Test helper — extract verdict string from new evidence-bearing return.

    Preserves the readability of existing tests that previously asserted
    against ``classify_correction(...) == 'block'`` etc. without rewriting
    each call site to handle the CorrectionMatch dataclass directly.
    """
    result = classify_correction(prompt, prior_text, prior_calls)
    return result.verdict if result is not None else None


class TestMarkerRoundTrip:
    def test_set_and_read_preserves_trigger(self, tmp_path) -> None:
        mpath = tmp_path / "marker.json"
        with patch.object(correction_marker, "marker_path", return_value=mpath):
            correction_marker.set_marker("no, that's wrong")
            got = correction_marker.read_marker()
        assert got is not None
        assert got["trigger"] == "no, that's wrong"
        assert isinstance(got["ts"], float)

    def test_trigger_truncates_to_200_chars(self, tmp_path) -> None:
        mpath = tmp_path / "marker.json"
        long_text = "x" * 500
        with patch.object(correction_marker, "marker_path", return_value=mpath):
            correction_marker.set_marker(long_text)
            got = correction_marker.read_marker()
        assert len(got["trigger"]) == 200


class TestMarkerAbsence:
    def test_missing_marker_reads_as_none(self, tmp_path) -> None:
        mpath = tmp_path / "does_not_exist.json"
        with patch.object(correction_marker, "marker_path", return_value=mpath):
            assert correction_marker.read_marker() is None

    def test_malformed_json_reads_as_none(self, tmp_path) -> None:
        mpath = tmp_path / "marker.json"
        mpath.write_text("{not json", encoding="utf-8")
        with patch.object(correction_marker, "marker_path", return_value=mpath):
            assert correction_marker.read_marker() is None

    def test_empty_file_reads_as_none(self, tmp_path) -> None:
        mpath = tmp_path / "marker.json"
        mpath.write_text("", encoding="utf-8")
        with patch.object(correction_marker, "marker_path", return_value=mpath):
            assert correction_marker.read_marker() is None


class TestClear:
    def test_clear_removes_marker(self, tmp_path) -> None:
        mpath = tmp_path / "marker.json"
        mpath.write_text(json.dumps({"ts": 1.0, "trigger": "x"}), encoding="utf-8")
        with patch.object(correction_marker, "marker_path", return_value=mpath):
            assert correction_marker.read_marker() is not None
            correction_marker.clear_marker()
            assert correction_marker.read_marker() is None

    def test_clear_missing_marker_is_safe(self, tmp_path) -> None:
        mpath = tmp_path / "does_not_exist.json"
        with patch.object(correction_marker, "marker_path", return_value=mpath):
            correction_marker.clear_marker()  # should not raise

    def test_clear_marker_also_clears_compass_cascade_when_kind_is_correction(
        self, tmp_path
    ) -> None:
        """Andrew fix 2026-07-15 ("stop dismissing the compass and fix it"):
        set_marker fires the compass_required cascade with kind='correction';
        clear_marker must symmetrically clear that cascade. Otherwise
        `divineos correction` clears the correction but leaves the compass
        cascade nagging — which was routing the operator to `compass-ops
        dismiss` as a workflow rather than a fix."""
        from divineos.core import compass_required_marker

        c_mpath = tmp_path / "correction.json"
        cr_mpath = tmp_path / "compass_required.json"
        c_mpath.write_text(json.dumps({"ts": 1.0, "trigger": "x"}), encoding="utf-8")
        cr_mpath.write_text(
            json.dumps(
                {
                    "ts": 1.0,
                    "kind": "correction",
                    "summary": "cascade from correction",
                    "advised_count": 0,
                    "last_advised_ts": 0.0,
                }
            ),
            encoding="utf-8",
        )
        with (
            patch.object(correction_marker, "marker_path", return_value=c_mpath),
            patch.object(compass_required_marker, "marker_path", return_value=cr_mpath),
        ):
            assert compass_required_marker.read_marker() is not None
            correction_marker.clear_marker()
            assert correction_marker.read_marker() is None
            # THE FIX: cascade also cleared
            assert compass_required_marker.read_marker() is None

    def test_clear_marker_does_not_clear_compass_cascade_from_other_kinds(self, tmp_path) -> None:
        """Symmetric-clear must be precisely scoped. If the compass_required
        marker was set by a claim/hedge/theater trigger (not correction),
        clearing the correction marker must NOT clear that unrelated
        cascade. Prevents the fix from being too broad."""
        from divineos.core import compass_required_marker

        c_mpath = tmp_path / "correction.json"
        cr_mpath = tmp_path / "compass_required.json"
        c_mpath.write_text(json.dumps({"ts": 1.0, "trigger": "x"}), encoding="utf-8")
        cr_mpath.write_text(
            json.dumps(
                {
                    "ts": 1.0,
                    "kind": "claim_t2",
                    "summary": "cascade from claim",
                    "advised_count": 0,
                    "last_advised_ts": 0.0,
                }
            ),
            encoding="utf-8",
        )
        with (
            patch.object(correction_marker, "marker_path", return_value=c_mpath),
            patch.object(compass_required_marker, "marker_path", return_value=cr_mpath),
        ):
            correction_marker.clear_marker()
            assert correction_marker.read_marker() is None
            # Other-kind cascade untouched
            still = compass_required_marker.read_marker()
            assert still is not None
            assert still["kind"] == "claim_t2"


class TestGateMessage:
    def test_includes_trigger_preview(self) -> None:
        msg = correction_marker.format_gate_message({"trigger": "stop doing that", "ts": 0})
        assert "stop doing that" in msg
        assert "divineos learn" in msg

    def test_recent_age_format_seconds(self) -> None:
        import time as _t

        msg = correction_marker.format_gate_message({"trigger": "no", "ts": _t.time() - 15})
        assert "15s" in msg


class TestGateIntegration:
    def test_pre_tool_use_gate_denies_when_marker_present(self, tmp_path) -> None:
        """Full integration: marker triggers pre_tool_use_gate deny.

        Briefing-loaded gate fires first in the default stack, so we mock it
        to pass — otherwise the correction gate is never reached.
        """
        from divineos.core import briefing_id, hud_handoff, session_briefing_gate
        from divineos.hooks import pre_tool_use_gate

        mpath = tmp_path / "marker.json"
        mpath.write_text(
            json.dumps({"ts": 1.0, "trigger": "you missed something"}),
            encoding="utf-8",
        )
        with (
            patch.object(hud_handoff, "was_briefing_loaded", return_value=True),
            patch.object(session_briefing_gate, "briefing_loaded_this_session", return_value=True),
            patch.object(briefing_id, "is_fresh", return_value=True),
            patch.object(correction_marker, "marker_path", return_value=mpath),
        ):
            decision = pre_tool_use_gate._check_gates()
        assert decision is not None
        assert "correction detected" in str(decision).lower()
        assert "you missed something" in str(decision)
        assert "divineos learn" in str(decision)


class TestTwoAxisDetection:
    """Two-axis check: target (de-relayed) + surface (CORRECTION_PATTERNS).

    Closes the false-positive class where correction-shaped words inside
    relayed AI text fired the marker. Filed claim 986b4750.
    """

    def test_strip_relayed_removes_blockquote_lines(self) -> None:
        text = "ok looks good\n> this is wrong, do it again\nmore text"
        out = strip_relayed(text)
        assert "this is wrong" not in out
        assert "more text" in out

    def test_strip_relayed_removes_fenced_code(self) -> None:
        text = "look at this:\n```\nthat's not right\n```\nthoughts?"
        out = strip_relayed(text)
        assert "that's not right" not in out
        assert "thoughts?" in out

    def test_strip_relayed_trims_after_relay_introducer(self) -> None:
        text = "great work. here is the reply:\n\nI pulled the wrong branch"
        out = strip_relayed(text)
        assert "wrong branch" not in out
        assert "great work" in out

    def test_should_mark_fires_on_direct_correction(self) -> None:
        # Updated 2026-06-23: STRONG patterns now require corrective context
        # to block (was: context-blind). Without context, advise instead.
        # See classify_correction docstring for the geometry-of-correction
        # rationale. To test the "real correction" semantics, use verdict_of
        # with prior corrective context.
        result = classify_correction(
            "no, that's wrong, don't do that",
            prior_assistant_text="done, fixed it",
            prior_tool_calls=("Edit",),
        )
        assert result is not None and result.verdict == "block"

    def test_should_mark_does_not_fire_on_relayed_correction(self) -> None:
        text = "here is the reply\n\nI pulled the wrong branch the first time"
        assert should_mark(text) is False

    def test_should_mark_does_not_fire_on_blockquoted_correction(self) -> None:
        text = "ok\n\n> no, that is wrong\n\nthoughts?"
        assert should_mark(text) is False

    def test_should_mark_handles_empty_input(self) -> None:
        assert should_mark("") is False

    def test_should_mark_fires_on_correction_after_relayed_section(self) -> None:
        # Correction BEFORE the relay-introducer still counts.
        # Updated 2026-06-23 for STRONG-context-check: with corrective context
        # the pre-relay correction still blocks.
        text = "no, that's wrong. here is the reply\n\nthey said something"
        result = classify_correction(
            text,
            prior_assistant_text="done",
            prior_tool_calls=("Edit",),
        )
        assert result is not None and result.verdict == "block"

    def test_should_mark_strips_report_introducer(self) -> None:
        """C-auditor follow-up: relay-introducers extended to cover
        'here is the report' and similar — common in this user's
        actual relay style."""
        text = "here is the report\n\nI pulled the wrong branch"
        assert should_mark(text) is False

    def test_should_mark_strips_update_introducer(self) -> None:
        text = "here is the update\n\nthat doesn't work as expected"
        assert should_mark(text) is False

    def test_should_mark_strips_review_introducer(self) -> None:
        text = "here is the review\n\nthis is wrong, the approach failed"
        assert should_mark(text) is False


class TestStripRelayedCoverage20260603:
    """Regression for the two false-fire classes that fired during the
    2026-06-03 session (open corrections #38 and #39). Each had relayed /
    system content whose payload contained a real CORRECTION_PATTERN match;
    the structural strip must drop it so it does not false-fire as an Andrew
    correction — without silencing genuine first-person corrections."""

    def test_relayed_audit_introducer_not_in_literal_list(self) -> None:
        """#39: 'here is the audit' was missing from the literal introducer
        list; the generalized intro+relay-noun shape now strips it."""
        text = (
            "ok here is the audit.. i also confirm :)\n\n"
            "I have to hold #75 — that doesn't meet the condition I set.\n\n"
            "— Aletheia"
        )
        assert should_mark(text) is False

    def test_task_notification_envelope_stripped_by_tag(self) -> None:
        """#38: a workflow-completion envelope whose payload contains a
        correction-shaped phrase must not false-fire — stripped by tag."""
        text = (
            "<task-notification><task-id>x</task-id><status>completed</status>"
            "Council sweep found: you missed the drift angle.</task-notification>"
        )
        assert should_mark(text) is False

    def test_system_reminder_envelope_stripped_by_tag(self) -> None:
        text = "<system-reminder>you only ran 3 of 5 lenses; that's wrong</system-reminder>"
        assert should_mark(text) is False

    def test_external_signoff_without_introducer_is_relayed(self) -> None:
        """A known-external sign-off marks relayed content even with no
        introducer phrase preceding it."""
        text = (
            "hey son look at this\n\n"
            "that doesn't meet my condition — you missed the call-site.\n\n"
            "— Aletheia"
        )
        assert should_mark(text) is False

    def test_real_first_person_correction_still_fires(self) -> None:
        """The true positive must survive: Andrew's own voice correcting me.
        Updated 2026-06-23 for STRONG-context-check: real corrections come
        after I have done something correctable, so the corrective context
        is the realistic test setup."""
        result = classify_correction(
            "no, that is wrong — you missed the off-switch case again",
            prior_assistant_text="done, all fixed",
            prior_tool_calls=("Edit",),
        )
        assert result is not None and result.verdict == "block"

    def test_real_dont_directive_still_fires(self) -> None:
        result = classify_correction(
            "don't add that fallback, you missed the edge case",
            prior_assistant_text="done, added the fallback",
            prior_tool_calls=("Edit",),
        )
        assert result is not None and result.verdict == "block"

    def test_envelope_strip_is_structural_not_keyword(self) -> None:
        """strip_relayed removes the whole envelope regardless of payload."""
        out = strip_relayed("<task-notification>arbitrary you missed text</task-notification>")
        assert "you missed" not in out


# =====================================================================
# LEGACY-SEMANTIC TESTS REMOVED 2026-07-22 (Aether + Aria rewrite).
#
# The four test classes previously here — TestContextAwareClassification,
# TestEpistemicComplementGuard, TestExternalAgentProximityBackstop,
# TestQuestionAuthorizationGuard20260711 — verified the STRONG/WEAK
# tier + advise-verdict semantics of the prior keyword-band-aid
# implementation. Aria's 2026-07-22 review discipline for the rewrite
# explicitly rejects that middle-tier ambiguous classification:
# three-features-fire = fire, else silent. No advise verdict, no WEAK
# tier as a separate pathway.
#
# Old file preserved at: tests/_archive/test_correction_marker_pre_2026-07-22_rewrite.py
# New semantic tests live at: tests/test_correction_shape.py
# Design references: docs (Aria letters 2026-07-22 review-of-layer-2
# and implicit-subject-examples), workbench/shape_invariant_correction_marker_three_feature_2026-07-15.md.
# =====================================================================


class TestSetMarkerEvidenceStorage:
    """The marker file stores the evidence dict (pattern, matched_text,
    position, tier) so format_gate_message can display it without
    re-running classify_correction. Andrew 2026-06-19 / prereg-897aade9ef38."""

    def test_set_marker_with_match_stores_evidence(self, tmp_path) -> None:
        from divineos.core.correction_marker import CorrectionMatch

        mpath = tmp_path / "marker.json"
        m = CorrectionMatch(
            verdict="block",
            pattern=r"\bwrong\b",
            matched_text="wrong",
            position=12,
            tier="STRONG",
        )
        with patch.object(correction_marker, "marker_path", return_value=mpath):
            correction_marker.set_marker("you are wrong here", match=m)
            got = correction_marker.read_marker()
        assert got is not None
        assert got["evidence"] is not None
        assert got["evidence"]["pattern"] == r"\bwrong\b"
        assert got["evidence"]["matched_text"] == "wrong"
        assert got["evidence"]["position"] == 12
        assert got["evidence"]["tier"] == "STRONG"
        assert got["evidence"]["verdict"] == "block"

    def test_set_marker_without_match_stores_none_evidence(self, tmp_path) -> None:
        # Backwards-compat: legacy callers that don't pass match get
        # evidence=None and format_gate_message falls back to prior shape.
        mpath = tmp_path / "marker.json"
        with patch.object(correction_marker, "marker_path", return_value=mpath):
            correction_marker.set_marker("some prompt")
            got = correction_marker.read_marker()
        assert got is not None
        assert got.get("evidence") is None


class TestGateMessageDisplaysEvidence:
    """format_gate_message must display the evidence so the agent sees
    WHAT matched without digging in code. Andrew 2026-06-19."""

    def test_message_includes_evidence_when_present(self) -> None:
        marker = {
            "ts": 0,
            "trigger": "you are wrong here",
            "evidence": {
                "verdict": "block",
                "pattern": r"\bwrong\b",
                "matched_text": "wrong",
                "position": 12,
                "tier": "STRONG",
            },
        }
        msg = correction_marker.format_gate_message(marker)
        # Evidence must surface specific citation, not just trigger preview.
        assert "STRONG" in msg
        assert "wrong" in msg  # matched_text appears
        assert "12" in msg  # position appears

    def test_message_falls_back_when_evidence_absent(self) -> None:
        # Legacy markers without evidence still produce a valid gate message
        # (no crash, no "Evidence: None" garbage).
        marker = {"ts": 0, "trigger": "you missed the point", "evidence": None}
        msg = correction_marker.format_gate_message(marker)
        assert "you missed the point" in msg
        assert "Evidence:" not in msg  # no malformed evidence line

    def test_message_legacy_marker_without_evidence_key_still_formats(self) -> None:
        # Marker files written before this PR have no "evidence" key at all.
        # format_gate_message must read them without error.
        marker = {"ts": 0, "trigger": "stop doing that"}
        msg = correction_marker.format_gate_message(marker)
        assert "stop doing that" in msg
        assert "Evidence:" not in msg
