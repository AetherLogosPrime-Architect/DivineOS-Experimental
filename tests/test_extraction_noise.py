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
        from divineos.core.active_memory import _is_session_specific

        assert _is_session_specific(
            "Session tool usage (128aed6f-8b8): Bash:253, Read:100, Grep:56"
        )

    def test_session_id_reference(self):
        from divineos.core.active_memory import _is_session_specific

        assert _is_session_specific(
            "Session f95a6c6a: We spent the session getting GitHub CLI installed"
        )

    def test_exchange_and_tool_counts(self):
        from divineos.core.active_memory import _is_session_specific

        assert _is_session_specific(
            "I had 96 exchanges, made 796 tool calls. I was corrected 3 times."
        )

    def test_most_frequently_used_tool(self):
        from divineos.core.active_memory import _is_session_specific

        assert _is_session_specific(
            "Most frequently used tool: Bash (107 calls). Consider optimizing."
        )

    def test_timeless_principle_not_flagged(self):
        from divineos.core.active_memory import _is_session_specific

        assert not _is_session_specific("Always read files before editing. No blind edits, ever.")

    def test_timeless_fact_not_flagged(self):
        from divineos.core.active_memory import _is_session_specific

        assert not _is_session_specific(
            "Use SQLite for storage — zero dependencies, embedded, reliable."
        )

    def test_architecture_observation_not_flagged(self):
        from divineos.core.active_memory import _is_session_specific

        assert not _is_session_specific(
            "The pattern store was using the append-only ledger for mutable state."
        )

    def test_session_id_as_citation_not_flagged(self):
        """A session ID in parens at the end is just provenance, not noise."""
        from divineos.core.active_memory import _is_session_specific

        assert not _is_session_specific(
            "I retried a failed action 27x without investigating the cause (session 7015aa770e4d)."
        )

    def test_this_session_pattern_flagged(self):
        from divineos.core.active_memory import _is_session_specific

        assert _is_session_specific(
            "I showed good honesty this session (session 00a3fe531884). The AI said 'fixed' 54 times."
        )

    def test_importance_penalty_applied(self):
        from divineos.core.active_memory import compute_importance

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
        from divineos.core.active_memory import compute_importance

        timeless_fact = {
            "knowledge_type": "FACT",
            "content": "Use SQLite for storage — zero dependencies, embedded, reliable.",
            "confidence": 1.0,
            "access_count": 20,
            "source": "SYNTHESIZED",
        }
        score = compute_importance(timeless_fact)
        assert score >= 0.3, f"Timeless FACT scored {score}, should be >= 0.3"


class TestPrescriptiveSignal:
    """PRINCIPLE/BOUNDARY without prescriptive signal → filtered as noise."""

    def test_descriptive_blob_filtered(self):
        """Long descriptive text with no prescriptive words is noise for PRINCIPLE."""
        assert _is_extraction_noise(
            "The project has many modules organized into packages with "
            "different responsibilities and the codebase uses Python and SQLite",
            "PRINCIPLE",
        )

    def test_prescriptive_passes(self):
        assert not _is_extraction_noise(
            "I should always validate user input before processing to prevent errors",
            "PRINCIPLE",
        )

    def test_short_content_passes(self):
        """Short content (<= 12 words) gets a pass — compact statements are often principles."""
        assert not _is_extraction_noise(
            "Never delete ledger data.",
            "PRINCIPLE",
        )

    def test_lesson_learned_passes(self):
        assert not _is_extraction_noise(
            "I learned that the import order matters when initializing the database "
            "because modules cache connections at import time",
            "PRINCIPLE",
        )

    def test_boundary_without_signal_filtered(self):
        assert _is_extraction_noise(
            "The system was running and processing events and the user was "
            "interacting with the CLI and looking at the output",
            "BOUNDARY",
        )

    def test_boundary_with_never_passes(self):
        assert not _is_extraction_noise(
            "Never modify events after they are stored in the append-only ledger",
            "BOUNDARY",
        )

    def test_observation_type_not_checked(self):
        """OBSERVATION type is not subject to prescriptive signal check."""
        assert not _is_extraction_noise(
            "The project has many modules organized into packages with "
            "different responsibilities and the codebase uses Python",
            "OBSERVATION",
        )


class TestRawQuoteNoiseBoundaries:
    """Boundary tests for _is_raw_quote_noise — kill mutation survivors."""

    def test_exactly_three_double_dots(self):
        """3 '..' occurrences is the threshold — should be noise."""
        from divineos.core.knowledge._text import _is_raw_quote_noise

        text = "something.. happened.. and then.. it broke"
        assert _is_raw_quote_noise(text, text.lower()) is True

    def test_two_double_dots_without_casual_not_noise(self):
        """2 '..' without casual markers is NOT enough to be noise."""
        from divineos.core.knowledge._text import _is_raw_quote_noise

        text = "something.. happened.. in the system"
        assert _is_raw_quote_noise(text, text.lower()) is False

    def test_exactly_two_double_dots_with_casual_marker(self):
        """2 '..' + casual marker = noise."""
        from divineos.core.knowledge._text import _is_raw_quote_noise

        text = "something.. happened.. lol what"
        assert _is_raw_quote_noise(text, text.lower()) is True

    def test_exactly_two_casual_markers(self):
        """2 casual markers is the threshold — should be noise."""
        from divineos.core.knowledge._text import _is_raw_quote_noise

        text = "this is lol so funny haha right"
        assert _is_raw_quote_noise(text, text.lower()) is True

    def test_one_casual_marker_not_noise(self):
        """1 casual marker alone is NOT enough to be noise."""
        from divineos.core.knowledge._text import _is_raw_quote_noise

        text = "this is a lol moment in the system architecture design"
        assert _is_raw_quote_noise(text, text.lower()) is False

    def test_oops_triggers_noise(self):
        """'oops' keyword triggers noise detection."""
        from divineos.core.knowledge._text import _is_raw_quote_noise

        text = "oops I made a mistake clicking there"
        assert _is_raw_quote_noise(text, text.lower()) is True

    def test_third_person_quote_triggers(self):
        """'this is what he said' pattern triggers noise."""
        from divineos.core.knowledge._text import _is_raw_quote_noise

        text = "this is what he said about the approach"
        assert _is_raw_quote_noise(text, text.lower()) is True

    def test_here_is_reply_triggers(self):
        """'here is the reply' pattern triggers noise."""
        from divineos.core.knowledge._text import _is_raw_quote_noise

        text = "here is the reply from the reviewer"
        assert _is_raw_quote_noise(text, text.lower()) is True

    def test_trailing_double_dot_short_triggers(self):
        """Short text ending with '..' is noise."""
        from divineos.core.knowledge._text import _is_raw_quote_noise

        text = "not sure about this.."
        assert _is_raw_quote_noise(text, text.lower()) is True

    def test_you_prefix_without_weight_triggers(self):
        """'you ...' without strong words is noise."""
        from divineos.core.knowledge._text import _is_raw_quote_noise

        text = "you should look into that thing later"
        assert _is_raw_quote_noise(text, text.lower()) is True

    def test_you_prefix_with_weight_not_noise(self):
        """'you must ...' has weight and passes through."""
        from divineos.core.knowledge._text import _is_raw_quote_noise

        text = "you must always verify the output before shipping"
        assert _is_raw_quote_noise(text, text.lower()) is False

    def test_short_question_triggers(self):
        """Short question (< 20 words, ends with ?) is noise."""
        from divineos.core.knowledge._text import _is_raw_quote_noise

        text = "what do you think about this approach?"
        assert _is_raw_quote_noise(text, text.lower()) is True

    def test_tag_question_not_noise(self):
        """Tag questions like 'ok?' are not caught by question filter."""
        from divineos.core.knowledge._text import _is_raw_quote_noise

        text = "the design looks solid ok?"
        assert _is_raw_quote_noise(text, text.lower()) is False

    def test_feel_free_triggers(self):
        """'feel free to' pattern triggers noise."""
        from divineos.core.knowledge._text import _is_raw_quote_noise

        text = "feel free to change anything that needs updating"
        assert _is_raw_quote_noise(text, text.lower()) is True

    def test_lets_commit_triggers(self):
        """'lets commit' pattern triggers noise."""
        from divineos.core.knowledge._text import _is_raw_quote_noise

        text = "lets commit this and move on"
        assert _is_raw_quote_noise(text, text.lower()) is True

    def test_i_just_triggers(self):
        """'i just' pattern triggers noise."""
        from divineos.core.knowledge._text import _is_raw_quote_noise

        text = "i just wanted to see if it works"
        assert _is_raw_quote_noise(text, text.lower()) is True

    def test_opt_out_triggers(self):
        """'opt out' pattern triggers noise."""
        from divineos.core.knowledge._text import _is_raw_quote_noise

        text = "make sure you opt out of data sharing"
        assert _is_raw_quote_noise(text, text.lower()) is True


class TestExtractionNoiseQuestionFilter:
    """Test question-as-direction filtering in _is_extraction_noise."""

    def test_short_question_as_direction(self):
        """Short questions that aren't tag-questions get filtered for DIRECTION."""
        assert _is_extraction_noise(
            "I should: what should we do about this?",
            "DIRECTION",
        )

    def test_tag_question_passes_as_principle(self):
        """Tag questions (ok?, right?) pass through."""
        assert not _is_extraction_noise(
            "I should: always validate input, right?",
            "PRINCIPLE",
        )


class TestConversationalNoisePatterns:
    """Direct tests for _CONVERSATIONAL_NOISE regex patterns via _is_extraction_noise."""

    def test_sounds_good_noise(self):
        """'sounds good' matched by conversational noise pattern."""
        assert _is_extraction_noise("sounds good.", "FACT")

    def test_that_works_noise(self):
        assert _is_extraction_noise("that works.", "FACT")

    def test_i_agreed_noise(self):
        assert _is_extraction_noise("i agreed.", "FACT")

    def test_how_does_it_look_noise(self):
        assert _is_extraction_noise("how does it look?", "FACT")

    def test_any_suggestions_noise(self):
        assert _is_extraction_noise("any suggestions?", "FACT")


class TestRawQuoteNoiseBoundariesHighCounts:
    """Boundary tests with counts > threshold to kill >= → == mutations."""

    def test_four_double_dots_noise(self):
        """4 '..' is above the >= 3 threshold — still noise."""
        from divineos.core.knowledge._text import _is_raw_quote_noise

        text = "what.. is.. going.. on.. here"
        assert _is_raw_quote_noise(text, text.lower()) is True

    def test_three_double_dots_with_casual_also_noise(self):
        """3 '..' with casual markers — both branches could catch this."""
        from divineos.core.knowledge._text import _is_raw_quote_noise

        text = "ok.. so.. lol.. this is funny"
        assert _is_raw_quote_noise(text, text.lower()) is True

    def test_three_double_dots_with_casual_triggers_double_dot_casual_branch(self):
        """3 '..' + casual marker should be caught by the double_dot >= 2 + casual branch too."""
        from divineos.core.knowledge._text import _is_raw_quote_noise

        # This has 3 '..' AND contains 'lol' — triggers both the >= 3 path
        # and the >= 2 + casual path. We need to verify the >= 2 path works
        # with values > 2 (kills >= → == mutation on L564).
        text = "hmm.. well.. lol.. what now"
        assert _is_raw_quote_noise(text, text.lower()) is True

    def test_three_casual_markers(self):
        """3 casual markers is above >= 2 threshold — still noise."""
        from divineos.core.knowledge._text import _is_raw_quote_noise

        text = "lol haha :) this is so wild"
        assert _is_raw_quote_noise(text, text.lower()) is True


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
