"""Tests for the extraction noise filter — ensures raw conversational quotes
don't become permanent 'knowledge'."""

from divineos.core.consolidation import _is_extraction_noise


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
