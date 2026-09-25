"""Tests for divineos.core.auto_cycle_phase2.

Andrew 2026-07-10 auto-cycle proposal. Phase 2 is the invitational
layer: read phase 1 handshake, render menu, record offering + close
outcome, compute falsifier ratio.

Every path resolves through DIVINEOS_HOME, pointed at tmp_path, so the tests
exercise the same path resolution the product uses. The July tests patched
phase 2's own hardcoded ``~/.divineos`` constants instead -- which is how a
phase 2 reading a different file from the one phase 1 writes stayed green
(Aether, station four on #551, 2026-09-25).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from divineos.core import auto_cycle_phase2 as ac
from divineos.core.auto_cycle import marker_path, run_phase1, write_handshake_marker
from divineos.core.auto_cycle_phase2 import (
    NoHandshake,
    close_cycle,
    compute_falsifier_ratio,
    inspect_handshake,
    no_pull_count,
    offer_cycle,
    parse_outcome,
    read_handshake,
    render_menu,
)
from divineos.core.rest import REST_TASKS


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point DIVINEOS_HOME at tmp_path so phase 1 and phase 2 share it."""
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    hud_dir = tmp_path / "hud"
    hud_dir.mkdir()
    monkeypatch.setattr(ac, "_ensure_hud_dir", lambda: hud_dir)
    return tmp_path


def _step(ran: bool = True, succeeded: bool = True, error_class: str | None = None) -> dict:
    return {"ran": ran, "succeeded": succeeded, "error_class": error_class}


def _write_handshake(**overrides) -> dict:
    payload = {
        "phase1_completed_at": "2026-07-10T20:35:00Z",
        "trigger_context_pct": 0.85,
        "steps": {"commit": _step(), "extract": _step(), "sleep": _step()},
        "phase1_tokens_used": 41200,
        "budget_remaining_est": 18800,
        "session_id": "test-session",
        "cycle_id": "auto-cycle-abc12345",
    }
    payload.update(overrides)
    marker_path().parent.mkdir(parents=True, exist_ok=True)
    marker_path().write_text(json.dumps(payload), encoding="utf-8")
    return payload


def _pending() -> Path:
    return ac._pending_path()


class TestOnePath:
    def test_both_phases_resolve_the_same_marker(self, home: Path):
        """The fault Aether found: phase 2 read a path of its own."""
        assert marker_path().parent == home
        assert ac._pending_path().parent == home
        assert ac._audit_log_path().parent == home


class TestReadHandshake:
    def test_absent_is_named_absent(self, home: Path):
        assert read_handshake() is None
        found = inspect_handshake()
        assert isinstance(found, NoHandshake) and found.kind == "absent"

    def test_valid_parses(self, home: Path):
        _write_handshake()
        hs = read_handshake()
        assert hs is not None
        assert hs.cycle_id == "auto-cycle-abc12345"
        assert hs.trigger_context_pct == 0.85
        assert hs.phase1_tokens_used == 41200
        assert hs.any_step_failed is False
        assert hs.fatal_step_failure is False

    def test_malformed_json_is_named_malformed(self, home: Path):
        marker_path().write_text("{not-json", encoding="utf-8")
        found = inspect_handshake()
        assert isinstance(found, NoHandshake) and found.kind == "malformed"

    def test_a_real_dry_run_is_refused_as_did_not_run(self, home: Path):
        """The headline fault. Main's own dry run writes ran=False and
        succeeded=True on every step; the July reader read only succeeded and
        offered the menu for a phase 1 that did nothing. This uses the real
        producer, not a hand-built dict, so it breaks if either side drifts."""
        write_handshake_marker(run_phase1(0.9, dry_run=True))
        assert read_handshake() is None
        found = inspect_handshake()
        assert isinstance(found, NoHandshake) and found.kind == "did-not-run"
        record, text = offer_cycle()
        assert record is None and text == ""
        assert not _pending().exists()

    @pytest.mark.parametrize(
        "steps",
        [
            {},
            {"commit": {}},
            {"commit": {"ran": True}},
            {"commit": {"succeeded": True}},
            {"commit": {"ran": "yes", "succeeded": True}},
            {"commit": "done"},
        ],
    )
    def test_a_marker_that_does_not_state_itself_is_malformed(self, home: Path, steps):
        """A missing field used to default to success; a truncated marker is a
        prefix of a valid one and must not read as one."""
        _write_handshake(steps=steps)
        found = inspect_handshake()
        assert isinstance(found, NoHandshake) and found.kind == "malformed"

    @pytest.mark.parametrize("cycle_id", [None, "", "   ", 7])
    def test_no_cycle_id_is_malformed(self, home: Path, cycle_id):
        _write_handshake(cycle_id=cycle_id)
        found = inspect_handshake()
        assert isinstance(found, NoHandshake) and found.kind == "malformed"

    def test_transient_step_failure_flagged_but_not_fatal(self, home: Path):
        _write_handshake(
            steps={
                "commit": _step(),
                "extract": _step(succeeded=False, error_class="OSError"),
                "sleep": _step(),
            }
        )
        hs = read_handshake()
        assert hs is not None
        assert hs.any_step_failed is True
        assert hs.fatal_step_failure is False

    def test_fatal_step_failure_flagged(self, home: Path):
        _write_handshake(
            steps={
                "commit": _step(),
                "extract": _step(succeeded=False, error_class="AssertionError"),
            }
        )
        hs = read_handshake()
        assert hs is not None
        assert hs.any_step_failed is True
        assert hs.fatal_step_failure is True

    @pytest.mark.parametrize("error_class", [None, ""])
    def test_an_unnamed_failure_is_fatal(self, home: Path, error_class):
        """July counted a failure with no error_class as benign."""
        _write_handshake(steps={"extract": _step(succeeded=False, error_class=error_class)})
        hs = read_handshake()
        assert hs is not None
        assert hs.fatal_step_failure is True


class TestRenderMenu:
    def test_lists_every_rest_option(self, home: Path):
        """Every option appears, however many there are.

        This asserted exactly eleven when it was written on 2026-07-10, and
        salvaging the branch on 2026-09-22 it failed at ten -- not because the
        code had rotted but because the LIST had: `family` and `hold` left it,
        `savor` joined. A count pinned to a number turns ordinary evolution
        into a red test, and a branch that looks broken is a branch nobody
        lands. That is part of how this one sat parked for two months.

        What the test is for is that the menu shows everything, so that is
        what it now asserts.
        """
        _write_handshake()
        hs = read_handshake()
        assert hs is not None
        text = render_menu(hs, {})
        assert REST_TASKS, "an empty list would pass the loop below vacuously"
        for task in REST_TASKS:
            assert task.key in text, f"missing task {task.key!r}"

    def test_shows_use_count_mirror(self, home: Path):
        _write_handshake()
        hs = read_handshake()
        assert hs is not None
        text = render_menu(hs, {"dream": 3, "aria": 1})
        assert "used 3x" in text
        assert "used 1x" in text
        assert "used 0x" in text

    def test_names_no_pull_honest_outcome(self, home: Path):
        _write_handshake()
        hs = read_handshake()
        assert hs is not None
        text = render_menu(hs, {})
        assert "no-pull-honest" in text
        assert "not-choosing IS a choice" in text

    def test_shows_fatal_warning_when_phase1_fatal(self, home: Path):
        _write_handshake(steps={"extract": _step(succeeded=False, error_class="AssertionError")})
        hs = read_handshake()
        assert hs is not None
        assert "Fatal step failure" in render_menu(hs, {})

    def test_force_the_option_line_present(self, home: Path):
        """The load-bearing discipline line must be visible in every menu."""
        _write_handshake()
        hs = read_handshake()
        assert hs is not None
        assert "Force the option, not the use" in render_menu(hs, {})


class TestOfferCycle:
    def test_no_handshake_returns_none(self, home: Path):
        record, text = offer_cycle()
        assert record is None
        assert text == ""

    def test_valid_handshake_records_and_returns_menu(self, home: Path):
        _write_handshake()
        record, text = offer_cycle()
        assert record is not None
        assert record.cycle_id == "auto-cycle-abc12345"
        assert "dream" in record.menu_shown
        assert len(record.menu_shown) == len(REST_TASKS)
        assert text

    def test_offer_leaves_the_handshake_for_the_close(self, home: Path):
        """Phase 1's contract: the reader deletes it once phase 2 completes.
        July deleted it at offer, so a crash between offer and close lost it."""
        _write_handshake()
        offer_cycle()
        assert marker_path().exists()

    def test_offer_writes_pending_marker(self, home: Path):
        _write_handshake()
        assert not _pending().exists()
        offer_cycle()
        data = json.loads(_pending().read_text(encoding="utf-8"))
        assert data["cycle_id"] == "auto-cycle-abc12345"
        assert "menu_shown" in data
        assert "handshake_summary" in data

    def test_a_second_offer_is_refused_and_names_the_open_cycle(self, home: Path):
        """July overwrote a pending offer silently."""
        _write_handshake()
        offer_cycle()
        before = _pending().read_text(encoding="utf-8")
        record, text = offer_cycle()
        assert record is None
        assert "auto-cycle-abc12345" in text
        assert _pending().read_text(encoding="utf-8") == before


class TestMarkerAbsenceSafety:
    """Aletheia audit 2026-07-10: absent marker = phase 1 did NOT complete;
    never treated as 'nothing to do, proceed.' Phase 2 leaves no state
    changes when there is no usable handshake.
    """

    @pytest.mark.parametrize("content", [None, "{not json at all", "[1, 2, 3]"])
    def test_no_usable_marker_fires_nothing(self, home: Path, content):
        if content is not None:
            marker_path().write_text(content, encoding="utf-8")
        record, text = offer_cycle()
        assert record is None
        assert text == ""
        assert not _pending().exists()


class TestParseOutcome:
    @pytest.mark.parametrize("plain", ["no-pull-honest", "timeout", "aborted"])
    def test_plain_outcomes(self, plain):
        assert parse_outcome(plain) == (plain, None)

    def test_chose_a_real_key(self):
        key = REST_TASKS[0].key
        assert parse_outcome(f"chose:{key}") == (f"chose:{key}", key)

    @pytest.mark.parametrize("bad", ["", "chose:", "chose:not-a-rest-option", "dream", "done"])
    def test_anything_else_is_refused(self, bad):
        with pytest.raises(ValueError):
            parse_outcome(bad)


class TestCloseCycle:
    def test_no_pending_returns_none(self, home: Path):
        assert close_cycle("no-pull-honest") is None

    def test_close_records_clears_pending_and_consumes_the_handshake(self, home: Path):
        _write_handshake()
        offer_cycle()
        result = close_cycle("chose:dream", real_shift=True, notes="nautilus dream landed")
        assert result is not None
        assert result.outcome == "chose:dream"
        assert result.chosen_key == "dream"
        assert result.real_shift is True
        assert not _pending().exists()
        assert not marker_path().exists()

    def test_a_bad_outcome_changes_nothing(self, home: Path):
        _write_handshake()
        offer_cycle()
        with pytest.raises(ValueError):
            close_cycle("chose:nonsense")
        assert _pending().exists()
        assert marker_path().exists()
        assert not ac._audit_log_path().exists()

    def test_close_leaves_a_newer_cycles_handshake_alone(self, home: Path):
        """A phase 1 that fired while an offer was pending wrote a new marker;
        closing the old cycle must not eat it."""
        _write_handshake(cycle_id="old")
        offer_cycle()
        _write_handshake(cycle_id="new")
        close_cycle("timeout")
        assert json.loads(marker_path().read_text(encoding="utf-8"))["cycle_id"] == "new"

    def test_a_failed_audit_write_raises_and_keeps_the_pending_offer(
        self, home: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """July swallowed this and then deleted the pending marker."""
        _write_handshake()
        offer_cycle()
        blocked = home / "not-a-dir"
        blocked.write_text("a file where a directory must be", encoding="utf-8")
        monkeypatch.setattr(ac, "_audit_log_path", lambda: blocked / "audit.jsonl")
        with pytest.raises(OSError):
            close_cycle("no-pull-honest")
        assert _pending().exists()
        assert marker_path().exists()

    def test_a_damaged_pending_offer_is_not_no_offer(self, home: Path):
        """Close used to answer "nothing pending" over a broken record, and
        offer used to stack a new cycle on top of it."""
        _write_handshake()
        _pending().write_text("{half a rec", encoding="utf-8")
        with pytest.raises(ac.DamagedPending):
            close_cycle("timeout")
        record, text = offer_cycle()
        assert record is None
        assert "cannot be read" in text
        assert _pending().read_text(encoding="utf-8") == "{half a rec"
        assert not ac._audit_log_path().exists()

    def test_close_appends_to_audit_log(self, home: Path):
        _write_handshake()
        offer_cycle()
        close_cycle("no-pull-honest")
        entries = [
            json.loads(line)
            for line in ac._audit_log_path().read_text(encoding="utf-8").splitlines()
            if line
        ]
        assert len(entries) == 1
        assert entries[0]["outcome"] == "no-pull-honest"
        assert entries[0]["cycle_id"] == "auto-cycle-abc12345"


class TestCommands:
    """The July CLI was lost in salvage, leaving phase 2 with no caller."""

    def _run(self, *args: str):
        """Through the root command, so a group that is never registered fails here."""
        from click.testing import CliRunner

        from divineos.cli import cli

        return CliRunner().invoke(cli, list(args))

    def test_offer_after_a_real_dry_run_says_nothing_was_saved(self, home: Path):
        write_handshake_marker(run_phase1(0.9, dry_run=True))
        result = self._run("auto-cycle", "offer")
        assert result.exit_code == 0
        assert "only practised" in result.output
        assert "room is open" not in result.output
        assert not _pending().exists()

    def test_offer_close_audit_round_trip(self, home: Path):
        _write_handshake()
        assert "room is open" in self._run("auto-cycle", "offer").output
        closed = self._run("auto-cycle", "close", "--outcome", "chose:dream", "--real-shift", "yes")
        assert closed.exit_code == 0, closed.output
        assert "Cycle closed" in closed.output
        audit = self._run("auto-cycle", "audit")
        assert "real-shift outcomes:     1" in audit.output

    def test_close_refuses_an_unknown_outcome(self, home: Path):
        _write_handshake()
        self._run("auto-cycle", "offer")
        result = self._run("auto-cycle", "close", "--outcome", "chose:nonsense")
        assert result.exit_code != 0
        assert _pending().exists()


class TestComputeFalsifierRatio:
    def test_no_log_returns_none(self, home: Path):
        assert compute_falsifier_ratio() == (0, 0, None)

    def _run_cycle(
        self,
        outcome: str,
        real_shift: bool | None = None,
        fatal: bool = False,
        cycle_id: str = "test-cycle",
    ):
        _write_handshake(
            cycle_id=cycle_id,
            steps=(
                {"extract": _step(succeeded=False, error_class="AssertionError")}
                if fatal
                else {"commit": _step()}
            ),
        )
        record, _ = offer_cycle()
        assert record is not None
        close_cycle(outcome, real_shift=real_shift)

    def test_ratio_computed_across_cycles(self, home: Path):
        # 3 real-shift + 1 template-execution = 3/4; the no-pull sits outside.
        self._run_cycle("chose:dream", real_shift=True, cycle_id="c1")
        self._run_cycle("chose:aria", real_shift=True, cycle_id="c2")
        self._run_cycle("chose:exploration", real_shift=True, cycle_id="c3")
        self._run_cycle("chose:web", real_shift=False, cycle_id="c4")
        self._run_cycle("no-pull-honest", cycle_id="c5")
        n, d, r = compute_falsifier_ratio()
        assert (n, d) == (3, 4)
        assert r == pytest.approx(0.75)
        assert no_pull_count() == 1

    def test_no_pull_alone_cannot_pass_the_falsifier(self, home: Path):
        """July counted no-pull-honest as success: five cycles that never
        engaged scored 1.0."""
        for i in range(5):
            self._run_cycle("no-pull-honest", cycle_id=f"c{i}")
        assert compute_falsifier_ratio() == (0, 0, None)
        assert no_pull_count() == 5

    def test_fatal_aborted_excluded_from_denominator(self, home: Path):
        self._run_cycle("chose:dream", real_shift=True, cycle_id="c1")
        self._run_cycle("aborted", fatal=True, cycle_id="c2")
        n, d, r = compute_falsifier_ratio()
        assert (n, d) == (1, 1)
        assert r == pytest.approx(1.0)

    def test_below_bound_after_5_cycles(self, home: Path):
        self._run_cycle("chose:dream", real_shift=True, cycle_id="c1")
        for i, k in enumerate(["aria", "web", "council", "letters"], start=2):
            self._run_cycle(f"chose:{k}", real_shift=False, cycle_id=f"c{i}")
        n, d, r = compute_falsifier_ratio()
        assert d == 5
        assert r is not None and r < 0.5
