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

    def test_returns_safe_when_free_memory_at_threshold(self) -> None:
        """Free memory exactly equal to threshold: proceed."""
        with mock.patch.object(system_load_check, "psutil") as mock_psutil:
            vm = mock.MagicMock()
            vm.available = system_load_check.SAFE_FREE_BYTES
            vm.total = 32 * 1024**3
            vm.percent = 50.0
            mock_psutil.virtual_memory.return_value = vm

            with mock.patch.dict("os.environ", {}, clear=True):
                safe, msg = system_load_check.check_capacity("test-job")

        assert safe is True
        assert "Memory OK" in msg
        assert "test-job" in msg

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
        assert "5.0 GB free" in msg
        assert "84% used" in msg
        assert "16.0 GB" in msg  # threshold surfaced in message

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

    def test_skip_env_var_still_wins_over_absence(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Ordering check: the explicit operator escape is evaluated before the
        # psutil branch, so an intentional skip reports as a skip rather than
        # being mislabelled a missing-dependency event.
        monkeypatch.setattr(system_load_check, "_PSUTIL_AVAILABLE", False)
        monkeypatch.setenv(system_load_check.SKIP_ENV_VAR, "1")
        safe, msg = system_load_check.check_capacity("job-x")
        assert safe is True
        assert system_load_check.SKIP_ENV_VAR in msg
        assert "NOT INSTALLED" not in msg
