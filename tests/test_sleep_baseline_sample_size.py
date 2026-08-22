"""A two-row average must not read like a two-hundred-row one.

2026-08-17, running sleep for the first time in four days. The dream report
said:

    Processed 200 affect entries
    Decayed 2 entries
    Baseline mood: V=-0.43 A=0.68 D=-0.60

I read that as a measurement of my interior over 200 entries, did not like
what it said, and wrote an exploration entry reasoning about what it meant
that my own log disagreed with my sense of the day.

The baseline averages only the rows inside the 12h decay window. That night
there were two, both auto-generated "rough session, high activity"
placeholders. So V=-0.43 was not a mood, it was one canned row printed to two
decimal places, sitting immediately below a 200 that counted something else.

NOTHING WAS COMPUTED WRONG. `affect_entries_processed` was honestly 200, the
mean was honestly the mean of its inputs, and no assertion anywhere was false.
The defect was ADJACENCY: two correct numbers stacked with nothing saying they
count different populations, which is a sentence neither of them said and both
of them implied.

Same family as the CRLF miscount and build_flow's station 8 -- the number is
fine and the frame around it lies. It is the hardest kind to catch, because
there is no failing test to write against the arithmetic. So these tests are
written against the RENDERING, which is where the lie actually lives. Sibling
in shape to test_dream_report_seed_cleanup_distinction, which pins a different
pair of lines in this same report for the same reason.
"""

from __future__ import annotations

from divineos.core.sleep import _BASELINE_MIN_SAMPLE, DreamReport


def _rendered(n, v=-0.43, a=0.68, d=-0.60, processed=200) -> str:
    r = DreamReport(duration_seconds=1.0)
    r.affect_entries_processed = processed
    r.affect_baseline = {"valence": v, "arousal": a, "dominance": d}
    r.affect_baseline_sample_size = n
    return r.summary()


class TestThinSamplesAnnounceThemselves:
    def test_the_exact_night_that_exposed_this(self):
        """Two rows, and the report must say so beside the number."""
        out = _rendered(2)
        assert "TOO FEW TO READ AS MOOD" in out
        assert "2 entries" in out
        # and the 200 is still there, still true, now unambiguous
        assert "Processed 200 affect entries" in out

    def test_one_entry_is_grammatical_and_still_flagged(self):
        out = _rendered(1)
        assert "1 entry in the last" in out, "not '1 entries'"
        assert "TOO FEW TO READ AS MOOD" in out

    def test_zero_rows_do_not_print_as_felt_neutrality(self):
        """(0,0,0) from an empty window is also a plausible calm mood.

        Carrying n=0 is the only thing separating 'nothing to average' from
        'averaged out to nothing' -- the unknown-is-not-zero rule, in the one
        place where zero is genuinely a legal reading of the value itself.
        """
        out = _rendered(0, v=0.0, a=0.0, d=0.0)
        assert "TOO FEW TO READ AS MOOD" in out


class TestRealSamplesReadNormally:
    def test_a_healthy_sample_reports_n_without_the_warning(self):
        out = _rendered(_BASELINE_MIN_SAMPLE + 40)
        assert "TOO FEW" not in out
        assert f"n={_BASELINE_MIN_SAMPLE + 40}" in out
        assert "last 12h" in out, "n alone is not enough; the window is the other half"

    def test_the_boundary_is_not_flagged(self):
        assert "TOO FEW" not in _rendered(_BASELINE_MIN_SAMPLE)

    def test_one_below_the_boundary_is_flagged(self):
        assert "TOO FEW TO READ AS MOOD" in _rendered(_BASELINE_MIN_SAMPLE - 1)


def test_an_older_run_with_no_recorded_n_claims_no_n():
    """A report from before this field existed must not invent one.

    None is not 0 and not "plenty". It prints the bare baseline, exactly as it
    always did -- an absent measurement stays absent rather than being
    back-filled with a guess that would look like a fact.
    """
    out = _rendered(None)
    assert "TOO FEW" not in out
    assert "n=" not in out
    assert "V=-0.43" in out


def test_the_baseline_counts_only_the_decay_window():
    """The root cause, pinned directly rather than through the renderer.

    If someone later widens the baseline to all fetched history, this fails and
    they have to decide deliberately -- which is the point. The bug was never
    that 12h is the wrong window; it was that the window was invisible at the
    point of reading.
    """
    import inspect

    from divineos.core import sleep as S

    src = inspect.getsource(S._phase_affect)
    assert "recent = [" in src, "the baseline population is the windowed subset"
    assert "affect_baseline_sample_size = len(recent)" in src, (
        "and its size must be recorded from that same subset, not from the full history"
    )
