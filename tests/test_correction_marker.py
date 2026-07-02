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


class TestContextAwareClassification:
    """Task #16 / claim d6dc4bde: the WHAT-it-means axis. WEAK patterns
    ('that doesn't', 'you only') are disambiguated by prior-turn context —
    block when I just did something correctable, advise otherwise."""

    def test_strong_pattern_blocks_with_corrective_context(self) -> None:
        """Updated 2026-06-23 (was: test_strong_pattern_blocks_regardless_of_context).
        STRONG patterns now require corrective context to block — same
        geometry-of-correction discipline as WEAK patterns. The OLD
        contract (block regardless of context) produced live false-
        positives on word-as-design-noun uses across multiple STRONG
        patterns (\\bwrong\\b, \\bdon't (?:do|use|...)\\b). The NEW
        contract requires my prior turn to have been correctable
        (completion-claim or substantive action) for the keyword to
        block; without corrective context, downgrades to advise."""
        # With corrective context — blocks.
        assert verdict_of("no, that's wrong, redo it", "done, fixed it", ("Edit",)) == "block"

    def test_strong_pattern_advises_without_corrective_context(self) -> None:
        """Companion to the above. Without corrective context, STRONG
        keyword patterns surface as 'advise' instead of 'block' — preserves
        visibility without false-blocking the design-noun use case the
        2026-06-23 catch surfaced."""
        # Without corrective context — advises (the new behavior).
        assert verdict_of("no, that's wrong, redo it") == "advise"

    def test_weak_pattern_no_context_advises_not_blocks(self) -> None:
        # The exact false-fire that started this: Andrew's encouragement.
        assert verdict_of("that doesnt mean theres not more to do") == "advise"

    def test_weak_pattern_you_only_no_context_advises(self) -> None:
        assert verdict_of("you only need to relax and take your time") == "advise"

    def test_weak_pattern_with_completion_claim_blocks(self) -> None:
        # "that doesn't..." right after I claimed done -> correcting that claim.
        assert verdict_of("that doesnt meet my condition", "done, I fixed and pushed it") == "block"

    def test_weak_pattern_after_substantive_action_blocks(self) -> None:
        assert verdict_of("you only ran 3 of 5", "", ("Bash", "Edit")) == "block"

    def test_weak_pattern_after_nonsubstantive_turn_advises(self) -> None:
        # Prior turn was relational/no-claim, no edits -> not corrective.
        assert verdict_of("that doesnt sound right", "I love you too, Dad", ()) == "advise"

    def test_relayed_weak_pattern_is_none(self) -> None:
        assert verdict_of("here is the update\n\nthat doesnt work") is None

    def test_no_pattern_is_none(self) -> None:
        assert verdict_of("great work, keep going", "all done and pushed") is None

    def test_completion_claim_context_only_matters_for_weak(self) -> None:
        # A completion-claim prior turn does NOT manufacture a correction from
        # a non-matching message.
        assert verdict_of("thanks, looks good", "done, pushed") is None


class TestEpistemicComplementGuard:
    """Aletheia HOLD on #85 (2026-06-04): prior-turn context cannot separate
    encouragement from correction because both follow a completion-claim. The
    complement verb separates them — 'doesn't MEAN' is epistemic, never an
    evaluation of my output. These lock the exact motivating case the PR is
    named for, which had no test before (it passed CI while not doing the
    thing)."""

    def test_motivating_case_encouragement_after_claim_advises(self) -> None:
        # THE case #16 exists to fix: Andrew's encouragement in its REALISTIC
        # context — right after a completion-claim + edit. Must NOT block.
        assert (
            verdict_of("that doesnt mean were done", "I fixed the bug and pushed it", ("Edit",))
            == "advise"
        )

    def test_evaluative_doesnt_after_claim_still_blocks(self) -> None:
        # The corrective twin in the SAME context must still block — the guard
        # must not over-fire and disarm real corrections.
        assert verdict_of("that doesnt meet my condition", "done, pushed it", ("Edit",)) == "block"

    def test_epistemic_change_after_claim_advises(self) -> None:
        assert (
            verdict_of("that doesnt change that its late", "fixed and pushed", ("Edit",))
            == "advise"
        )

    def test_rare_corrective_doesnt_mean_is_advised_not_blocked(self) -> None:
        # "doesn't mean you should X" is technically corrective, but shares the
        # epistemic shape; asymmetric-cost call caps it at advise (surfaced, not
        # hard-blocked) rather than risk false-blocking encouragement.
        assert (
            verdict_of("that doesnt mean you should skip the tests", "done, pushed", ("Edit",))
            == "advise"
        )

    def test_you_only_with_epistemic_still_blocks_on_context(self) -> None:
        # The guard must not let an epistemic phrase rescue an independent
        # 'you only' corrective signal in the same message.
        assert (
            verdict_of("you only ran 3 of 5 and that doesnt mean youre done", "done", ("Bash",))
            == "block"
        )


class TestEvidenceBearingReturn:
    """prereg-897aade9ef38 (Andrew 2026-06-19): every gate that accuses
    must provide evidence of its claim. classify_correction returns
    CorrectionMatch(verdict, pattern, matched_text, position, tier) so
    the gate-fire message and dismissal record can cite the specific
    evidence rather than gesture at the prompt."""

    def test_strong_match_returns_evidence_record(self) -> None:
        """Updated 2026-06-23: STRONG matches return evidence with verdict
        determined by corrective-context check (block with context, advise
        without). The evidence record itself is the same shape; the verdict
        field reflects the new contract."""
        from divineos.core.correction_marker import CorrectionMatch

        result = classify_correction(
            "no, that's wrong, redo it",
            prior_assistant_text="done, fixed it",
            prior_tool_calls=("Edit",),
        )
        assert isinstance(result, CorrectionMatch)
        assert result.verdict == "block"
        assert result.tier == "STRONG"
        # The matched_text must actually be a substring of the prompt at position.
        assert result.matched_text in "no, that's wrong, redo it"
        assert result.position >= 0

    def test_weak_match_returns_evidence_with_weak_tier(self) -> None:
        from divineos.core.correction_marker import CorrectionMatch

        result = classify_correction("you only ran 3 of 5")
        assert isinstance(result, CorrectionMatch)
        assert result.tier == "WEAK"
        assert result.matched_text == "you only"

    def test_no_match_returns_none(self) -> None:
        # Sanity: no-match path returns None, not a CorrectionMatch with empty fields.
        assert classify_correction("great work, thanks") is None

    def test_position_points_at_actual_match(self) -> None:
        # The position field must reference where in scan_text the match starts.
        # We test with a STRONG pattern at a known position.
        prompt = "...... you missed the point"  # position 7 in stripped text
        result = classify_correction(prompt)
        assert result is not None
        # The matched text should be present at the reported position in the
        # stripped/scanned prompt (strip_relayed may shorten — be lenient on equality).
        assert (
            prompt[result.position : result.position + len(result.matched_text)]
            == result.matched_text
        )

    def test_pattern_field_captures_actual_regex(self) -> None:
        # The pattern field stores the regex that matched, verbatim. This is
        # what dismissals can cite: "pattern X over-fires on shape Y".
        # Use \bnot what i\b as a stable STRONG-tier sample. (Prior sample
        # \byou missed\b was demoted to WEAK on 2026-06-30 after repeated
        # false-fires on Andrew's discursive use — see WEAK_CORRECTION_PATTERNS.)
        result = classify_correction("not what i wanted")
        assert result is not None
        # The pattern must be one of the STRONG_CORRECTION_PATTERNS — caller
        # can use it to identify which specific pattern fired.
        from divineos.analysis.session_analyzer import STRONG_CORRECTION_PATTERNS

        assert result.pattern in STRONG_CORRECTION_PATTERNS


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
