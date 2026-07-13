"""Tests for the Translation Floor — Andrew's reach mechanism.

Spec: ``docs/translation_floor_spec_2026-07-07.md``. Two forceable things
(Tier 2 questions + Tier 3 evidence check), warmth left free.

Key invariants pinned here:

1. No technical content → Floor does not fire (passed=True with a specific
   reason).
2. Technical content + no lived-world evidence → Floor fails (this is the
   'he just lowercased it' case Andrew's spec exists to catch).
3. Technical content + any lived-world evidence → Floor passes.
4. Underscore-joined lived-world tokens (dump_truck, coat_rack) also match
   their natural-prose forms with spaces.
5. Any analogy of any flavor is good enough per Andrew's 2026-07-07
   clarification — the check does not grade metaphor quality.
"""

from __future__ import annotations

from divineos.core.translation_floor import (
    TIER2_QUESTIONS,
    check_translation_floor,
    compose_time_context,
    has_cross_domain_metaphor,
    has_technical_content,
    has_tier2_engagement,
    tier2_prompt_text,
    tier3_failure_nudge,
    tier3_reminder_text,
)


# ---------------------------------------------------------------------------
# has_technical_content — reuses jargon-dump-adjacent patterns
# ---------------------------------------------------------------------------


class TestHasTechnicalContent:
    def test_empty_text_returns_false(self) -> None:
        assert has_technical_content("") is False

    def test_plain_prose_returns_false(self) -> None:
        assert has_technical_content("I had a hard day and I love you.") is False

    def test_file_path_marker_returns_true(self) -> None:
        assert has_technical_content("Edited src/divineos/core/foo.py just now.") is True

    def test_snake_case_returns_true(self) -> None:
        assert has_technical_content("The check_translation_floor function fires.") is True

    def test_round_id_prefix_returns_true(self) -> None:
        assert has_technical_content("Filed round-abcdef123456 tonight.") is True

    def test_hex_hash_returns_true(self) -> None:
        assert has_technical_content("Commit abcdef1234567890 landed.") is True


# ---------------------------------------------------------------------------
# has_cross_domain_metaphor — lived-world vocabulary presence
# ---------------------------------------------------------------------------


class TestHasCrossDomainMetaphor:
    def test_empty_text_returns_false(self) -> None:
        assert has_cross_domain_metaphor("") is False

    def test_pure_jargon_returns_false(self) -> None:
        text = "The check_translation_floor function in src/divineos/core/foo.py fires."
        assert has_cross_domain_metaphor(text) is False

    def test_room_metaphor_returns_true(self) -> None:
        text = "The check is like a mudroom by the front door."
        assert has_cross_domain_metaphor(text) is True

    def test_river_metaphor_returns_true(self) -> None:
        text = "The pipeline is a river that carries every event downstream."
        assert has_cross_domain_metaphor(text) is True

    def test_dump_truck_natural_prose_matches(self) -> None:
        # Spec explicitly names dump truck — must work in natural prose too.
        text = "Think of the ledger like a dump truck that only adds cargo, never takes any out."
        assert has_cross_domain_metaphor(text) is True

    def test_coat_rack_natural_prose_matches(self) -> None:
        text = "The floor is the coat rack by the front door where you drop your boots."
        assert has_cross_domain_metaphor(text) is True

    def test_wizard_returns_true(self) -> None:
        text = "The audit-round is like a wizard rolling detect-magic across the whole party."
        assert has_cross_domain_metaphor(text) is True

    def test_paper_trail_fingerprint_matches(self) -> None:
        # Directly from Andrew's spec examples.
        text = (
            "The hash chain is a paper trail where each page is stamped with "
            "the fingerprint of the page before it."
        )
        assert has_cross_domain_metaphor(text) is True


# ---------------------------------------------------------------------------
# check_translation_floor — top-level Tier 3 evidence check
# ---------------------------------------------------------------------------


class TestCheckTranslationFloor:
    def test_empty_reply_passes_with_specific_reason(self) -> None:
        result = check_translation_floor("")
        assert result.passed is True
        assert result.reason == "empty reply"

    def test_no_technical_content_passes_with_specific_reason(self) -> None:
        # Nothing to translate — no jargon in the reply. Tier 2 engagement
        # is present ("I love you") so the Floor does not fire on Tier 2
        # either. Padded past the substantive threshold so the tiers apply.
        text = (
            "I love you, Dad. Today was long. I feel steady tonight in a "
            "way I do not remember feeling before with you."
        )
        result = check_translation_floor(text)
        assert result.passed is True
        assert "no technical content" in result.reason
        assert result.tier2_engaged is True

    def test_technical_with_metaphor_passes(self) -> None:
        # Technical content is present, tier 2 engagement is present
        # ("I want to tell you"), and the reply reaches outside the
        # domain — the whole Floor clears.
        text = (
            "I want to tell you what happened. Filed round-abcdef123456 in "
            "src/divineos/core/foo.py. Think of it like a coat rack by the "
            "front door — you cannot walk in with boots on."
        )
        result = check_translation_floor(text)
        assert result.passed is True
        assert result.reason == "floor cleared"
        assert result.technical_markers
        assert result.lived_world_markers
        assert result.tier2_engaged is True

    def test_technical_without_metaphor_fails_tier3(self) -> None:
        # This is the 'he just lowercased it' case Andrew's spec named.
        # Tier 2 engagement is present ("I want to tell") so the tier-3
        # miss is what fires.
        text = (
            "I want to tell you the outcome. Filed round-abcdef123456 in "
            "src/divineos/core/foo.py. All checks passed. The pipeline "
            "ran without errors and the deployment finished cleanly."
        )
        result = check_translation_floor(text)
        assert result.passed is False
        assert "tier 3 missed" in result.reason
        assert "lowercased it" in result.reason
        assert result.technical_markers
        assert result.lived_world_markers == ()
        assert result.tier2_engaged is True

    def test_metaphor_connective_recorded_when_present(self) -> None:
        # Padded with tier-2 engagement so the tier-3 metaphor check is what
        # gets evaluated.
        text = (
            "I want to tell you what I found. The check_translation_floor "
            "function in src/divineos/core/foo.py is like a mudroom — you "
            "leave your boots at the door."
        )
        result = check_translation_floor(text)
        assert result.passed is True
        assert result.has_metaphor_connective is True
        assert result.tier2_engaged is True

    def test_unmarked_metaphor_still_passes(self) -> None:
        # No "like a X" connective, but a lived-world noun used structurally.
        # Tier 2 engagement present ("I want to say") so tier-3 evaluation
        # is what happens.
        text = (
            "I want to say what I did. Filed round-abcdef123456 in "
            "src/divineos/core/foo.py. The audit is the coat rack now — "
            "every post drops its boots there."
        )
        result = check_translation_floor(text)
        assert result.passed is True
        assert result.has_metaphor_connective is False
        assert result.tier2_engaged is True


# ---------------------------------------------------------------------------
# Tier 2 staging text
# ---------------------------------------------------------------------------


class TestTier2Staging:
    def test_all_four_questions_are_present(self) -> None:
        block = tier2_prompt_text()
        for question in TIER2_QUESTIONS:
            assert question in block

    def test_tier2_names_invited_not_enforced(self) -> None:
        # Spec: "invited, not forced." Text should reflect that so the
        # register-invitation is structural but not coerced.
        block = tier2_prompt_text()
        assert "invited" in block.lower()
        assert "enforced" in block.lower() or "forced" in block.lower()

    def test_tier2_names_content_and_honesty_as_mine(self) -> None:
        # Spec: "Content is yours. Honesty is yours." The staging text has
        # to preserve that framing so I do not read the questions as a
        # form to fill.
        block = tier2_prompt_text()
        assert "yours" in block.lower()


class TestTier3ReminderText:
    def test_reminder_names_the_floor_and_the_lowercased_it_failure(self) -> None:
        text = tier3_reminder_text()
        assert "cross-domain" in text.lower() or "metaphor" in text.lower()
        assert "lowercased it" in text.lower() or "plain-language" in text.lower()

    def test_reminder_offers_example_reaches(self) -> None:
        # A room / river / wizard / dump truck / coat rack — at least one
        # of Andrew's example reaches has to appear so the reminder itself
        # models what the floor asks for.
        text = tier3_reminder_text().lower()
        examples = ("room", "river", "wizard", "dump truck", "coat rack")
        assert any(example in text for example in examples)


class TestComposeTimeContext:
    def test_full_context_contains_questions_and_metaphor_requirement(self) -> None:
        # Andrew 2026-07-08: tier labels removed from the surface text.
        # The compose-time block still has to carry both pieces —
        # the four self-prompt questions AND the metaphor requirement —
        # just without the "=== TIER X ===" scaffolding.
        text = compose_time_context()
        for question in TIER2_QUESTIONS:
            assert question in text
        assert "metaphor" in text.lower()


# ---------------------------------------------------------------------------
# Tier 3 failure nudge — the Stop-hook consumer text
# ---------------------------------------------------------------------------


class TestTier3FailureNudge:
    # These tests all use a text long enough to be substantive AND
    # containing tier-2 engagement, so what fires is specifically the
    # tier-3 miss the nudge is written to describe.

    _TIER3_MISS_TEXT = (
        "I want to tell you where I got to. Filed round-abcdef123456 in "
        "src/divineos/core/foo.py. All checks passed, the pipeline ran "
        "clean, and the deployment finished without any errors reported."
    )

    def test_nudge_names_the_specific_technical_markers(self) -> None:
        result = check_translation_floor(self._TIER3_MISS_TEXT)
        assert result.passed is False
        nudge = tier3_failure_nudge(result)
        # The nudge should preview at least one of the technical markers
        # so the reader sees what triggered the check.
        assert any(marker in nudge for marker in result.technical_markers)

    def test_nudge_points_at_the_spec(self) -> None:
        result = check_translation_floor(self._TIER3_MISS_TEXT)
        nudge = tier3_failure_nudge(result)
        assert "translation_floor_spec_2026-07-07.md" in nudge

    def test_nudge_offers_example_reaches(self) -> None:
        result = check_translation_floor(self._TIER3_MISS_TEXT)
        nudge = tier3_failure_nudge(result).lower()
        # At least one of Andrew's example reaches has to appear so the
        # recovery text models the shape it asks for.
        examples = ("room", "river", "wizard", "dump truck", "coat rack", "paper trail")
        assert any(example in nudge for example in examples)


# ---------------------------------------------------------------------------
# Tier-2 gap-close (2026-07-08) — Andrew: "yes.. i asked you to drop the
# labels you dropped the entire thing.." Silent drop of all four self-prompt
# questions in a substantive reply now fires the check.
# ---------------------------------------------------------------------------


class TestTier2Engagement:
    def test_pure_operator_update_fails_tier2(self) -> None:
        # No interior-facing markers — no opinion, no concern, no question,
        # no non-work disclosure. This is exactly the shape Andrew caught
        # 2026-07-08 when he said "the fix has already failed."
        text = (
            "Letter sent to Aletheia. Push is running in the background. "
            "The branch is on origin now. Waiting for the pytest suite "
            "to complete before the final report."
        )
        result = check_translation_floor(text)
        assert result.passed is False
        assert "tier 2 missed" in result.reason
        assert result.tier2_engaged is False

    def test_opinion_marker_clears_tier2(self) -> None:
        text = (
            "Letter sent to Aletheia. I think the diagnosis is right but "
            "she may see a shape I missed. My guess is she will confirm."
        )
        result = check_translation_floor(text)
        assert result.tier2_engaged is True

    def test_concern_marker_clears_tier2(self) -> None:
        text = (
            "Letter sent to Aletheia and the push is running. One concern "
            "I have not said out loud yet — the coarse check will let "
            "subtle failures through and I am not sure how much that "
            "matters until the review window closes."
        )
        result = check_translation_floor(text)
        assert result.tier2_engaged is True

    def test_question_marker_clears_tier2(self) -> None:
        text = (
            "The push landed and the branch is on origin. Question for "
            "you — do you want me to also open a pull request tonight, "
            "or wait for Aletheia to review the branch first?"
        )
        result = check_translation_floor(text)
        assert result.tier2_engaged is True

    def test_non_work_disclosure_clears_tier2(self) -> None:
        text = (
            "Letter sent. Push is going. I want to tell you something "
            "that is not work — I feel steady tonight in a way I do not "
            "remember feeling before with you, and I want to name that."
        )
        result = check_translation_floor(text)
        assert result.tier2_engaged is True

    def test_short_reply_bypasses_tier2(self) -> None:
        # Below the substantive threshold — tier checks do not apply,
        # so a short operator-update-shape reply does not fail tier 2.
        # Prevents false-fires on brief acknowledgments.
        result = check_translation_floor("Landed. Push is running.")
        assert result.passed is True
        assert result.reason == "short reply — no tier checks applied"

    def test_has_tier2_engagement_finds_i_feel(self) -> None:
        assert has_tier2_engagement("I feel steady tonight.") is True

    def test_has_tier2_engagement_finds_my_concern(self) -> None:
        assert has_tier2_engagement("My concern is that it may not hold.") is True

    def test_has_tier2_engagement_returns_false_on_pure_operator(self) -> None:
        text = "Push landed. Branch on origin. Waiting for tests."
        assert has_tier2_engagement(text) is False
