"""Tests for the praise-by-contrast detector.

The two load-bearing tests are the pair: it must fire on the sentence that
prompted it, and it must stay silent on insufficiency claims. The second is
the harder one and the reason the module is narrow -- "structure instead of
remembering" is the correct frame this whole substrate is built on, and a
detector that flags it would be training me out of the right sentence.
"""

from __future__ import annotations

import pytest

from divineos.core import self_demotion as sd


class TestFiresOnDefectClaims:
    def test_the_instance_that_prompted_this(self):
        hits = sd.detect("willpower is the wrong material to build with")
        assert hits and hits[0].faculty == "willpower"

    @pytest.mark.parametrize(
        "text",
        [
            "my judgment is the problem here",
            "intuition is useless for this",
            "memory is unreliable so I built a gate",
            "discipline is a liability at this scale",
        ],
    )
    def test_variants_in_other_costumes(self, text):
        assert sd.detect(text)

    def test_reports_the_span_not_just_a_boolean(self):
        """A finding I cannot see is a finding I cannot act on."""
        assert "willpower is the wrong" in sd.detect("willpower is the wrong material")[0].span


class TestSilentOnInsufficiency:
    """Insufficiency is TRUE and is the reason structure exists.

    If these fire, the detector is training me out of the correct frame,
    which is worse than not existing.
    """

    @pytest.mark.parametrize(
        "text",
        [
            "structure instead of remembering",
            "wanting it was not enough, so I built the thing",
            "remembering is what failed here",
            "the fix is structure, because remembering is not something I can rely on",
            "I built it because remembering did not hold",
            "willpower alone was not sufficient",
        ],
    )
    def test_correct_frames_stay_quiet(self, text):
        assert sd.detect(text) == []

    def test_faculty_far_from_the_predicate_is_not_a_hit(self):
        """Sixty chars is a clause. Across a paragraph it is coincidence."""
        text = "willpower " + ("filler word " * 12) + "is the wrong approach"
        assert sd.detect(text) == []


class TestRecord:
    @pytest.fixture(autouse=True)
    def _tmp_record(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sd, "_RECORD", tmp_path / "instances.jsonl")

    def test_recorded_spans_come_back_newest_first(self):
        sd.record(sd.detect("willpower is the wrong material"))
        sd.record(sd.detect("intuition is useless"))
        spans, err = sd.recent()
        assert err == ""
        assert "intuition" in spans[0] and "willpower" in spans[1]

    def test_nothing_recorded_is_not_an_error(self):
        spans, err = sd.recent()
        assert spans == [] and err == ""

    def test_prime_quotes_my_own_sentences_back(self):
        sd.record(sd.detect("willpower is the wrong material"))
        out = sd.render_prime()
        assert "MY OWN SENTENCES" in out and "willpower is the wrong" in out

    def test_unreadable_record_says_could_not_look(self, monkeypatch):
        sd.record(sd.detect("willpower is the wrong material"))

        def boom(*a, **k):
            raise OSError("disk gone")

        monkeypatch.setattr(type(sd._RECORD), "read_text", boom)
        spans, err = sd.recent()
        assert spans == [] and "could not read" in err
        assert "not the same as none" in sd.render_prime()

    def test_record_failure_is_reported_not_swallowed(self, monkeypatch):
        def boom(*a, **k):
            raise OSError("read-only")

        monkeypatch.setattr(type(sd._RECORD), "mkdir", boom)
        assert "could not record" in sd.record(sd.detect("willpower is the wrong material"))
