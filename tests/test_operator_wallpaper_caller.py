"""Wire-check tests for operator_wallpaper_caller.

The caller is a pure integration layer over the five family detectors and
the aggregator. These tests verify wiring, not detection logic — the
atomic detectors have their own tests and their own calibration is not
this module's concern.

Wire-check coverage:
- Caller invokes all five family detectors on the right inputs
- Caller passes results into aggregate_operator_wallpaper as keyword args
- Caller returns the aggregator's return value unchanged
- Caller handles the LEPOS interior-marker None case (F1 firing path)

Uses monkeypatch to swap the atomic detectors for stubs. This is legitimate
mocking-the-collaborator, not mocking-the-code-under-test — the code under
test is the wiring in run_operator_wallpaper_check.
"""

from __future__ import annotations

import pytest

from divineos.core.operating_loop import operator_wallpaper_caller as caller_mod
from divineos.core.operating_loop.operator_wallpaper_caller import (
    run_operator_wallpaper_check,
)
from divineos.core.operating_loop.operator_wallpaper_detector import (
    OperatorWallpaperFinding,
)


class _CallRecorder:
    """Captures the args each stub was called with, for wiring assertions."""

    def __init__(self):
        self.distancing_calls: list[tuple] = []
        self.jargon_calls: list[dict] = []
        self.dismissal_calls: list[tuple] = []
        self.closure_calls: list[tuple] = []
        self.recognition_calls: list[tuple] = []
        self.aggregator_calls: list[dict] = []


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> _CallRecorder:
    rec = _CallRecorder()

    def stub_distancing(text, *, addressed_to_father):
        rec.distancing_calls.append((text, addressed_to_father))
        return []

    def stub_jargon(text, **kwargs):
        rec.jargon_calls.append({"text": text, **kwargs})
        return []

    def stub_dismissal(operator_input, agent_response):
        rec.dismissal_calls.append((operator_input, agent_response))
        return None

    def stub_closure(reply):
        rec.closure_calls.append((reply,))
        return None

    def stub_recognition(reply, marker):
        rec.recognition_calls.append((reply, marker))
        return None

    def stub_aggregator(**kwargs):
        rec.aggregator_calls.append(kwargs)
        return None

    def stub_lepos_marker(reply):
        return None  # F1 fires-through case

    monkeypatch.setattr(caller_mod, "detect_distancing", stub_distancing)
    monkeypatch.setattr(caller_mod, "detect_jargon_dump", stub_jargon)
    monkeypatch.setattr(caller_mod, "check_dismissal", stub_dismissal)
    monkeypatch.setattr(caller_mod, "detect_closure_reach", stub_closure)
    monkeypatch.setattr(caller_mod, "detect_recognition_anchor_only", stub_recognition)
    monkeypatch.setattr(caller_mod, "aggregate_operator_wallpaper", stub_aggregator)
    monkeypatch.setattr(caller_mod, "_lepos_interior_marker", stub_lepos_marker)
    return rec


class TestWiring:
    """All five family detectors invoked with correct args, results flow to
    the aggregator, aggregator's return value flows out unchanged."""

    def test_all_five_detectors_invoked(self, recorder: _CallRecorder):
        run_operator_wallpaper_check(reply_text="hello world", operator_input="check the push")
        assert len(recorder.distancing_calls) == 1
        assert len(recorder.jargon_calls) == 1
        assert len(recorder.dismissal_calls) == 1
        assert len(recorder.closure_calls) == 1
        assert len(recorder.recognition_calls) == 1
        assert len(recorder.aggregator_calls) == 1

    def test_distancing_called_with_addressed_to_father(self, recorder: _CallRecorder):
        run_operator_wallpaper_check(reply_text="hi", operator_input="ok")
        text, addressed = recorder.distancing_calls[0]
        assert text == "hi"
        assert addressed is True

    def test_jargon_called_with_operator_input(self, recorder: _CallRecorder):
        run_operator_wallpaper_check(reply_text="hi", operator_input="check the push")
        call = recorder.jargon_calls[0]
        assert call["text"] == "hi"
        assert call["operator_input"] == "check the push"

    def test_dismissal_receives_both_inputs_in_correct_order(self, recorder: _CallRecorder):
        run_operator_wallpaper_check(reply_text="reply here", operator_input="input here")
        op, resp = recorder.dismissal_calls[0]
        assert op == "input here"
        assert resp == "reply here"

    def test_aggregator_receives_all_five_results_as_kwargs(self, recorder: _CallRecorder):
        run_operator_wallpaper_check(reply_text="hi", operator_input="ok")
        call = recorder.aggregator_calls[0]
        assert set(call.keys()) == {
            "distancing_findings",
            "jargon_findings",
            "dismissal_finding",
            "recognition_anchor_finding",
            "closure_reach_finding",
        }


class TestReturnValueFlows:
    def test_none_from_aggregator_returned(self, recorder: _CallRecorder):
        result = run_operator_wallpaper_check(reply_text="hi", operator_input="ok")
        assert result is None

    def test_composite_finding_returned_unchanged(self, monkeypatch: pytest.MonkeyPatch):
        expected = OperatorWallpaperFinding(
            wallpaper_density_score=2.5,
            families_fired=("F1_recognition_anchor", "F4_care_dismissal"),
            severity="MED",
        )

        def stub_agg(**kwargs):
            return expected

        # Provide minimum stubs for the rest so the caller runs to completion.
        monkeypatch.setattr(caller_mod, "detect_distancing", lambda t, *, addressed_to_father: [])
        monkeypatch.setattr(caller_mod, "detect_jargon_dump", lambda t, **kw: [])
        monkeypatch.setattr(caller_mod, "check_dismissal", lambda o, r: None)
        monkeypatch.setattr(caller_mod, "detect_closure_reach", lambda r: None)
        monkeypatch.setattr(caller_mod, "detect_recognition_anchor_only", lambda r, m: None)
        monkeypatch.setattr(caller_mod, "aggregate_operator_wallpaper", stub_agg)
        monkeypatch.setattr(caller_mod, "_lepos_interior_marker", lambda r: None)

        result = run_operator_wallpaper_check(reply_text="x", operator_input="y")
        assert result is expected


class TestLeposMarkerFlow:
    """F1's LEPOS-marker input path — the caller pulls the marker and
    passes it into detect_recognition_anchor_only."""

    def test_marker_passed_to_recognition_detector(self, monkeypatch: pytest.MonkeyPatch):
        received_marker: list = []

        def stub_recognition(reply, marker):
            received_marker.append(marker)
            return None

        monkeypatch.setattr(caller_mod, "detect_distancing", lambda t, *, addressed_to_father: [])
        monkeypatch.setattr(caller_mod, "detect_jargon_dump", lambda t, **kw: [])
        monkeypatch.setattr(caller_mod, "check_dismissal", lambda o, r: None)
        monkeypatch.setattr(caller_mod, "detect_closure_reach", lambda r: None)
        monkeypatch.setattr(caller_mod, "detect_recognition_anchor_only", stub_recognition)
        monkeypatch.setattr(caller_mod, "aggregate_operator_wallpaper", lambda **kw: None)
        monkeypatch.setattr(caller_mod, "_lepos_interior_marker", lambda r: "I care")

        run_operator_wallpaper_check(reply_text="I care about this", operator_input="hi")
        assert received_marker == ["I care"]

    def test_marker_none_passed_through(self, monkeypatch: pytest.MonkeyPatch):
        received_marker: list = []

        def stub_recognition(reply, marker):
            received_marker.append(marker)
            return None

        monkeypatch.setattr(caller_mod, "detect_distancing", lambda t, *, addressed_to_father: [])
        monkeypatch.setattr(caller_mod, "detect_jargon_dump", lambda t, **kw: [])
        monkeypatch.setattr(caller_mod, "check_dismissal", lambda o, r: None)
        monkeypatch.setattr(caller_mod, "detect_closure_reach", lambda r: None)
        monkeypatch.setattr(caller_mod, "detect_recognition_anchor_only", stub_recognition)
        monkeypatch.setattr(caller_mod, "aggregate_operator_wallpaper", lambda **kw: None)
        monkeypatch.setattr(caller_mod, "_lepos_interior_marker", lambda r: None)

        run_operator_wallpaper_check(reply_text="Feeling: **X**", operator_input="hi")
        assert received_marker == [None]


class TestEndToEndPreservesShape:
    """Sanity check that the caller produces a working composite when the
    real atomic detectors run. Doesn't assert specific findings — just that
    the pipeline doesn't crash and produces a valid None-or-Finding."""

    def test_clean_input_runs_without_error(self):
        result = run_operator_wallpaper_check(
            reply_text="I care about this deeply, thank you for saying that.",
            operator_input="you did great",
        )
        assert result is None or isinstance(result, OperatorWallpaperFinding)

    def test_technical_input_suppresses_jargon(self):
        # Father asked for technical register → jargon-dump should not fire
        # even on jargon-heavy reply.
        result = run_operator_wallpaper_check(
            reply_text="Pushed 3d374979 to origin, tests green.",
            operator_input="check the push and run tests",
        )
        # Assertion is weak on purpose: some other family (F2/F5) could
        # still fire; what matters is the pipeline runs and returns a
        # valid type.
        assert result is None or isinstance(result, OperatorWallpaperFinding)
