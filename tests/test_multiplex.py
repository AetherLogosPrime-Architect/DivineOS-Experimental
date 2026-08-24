"""Tests for multiplex briefing architecture (MVP).

Covers prereg-ebee9082d201 falsifiers testable at unit level.
"""

from __future__ import annotations

from divineos.core.multiplex_panels import KNOWN_CONTEXTS, Panel, Tier, build_panels
from divineos.core.multiplex_renderer import (
    PANEL_MAX_CHARS,
    PANEL_MIN_CHARS,
    TOTAL_ALWAYS_ESSENTIAL_BUDGET_CHARS,
    render_multiplex,
    render_panel,
)
from divineos.core.multiplex_voice import check_voice, gate_render


def test_voice_clean_passes():
    assert check_voice("I decided to file. I am working.").passed


def test_voice_aether_third_person_fails():
    assert not check_voice("Aether decided to file.").passed


def test_voice_you_second_person_fails():
    assert not check_voice("You decided to file.").passed


def test_voice_label_colon_fails():
    assert not check_voice("Compass: 3 drifting").passed


def test_voice_drill_down_more_whitelisted():
    assert check_voice("I see three things. More: divineos compass").passed


def test_gate_passes_clean():
    out, r = gate_render("I am working. More: divineos hud", "t")
    assert r.passed and out == "I am working. More: divineos hud"


def test_gate_blocks_violation():
    out, r = gate_render("Aether did it.", "t")
    assert not r.passed and "VOICE-RULE-VIOLATION" in out


def test_compass_always_present():
    for ctx in KNOWN_CONTEXTS:
        panels = build_panels(ctx)
        assert any(p.name == "compass" for p in panels), ctx


def test_eight_always_essentials():
    """8 always-essential panels as of 2026-08-19.
    Original prereg-ebee9082d201 spec called for 5 always-essentials;
    the 6th (survival_link) was added per Aletheia consult + Andrew's
    morning-arc on substrate-level death-path-walking; the 7th
    (husbandman_work) was added evening of 2026-05-18 per Aria's
    request for a hard-day anchor pointing at her exploration entry.
    The 8th (component register) landed with c68fe234 on 2026-08-18 and
    this count was not updated with it, so the suite went red on the next
    full run -- caught by the pre-push gate rather than at the commit that
    caused it.

    The 9th arrived by MERGE, 2026-08-24, and is the same lesson from a new
    direction: both trees added an 8th independently -- component_register on
    main, owed_fixes here -- so the merged set is nine and neither side's
    count was wrong when it was written. A number that describes a set two
    people can both extend goes stale without anyone editing it."""
    for ctx in KNOWN_CONTEXTS:
        panels = build_panels(ctx)
        always = [p for p in panels if p.tier == Tier.ALWAYS]
        assert len(always) == 9, (
            f"Expected 9 always-essential panels in context {ctx!r}, got {len(always)}. "
            f"If a panel was intentionally added or removed, update this test."
        )


def test_chatting_includes_family_state():
    names = [p.name for p in build_panels("chatting")]
    assert "family_state" in names
    assert "corrections" not in names


def test_designing_includes_corrections():
    names = [p.name for p in build_panels("designing")]
    assert "corrections" in names
    assert "commitments" in names


def test_unknown_context_falls_back():
    g = [p.name for p in build_panels("garbage")]
    c = [p.name for p in build_panels("chatting")]
    assert g == c


def test_render_has_separators():
    # 9 always + 2 sometimes-essential in 'designing' context = 11 panels = 10 separators
    # (9 since the 2026-08-24 merge brought both trees' eighth panel together)
    out = render_multiplex(build_panels("designing"))
    assert out.count("-" * 60) == 10


def test_render_has_drill_downs():
    # 9 always + 2 sometimes-essential in 'designing' context = 11 'More: ' lines
    out = render_multiplex(build_panels("designing"))
    assert out.count("More: ") == 11


def test_render_empty_returns_empty():
    assert render_multiplex([]) == ""


def test_oversize_panel_violation():
    big = Panel(name="x", tier=Tier.ALWAYS, content="x" * 600, drill_down="d")
    _, ok = render_panel(big)
    assert not ok


def test_undersize_panel_violation():
    tiny = Panel(name="x", tier=Tier.ALWAYS, content="x" * 50, drill_down="d")
    _, ok = render_panel(tiny)
    assert not ok


def test_budget_violation_fires():
    six_big = [
        Panel(name=str(i), tier=Tier.ALWAYS, content="x" * 450, drill_down="d") for i in range(6)
    ]
    out = render_multiplex(six_big)
    assert "BUDGET-RULE-VIOLATION" in out


def test_missing_drill_down_violation():
    no_drill = Panel(name="x", tier=Tier.ALWAYS, content="x" * 100, drill_down="")
    _, ok = render_panel(no_drill)
    assert not ok


def test_all_panels_pass_voice():
    for ctx in KNOWN_CONTEXTS:
        for p in build_panels(ctx):
            assert check_voice(p.content).passed


def test_all_panels_fit_size():
    for ctx in KNOWN_CONTEXTS:
        for p in build_panels(ctx):
            assert PANEL_MIN_CHARS <= len(p.content)
            assert len(p.content) <= PANEL_MAX_CHARS


def test_total_budget_within_limit():
    for ctx in KNOWN_CONTEXTS:
        always = [p for p in build_panels(ctx) if p.tier == Tier.ALWAYS]
        total = sum(len(p.content) for p in always)
        assert total <= TOTAL_ALWAYS_ESSENTIAL_BUDGET_CHARS
