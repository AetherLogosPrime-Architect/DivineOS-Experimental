"""Worker count must scale with free memory, not with core count.

Aria 2026-07-31. check_capacity asked "is there 16 GB free?" and then
check_push_readiness.sh launched `pytest -n auto`, one worker per core.
Demand scaled with CORES while the gate measured MEMORY, so a 16-core box
could pass a 16 GB check and then ask for far more than 16 GB.

The property these tests defend is not "the numbers are right" — the
per-worker estimate is a judgement call. It is that every error direction
lands on FEWER workers, and that nothing the old code refused becomes a
larger job than before.
"""

from __future__ import annotations

import pytest

from divineos.core import system_load_check as slc

GB = 1024**3


class TestRecommendedWorkers:
    def test_below_hard_floor_refuses(self) -> None:
        assert slc.recommended_workers(slc.HARD_FLOOR_BYTES - 1, 16) == 0

    def test_exactly_hard_floor_allows_one(self) -> None:
        assert slc.recommended_workers(slc.HARD_FLOOR_BYTES, 16) == 1

    def test_capped_by_cores_not_just_memory(self) -> None:
        """Abundant memory must not spawn more workers than there are cores."""
        assert slc.recommended_workers(512 * GB, 4) == 4

    def test_capped_by_memory_not_just_cores(self) -> None:
        """THE BUG. 16 cores, 13.7 GB free — must not return 16."""
        got = slc.recommended_workers(int(13.7 * GB), 16)
        assert got < 16
        assert got >= 1
        # Every worker's budget must fit under the non-reserved memory.
        assert got * slc.WORKER_MEMORY_BYTES <= int(13.7 * GB) - slc.RESERVE_BYTES

    @pytest.mark.parametrize("free_gb", [6, 8, 10, 13.7, 16, 24, 32, 64])
    @pytest.mark.parametrize("cores", [1, 2, 4, 8, 16, 32])
    def test_demand_never_exceeds_budget(self, free_gb: float, cores: int) -> None:
        """The invariant that keeps the machine alive, over the whole grid."""
        avail = int(free_gb * GB)
        workers = slc.recommended_workers(avail, cores)
        if workers == 0:
            continue_ok = avail < slc.HARD_FLOOR_BYTES
            assert continue_ok, "refused despite having room for a worker"
            return
        assert workers <= cores
        assert workers * slc.WORKER_MEMORY_BYTES <= avail - slc.RESERVE_BYTES

    def test_strictly_no_worse_than_old_behavior(self) -> None:
        """Old code ran `-n auto` (=cores) whenever free >= SAFE_FREE_BYTES.

        New code must never authorize MORE workers than that in the same
        condition — the change may only ever lower demand.
        """
        for cores in (1, 2, 4, 8, 16, 32, 64):
            for free_gb in (16, 20, 32, 64, 128):
                got = slc.recommended_workers(int(free_gb * GB), cores)
                assert got <= cores


class TestParallelFlag:
    def test_refusal_returns_none(self, monkeypatch) -> None:
        monkeypatch.setattr(slc, "psutil", _FakePsutil(slc.HARD_FLOOR_BYTES - 1))
        monkeypatch.delenv(slc.SKIP_ENV_VAR, raising=False)
        flag, reason = slc.pytest_parallel_flag("suite")
        assert flag is None
        assert "REFUSED" in reason

    def test_scales_down_instead_of_refusing(self, monkeypatch) -> None:
        """13.7 GB free used to be a flat refusal. Now it runs, smaller.

        The machine is faked as well as the memory, and it has to be. Aether
        caught this failing on every CI run and passing on every local run
        (2026-08-23): the test patched psutil and left ``os.cpu_count()`` live,
        so what it actually asserted was *this host has more than seven cores*.

        ``recommended_workers`` caps at the core count, and 13.7 GB supports
        seven. Above seven cores memory binds and the flag is ``-n 7``; at or
        below seven, cores bind, ``workers >= cpus`` holds, and ``-n auto`` is
        the CORRECT answer. Sixteen here, two to four on a GitHub runner — same
        code, opposite verdicts, and the docstring described only one of them.

        Pinned high so memory is the binding constraint, which is the condition
        the first sentence is actually about.
        """
        monkeypatch.setattr(slc, "psutil", _FakePsutil(int(13.7 * GB)))
        monkeypatch.setattr(slc.os, "cpu_count", lambda: 16)
        monkeypatch.delenv(slc.SKIP_ENV_VAR, raising=False)
        flag, reason = slc.pytest_parallel_flag("suite")
        assert flag is not None
        assert flag.startswith("-n ")
        assert flag != "-n auto"
        assert "memory-scaled" in reason
        assert flag == f"-n {slc.recommended_workers(int(13.7 * GB), 16)}", (
            "the count must be the one memory supports, not merely 'not auto'"
        )

    def test_auto_is_right_when_cores_bind_not_memory(self, monkeypatch) -> None:
        """The other side of the case above, and the reason it is a pair.

        On a small runner the same 13.7 GB supports at least as many workers as
        there are cores, so ``-n auto`` is not a failure to scale down — there
        is nothing to scale down to. Pinning only the sixteen-core case would
        leave the shape that actually runs in CI untested, which is how the
        original defect survived: every local run took the other branch.
        """
        monkeypatch.setattr(slc, "psutil", _FakePsutil(int(13.7 * GB)))
        monkeypatch.setattr(slc.os, "cpu_count", lambda: 2)
        monkeypatch.delenv(slc.SKIP_ENV_VAR, raising=False)
        flag, _ = slc.pytest_parallel_flag("suite")
        assert flag == "-n auto"

    def test_psutil_missing_is_conservative_not_wide_open(self, monkeypatch) -> None:
        monkeypatch.setattr(slc, "psutil", None)
        monkeypatch.delenv(slc.SKIP_ENV_VAR, raising=False)
        flag, reason = slc.pytest_parallel_flag("suite")
        assert flag == "-n 2"
        assert "cannot measure" in reason

    def test_bypass_still_caps_workers(self, monkeypatch) -> None:
        """The emergency bypass skips the REFUSAL, not the memory ceiling.

        A bypass is for getting work through, not for unbounded fan-out on
        a machine that is already short. It must never yield `-n auto`.
        """
        monkeypatch.setattr(slc, "psutil", _FakePsutil(1 * GB))
        monkeypatch.setenv(slc.SKIP_ENV_VAR, "1")
        flag, _ = slc.pytest_parallel_flag("suite")
        assert flag == "-n 2"


class _FakePsutil:
    def __init__(self, available: int) -> None:
        self._available = available

    def virtual_memory(self):
        class _M:
            pass

        m = _M()
        m.available = self._available
        return m
