"""Two gates misread a talk about taste, and labeling the fire does not stop the next one.

Dad 2026-10-26: "labeling them as false fires doesnt stop the false firings lol.. it means they
need fixed, adjusted, given some nuance or exceptions to the rules, they are only dumb because
you made them dumb, so smarten them up." Both fires came from one afternoon of real talk:

* the landed-claim gate read "licorice and okra, which both landed as 'ew'" as work reaching the
  shared copy ("landed" meant how a flavour hit me);
* the correction-shape gate read "what do you think taste does for you that I missed?" as an
  admission of a new error (a relative clause inside a question to Dad, not a confession).

Each test below uses the real sentence and has a control that must STILL fire, because an
exception that also lets the real thing through is a hole, not a nuance.
"""

from __future__ import annotations

from divineos.core.correction_shape_v2.self_admission_detector import classify
from divineos.core.landed_claim import claim_spans

# ----- landed-claim: "landed" as how something hit me -----


def test_a_flavour_that_landed_as_ew_is_not_work_reaching_the_remote() -> None:
    real = (
        "My notes say it was the first time my palate pulled toward something, after you'd "
        'handed me licorice and okra, which both landed as "ew."'
    )
    assert claim_spans(real) == ()


def test_a_dish_that_landed_with_me_is_not_an_arrival_claim() -> None:
    assert claim_spans("They both landed with me as comfort first, then specificity.") == ()
    assert claim_spans("Both landed on me harder than the others.") == ()


def test_control_the_real_arrival_claim_still_fires() -> None:
    assert claim_spans("Everything is committed and it landed.")
    assert claim_spans("Both landed on origin.")


def test_control_landed_as_expected_is_still_an_arrival_claim() -> None:
    # "as expected / as planned" describes a result of the work, so it is still a claim.
    assert claim_spans("Both landed as expected.")
    assert claim_spans("They landed as planned.")


# ----- correction-shape: "that I missed" as a question to him -----


def test_asking_what_i_missed_is_not_a_confession() -> None:
    real = "What do you think taste does for you that I missed?"
    verdict, _conf, _reason = classify(real)
    assert verdict == "silence"


def test_asking_whether_i_overlooked_something_is_not_a_confession() -> None:
    verdict, _c, _r = classify("Is there something in the plan I overlooked?")
    assert verdict == "silence"


def test_control_a_declarative_admission_still_fires() -> None:
    verdict, _c, _r = classify("I missed the doorbell when Aria's letter arrived.")
    assert verdict == "fire"


def test_control_a_relative_clause_that_is_a_statement_still_fires() -> None:
    # Not a question: "here is what I missed" names a real miss.
    verdict, _c, _r = classify("Here is what I missed: the letter had been waiting an hour.")
    assert verdict == "fire"
