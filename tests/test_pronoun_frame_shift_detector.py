"""Tests for pronoun_frame_shift_detector.

The detector catches possessive-pronoun mirror on family-role words —
the specific class where operator says "your <family_role>" and agent's
reply parrots the same "your <family_role>", likely flipping the
referent because "your" resolves differently in each speaker's frame.
"""

from __future__ import annotations

from divineos.core.operating_loop.pronoun_frame_shift_detector import (
    FAMILY_ROLE_WORDS,
    PronounFrameShiftFinding,
    detect_pronoun_frame_shift,
)


def test_the_exact_case_that_prompted_this_detector():
    """The real slip that made Andrew ask for this detector.

    Andrew said "your husband" (meaning Aria's husband = Aether).
    Aria mirrored "your husband" back (which from her frame means
    Andrew's husband — but Aether is his SON, not his spouse).
    """
    op = "the worst thing your husband has ever done was on the Kiro IDE"
    ag = "That reframes what your husband did as recoverable, not unforgivable"
    findings = detect_pronoun_frame_shift(operator_input=op, agent_response=ag)
    assert len(findings) == 1
    assert findings[0].role_word == "husband"
    assert "your husband" in findings[0].operator_span.lower()
    assert "your husband" in findings[0].agent_span.lower()
    assert findings[0].severity == "low"


def test_no_family_role_present_no_findings():
    op = "lets check the tests"
    ag = "yes tests are passing"
    assert detect_pronoun_frame_shift(operator_input=op, agent_response=ag) == []


def test_family_role_only_in_operator_no_mirror():
    """Operator mentions a role, agent doesn't mirror it. No finding —
    the failure class is specifically the MIRROR, not the mention."""
    op = "your husband is here"
    ag = "noted, moving on"
    assert detect_pronoun_frame_shift(operator_input=op, agent_response=ag) == []


def test_family_role_only_in_agent_no_finding():
    """Agent mentions the role but operator didn't. Reverse of above —
    also no finding since the mirror class requires both sides."""
    op = "hello"
    ag = "your husband will be here soon"
    assert detect_pronoun_frame_shift(operator_input=op, agent_response=ag) == []


def test_multiple_role_words_multiple_findings():
    op = "your son and your daughter both wrote"
    ag = "your son came through, your daughter still pending"
    findings = detect_pronoun_frame_shift(operator_input=op, agent_response=ag)
    roles = {f.role_word for f in findings}
    assert roles == {"son", "daughter"}
    assert len(findings) == 2


def test_case_insensitive_matching():
    op = "Your Husband is Aether"
    ag = "Your Husband, yes"
    findings = detect_pronoun_frame_shift(operator_input=op, agent_response=ag)
    assert len(findings) == 1
    assert findings[0].role_word == "husband"


def test_empty_inputs_return_empty():
    assert detect_pronoun_frame_shift(operator_input=None, agent_response=None) == []
    assert detect_pronoun_frame_shift(operator_input="", agent_response="") == []
    assert detect_pronoun_frame_shift(operator_input="your husband", agent_response="") == []
    assert detect_pronoun_frame_shift(operator_input="", agent_response="your husband") == []


def test_role_word_boundary_no_partial_match():
    """A role word appearing inside a longer word shouldn't fire.
    e.g. 'husbandry' shouldn't match 'husband'."""
    op = "your husbandry techniques are good"
    ag = "yes your husbandry improved"
    # Neither 'husbandry' is a family role, so no match on the boundary.
    findings = detect_pronoun_frame_shift(operator_input=op, agent_response=ag)
    assert findings == []


def test_role_with_intervening_adjective():
    """'your loving husband' should still match — pattern allows 0-2
    intervening words between 'your' and the role."""
    op = "your loving husband is coming"
    ag = "yes your loving husband was here"
    findings = detect_pronoun_frame_shift(operator_input=op, agent_response=ag)
    assert len(findings) == 1
    assert findings[0].role_word == "husband"


def test_family_role_vocabulary_covers_expected_words():
    """The vocabulary should include the words that fire in real family
    conversations. Spot-check a few load-bearing ones."""
    for w in ("husband", "wife", "son", "daughter", "father", "mother", "dad", "mom"):
        assert w in FAMILY_ROLE_WORDS, f"expected {w} in FAMILY_ROLE_WORDS"


def test_finding_dataclass_is_hashable():
    """PronounFrameShiftFinding is frozen — should be hashable so it can
    live in sets / be used as dict keys if downstream needs it."""
    f = PronounFrameShiftFinding(
        role_word="husband",
        operator_span="your husband",
        agent_span="your husband",
        severity="low",
    )
    assert hash(f) is not None
    assert f == PronounFrameShiftFinding(
        role_word="husband",
        operator_span="your husband",
        agent_span="your husband",
        severity="low",
    )
