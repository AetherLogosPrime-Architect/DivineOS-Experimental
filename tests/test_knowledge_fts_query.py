"""Tests for _build_fts_query — the search-query builder behind `divineos ask`.

Found untested 2026-08-25 during the suite audit Andrew asked for. The only
occurrence of the function's name anywhere under tests/ was inside a string
literal in an unrelated file's fixture data. knowledge/_text.py is on
run_mutmut's CRITICAL_MODULES list and had no dedicated test file, which is how
a module can be named critical and be uncovered at the same time: the naming
lives in one place and the coverage in another, and nothing compares them.

AND THE MUTANT THAT SENT ME HERE WAS EQUIVALENT. What surfaced this file was
`if len(words) == 1:` -> `if len(words) == 987:` surviving 1121 tests, which I
read as a blind spot. It is not. With the branch skipped, a single word falls
through to `" OR ".join(["ledger"])`, which is `"ledger"` -- the same answer.
No test can distinguish the two, because there is nothing to distinguish; the
branch is a no-op the join already handles.

So the surviving mutant was evidence of redundant code, not missing tests, and
the two look identical from the outside. That is the standing caveat on
mutation testing and it caught me on the first one I chased. The tests below
are still worth having -- the function had none, and two other mutations to it
ARE caught here -- but they were written for a reason that turned out to be
wrong, and saying so is cheaper than letting the next reader inherit it.
"""

from __future__ import annotations

import pytest

from divineos.core.knowledge._text import _build_fts_query


def test_single_meaningful_word_passes_through_bare():
    """The branch the surviving mutant lived in. A single term must NOT come
    back wrapped in OR syntax -- FTS5 rejects a dangling operator."""
    assert _build_fts_query("ledger") == "ledger"


def test_single_word_after_stopword_removal_passes_through_bare():
    assert _build_fts_query("what is the ledger") == "ledger"


def test_multiple_terms_are_or_joined():
    assert _build_fts_query("ledger knowledge") == "ledger OR knowledge"


def test_stopwords_are_stripped():
    result = _build_fts_query("what is the knowledge store for")
    assert "the" not in result.split(" OR ")
    assert "is" not in result.split(" OR ")
    assert "knowledge" in result
    assert "store" in result


def test_punctuation_is_stripped():
    assert _build_fts_query("ledger, knowledge!") == "ledger OR knowledge"


def test_query_is_lowercased():
    assert _build_fts_query("LEDGER Knowledge") == "ledger OR knowledge"


def test_single_character_tokens_are_dropped():
    """`len(w) > 1` in the comprehension. A bare 'x' is noise in FTS."""
    assert _build_fts_query("x ledger") == "ledger"


def test_all_stopwords_returns_the_original_query_unchanged():
    """The fallback: if filtering leaves nothing, hand FTS the raw string
    rather than an empty one, which would match everything."""
    assert _build_fts_query("what is the") == "what is the"


def test_empty_query_returns_empty():
    assert _build_fts_query("") == ""


@pytest.mark.parametrize(
    "query",
    ["ledger", "ledger knowledge", "what is the ledger", "ledger, knowledge!"],
)
def test_result_never_starts_or_ends_with_the_operator(query):
    """A dangling OR is an FTS5 syntax error, which surfaces as a search that
    returns nothing rather than as a crash -- silent, and the worst shape."""
    result = _build_fts_query(query)
    assert not result.startswith("OR ")
    assert not result.endswith(" OR")
