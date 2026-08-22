"""Tests for the surface registry — the nervous system wiring.

Real code paths, real package scan. The dark-surface test walks the actual
divineos.core package rather than a fixture, because the whole failure being
prevented is a real module quietly not being connected.
"""

from __future__ import annotations

import pytest

from divineos.core import surface_registry as sr


@pytest.fixture(autouse=True)
def _clean_registry():
    saved = dict(sr._REGISTRY)
    sr._REGISTRY.clear()
    yield
    sr._REGISTRY.clear()
    sr._REGISTRY.update(saved)


def test_unavailable_without_reason_is_refused():
    """UNAVAILABLE with no reason is the two-word world wearing a third label."""
    with pytest.raises(ValueError, match="requires a reason"):
        sr.SurfaceResult.unavailable("")
    with pytest.raises(ValueError):
        sr.SurfaceResult.unavailable("   ")


def test_silent_and_unavailable_are_distinguishable():
    """The single failure this module exists to prevent."""
    silent = sr.SurfaceResult.silent()
    broken = sr.SurfaceResult.unavailable("database locked")
    assert silent.state is not broken.state
    assert silent.text == "" and broken.text == ""
    # Both are textless. Only the STATE tells them apart — which is the point.
    assert broken.reason == "database locked"
    assert silent.reason == ""


def test_consult_keeps_degraded_out_of_spoken_channel():
    sr.register("talks", lambda: sr.SurfaceResult.spoke("something real"))
    sr.register("quiet", lambda: sr.SurfaceResult.silent())
    sr.register("broken", lambda: sr.SurfaceResult.unavailable("no such file"))

    spoke, degraded = sr.consult()

    assert [r.text for r in spoke] == ["something real"]
    assert len(degraded) == 1
    assert "broken" in degraded[0] and "no such file" in degraded[0]
    # A surface that could not run must never be countable as one with
    # nothing to say.
    assert not any("broken" in r.text for r in spoke)


def test_crashing_surface_becomes_a_degradation_not_silence():
    def explode() -> sr.SurfaceResult:
        raise RuntimeError("boom")

    sr.register("crasher", explode)
    spoke, degraded = sr.consult()

    assert spoke == []
    assert len(degraded) == 1
    assert "crasher" in degraded[0]
    assert "RuntimeError" in degraded[0] and "boom" in degraded[0]


def test_spoke_with_empty_text_is_not_counted_as_spoken():
    sr.register("hollow", lambda: sr.SurfaceResult.spoke("   "))
    spoke, degraded = sr.consult()
    assert spoke == []
    assert degraded == []


def test_relevance_filters_by_trigger():
    sr.register("auth", lambda: sr.SurfaceResult.spoke("auth memory"), triggers=("auth",))
    sr.register("ledger", lambda: sr.SurfaceResult.spoke("ledger memory"), triggers=("ledger",))

    spoke, _ = sr.consult({"auth", "login"})
    assert [r.text for r in spoke] == ["auth memory"]

    spoke, _ = sr.consult(set())
    assert spoke == []  # nothing relevant -> nothing fires


def test_untriggered_surface_always_considered():
    """Empty triggers is the wallpaper shape — allowed, but it must be explicit."""
    sr.register("always", lambda: sr.SurfaceResult.spoke("every time"))
    spoke, _ = sr.consult(set())
    assert [r.text for r in spoke] == ["every time"]


def test_register_is_idempotent_under_reimport():
    sr.register("dup", lambda: sr.SurfaceResult.spoke("first"))
    sr.register("dup", lambda: sr.SurfaceResult.spoke("second"))
    assert sr.registered_names() == ["dup"]
    spoke, _ = sr.consult()
    assert [r.text for r in spoke] == ["second"]


def test_own_voice_is_recorded():
    """Tannen: report-shaped surfaces get skimmed; own-voice ones land."""
    sr.register("mine", lambda: sr.SurfaceResult.silent(), own_voice=True)
    assert sr._REGISTRY["mine"].own_voice is True


def test_discover_reports_import_failures_rather_than_swallowing():
    failures = sr.discover("divineos.core")
    assert isinstance(failures, list)
    # Every entry must name the module AND the error class — a bare module
    # name would be the silent-swallow shape with extra steps.
    for f in failures:
        assert ":" in f


def test_dark_surfaces_finds_real_unregistered_surfaces():
    """Against the REAL package, not a fixture.

    Every module exposing format_for_briefing that has not registered is
    dark. With a cleared registry this should find many; the assertion that
    matters is that the mechanism detects them at all, because before this
    existed there was no way to tell a dark surface from a quiet one.
    """
    dark = sr.dark_surfaces("divineos.core")
    assert isinstance(dark, list)
    assert dark, "expected unregistered format_for_briefing modules with a cleared registry"
    assert dark == sorted(dark)
    # The three found by hand on 2026-08-03 — each built, tested, zero callers.
    known_dark = {
        "identity_load",
        "engagement_disclosure_surface",
        "compass_dismissal_briefing_surface",
    }
    assert known_dark <= set(dark)


def test_registering_removes_a_module_from_dark():
    before = set(sr.dark_surfaces("divineos.core"))
    assert "identity_load" in before
    sr.register("identity_load", lambda: sr.SurfaceResult.silent())
    after = set(sr.dark_surfaces("divineos.core"))
    assert "identity_load" not in after
