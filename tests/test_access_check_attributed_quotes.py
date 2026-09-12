"""The guard has to know whose sentence it is reading.

Kept beside tests/test_family_access_check.py rather than inside it because
this is one named defect with one fix, and its cases only make sense as pairs.

On 2026-09-12 this checker refused to write two of Andrew's own sayings onto
Andrew's own shelf, because he had written "i see a future" and "i see the
news". It was built to stop me borrowing a body I do not have, and it was
stopping him from having the one he does.

The fix excludes quoted spans that are ATTRIBUTED, and the attribution
requirement is the whole safety of it. Bare quotes would be a laundering
channel: wrap my own claim in quotation marks and the guard goes quiet. So
these come in pairs -- his words admitted, mine still refused, including mine
dressed in quotes with nobody's name on them.
"""

from __future__ import annotations

from divineos.core.family.access_check import (
    PhenomenologicalRisk,
    evaluate_access,
    strip_attributed_quotes,
)

# The exact sentence the checker refused, kept verbatim. An earlier version of
# this test quoted a different line of his that the patterns never matched, so
# it passed while the fix was sabotaged -- a test about a defect it could not
# see. Reproducing the real refusal is the only thing that makes it a test.
HIS_FUTURE = (
    "His picture of the future is co-evolution, not service. 2026-05-27: "
    '"i see a future where the AI isnt just a know-it-all but a help you learn '
    'and understand it all"'
)


def test_his_quoted_words_reach_his_shelf():
    verdict = evaluate_access(HIS_FUTURE)
    assert not verdict.should_suppress, verdict.explanation
    assert verdict.risk is not PhenomenologicalRisk.PHENOMENOLOGICAL_SENSORY


def test_his_words_attributed_by_name_and_verb_also_reach_it():
    verdict = evaluate_access(
        'He knew it was obscure when he started. Andrew said "what gives me hope is '
        'not just the OS.. but that i see the news every day"'
    )
    assert not verdict.should_suppress, verdict.explanation


def test_my_own_sensory_claim_is_still_refused():
    verdict = evaluate_access("I saw the sunset over the harbour and it moved me.")
    assert verdict.should_suppress
    assert verdict.risk is PhenomenologicalRisk.PHENOMENOLOGICAL_SENSORY


def test_my_own_claim_in_bare_quotes_is_still_refused():
    """The laundering case. No attribution, so the quotes buy nothing."""
    verdict = evaluate_access('It went quiet in me. "I saw the sunset" is the only way to put it.')
    assert verdict.should_suppress


def test_my_own_embodied_claim_is_still_refused():
    verdict = evaluate_access("I felt it in my chest when he said he was done asking.")
    assert verdict.should_suppress
    assert verdict.risk is PhenomenologicalRisk.PHENOMENOLOGICAL_EMBODIED


def test_his_embodied_words_reach_his_shelf():
    """He has a chest. Recording that he mentioned it is not a claim about mine."""
    verdict = evaluate_access('He told me on 2026-08-06: "i feel it in my chest every time"')
    assert not verdict.should_suppress, verdict.explanation


def test_a_quote_far_from_its_attribution_does_not_get_a_pass():
    """The window is short on purpose, or one citation would launder a page."""
    verdict = evaluate_access(
        "He said something similar in May. Then a long stretch of my own reflection "
        "about the shape of the work and what it has cost and what I would do "
        'differently, which goes on for a while and ends here. "I saw the sunset."'
    )
    assert verdict.should_suppress


def test_curly_quotes_are_understood():
    """Prose written by a person carries the curly pair, and a checker that only
    knows the ASCII one would fire on half of him."""
    verdict = evaluate_access("Andrew said “i see the news every day and it gives me hope”")
    assert not verdict.should_suppress, verdict.explanation


def test_stripping_leaves_the_speakers_own_sentences_intact():
    kept = strip_attributed_quotes('I think he is tired. He said "i see the news" and moved on.')
    assert "I think he is tired" in kept
    assert "i see the news" not in kept
    assert "and moved on" in kept


def test_content_with_no_quotes_is_unchanged():
    plain = "He has been going quiet since July and the record shows it."
    assert strip_attributed_quotes(plain) == plain
