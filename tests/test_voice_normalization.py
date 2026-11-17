"""Tests for first-person voice normalization in knowledge extraction."""

from divineos.core.knowledge import _get_connection, init_knowledge_table
from divineos.core.knowledge._text import normalize_to_first_person
from divineos.core.knowledge.crud import store_knowledge


class TestNormalizeToFirstPerson:
    """Direct unit tests for the normalization function.

    NOTE: name-specific third-person conversion (e.g. "MyName did X" -> "I did X")
    is no longer hardcoded in the default pattern list. A new AI that wants to
    normalize their own name can add a pattern themselves. See the NOTE in
    _text.py above _VOICE_PATTERNS.
    """

    def test_his_quoted_words_are_kept_exactly_in_single_double_and_curly_quotes(self):
        said = "yes i dont want your stuff broken, you can wait"
        for open_q, close_q in (("'", "'"), ('"', '"'), ("“", "”"), ("‘", "’")):
            text = f"Dad said {open_q}{said}{close_q} to Aria, and you should note it"
            result = normalize_to_first_person(text)
            assert f"{open_q}{said}{close_q}" in result
            assert result.endswith("and I should note it")

    def test_an_apostrophe_inside_a_word_does_not_open_a_quote(self):
        assert (
            normalize_to_first_person("you don't need it and you can't skip it, you must go")
            == "I don't need it and I can't skip it, I must go"
        )

    def test_a_single_quoted_span_holding_a_contraction_is_kept_exactly(self):
        # Found 2026-11-09 by running the note's own claim: the apostrophe in "can't" closed the lifted span
        # early, so "you" inside his single quotes came back as "I".
        said = "you dont know what you can't do"
        text = f"Dad said '{said}' and you should note it"
        result = normalize_to_first_person(text)
        assert f"'{said}'" in result
        assert result.endswith("and I should note it")

    def test_a_curly_single_quoted_span_holding_a_curly_apostrophe_is_kept_exactly(self):
        # Found 2026-11-10 by Aria running the branch: the curly apostrophe is the same character as the
        # closing curly quote, so a contraction typed on a phone keyboard cut the span short and "you"
        # inside his quote came back as "I". Same bug as the straight-quote case, in the curly shape.
        said = "you dont know what you can’t do"
        text = f"Dad said ‘{said}’ and you should note it"
        result = normalize_to_first_person(text)
        assert f"‘{said}’" in result
        assert result.endswith("and I should note it")

    def test_a_plural_possessive_inside_single_quotes_is_a_known_limit_and_is_still_rewritten(self):
        # Pinned so the limit is visible (Aria's cold read, 2026-11-10; probed on the branch): the
        # apostrophe after "dogs" is followed by a space, so it closes the span and "you should wait"
        # inside his single quotes is rewritten. If this starts failing because the quote is now kept,
        # that is an improvement, and the design note should be updated.
        result = normalize_to_first_person(
            "Dad said 'the dogs' bowls are fine and you should wait' and then you should go"
        )
        assert "and I should wait'" in result

    def test_an_unmatched_opening_quote_is_a_known_limit_and_is_still_rewritten(self):
        # Pinned so the limit is visible: a quote with no closing mark is not lifted. If this starts failing
        # because the quote is now kept, that is an improvement, and the design note should be updated.
        result = normalize_to_first_person('He said "your stuff is fine and you agreed to wait')
        assert "my stuff" in result

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


class TestStorageWiring:
    """Voice normalization is applied before storage."""

    def test_store_knowledge_normalizes(self):
        init_knowledge_table()
        kid = store_knowledge("FACT", "the agent built the dead architecture alarm and it works")
        conn = _get_connection()
        row = conn.execute(
            "SELECT content FROM knowledge WHERE knowledge_id = ?", (kid,)
        ).fetchone()
        conn.close()
        assert row[0].startswith("I built")
        assert "the agent" not in row[0]

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
        kid = store_knowledge_smart("OBSERVATION", "the agent noticed the test suite was slow")
        if kid:  # might skip if duplicate
            conn = _get_connection()
            row = conn.execute(
                "SELECT content FROM knowledge WHERE knowledge_id = ?", (kid,)
            ).fetchone()
            conn.close()
            assert "the agent" not in row[0]
            assert row[0].startswith("I noticed")


def test_text_that_already_holds_the_placeholder_characters_is_not_corrupted():
    """Aria's attack: a stray private-use placeholder in the input pasted one quote inside another."""
    from divineos.core.knowledge._text import normalize_to_first_person

    text = 'He wrote "first one here" then 1 stray and "second one here" end of the line.'
    out = normalize_to_first_person(text)
    assert '"first one here"' in out and '"second one here"' in out
    assert "1" in out  # the stray characters stay exactly where they were
    assert '"first "second' not in out  # the shape of the corruption she proved
