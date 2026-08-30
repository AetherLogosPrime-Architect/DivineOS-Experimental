"""Tests for system_load_check — the pre-flight memory gate that prevents
concurrent-pytest crashes of the class that hit Andrew's machine 2026-07-30
and 2026-07-13.

Pre-reg: prereg-ca5fb15220ea.
"""

from __future__ import annotations

from unittest import mock

import pytest

from divineos.core import system_load_check


class TestCheckCapacity:
    """Verify check_capacity behaves correctly across memory conditions."""

    def test_headroom_met_but_ceiling_exceeded_still_refuses(self) -> None:
        """Two conditions, not one — and this is the case that distinguishes
        them. 2026-08-01: the check used to be a single absolute
        free-memory threshold. It now also projects usage AFTER the job.

        A large box that is already heavily consumed: 64 GB total with only
        9 GB available. Headroom passes (9 >= job 5 + reserve 3), but the
        job would land usage at ~94%, past the 92% ceiling. Absolute free
        memory looks fine and the machine is nearly full — which is exactly
        the case a single free-memory threshold cannot see.

        The ceiling is derived from Andrew's observed crash point of 98-99%,
        minus margin for the job cost being an estimate.
        """
        with mock.patch.object(system_load_check, "psutil") as mock_psutil:
            vm = mock.MagicMock()
            vm.available = 9 * 1024**3
            vm.total = 64 * 1024**3
            vm.percent = 86.0
            mock_psutil.virtual_memory.return_value = vm

            with mock.patch.dict("os.environ", {}, clear=True):
                safe, msg = system_load_check.check_capacity("test-job")

        assert safe is False
        assert "ceiling" in msg
        assert "94%" in msg

    def test_ninety_one_percent_projection_is_allowed(self) -> None:
        """Guards the recalibration itself. 8 GB free of 32 GB projects ~91%
        used, which my first pass REFUSED under an invented 85% ceiling.
        Andrew: 'my pc doesnt usually crash until 98-99%'. Observed
        behaviour beat the conventional number, so this must now pass — and
        this test fails loudly if anyone quietly restores a lower ceiling.
        """
        with mock.patch.object(system_load_check, "psutil") as mock_psutil:
            vm = mock.MagicMock()
            vm.available = 8 * 1024**3
            vm.total = 32 * 1024**3
            vm.percent = 75.0
            mock_psutil.virtual_memory.return_value = vm

            with mock.patch.dict("os.environ", {}, clear=True):
                safe, _ = system_load_check.check_capacity("test-job")

        assert safe is True

    def test_headroom_and_ceiling_both_met_proceeds(self) -> None:
        """Roomy machine: both conditions hold, job proceeds. This is the
        real-world case that the old 16 GB absolute threshold wrongly
        refused — 12.4 GB free of 31 GB with nothing heavy running."""
        with mock.patch.object(system_load_check, "psutil") as mock_psutil:
            vm = mock.MagicMock()
            vm.available = int(12.4 * 1024**3)
            vm.total = int(31.2 * 1024**3)
            vm.percent = 60.0
            mock_psutil.virtual_memory.return_value = vm

            with mock.patch.dict("os.environ", {}, clear=True):
                safe, msg = system_load_check.check_capacity("test-job")

        assert safe is True
        assert "Memory OK" in msg
        assert "test-job" in msg

    def test_second_concurrent_suite_is_refused(self) -> None:
        """The original crash class: concurrent pytest suites. One suite is
        already running, so it has taken ~5 GB out of `available`. The next
        spawn must be refused by the same arithmetic rather than by a fixed
        number tuned for one machine on one day."""
        total = 16 * 1024**3
        one_suite_running = int(6.5 * 1024**3)  # what's left with 1 suite up
        with mock.patch.object(system_load_check, "psutil") as mock_psutil:
            vm = mock.MagicMock()
            vm.available = one_suite_running
            vm.total = total
            vm.percent = 59.0
            mock_psutil.virtual_memory.return_value = vm

            with mock.patch.dict("os.environ", {}, clear=True):
                safe, _ = system_load_check.check_capacity("pytest suite")

        assert safe is False

    def test_returns_safe_when_free_memory_well_above_threshold(self) -> None:
        """Free memory much greater than threshold: proceed with concrete numbers."""
        with mock.patch.object(system_load_check, "psutil") as mock_psutil:
            vm = mock.MagicMock()
            vm.available = 25 * 1024**3  # 25 GB free
            vm.total = 32 * 1024**3
            vm.percent = 22.0
            mock_psutil.virtual_memory.return_value = vm

            with mock.patch.dict("os.environ", {}, clear=True):
                safe, msg = system_load_check.check_capacity("pytest suite")

        assert safe is True
        assert "25.0 GB free" in msg
        assert "22% used" in msg

    def test_refuses_when_free_memory_below_threshold(self) -> None:
        """Free memory below threshold: refuse with concrete numbers."""
        with mock.patch.object(system_load_check, "psutil") as mock_psutil:
            vm = mock.MagicMock()
            vm.available = 5 * 1024**3  # 5 GB free, way below threshold
            vm.total = 32 * 1024**3
            vm.percent = 84.0
            mock_psutil.virtual_memory.return_value = vm

            with mock.patch.dict("os.environ", {}, clear=True):
                safe, msg = system_load_check.check_capacity("pytest suite")

        assert safe is False
        assert "REFUSED" in msg
        assert "pytest suite" in msg
        assert "5.0 GB available" in msg
        assert "84% used" in msg
        # Derived requirement (job cost + reserve) surfaced in the message,
        # along with both of its components so the number is auditable
        # rather than magic.
        assert "8.0 GB" in msg
        assert "5.0 GB" in msg  # job cost
        assert "3.0 GB" in msg  # reserve

    def test_refuses_when_free_memory_just_below_threshold(self) -> None:
        """Boundary check: 1 byte below threshold still refuses."""
        with mock.patch.object(system_load_check, "psutil") as mock_psutil:
            vm = mock.MagicMock()
            vm.available = system_load_check.SAFE_FREE_BYTES - 1
            vm.total = 32 * 1024**3
            vm.percent = 51.0
            mock_psutil.virtual_memory.return_value = vm

            with mock.patch.dict("os.environ", {}, clear=True):
                safe, _msg = system_load_check.check_capacity()

        assert safe is False

    def test_skip_env_var_bypasses_check(self) -> None:
        """DIVINEOS_SKIP_LOAD_CHECK=1: proceed without checking memory."""
        # Mock psutil to raise if called, proving we short-circuit before it.
        with mock.patch.object(system_load_check, "psutil") as mock_psutil:
            mock_psutil.virtual_memory.side_effect = AssertionError(
                "psutil.virtual_memory should not be called when skip-env set"
            )

            with mock.patch.dict("os.environ", {"DIVINEOS_SKIP_LOAD_CHECK": "1"}, clear=True):
                safe, msg = system_load_check.check_capacity("test")

        assert safe is True
        assert "skipping load check" in msg
        assert "DIVINEOS_SKIP_LOAD_CHECK" in msg

    def test_message_carries_job_label(self) -> None:
        """job_label appears in both proceed and refuse messages."""
        with mock.patch.object(system_load_check, "psutil") as mock_psutil:
            vm = mock.MagicMock()
            vm.available = 25 * 1024**3
            vm.total = 32 * 1024**3
            vm.percent = 22.0
            mock_psutil.virtual_memory.return_value = vm

            with mock.patch.dict("os.environ", {}, clear=True):
                _, msg = system_load_check.check_capacity("distinct-label-xyz")
        assert "distinct-label-xyz" in msg


class TestMainCli:
    """Verify the CLI entry point exit-codes match check-capacity results."""

    def test_cli_exits_zero_when_safe(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(system_load_check, "check_capacity", lambda label: (True, "ok"))
        monkeypatch.setattr("sys.argv", ["prog", "job-x"])
        rc = system_load_check.main()
        captured = capsys.readouterr()
        assert rc == 0
        assert "ok" in captured.err

    def test_cli_exits_one_when_refused(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(system_load_check, "check_capacity", lambda label: (False, "refused"))
        monkeypatch.setattr("sys.argv", ["prog", "job-x"])
        rc = system_load_check.main()
        captured = capsys.readouterr()
        assert rc == 1
        assert "refused" in captured.err

    def test_cli_default_label_when_no_arg(self, monkeypatch: pytest.MonkeyPatch) -> None:
        received_labels: list[str] = []

        def fake_check(label: str) -> tuple[bool, str]:
            received_labels.append(label)
            return True, ""

        monkeypatch.setattr(system_load_check, "check_capacity", fake_check)
        monkeypatch.setattr("sys.argv", ["prog"])
        system_load_check.main()
        assert received_labels == ["resource-heavy job"]


class TestPsutilAbsent:
    """The guarded-import path (Aletheia F101, 2026-07-31).

    PR #402 died in CI at COLLECTION — `ModuleNotFoundError: No module named
    'psutil'` took down all 10852 tests before one ran. A pre-flight safety
    check must never be the reason the build cannot start.

    The chosen behaviour is fail-open-LOUDLY: proceed, but make it impossible
    to mistake an unrun check for a passing one. These tests pin both halves,
    because an untested guard is the failure mode it exists to prevent.
    """

    def test_proceeds_when_psutil_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(system_load_check, "_PSUTIL_AVAILABLE", False)
        safe, msg = system_load_check.check_capacity("pre-push pytest suite")
        assert safe is True, "must fail OPEN — a missing advisory cannot block every push"
        assert msg

    def test_says_loudly_that_it_did_not_run(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(system_load_check, "_PSUTIL_AVAILABLE", False)
        _, msg = system_load_check.check_capacity("pre-push pytest suite")
        # The whole point: nobody may read this as "the machine was checked".
        assert "DID NOT RUN" in msg
        assert "NOT INSTALLED" in msg
        assert "pre-push pytest suite" in msg, "must name what proceeded unchecked"
        assert "not a pass" in msg.lower()

    def test_skip_env_var_still_wins_over_absence(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Ordering check: the explicit operator escape is evaluated before the
        # psutil branch, so an intentional skip reports as a skip rather than
        # being mislabelled a missing-dependency event.
        monkeypatch.setattr(system_load_check, "_PSUTIL_AVAILABLE", False)
        monkeypatch.setenv(system_load_check.SKIP_ENV_VAR, "1")
        safe, msg = system_load_check.check_capacity("job-x")
        assert safe is True
        assert system_load_check.SKIP_ENV_VAR in msg
        assert "NOT INSTALLED" not in msg


# ---------------------------------------------------------------------------
# Re-sampling on the refusal path (2026-08-19).
#
# The guard refused a push at "only 0.7 GB available... 98% used" while the
# machine sat at 55%. Both readings were honest -- psutil and the Windows API
# agree to two decimals at every instant sampled, and available memory really
# does fall under a gigabyte while a pytest or mypy run finishes. The defect
# was never a bad number. It was ONE instantaneous sample of a metric that
# moves 13 GB, driving a BLOCKING decision, then reported as a standing
# condition.
#
# These pin the shape: refuse only on pressure that survives re-sampling, and
# never pay for the re-sample when the first reading already clears.
# ---------------------------------------------------------------------------

_TOTAL = 31 * 1024**3


def _reading(available: int, percent: float):
    vm = mock.MagicMock()
    vm.available = available
    vm.total = _TOTAL
    vm.percent = percent
    return vm


def test_a_dip_that_recovers_does_not_refuse() -> None:
    """The spike that cost an hour: first sample low, machine actually fine."""
    roomy = system_load_check.SAFE_FREE_BYTES * 2
    samples = [
        _reading(int(0.4 * 1024**3), 98.0),  # the spike
        _reading(roomy, 45.0),  # the machine as it really is
        _reading(roomy, 45.0),
    ]
    with mock.patch.object(system_load_check, "psutil") as mock_psutil:
        mock_psutil.virtual_memory.side_effect = samples
        with mock.patch.object(system_load_check.time, "sleep"):
            with mock.patch.dict("os.environ", {}, clear=True):
                safe, msg = system_load_check.check_capacity("test-job")

    assert safe is True, f"a recovered dip must not refuse; got: {msg}"


def test_sustained_pressure_still_refuses() -> None:
    """Re-sampling must not disarm the guard. A full machine stays full."""
    with mock.patch.object(system_load_check, "psutil") as mock_psutil:
        mock_psutil.virtual_memory.return_value = _reading(int(0.4 * 1024**3), 98.0)
        with mock.patch.object(system_load_check.time, "sleep"):
            with mock.patch.dict("os.environ", {}, clear=True):
                safe, msg = system_load_check.check_capacity("test-job")

    assert safe is False
    assert "REFUSED" in msg


def test_pass_path_reads_once_and_never_sleeps() -> None:
    """A first reading that clears must cost no extra samples and no delay."""
    roomy = system_load_check.SAFE_FREE_BYTES * 2
    with mock.patch.object(system_load_check, "psutil") as mock_psutil:
        mock_psutil.virtual_memory.return_value = _reading(roomy, 40.0)
        with mock.patch.object(system_load_check.time, "sleep") as mock_sleep:
            with mock.patch.dict("os.environ", {}, clear=True):
                safe, _ = system_load_check.check_capacity("test-job")

    assert safe is True
    assert mock_psutil.virtual_memory.call_count == 1, "pass path must read once"
    assert mock_sleep.call_count == 0, "pass path must never sleep"
