"""The edit log for his words: slips pass quietly, real-word swaps wait for him, what he typed stays quotable.

Promises pinned (Andrew 2026-10-07: edits "can be logged but they cannot be made
uneditable"; 2026-10-28: simple spelling errors "can be corrected automatically",
only whole-word swaps need his correction):
  1. a spelling slip passes on its own and is recorded for him to see;
  2. a real word in place of another real word is held, never passed;
  3. a row with no proof of his yes is ignored by the loader;
  4. after a confirmed edit the corrected wording passes AND what he typed still does.
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


def test_a_spelling_slip_passes_on_its_own_and_is_recorded(tmp_path):
    index = _index(_marks(tmp_path, TYPED))
    result = hw.check(f'Dad said: "{FIXED}"', index=index)
    assert result.state == "pass"
    assert result.auto_fixed and "definately" in result.auto_fixed[0][1].split()


def test_the_sky_is_blu_passes_and_the_sky_is_red_for_blue_is_asked_about(tmp_path):
    # His own two examples (2026-10-28): a forgotten last letter is fixed quietly,
    # a real word in the place of another real word is held for him.
    slip = _index(_marks(tmp_path, "i said the sky is blu today for sure"))
    assert hw.check('Dad said: "the sky is blue today"', index=slip).state == "pass"
    swap = tmp_path / "swap"
    swap.mkdir()
    other = _index(_marks(swap, "i said the sky is red today for sure"))
    result = hw.check('Dad said: "the sky is blue today"', index=other)
    assert result.state == "held"
    assert result.auto_fixed == []


def test_a_short_word_he_writes_often_is_a_word_of_his_not_a_slip():
    assert edits.is_typo_of("car", "care")
    assert not edits.is_typo_of("car", "care", frozenset({"car"}))


def test_a_real_word_swapped_for_a_real_word_is_never_a_slip(tmp_path):
    index = _index(_marks(tmp_path, "i think this is quite the right fix for the door"))
    result = hw.check('Dad said: "this is quote the right fix"', index=index)
    assert result.state == "held"
    assert result.auto_fixed == []


def test_the_slips_the_door_passed_are_logged_for_him(tmp_path):
    log = tmp_path / "auto_fixes_log.jsonl"
    edits.log_auto_fixes([("this is definitely the", "this is definately the")], "2026-10-28", log)
    rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    assert rows == [
        {
            "when": "2026-10-28",
            "quote": "this is definitely the",
            "he_typed": "this is definately the",
        }
    ]


def test_a_missing_vocabulary_holds_the_quote_and_says_spelling_was_not_judged(
    tmp_path, monkeypatch
):
    index = _index(_marks(tmp_path, TYPED))
    monkeypatch.setenv("HUGGINGFACE_HUB_CACHE", str(tmp_path / "empty_cache"))
    monkeypatch.setattr(light_embedder, "_VOCAB_TOKENIZER", None)
    result = hw.check(f'Dad said: "{FIXED}"', index=index)
    assert result.state == "held"
    assert result.auto_fixed == []
    assert result.spelling_unjudged, "an outage must carry its reason, never look like a clean no"
    assert "Spelling could not be judged" in hw.refusal_text(result)


def test_his_slang_is_not_read_as_a_typo():
    assert edits.is_typo_of("definately", "definitely")
    assert edits.is_typo_of("blu", "blue")
    assert not edits.is_typo_of("quote", "quite")
    assert not edits.is_typo_of("alot", "allot")
    assert not edits.is_typo_of("thats", "that")
    assert not edits.is_typo_of("dont", "done")
    assert not edits.is_typo_of("cant", "cane")


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
