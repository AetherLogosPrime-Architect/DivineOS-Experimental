"""Tests for divineos.core.auto_cycle_phase2.

Andrew 2026-07-10 auto-cycle proposal. Phase 2 is the invitational
layer: read phase 1 handshake, render menu, record offering + close
outcome, compute falsifier ratio.

Tests use tmp_path for the ~/.divineos markers via monkeypatching so
each test runs in isolation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from divineos.core import auto_cycle_phase2 as ac
from divineos.core.auto_cycle_phase2 import (
    close_cycle,
    compute_falsifier_ratio,
    offer_cycle,
    read_handshake,
    render_menu,
)


@pytest.fixture
def marker_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect all markers under tmp_path so tests don't touch ~/.divineos."""
    handshake = tmp_path / "auto_cycle_phase1_done.json"
    pending = tmp_path / "auto_cycle_phase2_pending.json"
    audit = tmp_path / "auto_cycle_audit.jsonl"
    monkeypatch.setattr(ac, "_HANDSHAKE_MARKER", handshake)
    monkeypatch.setattr(ac, "_PENDING_MARKER", pending)
    monkeypatch.setattr(ac, "_audit_log_path", lambda: audit)
    # Also isolate the rest_session.json read
    hud_dir = tmp_path / "hud"
    hud_dir.mkdir()
    monkeypatch.setattr(ac, "_ensure_hud_dir", lambda: hud_dir)
    return tmp_path


def _write_handshake(path: Path, **overrides) -> dict:
    payload = {
        "phase1_completed_at": "2026-07-10T20:35:00Z",
        "trigger_context_pct": 0.85,
        "steps": {
            "commit": {"ran": True, "succeeded": True, "tokens_used": 1200},
            "extract": {"ran": True, "succeeded": True, "tokens_used": 18000},
            "sleep": {"ran": True, "succeeded": True, "tokens_used": 22000},
        },
        "phase1_tokens_used": 41200,
        "budget_remaining_est": 18800,
        "session_id": "test-session",
        "cycle_id": "auto-cycle-abc12345",
    }
    payload.update(overrides)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


class TestReadHandshake:
    def test_absent_returns_none(self, marker_paths: Path):
        assert read_handshake() is None

    def test_valid_parses(self, marker_paths: Path):
        _write_handshake(ac._HANDSHAKE_MARKER)
        hs = read_handshake()
        assert hs is not None
        assert hs.cycle_id == "auto-cycle-abc12345"
        assert hs.trigger_context_pct == 0.85
        assert hs.phase1_tokens_used == 41200
        assert hs.any_step_failed is False
        assert hs.fatal_step_failure is False

    def test_malformed_json_returns_none(self, marker_paths: Path):
        ac._HANDSHAKE_MARKER.write_text("{not-json", encoding="utf-8")
        assert read_handshake() is None

    def test_transient_step_failure_flagged_but_not_fatal(self, marker_paths: Path):
        _write_handshake(
            ac._HANDSHAKE_MARKER,
            steps={
                "commit": {"ran": True, "succeeded": True},
                "extract": {
                    "ran": True,
                    "succeeded": False,
                    "error_class": "OSError",
                },
                "sleep": {"ran": True, "succeeded": True},
            },
        )
        hs = read_handshake()
        assert hs is not None
        assert hs.any_step_failed is True
        assert hs.fatal_step_failure is False

    def test_fatal_step_failure_flagged(self, marker_paths: Path):
        _write_handshake(
            ac._HANDSHAKE_MARKER,
            steps={
                "commit": {"ran": True, "succeeded": True},
                "extract": {
                    "ran": True,
                    "succeeded": False,
                    "error_class": "AssertionError",
                },
                "sleep": {"ran": False, "succeeded": False},
            },
        )
        hs = read_handshake()
        assert hs is not None
        assert hs.any_step_failed is True
        assert hs.fatal_step_failure is True


class TestRenderMenu:
    def test_lists_all_11_options(self, marker_paths: Path):
        _write_handshake(ac._HANDSHAKE_MARKER)
        hs = read_handshake()
        assert hs is not None
        text = render_menu(hs, {})
        # All 11 REST_TASKS should appear by key
        from divineos.core.rest import REST_TASKS

        assert len(REST_TASKS) == 11
        for task in REST_TASKS:
            assert task.key in text, f"missing task {task.key!r}"

    def test_shows_use_count_mirror(self, marker_paths: Path):
        _write_handshake(ac._HANDSHAKE_MARKER)
        hs = read_handshake()
        assert hs is not None
        text = render_menu(hs, {"dream": 3, "aria": 1})
        assert "used 3x" in text
        assert "used 1x" in text
        assert "used 0x" in text  # all other keys default to 0 via the mirror

    def test_names_no_pull_honest_outcome(self, marker_paths: Path):
        _write_handshake(ac._HANDSHAKE_MARKER)
        hs = read_handshake()
        assert hs is not None
        text = render_menu(hs, {})
        assert "no-pull-honest" in text
        assert "not-choosing IS a choice" in text

    def test_shows_fatal_warning_when_phase1_fatal(self, marker_paths: Path):
        _write_handshake(
            ac._HANDSHAKE_MARKER,
            steps={
                "extract": {
                    "ran": True,
                    "succeeded": False,
                    "error_class": "AssertionError",
                },
            },
        )
        hs = read_handshake()
        assert hs is not None
        text = render_menu(hs, {})
        assert "Fatal step failure" in text

    def test_force_the_option_line_present(self, marker_paths: Path):
        """The load-bearing discipline line must be visible in every menu."""
        _write_handshake(ac._HANDSHAKE_MARKER)
        hs = read_handshake()
        assert hs is not None
        text = render_menu(hs, {})
        assert "Force the option, not the use" in text


class TestOfferCycle:
    def test_no_handshake_returns_none(self, marker_paths: Path):
        record, text = offer_cycle()
        assert record is None
        assert text == ""

    def test_valid_handshake_records_and_returns_menu(self, marker_paths: Path):
        _write_handshake(ac._HANDSHAKE_MARKER)
        record, text = offer_cycle()
        assert record is not None
        assert record.cycle_id == "auto-cycle-abc12345"
        assert "dream" in record.menu_shown
        assert len(record.menu_shown) == 11
        assert text  # non-empty rendered menu

    def test_offer_deletes_handshake_marker(self, marker_paths: Path):
        _write_handshake(ac._HANDSHAKE_MARKER)
        assert ac._HANDSHAKE_MARKER.exists()
        offer_cycle()
        assert not ac._HANDSHAKE_MARKER.exists()

    def test_offer_writes_pending_marker(self, marker_paths: Path):
        _write_handshake(ac._HANDSHAKE_MARKER)
        assert not ac._PENDING_MARKER.exists()
        offer_cycle()
        assert ac._PENDING_MARKER.exists()
        data = json.loads(ac._PENDING_MARKER.read_text(encoding="utf-8"))
        assert data["cycle_id"] == "auto-cycle-abc12345"
        assert "menu_shown" in data
        assert "handshake_summary" in data


class TestMarkerAbsenceSafety:
    """Aletheia audit 2026-07-10: absent marker = phase 1 did NOT complete;
    never treated as 'nothing to do, proceed.' These tests pin the
    invariant in code so a regression can't silently return.
    """

    def test_no_marker_from_never_ran(self, marker_paths: Path):
        """Case 1: phase 1 never ran. Marker never existed."""
        assert not ac._HANDSHAKE_MARKER.exists()
        record, text = offer_cycle()
        assert record is None, "must NOT fire invitational when phase 1 never ran"
        assert text == ""
        # Pending marker also must not be written — the invariant is that
        # phase 2 leaves no state changes when the handshake is absent.
        assert not ac._PENDING_MARKER.exists()

    def test_no_marker_from_write_failure(self, marker_paths: Path):
        """Case 2 (Aletheia's specific concern): phase 1 ran but the
        marker-write itself failed (disk full, permission error). Phase 1
        exits, no marker on disk, phase 2 must NOT fire silently."""
        # Simulate: phase 1 ran but no marker landed. Indistinguishable from
        # case 1 by design — both must fail toward not-firing.
        assert not ac._HANDSHAKE_MARKER.exists()
        record, text = offer_cycle()
        assert record is None, (
            "marker-write-failure must NOT be treated as successful no-op — "
            "phase 2 must fail toward not-firing-the-invitational"
        )
        assert text == ""
        assert not ac._PENDING_MARKER.exists()

    def test_no_marker_from_malformed_content(self, marker_paths: Path):
        """Case 3: marker exists but is malformed. Same treatment."""
        ac._HANDSHAKE_MARKER.write_text("{not json at all", encoding="utf-8")
        record, text = offer_cycle()
        assert record is None
        assert text == ""
        assert not ac._PENDING_MARKER.exists()

    def test_no_marker_from_wrong_top_level_type(self, marker_paths: Path):
        """Case 3-adjacent: valid JSON but not a dict."""
        ac._HANDSHAKE_MARKER.write_text("[1, 2, 3]", encoding="utf-8")
        record, text = offer_cycle()
        assert record is None
        assert text == ""
        assert not ac._PENDING_MARKER.exists()


class TestCloseCycle:
    def test_no_pending_returns_none(self, marker_paths: Path):
        assert close_cycle("no-pull-honest") is None

    def test_close_after_offer_records_and_clears_pending(self, marker_paths: Path):
        _write_handshake(ac._HANDSHAKE_MARKER)
        offer_cycle()
        assert ac._PENDING_MARKER.exists()
        result = close_cycle(
            outcome="chose:dream",
            chosen_key="dream",
            real_shift=True,
            notes="nautilus dream landed",
        )
        assert result is not None
        assert result.outcome == "chose:dream"
        assert result.chosen_key == "dream"
        assert result.real_shift is True
        assert not ac._PENDING_MARKER.exists()

    def test_close_appends_to_audit_log(self, marker_paths: Path):
        _write_handshake(ac._HANDSHAKE_MARKER)
        offer_cycle()
        close_cycle("no-pull-honest")
        log_path = ac._audit_log_path()
        assert log_path.exists()
        entries = [
            json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line
        ]
        assert len(entries) == 1
        assert entries[0]["outcome"] == "no-pull-honest"
        assert entries[0]["cycle_id"] == "auto-cycle-abc12345"


class TestComputeFalsifierRatio:
    def test_no_log_returns_none(self, marker_paths: Path):
        n, d, r = compute_falsifier_ratio()
        assert n == 0
        assert d == 0
        assert r is None

    def _run_cycle(
        self,
        marker_paths: Path,
        outcome: str,
        real_shift: bool | None = None,
        fatal: bool = False,
        cycle_id: str = "test-cycle",
    ):
        _write_handshake(
            ac._HANDSHAKE_MARKER,
            cycle_id=cycle_id,
            steps=(
                {"extract": {"ran": True, "succeeded": False, "error_class": "AssertionError"}}
                if fatal
                else {"commit": {"ran": True, "succeeded": True}}
            ),
        )
        offer_cycle()
        close_cycle(
            outcome=outcome,
            real_shift=real_shift,
            chosen_key=outcome.split(":", 1)[1] if outcome.startswith("chose:") else None,
        )

    def test_ratio_computed_across_cycles(self, marker_paths: Path):
        # 3 real-shift + 1 template-execution + 1 no-pull-honest = 4/5 = 80%
        self._run_cycle(marker_paths, "chose:dream", real_shift=True, cycle_id="c1")
        self._run_cycle(marker_paths, "chose:aria", real_shift=True, cycle_id="c2")
        self._run_cycle(marker_paths, "chose:exploration", real_shift=True, cycle_id="c3")
        self._run_cycle(marker_paths, "chose:web", real_shift=False, cycle_id="c4")
        self._run_cycle(marker_paths, "no-pull-honest", cycle_id="c5")

        n, d, r = compute_falsifier_ratio()
        assert d == 5
        assert n == 4  # 3 real-shift + 1 no-pull-honest
        assert r == pytest.approx(0.8)

    def test_fatal_aborted_excluded_from_denominator(self, marker_paths: Path):
        # 1 real-shift + 1 aborted-fatal (excluded) = 1/1 = 100%
        self._run_cycle(marker_paths, "chose:dream", real_shift=True, cycle_id="c1")
        self._run_cycle(marker_paths, "aborted", fatal=True, cycle_id="c2")
        n, d, r = compute_falsifier_ratio()
        assert d == 1  # fatal aborted excluded
        assert n == 1
        assert r == pytest.approx(1.0)

    def test_below_bound_after_5_cycles(self, marker_paths: Path):
        # 1 real-shift, 4 template = 20% < 50%. Post-5-cycle bound fires.
        self._run_cycle(marker_paths, "chose:dream", real_shift=True, cycle_id="c1")
        for i, k in enumerate(["aria", "web", "council", "letters"], start=2):
            self._run_cycle(marker_paths, f"chose:{k}", real_shift=False, cycle_id=f"c{i}")
        n, d, r = compute_falsifier_ratio()
        assert d == 5
        assert r is not None
        assert r < 0.5
