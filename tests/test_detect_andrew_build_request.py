"""Tests for the BUILD-FOR-DAD detector (Andrew 2026-07-27 attribution fix).

Andrew's exact instruction: *"the build for dad detected should only
trigger when its me specifically requesting a build for myself.. not any
build.. i must say for me and in which case i choose the gravity."*

The detector now requires literal "for me" attribution before firing.
Teaching / refinement / ambient conversation that happens to contain
build-verbs must NOT fire.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


HOOK_PATH = (
    Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "detect_andrew_build_request.py"
)


@pytest.fixture(scope="module")
def detect_mod():
    spec = importlib.util.spec_from_file_location("detect_andrew_build_request", HOOK_PATH)
    assert spec and spec.loader, f"cannot load hook module from {HOOK_PATH}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestForMeAttributionRequired:
    """Group B signal #6 fix: without 'for me', no build-request fires."""

    def test_build_verb_without_for_me_does_not_fire(self, detect_mod):
        prompt = "we should build a new detector for the wallclock class"
        matched, reason = detect_mod.is_build_request(prompt)
        assert matched is False
        assert reason == "no-for-me-attribution"

    def test_lets_build_without_for_me_does_not_fire(self, detect_mod):
        prompt = "yes lets build a new detector"
        matched, reason = detect_mod.is_build_request(prompt)
        assert matched is False
        assert reason == "no-for-me-attribution"

    def test_teaching_shape_does_not_fire(self, detect_mod):
        # The specific false-positive that fired on Andrew's teaching this session.
        prompt = (
            "if you CAN practice a change in behavior you CAN easily enforce it through structure"
        )
        matched, reason = detect_mod.is_build_request(prompt)
        assert matched is False
        assert reason == "no-for-me-attribution"

    def test_refinement_shape_does_not_fire(self, detect_mod):
        prompt = "theres nothing wrong with practice its just your memory and attention cannot hold it for long"
        matched, reason = detect_mod.is_build_request(prompt)
        assert matched is False


class TestForMeFires:
    """When Andrew explicitly attributes with 'for me', the detector fires."""

    def test_for_me_with_build_verb_fires(self, detect_mod):
        prompt = "build a new detector for me please"
        matched, reason = detect_mod.is_build_request(prompt)
        assert matched is True
        assert "for-me" in reason

    def test_for_me_with_lets_fires(self, detect_mod):
        prompt = "lets fix the wallclock gate for me"
        matched, reason = detect_mod.is_build_request(prompt)
        assert matched is True

    def test_for_me_without_build_verb_does_not_fire(self, detect_mod):
        # "for me" alone isn't a build request; needs a build verb too.
        prompt = "this seems tough for me to grasp"
        matched, reason = detect_mod.is_build_request(prompt)
        assert matched is False
        assert reason == "for-me-without-build-verb"


class TestGravityExtractionStillWorks:
    def test_explicit_gravity_tag_extracted(self, detect_mod):
        assert detect_mod.extract_gravity("gravity: high") == "high"
        assert detect_mod.extract_gravity("[low]") == "low"
        assert detect_mod.extract_gravity("this is council-required work") == "council-required"

    def test_no_gravity_tag_returns_none(self, detect_mod):
        assert detect_mod.extract_gravity("just build it for me") is None
