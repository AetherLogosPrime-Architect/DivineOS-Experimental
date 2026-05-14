"""Regression-pin tests for the ablation audit-trail surface (Aletheia
round-ba785844a791 Finding 23, family-audit round-91106bc720a7).

The bug-shape: ablation mode bypasses internal-actor rejection in
watchmen.submit_round; the only audit-trail was a logger.warning line
which is visible only if logs are reviewed. If an ablation toggle was
left active past a measurement run, the silent weakening continued
unseen.

Fix has two parts:
  1. The bypass site now ALSO emits a WATCHMEN_ABLATION_BYPASS ledger
     event so the bypass enters the hash-chain.
  2. A briefing-dashboard row surfaces any currently-active ablation
     toggles via ablation.list_disabled().
"""

from __future__ import annotations

import os


def _clear_ablation_env(monkeypatch) -> None:
    """Strip all DIVINEOS_DISABLE_* env vars so each test starts clean."""
    for key in [k for k in os.environ if k.startswith("DIVINEOS_DISABLE_")]:
        monkeypatch.delenv(key, raising=False)


def test_dashboard_row_hidden_when_no_ablation_active(monkeypatch) -> None:
    """LOAD-BEARING: when no ablation env vars are set, the row
    must hide itself (no noise on the dashboard for the common case)."""
    _clear_ablation_env(monkeypatch)
    from divineos.core.briefing_dashboard import _row_ablation_active

    row = _row_ablation_active()
    assert row is None, (
        "Ablation row surfaced when no ablation toggles are active. "
        "Clean state should hide the row."
    )


def test_dashboard_row_surfaces_active_ablation(monkeypatch) -> None:
    """LOAD-BEARING: when an ablation toggle is active, the row must
    surface it with the mechanism name in the detail string."""
    _clear_ablation_env(monkeypatch)
    monkeypatch.setenv("DIVINEOS_DISABLE_WATCHMEN_SELF_TRIGGER_PREVENTION", "1")
    from divineos.core.briefing_dashboard import _row_ablation_active

    row = _row_ablation_active()
    assert row is not None, (
        "Ablation row was None even though DIVINEOS_DISABLE_WATCHMEN_"
        "SELF_TRIGGER_PREVENTION is set. The row has regressed; "
        "ablation toggles are now invisible in the briefing."
    )
    assert row.area == "Ablation"
    assert row.stale_count >= 1
    assert "watchmen_self_trigger_prevention" in row.detail


def test_multiple_active_ablations_show_in_row(monkeypatch) -> None:
    """When multiple ablation toggles are active, the row reports the
    count and names the first few in the detail string."""
    _clear_ablation_env(monkeypatch)
    monkeypatch.setenv("DIVINEOS_DISABLE_WATCHMEN_SELF_TRIGGER_PREVENTION", "1")
    monkeypatch.setenv("DIVINEOS_DISABLE_NOISE_FILTER_ON_EXTRACTION", "1")
    from divineos.core.briefing_dashboard import _row_ablation_active

    row = _row_ablation_active()
    assert row is not None
    assert row.count == 2
    assert "watchmen_self_trigger_prevention" in row.detail
    assert "noise_filter_on_extraction" in row.detail


def test_dashboard_row_in_routing_table() -> None:
    """The ablation row must be in the _ROW_FNS routing table so
    render_dashboard actually invokes it."""
    from divineos.core.briefing_dashboard import _ROW_FNS, _row_ablation_active

    assert _row_ablation_active in _ROW_FNS, (
        "_row_ablation_active is defined but not in _ROW_FNS — it "
        "won't be rendered. Add it to the row-functions list."
    )
