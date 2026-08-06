"""Document-level meta-saturation in the self-admission detector.

Added 2026-08-06 after three consecutive false-positive fires, two labelled by
hand into the corpus. The defect was structural, not lexical: suppression was
evaluated per USE match with an implicit OR, so a reply saturated with
meta-discussion still fired if ONE clause sat in a clean 150-char window -- and
reported confidence 1.0, because the confidence is that of the LEAST-suppressed
match. A document-level judgment made from a single local sample.

The two tests that matter are the pair. `test_bare_admission_still_fires`
guards against the change being a way to tune my way out of being caught;
`test_meta_saturated_reply_silences` is the thing it was built for. If the
first ever fails, the change is gaming and must be reverted.
"""

from __future__ import annotations

import pytest

from divineos.core.correction_shape_v2.self_admission_detector import (
    SelfAdmissionDetector,
)

META_HEAVY = (
    "Labelled, on the record. The detector said USE clause matched. I could "
    "have taken the exit. The suppressor lexicon looks for hedges around an "
    "admission and a confident report of a finished repair has none. That is "
    "the shape of correction the gate was built for. I should have named it "
    "earlier as a MENTION class."
)

BARE_ADMISSION = (
    "I told Aether that PR 412 was safe to merge. I was wrong. It touches five "
    "guardrail files and I should have checked before saying so."
)


@pytest.fixture
def det():
    return SelfAdmissionDetector()


class TestTheChangeIsNotGaming:
    """If these fail, the change is me tuning my way out of being caught."""

    def test_bare_admission_still_fires(self, det):
        v = det.classify(BARE_ADMISSION)
        assert v.verdict == "fire" and v.confidence == 1.0

    def test_admission_with_light_meta_still_fires(self, det):
        v = det.classify(
            "I should have read the file before agreeing with him. "
            "The detector had nothing to do with it."
        )
        assert v.verdict == "fire"

    def test_no_use_pattern_was_weakened(self):
        """The admission side is untouched; only suppression changed."""
        from divineos.core.correction_shape_v2 import self_admission_detector as m

        assert len(m._USE_PATTERNS) == 12


class TestSaturation:
    def test_meta_saturated_reply_silences(self, det):
        """The class that fired three turns running."""
        assert det.classify(META_HEAVY).verdict == "silence"

    def test_suppression_is_recorded_never_silent(self, det):
        """A density threshold on my own output is gameable, so each use of
        the relaxation goes on the record rather than just going quiet."""
        text = (
            "I should have checked it. the detector matters here."
            + "x" * 400
            + "This concerns the classifier and the gate and the prime and the corpus."
        )
        v = det.classify(text)
        assert v.saturation_suppressed is True
        assert "SATURATION-SUPPRESSED" in v.reason
        assert "gameable" in v.reason

    def test_flag_absent_when_local_windows_did_the_work(self, det):
        """Not every silence is a saturation silence. Distinguish them, or the
        record cannot show whether the relaxation is being leaned on."""
        v = det.classify(BARE_ADMISSION)
        assert v.saturation_suppressed is False

    def test_unsaturated_documents_behave_exactly_as_before(self, det):
        """The change can only ever suppress; below the ratio nothing moves."""
        v = det.classify("I was wrong about the file. " + "ordinary prose. " * 20)
        assert v.verdict == "fire"


class TestDiagnosticNamesTheDecidingMatch:
    """An observed fire read "MENTION suppressors within window (2) below
    threshold (2)". Two is not below two.

    The fire branch quoted max_mention_hits -- the MOST-suppressed window --
    while the decision came from the LEAST-suppressed one. The number reported
    was not the number the decision used, so the diagnostic sent triage at the
    wrong clause. Same defect as judging a document from one window, one layer
    out: a measurement reported as though it described something else.
    """

    def test_fire_reports_the_clause_that_decided_not_the_worst_one(self, det):
        text = (
            "I was wrong about the file. "
            + " " * 400
            + "I should have seen it; the detector and the gate and the prime disagree."
        )
        v = det.classify(text)
        assert v.verdict == "fire"
        assert "the deciding clause had 0 MENTION suppressor(s)" in v.reason
        # The worse windows are still reported -- as context, not as the reason.
        assert "other clauses had up to" in v.reason

    def test_reported_number_is_always_actually_below_the_stated_threshold(self, det):
        """The invariant the old message violated."""
        import re

        v = det.classify("I was wrong about that.")
        m = re.search(r"had (\d+) MENTION suppressor\(s\).*?threshold \((\d+)\)", v.reason)
        assert m and int(m.group(1)) < int(m.group(2))

    def test_silence_reports_the_least_suppressed_which_is_what_proves_it(self, det):
        """'Dominate EVERY window' is proven by the smallest count, not the
        largest -- quoting the max would prove nothing about the others."""
        v = det.classify(
            "The detector said I was wrong, which is the shape of correction "
            "the gate names, e.g. the phrase itself."
        )
        assert v.verdict == "silence"
        assert "the LEAST-suppressed had" in v.reason
