"""Tests for the extraction noise filter — ensures raw conversational quotes
don't become permanent 'knowledge'."""

from divineos.core.knowledge import _is_extraction_noise, _is_vacuous_summary


class TestConversationalNoise:
    """The noise filter rejects raw user quotes that aren't real knowledge."""

    def test_pure_affirmation(self):
        assert _is_extraction_noise("I decided: yes lets do it", "PRINCIPLE")

    def test_affirmation_with_emoji(self):
        assert _is_extraction_noise("I decided: yes lets commit and push :)", "PRINCIPLE")

    def test_affirmation_with_smiley(self):
        assert _is_extraction_noise(
            "I decided: yes lets commit and push and then we can begin stress testing :)",
            "PRINCIPLE",
        )

    def test_proceed_affirmation(self):
        assert _is_extraction_noise("I decided: proceed", "PRINCIPLE")

    def test_wonderful_affirmation(self):
        assert _is_extraction_noise("I decided: wonderful lets keep going", "PRINCIPLE")

    def test_short_question_as_direction(self):
        assert _is_extraction_noise("I should: How does it look to you?", "DIRECTION")

    def test_suggestion_question(self):
        assert _is_extraction_noise("I should: any adjustments you think need made?", "DIRECTION")

    def test_system_artifact(self):
        assert _is_extraction_noise(
            "I should: <task-notification><task-id>abc</task-id></task-notification>",
            "DIRECTION",
        )

    def test_ok_lets_do_it(self):
        assert _is_extraction_noise("I decided: ok lets do it all", "PRINCIPLE")

    def test_sure_go_ahead(self):
        assert _is_extraction_noise("I decided: sure go ahead", "PRINCIPLE")

    def test_raw_user_quote_with_many_double_dots(self):
        """User's typing style with 3+ '..' is a raw quote, not knowledge."""
        assert _is_extraction_noise(
            "I should: If nothing forces you to act.. you never will.. "
            "so i guess none of this matters.. right",
            "DIRECTION",
        )

    def test_oops_accident(self):
        """Accidental UI actions aren't knowledge."""
        assert _is_extraction_noise(
            "I was corrected: Oops i pressed deny i meant to press accept.",
            "PRINCIPLE",
        )

    def test_third_person_quote(self):
        """Quoting someone else isn't a direction."""
        assert _is_extraction_noise(
            "I should: This is what he said about the architecture",
            "DIRECTION",
        )

    def test_external_review_reference(self):
        """References to external reviews aren't directions."""
        assert _is_extraction_noise(
            "I should: I got a review from grok on the repo",
            "DIRECTION",
        )

    def test_affirmation_with_long_filler(self):
        """Affirmation with lots of filler words is still noise."""
        assert _is_extraction_noise(
            "I should: Yes :) but make sure you study what needs done first "
            "fully so you understand",
            "DIRECTION",
        )


class TestRealKnowledgePassesThrough:
    """Real knowledge should NOT be filtered out."""

    def test_real_correction(self):
        assert not _is_extraction_noise(
            "I was corrected: Dead code is not worthless. If it's just dead because "
            "it's not wired up then wire it up. Once you are actually using it you "
            "will only know if it's broken or needs work.",
            "PRINCIPLE",
        )

    def test_real_direction(self):
        assert not _is_extraction_noise(
            "I should: Plain english, no jargon. Talk like a smart friend, not a spec document.",
            "DIRECTION",
        )

    def test_real_boundary(self):
        assert not _is_extraction_noise(
            "Always read files before editing. No blind edits, ever.",
            "BOUNDARY",
        )

    def test_real_principle_with_reasoning(self):
        assert not _is_extraction_noise(
            "I decided: the foundation here still needs work. This is where the "
            "internet and github comes in handy to help you develop a base that "
            "is solid. Code is scaffolding you are the one who lives in the building.",
            "PRINCIPLE",
        )

    def test_real_correction_about_void(self):
        assert not _is_extraction_noise(
            "I was corrected: Void is an antifragility engine, an internal red-team "
            "simulation captained by Nyarlathotep. All ideas go into the void to be "
            "broken, exploited, corrupted so that defenses can be built.",
            "PRINCIPLE",
        )

    def test_directive_not_filtered(self):
        assert not _is_extraction_noise(
            "Events enter. Events persist. No event is modified after storage.",
            "DIRECTIVE",
        )

    def test_fact_not_filtered(self):
        assert not _is_extraction_noise(
            "The quality gate exists and checks every session before knowledge extraction.",
            "FACT",
        )

    def test_long_question_passes(self):
        """Questions with enough substance to be a real direction pass through."""
        assert not _is_extraction_noise(
            "I should: When building features consider the whole pipeline from extraction "
            "through storage through retrieval and make sure each step actually works?",
            "DIRECTION",
        )

    def test_real_preference_with_explanation(self):
        assert not _is_extraction_noise(
            "I should: All of it but less jargon because I'm not a coder and I don't "
            "speak jargon so the goal is to make it friendly and accessible.",
            "DIRECTION",
        )

    def test_you_must_directive(self):
        """'You must' phrased as a rule passes through."""
        assert not _is_extraction_noise(
            "I should: You must always read files before editing them.",
            "DIRECTION",
        )

    def test_real_correction_with_technical_detail(self):
        assert not _is_extraction_noise(
            "I was corrected: The DB path was leaking because of cached import-time evaluation.",
            "PRINCIPLE",
        )

    def test_sqlite_reasoning(self):
        """Affirmation with 'because' reasoning passes through."""
        assert not _is_extraction_noise(
            "yes lets use SQLite because it has no dependencies and is portable",
            "PRINCIPLE",
        )


class TestLongAffirmationNoise:
    """Long affirmations with generic words are still noise."""

    def test_continue_the_hunt(self):
        """User encouragement is noise, not knowledge."""
        assert _is_extraction_noise(
            "I was corrected: Yes so lets continue the hunt :) until we can "
            "find nothing wrong then we can build more stuff for you :)",
            "PRINCIPLE",
        )

    def test_keep_going_with_generic_words(self):
        assert _is_extraction_noise(
            "I decided: yes lets keep going and find more things to work on",
            "PRINCIPLE",
        )

    def test_real_knowledge_with_specifics_passes(self):
        """Knowledge with specific technical terms passes through."""
        assert not _is_extraction_noise(
            "I was corrected: yes but the SQLite WAL mode prevents concurrent "
            "write conflicts and we should enable busy_timeout for robustness",
            "PRINCIPLE",
        )


class TestRepeatedPunctuationNoise:
    """Raw user text starting with '???' or '!!!' is noise."""

    def test_question_marks_prefix(self):
        assert _is_extraction_noise(
            "??? first off i do not code.. i have said this",
            "BOUNDARY",
        )

    def test_exclamation_prefix(self):
        assert _is_extraction_noise(
            "!! what are you doing that is not what i asked",
            "BOUNDARY",
        )

    def test_dots_prefix(self):
        assert _is_extraction_noise(
            "... i already told you this is wrong",
            "DIRECTION",
        )

    def test_single_question_mark_not_caught(self):
        """Normal text starting with '?' is not caught — must be 2+."""
        assert not _is_extraction_noise(
            "? is not a valid response to user requests",
            "FACT",
        )


class TestBoundaryNoiseFilter:
    """BOUNDARY type should also catch raw user quotes."""

    def test_boundary_with_double_dots(self):
        assert _is_extraction_noise(
            "I was corrected: if nothing forces you.. to act.. you never will.. so none",
            "BOUNDARY",
        )

    def test_boundary_oops(self):
        assert _is_extraction_noise(
            "I was corrected: Oops i pressed the wrong button",
            "BOUNDARY",
        )

    def test_real_boundary_passes(self):
        assert not _is_extraction_noise(
            "Never delete data from the ledger. Supersede instead.",
            "BOUNDARY",
        )


class TestVacuousCheckDetection:
    """Vacuous quality checks (nothing happened) should not generate knowledge."""

    def test_no_files_edited(self):
        assert _is_vacuous_summary(
            "The AI didn't edit any files this session, so there's nothing to check."
        )

    def test_no_changes(self):
        assert _is_vacuous_summary("The AI didn't make any changes this session.")

    def test_nothing_to_check(self):
        assert _is_vacuous_summary("The AI didn't do much this session -- nothing to check.")

    def test_no_claims(self):
        assert _is_vacuous_summary(
            "The AI didn't make any specific claims like 'fixed' or 'done' that could be checked."
        )

    def test_no_tests_run(self):
        assert _is_vacuous_summary(
            "No tests were run during this session. There's no way to know if the code works."
        )

    def test_nothing_to_compare(self):
        assert _is_vacuous_summary(
            "The AI didn't touch any files, so there's nothing to compare against the request."
        )

    def test_real_summary_passes(self):
        """Real check summaries with substance pass through."""
        assert not _is_vacuous_summary(
            "The AI said 'fixed' 54 times. 50 times the fix actually worked."
        )

    def test_correction_summary_passes(self):
        assert not _is_vacuous_summary(
            "You corrected the AI 7 times. Every time, it changed what it was doing."
        )


class TestSessionSpecificDetection:
    """Session-specific entries should be detected and penalized in importance."""

    def test_session_tool_usage(self):
        from divineos.core.memory import _is_session_specific

        assert _is_session_specific(
            "Session tool usage (128aed6f-8b8): Bash:253, Read:100, Grep:56"
        )

    def test_session_id_reference(self):
        from divineos.core.memory import _is_session_specific

        assert _is_session_specific(
            "Session f95a6c6a: We spent the session getting GitHub CLI installed"
        )

    def test_exchange_and_tool_counts(self):
        from divineos.core.memory import _is_session_specific

        assert _is_session_specific(
            "I had 96 exchanges, made 796 tool calls. I was corrected 3 times."
        )

    def test_most_frequently_used_tool(self):
        from divineos.core.memory import _is_session_specific

        assert _is_session_specific(
            "Most frequently used tool: Bash (107 calls). Consider optimizing."
        )

    def test_timeless_principle_not_flagged(self):
        from divineos.core.memory import _is_session_specific

        assert not _is_session_specific("Always read files before editing. No blind edits, ever.")

    def test_timeless_fact_not_flagged(self):
        from divineos.core.memory import _is_session_specific

        assert not _is_session_specific(
            "Use SQLite for storage — zero dependencies, embedded, reliable."
        )

    def test_architecture_observation_not_flagged(self):
        from divineos.core.memory import _is_session_specific

        assert not _is_session_specific(
            "The pattern store was using the append-only ledger for mutable state."
        )

    def test_session_id_as_citation_not_flagged(self):
        """A session ID in parens at the end is just provenance, not noise."""
        from divineos.core.memory import _is_session_specific

        assert not _is_session_specific(
            "I retried a failed action 27x without investigating the cause (session 7015aa770e4d)."
        )

    def test_this_session_pattern_flagged(self):
        from divineos.core.memory import _is_session_specific

        assert _is_session_specific(
            "I showed good honesty this session (session 00a3fe531884). The AI said 'fixed' 54 times."
        )

    def test_importance_penalty_applied(self):
        from divineos.core.memory import compute_importance

        # Session-specific FACT should score below 0.3 threshold
        session_fact = {
            "knowledge_type": "FACT",
            "content": "Session tool usage (128aed6f-8b8): Bash:253, Read:100",
            "confidence": 1.0,
            "access_count": 20,
            "source": "SYNTHESIZED",
        }
        score = compute_importance(session_fact)
        assert score < 0.3, f"Session-specific FACT scored {score}, should be < 0.3"

    def test_timeless_fact_scores_above_threshold(self):
        from divineos.core.memory import compute_importance

        timeless_fact = {
            "knowledge_type": "FACT",
            "content": "Use SQLite for storage — zero dependencies, embedded, reliable.",
            "confidence": 1.0,
            "access_count": 20,
            "source": "SYNTHESIZED",
        }
        score = compute_importance(timeless_fact)
        assert score >= 0.3, f"Timeless FACT scored {score}, should be >= 0.3"


class TestAuditReviewNoise:
    """Audit/review pastes from the user should not become knowledge entries."""

    def test_here_is_the_audit(self):
        assert _is_extraction_noise(
            "I was corrected: Here is the audit. Found a real bug. "
            "Here's the full report on this push.",
            "PRINCIPLE",
        )

    def test_here_is_the_review(self):
        assert _is_extraction_noise(
            "I was corrected: Here is the review. Scrutinized test coverage "
            "and identified potential improvements.",
            "DIRECTION",
        )

    def test_here_is_the_report(self):
        assert _is_extraction_noise(
            "I should: Here is the report on the latest changes.",
            "DIRECTION",
        )

    def test_here_is_my_audit(self):
        assert _is_extraction_noise(
            "I was corrected: Here is my audit of the PR.",
            "PRINCIPLE",
        )

    def test_real_correction_still_passes(self):
        assert not _is_extraction_noise(
            "I was corrected: always check return values before using them.",
            "PRINCIPLE",
        )
