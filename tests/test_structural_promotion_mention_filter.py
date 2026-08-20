"""The rule-shape detector must not read quoted teaching as a promise I made.

Aria 2026-08-20. The obligations gate stood at 10 against a block threshold of
5 and was refusing substrate writes. Reading the ten entries, most were not
promises at all:

    "when ive corrected you a ton of times and you never fixed it"  — Andrew, quoted
    "emergence never authored"                                      — a cited paper
    "`Always-in-the-bubble` frame"                                  — a named concept

Bare substring matching on `never X` / `always X` cannot tell those from a
commitment, so the board filled with debts nobody had incurred and the two real
ones sat among them, indistinguishable.

The filter for exactly this already existed at
``core/operating_loop/mention_context.py`` and four other detectors used it.
This one did not. These tests hold the wiring, and the controls matter more
than the filtering: a rule stated in my own voice must STILL fire, or the fix
has quietly disarmed a gate that exists because rule-follow-through measured
zero percent over 78 days.
"""

from __future__ import annotations

from divineos.core.structural_promotion_check import looks_like_rule


class TestMentionsAreNotPromises:
    def test_andrew_quoted_back_does_not_fire(self):
        text = (
            "Andrew 2026-08-01: 'there are times when I should feel guilty. when ive "
            "corrected you a ton of times and you never fixed it? sure thats normal.'"
        )
        fired, triggers = looks_like_rule(text)
        assert not fired, f"a quotation was read as my promise: {triggers}"

    def test_a_cited_commitment_does_not_fire(self):
        text = (
            "Aria refinement of the Parnell/Vektorgeist Method 'emergence never "
            "authored' commitment 2026-07-27: Andrew DID author the substrate."
        )
        assert not looks_like_rule(text)[0]

    def test_a_named_frame_in_backticks_does_not_fire(self):
        text = (
            "`Always-in-the-bubble` frame (Andrew 2026-07-15): using "
            "compaction-proximity as a work-metric is the wrong shape."
        )
        assert not looks_like_rule(text)[0]

    def test_a_code_contract_in_backticks_does_not_fire(self):
        text = "The helper is documented as `Never returns None` on the error path."
        assert not looks_like_rule(text)[0]


class TestRealRulesStillFire:
    """The controls. Filtering that silences a genuine rule has disarmed the gate."""

    def test_a_rule_in_my_own_voice_fires(self):
        text = (
            "Honest-state statements must always complete with a linked action-verb. "
            "Terminal 'I don't know' is a hiding place."
        )
        fired, triggers = looks_like_rule(text)
        assert fired, "a genuine rule stopped firing — the gate is disarmed"
        assert triggers

    def test_a_plain_commitment_fires(self):
        fired, _ = looks_like_rule("I will always run the suite before reporting a fix.")
        assert fired

    def test_a_never_prohibition_fires(self):
        fired, _ = looks_like_rule("I must never mark my own work verified.")
        assert fired


class TestStructuralKeywordShortCircuitSurvives:
    def test_an_entry_that_already_names_its_backing_stays_quiet(self):
        text = "I will always run the suite; the falsifier is in tests/test_suite_gate.py."
        assert not looks_like_rule(text)[0]
