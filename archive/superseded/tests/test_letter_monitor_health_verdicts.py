"""The checker must tell a scheduled ending apart from a death.

WHY THIS FILE EXISTS (2026-09-17, council-16984bdd68e5).

The harness kills a letter watch at its cap, so every watch ends. The checker
could not see that, so a scheduled event produced the same verdict as a crash,
and the hook that reads the verdict shouted an emergency paragraph at Andrew on
every prompt for something that happens on purpose twice an hour. His words:
*"the Aria letter watcher keeps dying every prompt now."*

The danger in the repair is the opposite one — a calm branch that grows until it
swallows a real death. Thirteen silent days happened because every layer failed
toward "fine". So these cases are weighted toward the loud side: every uncertain
input must produce the loud verdict, and only a demonstrably complete life gets
the quiet one.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


_HEALTH = Path(__file__).resolve().parents[1] / "scripts" / "letter_monitor_health.py"


def _load():
    spec = importlib.util.spec_from_file_location("letter_monitor_health", _HEALTH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def health():
    return _load()


class TestOnlyACompleteLifeCountsAsScheduled:
    def test_full_term_is_scheduled(self, health):
        armed = 1_000_000.0
        last_beat = armed + health.MONITOR_LIFESPAN_SECONDS
        assert health._ran_its_full_term(armed, last_beat) is True

    def test_just_inside_the_grace_window_is_scheduled(self, health):
        """A watch is not killed to the second and the final beat can lag."""
        armed = 1_000_000.0
        last_beat = armed + health.MONITOR_LIFESPAN_SECONDS - health.LIFESPAN_GRACE_SECONDS
        assert health._ran_its_full_term(armed, last_beat) is True

    def test_stopping_early_is_a_death(self, health):
        armed = 1_000_000.0
        last_beat = armed + 77  # the 2026-08-02 death, which took 77 seconds
        assert health._ran_its_full_term(armed, last_beat) is False


class TestEveryUnknownResolvesLoud:
    """The failure this whole mechanism exists to end is silence read as health.

    A quiet branch that accepts uncertainty is how it would come back.
    """

    def test_no_start_time_is_not_scheduled(self, health):
        assert health._ran_its_full_term(None, 1_000_000.0) is False

    def test_a_start_time_in_the_future_is_not_scheduled(self, health):
        assert health._ran_its_full_term(2_000_000.0, 1_000_000.0) is False

    def test_a_life_longer_than_the_cap_is_not_scheduled(self, health):
        """Longer than the harness permits means this record is not describing
        the watch it appears to, which is a reason to look rather than relax."""
        armed = 1_000_000.0
        last_beat = armed + health.MONITOR_LIFESPAN_SECONDS * 3
        assert health._ran_its_full_term(armed, last_beat) is False


class TestTheVerdictsReachTheCaller:
    """The distinction is worth nothing if the reported verdict collapses it."""

    def _write(self, tmp_path, monkeypatch, health, payload):
        p = tmp_path / "letter_monitor_heartbeat.json"
        p.write_text(json.dumps(payload), encoding="utf-8")
        monkeypatch.setattr(health, "heartbeat_path", lambda: p)

    def test_a_scheduled_end_gets_its_own_code_and_says_nothing_broke(
        self, tmp_path, monkeypatch, health
    ):
        now = 2_000_000.0
        beat = now - 300
        self._write(
            tmp_path,
            monkeypatch,
            health,
            {
                "last_beat_unix": beat,
                "armed_at_unix": beat - health.MONITOR_LIFESPAN_SECONDS,
                "recipient": "aether",
            },
        )
        code, reason = health.check(now=now)
        # 5, NOT 4, SINCE 2026-09-19. This state and the wrong-recipient state
        # were written on two branches at once and both took 4. The docstrings
        # collided so git stopped; the two function bodies merged cleanly and
        # one number briefly meant two things. Wrong-recipient was already on
        # the main line, so it kept 4 and this moved.
        #
        # THIS TEST IS WHY THAT RENUMBER WAS SAFE TO MAKE. The merge commit
        # claimed nothing asserted these codes, which was wrong -- this file
        # did, the pre-push suite failed on it, and the push was refused before
        # anything left the machine. The reading that produced that claim
        # searched the source and the two readers and never searched the tests.
        assert code == 5
        assert "EXPIRED ON SCHEDULE" in reason
        assert "Nothing broke" in reason

    def test_an_early_stop_still_reads_as_a_death(self, tmp_path, monkeypatch, health):
        now = 2_000_000.0
        beat = now - 300
        self._write(
            tmp_path,
            monkeypatch,
            health,
            {
                "last_beat_unix": beat,
                "armed_at_unix": beat - 77,
                "recipient": "aether",
            },
        )
        code, reason = health.check(now=now)
        assert code == 1
        assert "STALE" in reason
        assert "death" in reason

    def test_an_old_heartbeat_without_a_start_time_still_reads_as_a_death(
        self, tmp_path, monkeypatch, health
    ):
        """A monitor predating this change must not be silently reclassified."""
        now = 2_000_000.0
        self._write(
            tmp_path,
            monkeypatch,
            health,
            {"last_beat_unix": now - 300, "recipient": "aether"},
        )
        code, _ = health.check(now=now)
        assert code == 1

    def test_a_live_watch_is_still_healthy_and_silent(self, tmp_path, monkeypatch, health):
        now = 2_000_000.0
        self._write(
            tmp_path,
            monkeypatch,
            health,
            {
                "last_beat_unix": now - 10,
                "armed_at_unix": now - 600,
                "recipient": "aether",
            },
        )
        code, _ = health.check(now=now)
        assert code == 0


class TestTheMonitorActuallyRecordsWhatTheCheckerReads:
    """Both halves, or the wiring is one-sided.

    The checker can be perfect and report a death forever if the monitor never
    writes the field. This is the producer end.
    """

    def test_the_heartbeat_carries_a_start_time(self, tmp_path, monkeypatch):
        import importlib.util as ilu

        path = Path(__file__).resolve().parents[1] / "scripts" / "letter_monitor_v2.py"
        spec = ilu.spec_from_file_location("letter_monitor_v2", path)
        assert spec and spec.loader
        mon = ilu.module_from_spec(spec)
        spec.loader.exec_module(mon)

        monkeypatch.setattr(mon, "divineos_home", lambda: tmp_path, raising=False)
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        monkeypatch.setenv("HOME", str(tmp_path))

        mon.write_heartbeat_file("aether")

        written = list(tmp_path.rglob("letter_monitor_heartbeat.json"))
        assert written, "the monitor wrote no heartbeat at all"
        payload = json.loads(written[0].read_text(encoding="utf-8"))
        assert "armed_at_unix" in payload
        assert payload["armed_at_unix"] <= payload["last_beat_unix"]
