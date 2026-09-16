"""The game-walk requirement: owed on the same gravity call, spent once.

Written because the command this tests was written, registered, and never
run, and a signature error sat in it undisturbed until the first invocation.
The lesson was not the keyword argument. It was that an unrun thing and a
working thing look identical from every surface this house has.

Fingerprints are uniquified per test so these run against the real ledger
without colliding with each other or with live walks.
"""

from __future__ import annotations

import uuid

import pytest

from divineos.core import game_walk_required as gw
from divineos.core.ledger import log_event


def _fingerprint() -> str:
    return f"edit:tests/fixture_{uuid.uuid4().hex[:12]}.py"


def _file_walk(fingerprint: str, *, mechanism: str = "a fixture mechanism") -> str:
    return log_event(
        event_type=gw.GAME_WALK_FILED,
        actor="test",
        payload={
            "mechanism": mechanism,
            "edit_fingerprint": fingerprint,
            "route_count": 1,
            "leak_count": 0,
            "open_route_count": 1,
            "rendered": "GAME-WALK -- fixture",
        },
    )


class TestBothAbsencesArriveTogether:
    """The one-refusal rule, which is the whole reason this rides the
    council gate instead of carrying its own trigger."""

    def test_nothing_filed_reports_both(self) -> None:
        missing = gw.missing_artifacts(_fingerprint(), council_record_present=False)
        assert missing == ["council", "game-walk"]

    def test_council_done_reports_only_the_game_walk(self) -> None:
        missing = gw.missing_artifacts(_fingerprint(), council_record_present=True)
        assert missing == ["game-walk"]

    def test_both_present_reports_nothing(self) -> None:
        fp = _fingerprint()
        _file_walk(fp)
        assert gw.missing_artifacts(fp, council_record_present=True) == []

    def test_the_refusal_names_every_missing_artifact_in_one_message(self) -> None:
        fp = _fingerprint()
        msg = gw.format_missing_message(["council", "game-walk"], fp)
        assert "MISSING: council walk" in msg
        assert "MISSING: game-walk" in msg
        assert fp in msg

    def test_the_refusal_states_what_it_did_not_check(self) -> None:
        """A gate that overstates its assurance teaches the reader to relax
        on something it never verified."""
        msg = gw.format_missing_message(["game-walk"], _fingerprint())
        assert "did NOT check that the thinking" in msg

    def test_no_missing_artifacts_produces_no_message(self) -> None:
        assert gw.format_missing_message([], _fingerprint()) == ""


class TestOneWalkClearsOneEdit:
    """Without consumption a single filing would clear every future edit of
    the same file forever, which is the cheapest route around the
    requirement and would not even look like cheating."""

    def test_a_filed_walk_is_found(self) -> None:
        fp = _fingerprint()
        _file_walk(fp)
        assert gw.find_unconsumed_walk(fp) is not None

    def test_a_spent_walk_is_not_found_again(self) -> None:
        fp = _fingerprint()
        _file_walk(fp)
        walk = gw.find_unconsumed_walk(fp)
        assert walk is not None
        gw.consume_walk(walk, consumed_by_fingerprint=fp)
        assert gw.find_unconsumed_walk(fp) is None

    def test_a_walk_for_another_edit_does_not_clear_this_one(self) -> None:
        other = _fingerprint()
        _file_walk(other)
        assert gw.find_unconsumed_walk(_fingerprint()) is None

    def test_consumption_records_which_edit_spent_it(self) -> None:
        """Filed and consuming fingerprints are written down separately so a
        reader can see whether a walk was used where it was aimed."""
        from divineos.core.ledger import get_events

        fp = _fingerprint()
        _file_walk(fp)
        walk = gw.find_unconsumed_walk(fp)
        assert walk is not None
        gw.consume_walk(walk, consumed_by_fingerprint="edit:somewhere/else.py")

        rows = get_events(limit=20, event_type=[gw.GAME_WALK_CONSUMED], order="desc")
        payloads = [r.get("payload") or {} for r in rows]
        mine = [p for p in payloads if p.get("filed_fingerprint") == fp]
        assert mine, "the consume event was not written"
        assert mine[0]["consumed_by_fingerprint"] == "edit:somewhere/else.py"


class TestOneActCostsOneWalkOnBothSidesOfTheDoor:
    """The retry window, added because the absence of one was MEASURED during
    this module's own build: three edits to one file cost three game-walks
    while the council side cost one, because the council gate has a retry
    window and this had none."""

    def test_a_just_spent_walk_still_clears_the_next_edit(self) -> None:
        fp = _fingerprint()
        _file_walk(fp)
        walk = gw.find_unconsumed_walk(fp)
        assert walk is not None
        gw.consume_walk(walk, consumed_by_fingerprint=fp)

        assert gw.find_unconsumed_walk(fp) is None, "the walk should be spent"
        assert gw.find_recently_consumed_walk(fp) is not None
        assert gw.missing_artifacts(fp, council_record_present=True) == []

    def test_the_window_closes(self) -> None:
        """A generous-enough window would make every walk permanent after the
        first edit of any file, which is the route the walk named as open."""
        import time

        from divineos.core.council_required.types import RETRY_WINDOW_SECONDS

        fp = _fingerprint()
        _file_walk(fp)
        walk = gw.find_unconsumed_walk(fp)
        assert walk is not None
        gw.consume_walk(walk, consumed_by_fingerprint=fp)

        later = time.time() + RETRY_WINDOW_SECONDS + 60
        assert gw.find_recently_consumed_walk(fp, now=later) is None
        assert gw.missing_artifacts(fp, council_record_present=True, now=later) == ["game-walk"]

    def test_a_spent_walk_does_not_clear_a_different_edit(self) -> None:
        """Fingerprint-exact, same as the council gate's own retry scope."""
        fp = _fingerprint()
        _file_walk(fp)
        walk = gw.find_unconsumed_walk(fp)
        assert walk is not None
        gw.consume_walk(walk, consumed_by_fingerprint=fp)

        assert gw.find_recently_consumed_walk(_fingerprint()) is None


class TestItRidesTheAssessor:
    def test_a_council_required_edit_owes_a_game_walk(self) -> None:
        class Gravity:
            is_council_required = True

        assert gw.is_game_walk_required(Gravity()) is True

    def test_an_edit_below_the_threshold_owes_nothing(self) -> None:
        class Gravity:
            is_council_required = False

        assert gw.is_game_walk_required(Gravity()) is False

    def test_a_degraded_assessor_fails_toward_scrutiny(self) -> None:
        """Matching the council gate's own 2026-07-19 flip. Failing open
        means the gate is silently absent exactly when the thing that
        reports on edits is itself broken."""

        class Broken:
            pass

        assert gw.is_game_walk_required(Broken()) is True

    def test_the_real_assessor_agrees_with_the_council_tier(self) -> None:
        from divineos.core.gravity_classifier import score_substrate_modification

        gravity = score_substrate_modification("Edit", ("src/divineos/core/x.py",), "")
        assert gw.is_game_walk_required(gravity) == gravity.is_council_required


class TestTheAgeOfARowIsReadDirectly:
    """Added after 44 green tests passed over a function missing its final
    return. Every one of them reached the numeric branch; none reached the
    parsing one, because the live store returns numbers. A suite green over
    a dead branch is an instrument reading zero and I read it as a clean
    bill of health."""

    def test_a_numeric_timestamp_is_read_as_is(self) -> None:
        assert gw._event_time({"timestamp": 1700000000.5}) == 1700000000.5

    def test_a_text_timestamp_is_parsed(self) -> None:
        """The branch that was silently broken."""
        got = gw._event_time({"timestamp": "2026-09-16T12:00:00+00:00"})
        assert got is not None
        assert got > 0

    def test_a_text_timestamp_with_a_zulu_suffix_is_parsed(self) -> None:
        assert gw._event_time({"timestamp": "2026-09-16T12:00:00Z"}) is not None

    def test_the_two_text_timestamps_agree(self) -> None:
        zulu = gw._event_time({"timestamp": "2026-09-16T12:00:00Z"})
        offset = gw._event_time({"timestamp": "2026-09-16T12:00:00+00:00"})
        assert zulu == offset

    def test_an_unparseable_timestamp_is_unknown_age(self) -> None:
        assert gw._event_time({"timestamp": "not a date at all"}) is None

    def test_a_missing_timestamp_is_unknown_age(self) -> None:
        assert gw._event_time({}) is None

    def test_a_parsed_row_is_inside_its_own_window(self) -> None:
        """End to end on the branch: a walk whose row carries a TEXT time is
        still found. This is the assertion the missing return would fail."""
        import time
        from datetime import datetime, timezone

        fp = _fingerprint()
        now = time.time()
        row = {
            "event_type": gw.GAME_WALK_FILED,
            "event_id": "fixture-1",
            "timestamp": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
            "payload": {"edit_fingerprint": fp},
        }
        age = gw._event_time(row)
        assert age is not None, "a text timestamp must yield an age"
        assert abs(now - age) < 5


class TestTheLookupRefusesRatherThanGuesses:
    @pytest.mark.parametrize("empty", ["", "   "])
    def test_an_empty_fingerprint_matches_nothing(self, empty: str) -> None:
        assert gw.find_unconsumed_walk(empty) is None

    def test_a_walk_outside_the_recency_window_does_not_clear_the_edit(self) -> None:
        import time

        fp = _fingerprint()
        _file_walk(fp)
        future = time.time() + (gw.GAME_WALK_RECENCY_MINUTES * 60) + 60
        assert gw.find_unconsumed_walk(fp, now=future) is None
