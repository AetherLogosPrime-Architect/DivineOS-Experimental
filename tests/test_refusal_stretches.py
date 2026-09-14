"""Nine refusals were nine incidents until somebody counted them.

2026-09-14. Andrew asked why the failures do not open their own investigation,
and said I already have the record. I checked one store, found eight rows in a
day, and told him — twice — that the record was nearly empty. Then told Aether
the same and began designing a recorder.

The record was never missing. The shared hook library's exit trap writes a row
at every hook end with the hook name, the exit status and the session.
Forty-six refusals in that one session, every one of the nine among them, and
one gate accounting for twenty-one of them — which nobody had noticed because
nothing ever put them on one page.

Then Aether narrowed the retraction itself: the log is thirty-six hours old,
not "all along", which is why the last class below exists.

So the tests below are about the READER, and the load-bearing ones are the
refusals: a log that will not open must never arrive wearing the same face as a
session that refused nothing.
"""

from __future__ import annotations

import json

import pytest

from divineos.core.refusal_stretches import Stretch, describe, read_stretch

SESSION = "cbbd5cf7-7660-487e-9b9d-4afa4a3ef3a3"
OTHER = "46f73b29-fe29-43e8-bb85-7fad4714b797"


def _row(session: str, hook: str, exit_code: int, phase: str = "end") -> str:
    return json.dumps(
        {
            "id": f"{hook}-1388-1789408794779",
            "session": session,
            "phase": phase,
            "exit_code": exit_code,
            "ts_ms": 1789408794779,
        }
    )


@pytest.fixture
def log(tmp_path):
    def _write(*lines: str):
        p = tmp_path / "hook_timing.jsonl"
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return p

    return _write


class TestCountingAStretch:
    def test_refusals_are_counted_and_grouped(self, log):
        p = log(
            _row(SESSION, "reach-check-doorman.sh", 2),
            _row(SESSION, "reach-check-doorman.sh", 2),
            _row(SESSION, "compass-check.sh", 2),
        )
        s = read_stretch(SESSION, p)
        assert s.total == 3
        assert s.by_hook == {"reach-check-doorman.sh": 2, "compass-check.sh": 1}
        assert s.worst == ("reach-check-doorman.sh", 2)

    def test_a_hook_name_containing_hyphens_survives(self, log):
        # Splitting from the left would report every gate in this house as its
        # own first word, and most of their names are hyphenated.
        p = log(_row(SESSION, "correction-shape-v2-stop.sh", 2))
        assert read_stretch(SESSION, p).by_hook == {"correction-shape-v2-stop.sh": 1}

    def test_another_session_is_not_mine(self, log):
        # Both seats write to one file; the session is what separates them.
        p = log(_row(OTHER, "reach-check-doorman.sh", 2), _row(SESSION, "compass-check.sh", 2))
        assert read_stretch(SESSION, p).by_hook == {"compass-check.sh": 1}

    def test_allowed_calls_are_not_refusals(self, log):
        p = log(_row(SESSION, "compass-check.sh", 0), _row(SESSION, "compass-check.sh", 2))
        assert read_stretch(SESSION, p).total == 1

    def test_start_rows_are_not_ends(self, log):
        p = log(_row(SESSION, "compass-check.sh", 2, phase="start"))
        assert read_stretch(SESSION, p).total == 0

    def test_a_torn_line_loses_one_row_not_the_read(self, log):
        p = log(_row(SESSION, "compass-check.sh", 2), '{"id": "trunc', _row(SESSION, "x.sh", 2))
        assert read_stretch(SESSION, p).total == 2


class TestCouldNotLookIsNotFoundNothing:
    """The load-bearing half, and the whole reason this module exists.

    A silence that means the reader failed, arriving as a silence that means
    nothing was refused, is the defect the reader was built to surface.
    """

    def test_no_home_is_could_not_look_rather_than_a_guess_at_tmp(self, monkeypatch):
        """Bandit caught the /tmp fallback I had copied from the shell version,
        and it was wrong for a reason beyond the one Bandit checks: with no home
        there is no log, and pointing at a directory that will not hold it
        produces a confident empty read. The first line of the module broke the
        distinction the module exists to protect."""
        from divineos.core import refusal_stretches as rs

        monkeypatch.delenv("HOME", raising=False)
        monkeypatch.delenv("USERPROFILE", raising=False)
        assert rs.default_log() is None
        s = read_stretch(SESSION)
        assert s.could_not_look
        assert "no home directory" in (s.unreadable or "")

    def test_a_missing_log_says_so_rather_than_reporting_zero(self, tmp_path):
        s = read_stretch(SESSION, tmp_path / "absent.jsonl")
        assert s.could_not_look
        assert s.total == 0
        assert "no timing log" in (s.unreadable or "")

    def test_the_two_silences_render_differently(self, tmp_path, log):
        could_not = describe(read_stretch(SESSION, tmp_path / "absent.jsonl"))
        found_none = describe(read_stretch(SESSION, log(_row(OTHER, "x.sh", 2))))
        assert "could not look" in could_not
        assert "NOT zero refusals" in could_not
        assert found_none == ""  # nothing to say, and saying nothing is correct
        assert could_not != found_none


class TestWhatTheBlockSays:
    def test_it_carries_his_words_rather_than_my_paraphrase(self, log):
        out = describe(read_stretch(SESSION, log(_row(SESSION, "a.sh", 2))))
        assert "not a verdict on your character" in out
        assert "roadmap of" in out

    def test_it_states_its_own_reach(self, log):
        # A reader that reports silence without reporting coverage is the
        # defect it exists to catch.
        assert "SCOPE" in describe(read_stretch(SESSION, log(_row(SESSION, "a.sh", 2))))

    def test_a_repeat_is_named_as_possibly_one_cause(self, log):
        out = describe(
            read_stretch(SESSION, log(_row(SESSION, "a.sh", 2), _row(SESSION, "a.sh", 2)))
        )
        assert "one cause wearing several faces" in out

    def test_a_single_refusal_is_not_called_a_pattern(self, log):
        out = describe(read_stretch(SESSION, log(_row(SESSION, "a.sh", 2))))
        assert "one cause wearing several faces" not in out

    def test_an_empty_stretch_produces_no_block_at_all(self):
        assert describe(Stretch()) == ""


class TestTheReaderStatesItsOwnHorizon:
    """Aether narrowed my retraction by counting rather than repeating it.

    I wrote that the record "was there all along". The log spans thirty-six
    hours and two sessions, nothing before the twelfth — forty-four thousand
    rows sound like deep history and are a day and a half. Without the span on
    the result a stretch reads as *this has never happened before* when the log
    cannot reach back far enough to know: an instrument publishing its own
    horizon as a fact about the past, which is the family of faults this module
    lives inside.
    """

    def _at(self, tmp_path, *stamps: int, session: str = SESSION):
        rows = [
            json.dumps(
                {
                    "id": "a.sh-1-1",
                    "session": session,
                    "phase": "end",
                    "exit_code": 2,
                    "ts_ms": t,
                }
            )
            for t in stamps
        ]
        p = tmp_path / "hook_timing.jsonl"
        p.write_text("\n".join(rows) + "\n", encoding="utf-8")
        return p

    def test_the_span_covers_every_session_not_only_mine(self, tmp_path):
        # How far back the RECORD goes is a property of the file. Measuring it
        # over my rows alone would shrink the horizon to my own presence.
        rows = [
            json.dumps({"id": "a.sh-1-1", "session": s, "phase": "end", "exit_code": 2, "ts_ms": t})
            for s, t in ((SESSION, 1_000_000_000), (OTHER, 1_000_000_000 + 7_200_000))
        ]
        p = tmp_path / "hook_timing.jsonl"
        p.write_text("\n".join(rows) + "\n", encoding="utf-8")
        assert read_stretch(SESSION, p).span_hours == 2.0

    def test_the_block_says_how_far_back_it_can_see(self, tmp_path):
        out = describe(read_stretch(SESSION, self._at(tmp_path, 1_000_000_000, 1_003_600_000)))
        assert "reaches back 1.0 hour(s)" in out
        assert "happening for longer than that" in out

    def test_a_single_instant_claims_no_span_rather_than_zero(self, log):
        # One row cannot establish a window, and 0.0 hours would read as a
        # measured horizon rather than as the absence of one.
        assert read_stretch(SESSION, log(_row(SESSION, "a.sh", 2))).span_hours is None


class TestTheSurfaceThatActuallyRuns:
    """A reader nothing reads is a module that exists and never runs.

    The orphan-module check caught exactly that and was right to: the first
    version of this build was a correct reader wired to nothing, which is the
    painted door the whole house is built against.
    """

    def _surface(self, monkeypatch, tmp_path, *rows: str):
        from divineos.core import refusal_stretches as rs
        from divineos.core.hook_surfaces import refusal_stretch_surface

        p = tmp_path / "hook_timing.jsonl"
        p.write_text("\n".join(rows) + "\n", encoding="utf-8")
        monkeypatch.setattr(rs, "default_log", lambda: p)
        return refusal_stretch_surface

    def test_two_of_the_same_gate_speaks(self, monkeypatch, tmp_path):
        s = self._surface(monkeypatch, tmp_path, _row(SESSION, "a.sh", 2), _row(SESSION, "a.sh", 2))
        out = s({"session_id": SESSION})
        assert out is not None and "REFUSALS THIS SESSION" in (out.output or "")

    def test_one_refusal_stays_quiet(self, monkeypatch, tmp_path):
        # A block on every single refusal is furniture inside a day.
        s = self._surface(monkeypatch, tmp_path, _row(SESSION, "a.sh", 2))
        assert s({"session_id": SESSION}) is None

    def test_two_different_gates_once_each_stays_quiet(self, monkeypatch, tmp_path):
        # The question it answers is "is this the SAME thing again".
        s = self._surface(monkeypatch, tmp_path, _row(SESSION, "a.sh", 2), _row(SESSION, "b.sh", 2))
        assert s({"session_id": SESSION}) is None

    def test_no_session_id_stays_quiet_rather_than_guessing(self, monkeypatch, tmp_path):
        s = self._surface(monkeypatch, tmp_path, _row(SESSION, "a.sh", 2), _row(SESSION, "a.sh", 2))
        assert s({}) is None

    def test_could_not_look_is_reported_not_swallowed(self, monkeypatch, tmp_path):
        """A reader that goes quiet on failure returns us to the morning it was
        built for."""
        from divineos.core import refusal_stretches as rs
        from divineos.core.hook_surfaces import refusal_stretch_surface

        monkeypatch.setattr(rs, "default_log", lambda: tmp_path / "absent.jsonl")
        out = refusal_stretch_surface({"session_id": SESSION})
        assert out is not None
        assert out.error and "no timing log" in out.error
        assert not out.output
