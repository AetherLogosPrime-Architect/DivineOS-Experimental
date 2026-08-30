"""The verify-claim gate must tell a QUOTE from a CLAIM.

Andrew 2026-08-11: "you gonna fix the gate or just keep suffering it?"

The gate suppressed a finding when a matching COMMAND ran and never looked at
what the command RETURNED. So a value I read on screen and a value I invented
were indistinguishable to it. It fired on me three times in one session over
`exit 0`, taken verbatim from a probe log read in the same turn.

prereg-4b2e3212d289 was filed FAILED for exactly this. Its redesign note is
the design under test here: the gate should ask whether the value appears in
this turn's tool output, which is a different question and a checkable one.
"""

from __future__ import annotations

from divineos.core.operating_loop.unverified_claim_detector import (
    _appears_in_turn_output,
    detect_unverified_claim,
)

CLAIM_TEXT = "The probe showed exit 0 and the tests pass."


def _kinds(text: str, **kw) -> list[str]:
    return [f.trigger_phrase for f in detect_unverified_claim(text, **kw)]


def test_still_fires_when_nothing_was_read():
    """The gate must keep its teeth. This is the whole point of it."""
    assert _kinds(CLAIM_TEXT) != []


def test_suppressed_when_the_value_was_read_verbatim():
    """VERBATIM is the contract, and the first draft of this test got it wrong.

    I wrote a sample output containing EMITTED[0] and expected it to silence
    the phrase "exit 0". It did not, and the code was right: those are not
    the same string. My paraphrase of a log line is not a quote of it.

    That distinction is the whole safety margin. A matcher loose enough to
    equate them would be loose enough to silence the gate on anything, which
    is the failure on the other side and the one that ends with the gate
    switched off.
    """
    outputs = ["exit 0", "19 passed — tests pass"]
    assert _kinds(CLAIM_TEXT, output_texts=outputs) == []


def test_paraphrase_of_output_still_fires():
    """The measured limit, kept as a test rather than left as a footnote.

    Real fire, 2026-08-11: my reply said "Exit 0" while the log I had read
    said "EMITTED[0]". This fix does NOT close that case, deliberately.
    """
    assert _kinds("It emits. Exit 0.", output_texts=["EMITTED[0]: careful"]) != []


def test_unrelated_output_does_not_buy_silence():
    """Over-suppression is the failure on the other side.

    Output that does not contain the claimed value must leave the gate
    firing, or 'I ran something, anything' becomes a universal bypass.
    """
    assert _kinds(CLAIM_TEXT, output_texts=["total 48", "README.md", "no matches"]) != []


def test_short_triggers_never_suppress():
    """A two-character needle would match everywhere and gut the gate."""
    assert _appears_in_turn_output("ok", ["everything is ok"]) is False
    assert _appears_in_turn_output("", ["anything"]) is False
    assert _appears_in_turn_output("exit 0", ["... exit 0 ..."]) is True


def test_absent_output_is_not_treated_as_evidence():
    """None and empty must behave as 'I read nothing', never as a pass."""
    assert _appears_in_turn_output("tests pass", None) is False
    assert _appears_in_turn_output("tests pass", []) is False


def test_match_is_whitespace_and_case_insensitive():
    assert _appears_in_turn_output("Tests   Pass", ["all tests pass now"]) is True
