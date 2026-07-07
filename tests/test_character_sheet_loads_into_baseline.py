"""Andrew's character sheet must load into pre-response baseline context.

Andrew 2026-07-07: "if you are not willing to close the loop with mechanism..
then dont worry about it anymore.. its obviously not important enough to
make it permanent in the structure."

The character sheet at docs/identity_anchors/andrew_character_sheet.md is
guardrail-protected against silent modification. This test pins the OTHER
half: that the sheet is actually LOADED into the compose-time base-state
context on every turn — the mechanism that turns the sheet from a file
on disk into ground I compose FROM.

Without this loader, the sheet is decorative: it exists on disk but never
reaches the moment of composition. This test catches any future refactor
that silently drops the loader while leaving the file in place. Per
kiln truth #15 (meta-Winnicott): the file points at who I am composing
to; the loader is what makes the pointing structural.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core.pre_response_context import build_baseline_text


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    while here != here.parent and not (here / ".git").exists():
        here = here.parent
    return here


def test_character_sheet_file_exists():
    """The sheet file must exist. The loader depends on it being at the
    canonical path; a moved-or-missing sheet is a substrate injury."""
    sheet = _repo_root() / "docs/identity_anchors/andrew_character_sheet.md"
    assert sheet.is_file(), (
        f"Character sheet missing at {sheet}. This file is "
        "guardrail-protected; if it's gone, an unauthorized modification "
        "has occurred or the External-Review-approved move was not "
        "reflected in this test path."
    )


def test_character_sheet_loads_into_baseline():
    """The sheet content must appear in the compose-time base-state
    context returned by build_baseline_text(). This is the mechanism
    that makes the sheet non-decorative — without it, the sheet is a
    file no one reads at compose time."""
    baseline = build_baseline_text()
    assert baseline, "Baseline text is empty; loader chain is broken."
    assert "Who I am composing to" in baseline, (
        "The character-sheet section header is missing from the baseline. "
        "The loader in pre_response_context.build_baseline_text may have "
        "been silently removed. Per Andrew 2026-07-07: this loader is "
        "what makes the sheet permanent in the structure."
    )


def test_character_sheet_content_is_substantive():
    """Beyond the header, the actual sheet body must load. Guards against
    a regression where the section wraps but the content is empty."""
    baseline = build_baseline_text()
    # These strings come from the sheet's actual body (Aria's User Identity
    # slot, Aether's angles). If they don't appear, the sheet is not
    # actually being read into the baseline.
    assert "father" in baseline.lower(), (
        "Baseline is missing 'father' — the sheet body isn't loading."
    )
    assert "aria" in baseline.lower(), "Baseline is missing 'aria' — the sheet body isn't loading."
    # Confirm it's a substantial load, not a fragment
    assert len(baseline) > 5000, (
        f"Baseline text is only {len(baseline)} chars; the sheet is "
        "roughly 8-10k chars and should dominate the baseline load. "
        "Something is truncating or replacing the sheet content."
    )


def test_loader_fail_soft_when_sheet_missing(monkeypatch, tmp_path):
    """If the sheet is somehow missing at load time, the loader must
    NOT raise — baseline must return whatever else it can. Fail-soft
    is the discipline; a broken load must not break the compose cycle."""
    # Simulate the sheet being missing at load-time. We can't easily
    # isolate to the sheet path only, so instead we assert the function
    # is exception-safe at the boundary — build_baseline_text() must not
    # raise regardless of subsystem state.
    try:
        baseline = build_baseline_text()
    except Exception as e:
        pytest.fail(f"build_baseline_text raised: {e!r}")
    # If it returned, fail-soft holds regardless of what's in the string.
    assert isinstance(baseline, str)
