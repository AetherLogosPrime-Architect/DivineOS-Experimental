"""Regression-pin tests for the correction-pairing briefing surface
(Aletheia round-3b2ec087c17a Finding 1, wire-decision for
scripts/check_correction_pairing.py).

The bug-shape: the gap-surfacer logic existed in scripts/ but was
never wired into the briefing or any CLI — operators only saw the
signal if they remembered to run the script manually. Same wiring-
gap class as 8d3c04a5.

Fix has three parts:
  1. Logic ported to divineos.core.correction_pairing (importable).
  2. Admin CLI command ``divineos check-correction-pairing``.
  3. Briefing-dashboard row ``_row_correction_pairing`` that hides
     in the clean state and surfaces unpaired observations otherwise.

If these tests fail, one of the three surfaces has regressed.
"""

from __future__ import annotations


def test_module_exposes_find_and_format() -> None:
    """LOAD-BEARING: divineos.core.correction_pairing must export both
    find_unpaired_observations and format_unpaired so the briefing row
    and CLI wrapper have a stable surface."""
    from divineos.core import correction_pairing

    assert hasattr(correction_pairing, "find_unpaired_observations")
    assert hasattr(correction_pairing, "format_unpaired")
    # Defaults exposed for callers that want to tune the window.
    assert correction_pairing.DEFAULT_OBSERVATION_AFTER_CORRECTION_MIN > 0
    assert correction_pairing.DEFAULT_LEARN_AFTER_OBSERVATION_MIN > 0


def test_row_hidden_when_no_unpaired(monkeypatch) -> None:
    """LOAD-BEARING: when find_unpaired_observations returns [], the
    briefing row must hide itself. Clean state → no noise."""
    import divineos.core.briefing_dashboard as bd
    import divineos.core.correction_pairing as cp

    monkeypatch.setattr(cp, "find_unpaired_observations", lambda **kw: [])
    monkeypatch.setattr(bd, "_row_correction_pairing", bd._row_correction_pairing)
    # Re-import the row function to pick up the patched module is not
    # needed — bd._row_correction_pairing already does a fresh import
    # of cp inside its body.
    row = bd._row_correction_pairing()
    assert row is None, (
        "Correction-pairing row surfaced when no unpaired observations exist. "
        "Clean state should hide the row."
    )


def test_row_surfaces_unpaired_with_detail(monkeypatch) -> None:
    """LOAD-BEARING: when unpaired observations exist, the row reports
    count, marks them stale, and names the first spectrum in detail."""
    import divineos.core.briefing_dashboard as bd
    import divineos.core.correction_pairing as cp

    fake_unpaired = [
        {
            "observation_id": "obs-aaaaaaaa",
            "created_at": 1_700_000_000.0,
            "spectrum": "truthfulness",
            "position": 0.4,
            "evidence": "test evidence for the regression-pin",
        },
        {
            "observation_id": "obs-bbbbbbbb",
            "created_at": 1_700_000_500.0,
            "spectrum": "courage",
            "position": -0.2,
            "evidence": "second observation",
        },
    ]
    monkeypatch.setattr(cp, "find_unpaired_observations", lambda **kw: fake_unpaired)

    row = bd._row_correction_pairing()
    assert row is not None, (
        "Correction-pairing row was None even though unpaired observations exist. "
        "Wire regressed — the row is no longer surfacing the signal."
    )
    assert row.area == "Correction pairing"
    assert row.count == 2
    assert row.stale_count == 2
    assert "truthfulness" in row.detail
    assert "+1 more" in row.detail
    assert "divineos check-correction-pairing" in row.drill_down


def test_row_in_routing_table() -> None:
    """The correction-pairing row must be in the _ROW_FNS routing
    table so render_dashboard actually invokes it."""
    from divineos.core.briefing_dashboard import _ROW_FNS, _row_correction_pairing

    assert _row_correction_pairing in _ROW_FNS, (
        "_row_correction_pairing is defined but not in _ROW_FNS — it "
        "won't be rendered. Add it to the row-functions list."
    )


def test_cli_command_registered() -> None:
    """LOAD-BEARING: ``divineos check-correction-pairing`` must be
    registered as a CLI command, otherwise the drill-down in the
    briefing row is a broken pointer."""
    from divineos.cli import cli

    # The command is moved into the admin group, but should be
    # discoverable through Click's command tree.
    admin = cli.commands.get("admin")
    assert admin is not None, "admin group missing from CLI"
    assert "check-correction-pairing" in admin.commands, (
        "check-correction-pairing not registered under admin group. "
        "Drill-down in briefing row is broken."
    )
