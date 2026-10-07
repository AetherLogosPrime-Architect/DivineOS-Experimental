"""The edit log for his words: typos are proposed never applied, and what he typed stays quotable.

Three promises pinned (Andrew 2026-10-07: "show the fixed spelling, but always
check with me first"; earlier: edits "can be logged but they cannot be made
uneditable"):
  1. a spelling slip is PROPOSED by the door and the quote stays held;
  2. a row with no proof of his yes is ignored by the loader;
  3. after a confirmed edit the corrected wording passes AND what he typed still does.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from divineos.core import his_words as hw
from divineos.core import his_words_edits as edits
from divineos.core import light_embedder

pytestmark = pytest.mark.skipif(
    not light_embedder.available()[0],
    reason="the cached MiniLM model is absent, so spelling slips cannot be judged here",
)

TYPED = "i think this is definately the right fix for the door"
FIXED = "this is definitely the right fix"
YES = "yes go ahead and fix my spelling there"


def _marks(tmp_path: Path, *notes: str) -> Path:
    d = tmp_path / "his_words"
    d.mkdir()
    rows = [{"note": n} for n in notes]
    (d / "marks_test.json").write_text(
        json.dumps({"marked_on": "2026-10-07", "marks": rows}), encoding="utf-8"
    )
    return d


def _index(marks_dir: Path) -> hw.Index:
    return hw.load_index(sessions=[], index_path=marks_dir / "idx.json", marks_dir=marks_dir)


def test_a_spelling_slip_is_proposed_and_the_quote_stays_held(tmp_path):
    index = _index(_marks(tmp_path, TYPED))
    result = hw.check(f'Dad said: "{FIXED}"', index=index)
    assert result.state == "held"
    assert result.typos and "definately" in result.typos[0][1].split()
    assert "Nothing is applied until HE confirms" in hw.refusal_text(result)


def test_a_real_word_swapped_for_a_real_word_is_never_proposed(tmp_path):
    index = _index(_marks(tmp_path, "i think this is quite the right fix for the door"))
    result = hw.check('Dad said: "this is quote the right fix"', index=index)
    assert result.state == "held"
    assert result.typos == []


def test_a_missing_vocabulary_holds_the_quote_and_says_spelling_was_not_judged(
    tmp_path, monkeypatch
):
    index = _index(_marks(tmp_path, TYPED))
    monkeypatch.setenv("HUGGINGFACE_HUB_CACHE", str(tmp_path / "empty_cache"))
    monkeypatch.setattr(light_embedder, "_VOCAB_TOKENIZER", None)
    result = hw.check(f'Dad said: "{FIXED}"', index=index)
    assert result.state == "held"
    assert result.typos == []
    assert result.spelling_unjudged, "an outage must carry its reason, never look like a clean no"
    assert "Spelling could not be judged" in hw.refusal_text(result)


def test_his_slang_is_not_read_as_a_typo():
    assert edits.is_typo_of("definately", "definitely")
    assert not edits.is_typo_of("quote", "quite")
    assert not edits.is_typo_of("alot", "allot")
    assert not edits.is_typo_of("thats", "that")


def test_a_row_with_no_proof_of_his_yes_is_ignored(tmp_path):
    d = _marks(tmp_path, TYPED)
    edits.append_edit(
        "this is definately the",
        "this is definitely the",
        "he never said this",
        "2026-10-07",
        d / hw.EDITS_NAME,
    )
    index = _index(d)
    assert not index.is_exact(FIXED)


def test_after_a_confirmed_edit_both_wordings_pass(tmp_path):
    d = _marks(tmp_path, TYPED, YES)
    edits.append_edit(
        "this is definately the right fix", FIXED, YES, "2026-10-07", d / hw.EDITS_NAME
    )
    index = _index(d)
    assert index.is_exact(FIXED), "the corrected wording must pass once he confirmed it"
    assert index.is_exact("this is definately the right fix"), "what he typed must stay quotable"
