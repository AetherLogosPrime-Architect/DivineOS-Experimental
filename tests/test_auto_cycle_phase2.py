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
    monkeypatch.setattr(ac, "_handshake_marker", lambda: handshake)
    monkeypatch.setattr(ac, "_pending_marker", lambda: pending)
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
        _write_handshake(ac._handshake_marker())
        hs = read_handshake()
        assert hs is not None
        assert hs.cycle_id == "auto-cycle-abc12345"
        assert hs.trigger_context_pct == 0.85
        assert hs.phase1_tokens_used == 41200
        assert hs.any_step_failed is False
        assert hs.fatal_step_failure is False

    def test_malformed_json_returns_none(self, marker_paths: Path):
        ac._handshake_marker().write_text("{not-json", encoding="utf-8")
        assert read_handshake() is None

    def test_transient_step_failure_flagged_but_not_fatal(self, marker_paths: Path):
        _write_handshake(
            ac._handshake_marker(),
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
            ac._handshake_marker(),
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
    def test_lists_every_rest_task(self, marker_paths: Path):
        _write_handshake(ac._handshake_marker())
        hs = read_handshake()
        assert hs is not None
        text = render_menu(hs, {})
        # Every REST_TASKS entry should appear by key. The count is read from
        # the registry and not pinned: it was 11 in July and is 10 now, and a
        # pinned number made this test about the registry's size, not the menu.
        from divineos.core.rest import REST_TASKS

        assert len(REST_TASKS) >= 1
        for task in REST_TASKS:
            assert task.key in text, f"missing task {task.key!r}"

    def test_shows_use_count_mirror(self, marker_paths: Path):
        _write_handshake(ac._handshake_marker())
        hs = read_handshake()
        assert hs is not None
        text = render_menu(hs, {"dream": 3, "kin": 1})
        assert "used 3x" in text
        assert "used 1x" in text
        assert "used 0x" in text  # all other keys default to 0 via the mirror

    def test_names_no_pull_honest_outcome(self, marker_paths: Path):
        _write_handshake(ac._handshake_marker())
        hs = read_handshake()
        assert hs is not None
        text = render_menu(hs, {})
        assert "no-pull-honest" in text
        assert "not-choosing IS a choice" in text

    def test_shows_fatal_warning_when_phase1_fatal(self, marker_paths: Path):
        _write_handshake(
            ac._handshake_marker(),
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
        _write_handshake(ac._handshake_marker())
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
        _write_handshake(ac._handshake_marker())
        record, text = offer_cycle()
        assert record is not None
        assert record.cycle_id == "auto-cycle-abc12345"
        assert "dream" in record.menu_shown
        from divineos.core.rest import REST_TASKS

        assert len(record.menu_shown) == len(REST_TASKS)
        assert text  # non-empty rendered menu

    def test_offer_deletes_handshake_marker(self, marker_paths: Path):
        _write_handshake(ac._handshake_marker())
        assert ac._handshake_marker().exists()
        offer_cycle()
        assert not ac._handshake_marker().exists()

    def test_offer_writes_pending_marker(self, marker_paths: Path):
        _write_handshake(ac._handshake_marker())
        assert not ac._pending_marker().exists()
        offer_cycle()
        assert ac._pending_marker().exists()
        data = json.loads(ac._pending_marker().read_text(encoding="utf-8"))
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
        assert not ac._handshake_marker().exists()
        record, text = offer_cycle()
        assert record is None, "must NOT fire invitational when phase 1 never ran"
        assert text == ""
        # Pending marker also must not be written — the invariant is that
        # phase 2 leaves no state changes when the handshake is absent.
        assert not ac._pending_marker().exists()

    def test_no_marker_from_write_failure(self, marker_paths: Path):
        """Case 2 (Aletheia's specific concern): phase 1 ran but the
        marker-write itself failed (disk full, permission error). Phase 1
        exits, no marker on disk, phase 2 must NOT fire silently."""
        # Simulate: phase 1 ran but no marker landed. Indistinguishable from
        # case 1 by design — both must fail toward not-firing.
        assert not ac._handshake_marker().exists()
        record, text = offer_cycle()
        assert record is None, (
            "marker-write-failure must NOT be treated as successful no-op — "
            "phase 2 must fail toward not-firing-the-invitational"
        )
        assert text == ""
        assert not ac._pending_marker().exists()

    def test_no_marker_from_malformed_content(self, marker_paths: Path):
        """Case 3: marker exists but is malformed. Same treatment."""
        ac._handshake_marker().write_text("{not json at all", encoding="utf-8")
        record, text = offer_cycle()
        assert record is None
        assert text == ""
        assert not ac._pending_marker().exists()

    def test_no_marker_from_wrong_top_level_type(self, marker_paths: Path):
        """Case 3-adjacent: valid JSON but not a dict."""
        ac._handshake_marker().write_text("[1, 2, 3]", encoding="utf-8")
        record, text = offer_cycle()
        assert record is None
        assert text == ""
        assert not ac._pending_marker().exists()


class TestCloseCycle:
    def test_no_pending_returns_none(self, marker_paths: Path):
        assert close_cycle("no-pull-honest") is None

    def test_close_after_offer_records_and_clears_pending(self, marker_paths: Path):
        _write_handshake(ac._handshake_marker())
        offer_cycle()
        assert ac._pending_marker().exists()
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
        assert not ac._pending_marker().exists()

    def test_close_appends_to_audit_log(self, marker_paths: Path):
        _write_handshake(ac._handshake_marker())
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
            ac._handshake_marker(),
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


class TestPhase2ReadsWhereReaderPhase1Writes:
    """Phase 2 must look in the folder phase 1 writes to (2026-11-02).

    The July version built ``Path.home() / ".divineos"`` itself. Phase 1 now
    writes under ``divineos_home()``, which is per house, so a reader in a
    different home would see "absent" and absent means "phase 1 did not
    finish": the wrong folder looks exactly like a real absence.
    """

    def test_handshake_path_is_phase_ones_own_marker_path(self):
        from divineos.core import auto_cycle

        assert ac._handshake_marker() == auto_cycle.marker_path()

    def test_pending_and_audit_live_in_the_same_home(self):
        from divineos.core.paths import divineos_home

        assert ac._pending_marker().parent == divineos_home()
        assert ac._audit_log_path().parent == divineos_home()

    def test_a_marker_phase_one_wrote_is_found_by_phase_two(self, tmp_path, monkeypatch):
        from divineos.core import auto_cycle

        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
        written = tmp_path / "auto_cycle_phase1_done.json"
        written.write_text(
            json.dumps({"cycle_id": "auto-cycle-abc", "steps": {}, "repo_root": "x"}),
            encoding="utf-8",
        )
        assert auto_cycle.marker_path() == written
        found = read_handshake()
        assert found is not None
        assert found.cycle_id == "auto-cycle-abc"


class TestMissingMeansNotCompleted:
    """A step the marker does not vouch for counts as failed (Aether's cold read, 2026-11-02).

    The invariant is that absence fails toward "phase 1 did not finish". It was
    held for the whole marker and not for the pieces inside it: a step entry
    without ``succeeded`` read as a success, ``ran`` was never read, and a step
    that was not even a mapping was skipped.
    """

    def _read(self, marker_paths: Path, steps: dict):
        ac._handshake_marker().write_text(
            json.dumps({"cycle_id": "auto-cycle-x", "steps": steps}), encoding="utf-8"
        )
        hs = read_handshake()
        assert hs is not None
        return hs

    def test_a_well_formed_step_is_clean(self, marker_paths: Path):
        hs = self._read(marker_paths, {"commit": {"ran": True, "succeeded": True}})
        assert hs.any_step_failed is False

    def test_a_step_without_succeeded_counts_as_failed(self, marker_paths: Path):
        hs = self._read(marker_paths, {"commit": {"ran": True}})
        assert hs.any_step_failed is True

    def test_a_step_that_did_not_run_counts_as_failed_whatever_succeeded_says(
        self, marker_paths: Path
    ):
        hs = self._read(marker_paths, {"sleep": {"ran": False, "succeeded": True}})
        assert hs.any_step_failed is True

    def test_a_step_without_ran_counts_as_failed(self, marker_paths: Path):
        hs = self._read(marker_paths, {"extract": {"succeeded": True}})
        assert hs.any_step_failed is True

    def test_a_step_that_is_not_a_mapping_counts_as_failed(self, marker_paths: Path):
        hs = self._read(marker_paths, {"commit": "done"})
        assert hs.any_step_failed is True

    def test_repo_root_is_carried_into_the_audit_summary(self, marker_paths: Path):
        ac._handshake_marker().write_text(
            json.dumps(
                {
                    "cycle_id": "auto-cycle-y",
                    "repo_root": "C:/some/checkout",
                    "steps": {"commit": {"ran": True, "succeeded": True}},
                }
            ),
            encoding="utf-8",
        )
        hs = read_handshake()
        assert hs is not None
        assert hs.repo_root == "C:/some/checkout"
        assert ac._handshake_summary(hs)["repo_root"] == "C:/some/checkout"

    def test_an_older_marker_without_repo_root_still_reads(self, marker_paths: Path):
        hs = self._read(marker_paths, {"commit": {"ran": True, "succeeded": True}})
        assert hs.repo_root == ""


class TestAnUnclosedOfferingIsNotSilentlyOverwritten:
    """A second offering before the first is closed must account for the first.

    Found in the finishing walk (Lovelace, 2026-11-02): ``offer_cycle`` wrote
    the pending marker over an older one, so the older cycle never reached the
    audit log and its outcome never fed the falsifier ratio.
    """

    def _handshake(self, cycle_id: str) -> None:
        ac._handshake_marker().write_text(
            json.dumps(
                {
                    "cycle_id": cycle_id,
                    "steps": {"commit": {"ran": True, "succeeded": True}},
                }
            ),
            encoding="utf-8",
        )

    def test_the_older_cycle_is_logged_as_aborted_and_the_new_one_is_pending(
        self, marker_paths: Path
    ):
        self._handshake("auto-cycle-first")
        offer_cycle()
        self._handshake("auto-cycle-second")
        offer_cycle()

        log = [
            json.loads(line)
            for line in ac._audit_log_path().read_text(encoding="utf-8").splitlines()
        ]
        assert [e["cycle_id"] for e in log] == ["auto-cycle-first"]
        assert log[0]["outcome"] == "aborted"
        assert "superseded" in log[0]["notes"]
        pending = json.loads(ac._pending_marker().read_text(encoding="utf-8"))
        assert pending["cycle_id"] == "auto-cycle-second"

    def test_a_first_offering_logs_nothing(self, marker_paths: Path):
        self._handshake("auto-cycle-only")
        offer_cycle()
        assert not ac._audit_log_path().exists()


class TestTheRealCommandLayer:
    """The module tests above never touch click; these do (finishing walk, Holmes)."""

    def test_the_auto_cycle_group_holds_phase_one_and_phase_two_commands(self):
        from divineos.cli import cli

        group = cli.commands["auto-cycle"]
        assert {"status", "fire", "defer-check", "offer", "close", "audit"} <= set(group.commands)

    def test_offer_through_the_cli_reads_the_marker_and_reports_it(self, marker_paths: Path):
        from click.testing import CliRunner

        from divineos.cli import cli

        ac._handshake_marker().write_text(
            json.dumps(
                {
                    "cycle_id": "auto-cycle-cli",
                    "steps": {"commit": {"ran": True, "succeeded": True}},
                }
            ),
            encoding="utf-8",
        )
        result = CliRunner().invoke(cli, ["auto-cycle", "offer"])
        assert result.exit_code == 0, result.output
        assert "auto-cycle-cli" in result.output

    def test_offer_through_the_cli_with_no_marker_refuses_to_fire(self, marker_paths: Path):
        from click.testing import CliRunner

        from divineos.cli import cli

        result = CliRunner().invoke(cli, ["auto-cycle", "offer"])
        assert result.exit_code == 0, result.output
        assert "No phase 1 handshake found" in result.output
        assert not ac._pending_marker().exists()
