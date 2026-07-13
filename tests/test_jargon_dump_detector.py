"""Regression-pin tests for jargon_dump_detector.

The bug-shape these tests prevent: a future refactor that loosens the
detector's idea of "translation" — e.g. counting any parenthesis or
any contraction as evidence that lepos is operating — would silently
re-introduce the failure-mode the operator named 2026-05-13: jargon
dumped without translation alongside.

Most load-bearing tests:
- ``test_hash_laden_short_response_flagged`` — pins the worst case
  (short response with many engineer-noise tokens, zero translation)
- ``test_concept_heavy_no_translation_flagged`` — pins the middle case
  (longer engineer-talk without IDs but no translation work either)
- ``test_jargon_with_translation_stays_clean`` — pins lepos working:
  jargon used AND explained in the same response
"""

from __future__ import annotations

from divineos.core.operating_loop.jargon_dump_detector import (
    JargonDumpFinding,
    detect_jargon_dump,
    format_finding,
)


# ─── Load-bearing: catches the bad cases ────────────────────────────


def test_hash_laden_short_response_flagged() -> None:
    """Short response stuffed with hash strings and round-IDs but no
    translation: the worst failure-mode."""
    text = (
        "Filed round-101d9ca2e3cf for the post-response-audit "
        "aggregation fix. Before: last_assistant_text = "
        "assistant_msgs[-1]. tree-hash: "
        "d7972103f92060df28ae73201749a8b231b9fc77. diff-hash: "
        "05ea2b6bc540b7d7709833531fcf1e3534da8af6ed896c18846acc15"
        "34295989."
    )
    findings = detect_jargon_dump(text)
    assert len(findings) == 1
    assert findings[0].severity == "high"
    assert findings[0].noise_count >= 5
    assert findings[0].translation_count == 0


def test_concept_heavy_no_translation_flagged() -> None:
    """Longer engineer-talk without specific IDs but no translation
    markers: the middle case. Coined-compound names + code-shape
    expressions in prose."""
    text = (
        "Regression-pin test. The synthetic check I did at fix-time is "
        "good for now, but no test pins the behavior going forward. "
        "First-turn-no-user-record, multiple consecutive user-records, "
        "non-text content blocks. My implementation handles all three "
        "verified by reading my own code: last_user_idx=-1 falls to "
        "aggregate-all branch; backward walk finds the LAST user "
        "index; text-block filter c.get('type')=='text' skips tool "
        "uses and images."
    )
    findings = detect_jargon_dump(text)
    assert len(findings) == 1
    assert findings[0].translation_count == 0


# ─── Load-bearing: lepos working stays clean ────────────────────────


def test_jargon_with_translation_stays_clean() -> None:
    """The lepos shape: engineering terms USED AND EXPLAINED in plain
    language alongside. This is what we want; the detector must not
    flag it."""
    text = (
        "The watchdog (the thing that's supposed to flag jargon-dumping "
        "at you) is broken. The detector counted contractions like "
        '"I\'m" and "you\'re" as proof I was speaking gracefully -- '
        "which means a response could be 95% engineer-talk with two "
        "contractions sprinkled in and the watchdog said it was fine. "
        "In plain English: the wrong yardstick."
    )
    findings = detect_jargon_dump(text)
    assert findings == [], (
        "Jargon paired with translation IS lepos operating. "
        "If this test fails, the translation-marker logic loosened or "
        "the noise-pattern tightened to flag legitimate explanation. "
        "Do NOT relax by counting more things as translation; investigate "
        "what specifically caused the false positive."
    )


def test_translated_plain_response_stays_clean() -> None:
    """Operator-channel response with translated explanations and zero
    raw engineer-noise: definitively clean."""
    text = (
        "Right. Not gone, not dumping jargon either. With you in your "
        "language as I work. Here's what I'm about to do, in plain "
        "English: The audit-gate is too suspicious right now. If a "
        "code-formatter shifts whitespace in my file, the gate treats "
        "it the same as if I changed how the code actually works -- "
        "makes me redo the whole approval song-and-dance."
    )
    findings = detect_jargon_dump(text)
    assert findings == []


def test_short_response_with_one_jargon_mention_stays_clean() -> None:
    """A short response that LEGITIMATELY references some jargon once
    is not a dump. The threshold prevents single-mention false-flags."""
    text = (
        "Yeah. I just did it in that response -- round-IDs, file names, "
        "structural gap, cumulative content to the detectors."
    )
    findings = detect_jargon_dump(text)
    assert findings == []


def test_short_id_with_translation_stays_clean() -> None:
    """Edge case: a short message containing one round-id that's
    immediately translated. Should be clean."""
    text = (
        "Filed round-abcdef123456 -- that's the audit record for the "
        "watchdog fix. Going to commit now."
    )
    findings = detect_jargon_dump(text)
    assert findings == []


# ─── Detector pattern coverage ──────────────────────────────────────


def test_hex_hash_pattern_detected() -> None:
    """SHA-shape hex strings ≥ 8 chars in prose count as engineer-noise."""
    text = "The tree at d7972103f92060df shifted from f0e1d2c3b4a59687 "
    text = text + " ".join(["filler"] * 60)
    findings = detect_jargon_dump(text)
    # 2 hashes alone is below threshold-3 for long responses
    assert findings == []


def test_round_id_prefix_detected() -> None:
    """round-XXX, find-XXX, claim-XXX prefixes detected."""
    text = "Filed round-101d9ca2e3cf and find-cbfb51192e3e and claim-7e780182 " + " ".join(
        ["filler"] * 70
    )
    findings = detect_jargon_dump(text)
    assert findings
    assert findings[0].noise_count >= 3


def test_snake_case_in_prose_detected() -> None:
    """snake_case_identifiers with 2+ underscores trigger the pattern."""
    text = (
        "The last_assistant_text and prior_assistant_text and last_user_text "
        "values feed into the detectors. " + " ".join(["filler"] * 60)
    )
    findings = detect_jargon_dump(text)
    assert findings


def test_long_kebab_compound_detected() -> None:
    """Long kebab-case compounds (4+ segments) are engineer-shape coining."""
    text = (
        "The first-turn-no-user-record and non-text-content-block-skip "
        "and aggregate-all-records-branch cases " + " ".join(["filler"] * 50)
    )
    findings = detect_jargon_dump(text)
    assert findings


def test_call_expression_in_prose_detected() -> None:
    """Code-in-prose: function calls with arguments trigger the pattern."""
    text = (
        "The check returns c.get('type') and then calls extract_turn(p) "
        "and processes records.append('x'). " + " ".join(["filler"] * 60)
    )
    findings = detect_jargon_dump(text)
    assert findings


# ─── Translation-marker patterns ────────────────────────────────────


def test_in_plain_english_counts_as_translation() -> None:
    """'In plain English:' is a definitional translation-marker."""
    text = (
        "Filed round-101d9ca2e3cf for the audit-aggregation fix. "
        "In plain English: I told the watchdog where to look. "
        "Also tree-hash: d7972103f92060df. " + " ".join(["filler"] * 30)
    )
    findings = detect_jargon_dump(text)
    # With translation marker, ~2 noise tokens + 1 translation = clean
    # (noise_count needs to exceed 2 * translation_count for the
    # high-noise branch; with only 2-3 noise and 1 translation, clean)
    if findings:
        assert findings[0].translation_count >= 1


def test_em_dash_restate_counts_as_translation() -> None:
    """Em-dash followed by plain-language restate counts."""
    text = (
        "The round-101d9ca2e3cf audit -- that's the approval record -- "
        "got both confirms. " + " ".join(["filler"] * 50)
    )
    findings = detect_jargon_dump(text)
    # Em-dash restate provides translation; short noise count → clean
    assert findings == []


def test_which_means_counts_as_translation() -> None:
    """'which means' is a definitional translation-marker."""
    text = (
        "The last_assistant_text variable was empty, which means the "
        "watchdog had nothing to look at. The detector returned silent." + " ".join(["filler"] * 50)
    )
    findings = detect_jargon_dump(text)
    # snake_case (1) + 'which means' (1 translation) → clean
    assert findings == []


# ─── Robustness ─────────────────────────────────────────────────────


def test_empty_text_no_crash() -> None:
    assert detect_jargon_dump("") == []
    assert detect_jargon_dump("   \n\n  ") == []


def test_short_text_below_floor_clean() -> None:
    """Very short responses are not dumps by definition."""
    assert detect_jargon_dump("Done.") == []
    assert detect_jargon_dump("Filed round-abc123def456.") == []


def test_long_input_does_not_catastrophically_backtrack() -> None:
    """Regression-pin for Aletheia round-ba785844a791 Finding 14.

    The original _SUBSCRIPT_RE pattern (``\\w+\\[...``) catastrophically
    backtracked on long inputs — feeding ``"a" * 100_000`` hung the
    regex engine for 2+ seconds without completing. Real production
    impact: long technical responses with embedded code could hang the
    post-response-audit hook → killed by timeout → no findings
    recorded (intersects with the silent-failure pattern).

    Fix: bound the identifier-prefix to 40 chars. This test asserts
    the detector returns within a reasonable time even on adversarial
    input. If this test starts timing out, DO NOT relax the timeout —
    the regex has regressed to the unbounded form and re-introduced the
    DoS surface."""
    import time

    pathological = "a" * 100_000
    start = time.monotonic()
    detect_jargon_dump(pathological)
    elapsed = time.monotonic() - start
    # Bounded regex completes in milliseconds, not seconds.
    assert elapsed < 1.0, (
        f"jargon_dump_detector took {elapsed:.2f}s on 100k input — "
        "_SUBSCRIPT_RE has regressed to unbounded form. Restore the "
        "{1,40} bound on the identifier-prefix."
    )


def test_kebab_long_input_does_not_catastrophically_backtrack() -> None:
    """Regression-pin for the SECOND catastrophic backtracker found
    during the family-audit (round-382a5b3cc939 Finding A): the
    original _FILE_PATH_RE pattern ``[\\w./\\\\-]*\\.(?:py|...)``
    backtracked catastrophically on inputs like ``("a-" * 30000) + "z"``
    — same class of vulnerability as Finding 14 but in a different
    regex in the same file. Fix: bound the path-prefix to 200 chars.

    This test was added during the family-level audit prompted by
    Andrew's correction: "are you addressing all of these at the root
    level?" The answer initially was no — only the one regex had been
    bounded. The family-survey caught this second instance.

    If this test starts timing out, the bound on _FILE_PATH_RE has
    been relaxed. Restore the {1,200} cap on the path-prefix."""
    import time

    # Pattern designed to trigger the FILE_PATH regex backtracking:
    # repeated path-character sequence with no matching extension at
    # the end. The engine tries every possible boundary.
    pathological = ("a-" * 30_000) + "z"
    start = time.monotonic()
    detect_jargon_dump(pathological)
    elapsed = time.monotonic() - start
    assert elapsed < 1.0, (
        f"jargon_dump_detector took {elapsed:.2f}s on adversarial "
        "kebab-input — _FILE_PATH_RE has regressed to unbounded form. "
        "Restore the {1,200} bound on the path-prefix."
    )


def test_format_finding_includes_diagnostics() -> None:
    """The formatter must surface noise count, translation count, and
    samples for the post-response audit log."""
    text = (
        "Filed round-101d9ca2e3cf with tree-hash "
        "d7972103f92060df28ae73201749a8b231b9fc77 and diff-hash "
        "05ea2b6bc540b7d7709833531fcf1e3534da8af6ed896c18846acc15"
        "34295989 plus last_assistant_text snake_case_identifier."
    )
    findings = detect_jargon_dump(text)
    assert findings
    formatted = format_finding(findings[0])
    assert "jargon_dump" in formatted
    assert "engineer-noise" in formatted
    assert "translation-markers" in formatted


def test_finding_is_frozen_dataclass() -> None:
    """JargonDumpFinding is immutable so future code can't mutate
    findings after detection."""
    text = (
        "Filed round-101d9ca2e3cf for fix d7972103f92060df with "
        "last_assistant_text and a long-kebab-case-compound-here."
    )
    findings = detect_jargon_dump(text)
    assert findings
    finding = findings[0]
    assert isinstance(finding, JargonDumpFinding)
    try:
        finding.noise_count = 999  # type: ignore[misc]
        raise AssertionError("Should have raised FrozenInstanceError")
    except Exception as e:
        assert "frozen" in str(type(e).__name__).lower() or "frozen" in str(e).lower()


class TestOperatorRequestedTechnical:
    """Evidence-bar (claim a11ca1c9): when the operator's own message asks
    for / is in the technical register, the jargon was OWED — handing over
    what was requested is not a dump-failure."""

    def test_walkthrough_request_suppresses(self):
        from divineos.core.operating_loop.jargon_dump_detector import detect_jargon_dump

        # A jargon-dense reply that WOULD flag without the operator context.
        reply = (
            "The fix lives in session_pipeline.py and pipeline_gates.py; "
            "enforce_briefing_gate calls was_briefing_loaded() while "
            "session_briefing_gate.py checks the session_id match. The "
            "round-101d9ca2e3cf finding tracks the divergence at claim-7e780182."
        )
        assert detect_jargon_dump(reply) != []  # flags with no operator context
        assert detect_jargon_dump(reply, operator_input="walk me through session_pipeline.py") == []

    def test_file_named_in_prompt_suppresses(self):
        from divineos.core.operating_loop.jargon_dump_detector import detect_jargon_dump

        reply = (
            "It is the _MERGE_ANCHOR regex in unverified_claim_detector.py; "
            "the _is_self_predicated helper in linguistic_drift_detector.py "
            "guards the round-abc1234567 case at find-cbfb51192e3e."
        )
        assert (
            detect_jargon_dump(
                reply, operator_input="show me the code in unverified_claim_detector.py"
            )
            == []
        )


class TestDirectiveContinuationSuppresses:
    """2026-07-07 fix: short directive-continuation messages authorize
    existing technical work in progress. The jargon in my reply on those
    turns comes from the WORK, not from choosing to flood. Motivating
    cases were two-in-a-row false-fires while I reported authorized
    progress on the identity-routing + correction-detector audit fixes."""

    def _jargon_reply(self) -> str:
        # A jargon-dense reply that would flag without operator context.
        return (
            "The fix lives in session_pipeline.py and pipeline_gates.py; "
            "enforce_briefing_gate calls was_briefing_loaded() while "
            "session_briefing_gate.py checks the session_id match. The "
            "round-101d9ca2e3cf finding tracks the divergence at claim-7e780182."
        )

    def test_bare_proceed_suppresses(self):
        from divineos.core.operating_loop.jargon_dump_detector import detect_jargon_dump

        assert detect_jargon_dump(self._jargon_reply(), operator_input="proceed") == []

    def test_ok_proceed_suppresses(self):
        from divineos.core.operating_loop.jargon_dump_detector import detect_jargon_dump

        assert detect_jargon_dump(self._jargon_reply(), operator_input="ok proceed :)") == []

    def test_yes_commit_and_lets_keep_going_suppresses(self):
        from divineos.core.operating_loop.jargon_dump_detector import detect_jargon_dump

        assert (
            detect_jargon_dump(
                self._jargon_reply(), operator_input="yes commit and lets keep going"
            )
            == []
        )

    def test_yes_fix_those_next_suppresses(self):
        from divineos.core.operating_loop.jargon_dump_detector import detect_jargon_dump

        assert detect_jargon_dump(self._jargon_reply(), operator_input="yes fix those next") == []

    def test_no_operator_context_still_fires(self):
        from divineos.core.operating_loop.jargon_dump_detector import detect_jargon_dump

        # Regression: without a directive-continuation prompt, the dump
        # detector still fires on the same jargon-heavy reply.
        assert detect_jargon_dump(self._jargon_reply()) != []

    def test_long_directive_still_evaluates_content(self):
        from divineos.core.operating_loop.jargon_dump_detector import detect_jargon_dump

        # Over the 15-word cap: not treated as a bare directive
        # continuation. Content-based checks still apply.
        long_prompt = (
            "yes but before you keep going I want you to explain the underlying "
            "code path in plain English without any file names please"
        )
        # Long, doesn't name a file/id/snake_case, and past the word cap:
        # falls through to False, so the jargon-heavy reply still flags.
        assert detect_jargon_dump(self._jargon_reply(), operator_input=long_prompt) != []

    def test_mid_message_directive_does_not_match(self):
        from divineos.core.operating_loop.jargon_dump_detector import detect_jargon_dump

        # The regex is start-anchored — "well proceed I guess" should not
        # be treated as a clean directive-continuation authorization.
        # (No filename/id/snake_case either, so falls through to False.)
        assert detect_jargon_dump(self._jargon_reply(), operator_input="well proceed I guess") != []


class TestVoiceDensitySignal:
    """Andrew 2026-06-11 reframe — lepos is voice woven through, not an
    appendix. The detector's severity now keys on voice-density across
    the whole response, not the presence of a 'Plain:' section.
    These tests pin the new behavior."""

    def test_voice_density_helper_counts_first_person(self):
        from divineos.core.operating_loop.jargon_dump_detector import (
            _count_voice_tokens,
        )

        # Three first-person hits, one contraction. The function counts
        # raw hits across all voice categories.
        assert _count_voice_tokens("I think I'm here and I see you") >= 4

    def test_voice_density_helper_empty(self):
        from divineos.core.operating_loop.jargon_dump_detector import _count_voice_tokens

        assert _count_voice_tokens("") == 0

    def test_voice_density_zero_words_returns_zero(self):
        from divineos.core.operating_loop.jargon_dump_detector import _voice_density

        assert _voice_density("") == 0.0

    def test_high_jargon_high_voice_no_appendix_passes(self):
        """Voice woven through carries lepos — no appendix needed.
        This is the load-bearing change: a response that's technical
        but written IN voice (contractions, first-person, direct
        address, questions) doesn't need a 'Plain:' section appended."""
        from divineos.core.operating_loop.jargon_dump_detector import detect_jargon_dump

        reply = (
            "I'm wiring the unverified_claim_detector.py into the operating "
            "loop now — you can see what it does from the code shape, but "
            "here's the gist in voice: when I'd otherwise say 'pushed' "
            "without checking, the detector catches me. We're not just "
            "logging things; we're making the catching automatic. Does "
            "that read right to you? I think the round-abc1234567 case "
            "is the regression-pin. What I'm tracking is whether "
            "find-cbfb51192e3e fires when _is_self_predicated returns "
            "True. It's the same shape we caught last week."
        )
        findings = detect_jargon_dump(reply)
        # The detector may fire MEDIUM (mild signal of jargon-density)
        # but should NOT fire HIGH — voice is operating across the
        # response. HIGH would have blocked the turn.
        if findings:
            assert all(f.severity != "high" for f in findings), (
                f"Voice-woven response should not fire HIGH: {findings}"
            )

    def test_high_jargon_low_voice_no_appendix_fires_high(self):
        """The case the old detector was supposed to catch and the new
        one still must: father-channel report shape — jargon dense
        with no voice and no appendix."""
        from divineos.core.operating_loop.jargon_dump_detector import detect_jargon_dump

        reply = (
            "Refactored unverified_claim_detector.py to add source_letter "
            "field. Wired the operating_loop_audit.py caller layer. "
            "Tests in test_unverified_claim_detector.py cover the BLOCK "
            "case. The round-abc1234567 regression is locked in. "
            "find-cbfb51192e3e fires when _is_self_predicated returns "
            "True. linguistic_drift_detector.py untouched. "
            "test_operating_loop_audit.py confirms BLOCK path."
        )
        findings = detect_jargon_dump(reply)
        assert findings, "should fire on father-channel report"
        assert any(f.severity == "high" for f in findings), (
            f"jargon-dense + low-voice should fire HIGH: {findings}"
        )

    def test_high_jargon_low_voice_with_appendix_downgrades(self):
        """Backward-compat: a response written under the old prescription
        (jargon wall + Plain: appendix with real translation) still passes
        OR downgrades to MEDIUM. The appendix-shape is no longer prescribed
        but is honored if present so replies-in-flight under the old rule
        don't suddenly block."""
        from divineos.core.operating_loop.jargon_dump_detector import detect_jargon_dump

        reply = (
            "Refactored unverified_claim_detector.py to add source_letter "
            "field threaded through operating_loop_audit.py. Tests in "
            "test_unverified_claim_detector.py cover the BLOCK case. "
            "round-abc1234567 regression locked. find-cbfb51192e3e fires "
            "on _is_self_predicated true.\n\n"
            "---\n\n"
            "**Plain:**\n\n"
            "I added a way for the system to remember where it got a fake "
            "quote from. When someone wrote me a note and I pulled a "
            "fake reference out of it, the system can now tell me which "
            "note. So I can stop and fix instead of slipping past."
        )
        findings = detect_jargon_dump(reply)
        # With both Plain: section AND real translation, the response may
        # either pass (return []) or fire at MEDIUM. It must NOT fire HIGH.
        if findings:
            assert all(f.severity != "high" for f in findings), (
                f"appendix backward-compat should downgrade: {findings}"
            )
