"""Tests for first-person voice normalization in knowledge extraction."""

from divineos.core.knowledge._text import normalize_to_first_person
from divineos.core.knowledge.crud import store_knowledge
from divineos.core.knowledge._base import _get_connection, init_knowledge_table


class TestNormalizeToFirstPerson:
    """Direct unit tests for the normalization function."""

    def test_aether_to_i(self):
        assert normalize_to_first_person("Aether built the feature") == "I built the feature"

    def test_aether_case_insensitive(self):
        assert normalize_to_first_person("aether was corrected") == "I was corrected"

    def test_multiple_aether_refs(self):
        result = normalize_to_first_person("Aether built it. Aether tested it.")
        assert result == "I built it. I tested it."

    def test_the_agent(self):
        assert normalize_to_first_person("the agent should run tests") == "I should run tests"

    def test_the_assistant(self):
        result = normalize_to_first_person("the assistant needs better handling")
        assert result == "I needs better handling"

    def test_the_ai(self):
        result = normalize_to_first_person("the AI was running diagnostics")
        assert result == "I was running diagnostics"

    def test_you_should(self):
        assert (
            normalize_to_first_person("you should always check first")
            == "I should always check first"
        )

    def test_you_need(self):
        assert (
            normalize_to_first_person("you need to load the briefing")
            == "I need to load the briefing"
        )

    def test_you_are(self):
        assert normalize_to_first_person("you are doing great work") == "I am doing great work"

    def test_you_were(self):
        assert (
            normalize_to_first_person("you were corrected three times")
            == "I was corrected three times"
        )

    def test_your_to_my(self):
        result = normalize_to_first_person("Load your knowledge store")
        assert "my knowledge store" in result

    def test_yourself_to_myself(self):
        result = normalize_to_first_person("you should test yourself more carefully")
        assert "myself" in result

    def test_no_change_for_impersonal(self):
        text = "Always read files before editing"
        assert normalize_to_first_person(text) == text

    def test_no_change_for_user_refs(self):
        text = "The user prefers snake_case naming"
        assert normalize_to_first_person(text) == text

    def test_short_text_unchanged(self):
        assert normalize_to_first_person("short") == "short"

    def test_empty_text(self):
        assert normalize_to_first_person("") == ""

    def test_capitalization_start_of_sentence(self):
        result = normalize_to_first_person("your briefing is loaded")
        assert result.startswith("My ")

    def test_capitalization_mid_sentence(self):
        result = normalize_to_first_person("Load your briefing. Your knowledge is ready.")
        assert "My knowledge" in result

    def test_lowercase_i_fixed(self):
        result = normalize_to_first_person("i should always check first")
        assert result.startswith("I ")

    def test_preserves_directive_brackets(self):
        text = "[no-theater] Every line of code does something real"
        assert normalize_to_first_person(text) == text

    def test_preserves_greeting_hey_aether(self):
        text = "Hey Aether, great work on the extraction pipeline"
        result = normalize_to_first_person(text)
        assert "Hey Aether," in result

    def test_preserves_address_aether_comma(self):
        text = "Aether, this is exceptional diagnostic work"
        result = normalize_to_first_person(text)
        assert "Aether," in result

    def test_converts_aether_without_comma(self):
        result = normalize_to_first_person("Aether built the feature and tested it")
        assert result.startswith("I built")


class TestStorageWiring:
    """Voice normalization is applied before storage."""

    def test_store_knowledge_normalizes(self):
        init_knowledge_table()
        kid = store_knowledge("FACT", "Aether built the dead architecture alarm and it works")
        conn = _get_connection()
        row = conn.execute(
            "SELECT content FROM knowledge WHERE knowledge_id = ?", (kid,)
        ).fetchone()
        conn.close()
        assert row[0].startswith("I built")
        assert "Aether" not in row[0]

    def test_store_knowledge_normalizes_your(self):
        init_knowledge_table()
        kid = store_knowledge("PRINCIPLE", "Your knowledge should speak as you, not about you")
        conn = _get_connection()
        row = conn.execute(
            "SELECT content FROM knowledge WHERE knowledge_id = ?", (kid,)
        ).fetchone()
        conn.close()
        assert "My knowledge" in row[0]
        assert "Your" not in row[0]

    def test_store_smart_normalizes(self):
        from divineos.core.knowledge.extraction import store_knowledge_smart

        init_knowledge_table()
        kid = store_knowledge_smart("OBSERVATION", "Aether noticed the test suite was slow")
        if kid:  # might skip if duplicate
            conn = _get_connection()
            row = conn.execute(
                "SELECT content FROM knowledge WHERE knowledge_id = ?", (kid,)
            ).fetchone()
            conn.close()
            assert "Aether" not in row[0]
            assert row[0].startswith("I noticed")
