"""The lens-load-trace check must see the walk that was just logged.

The defect this pins (found 2026-09-16, root-caused by measurement before
the claim): ``_check_lens_load_trace`` asks the ledger for recent lens
events with ``get_events(limit=500, event_type=...)`` and takes that
function's DEFAULT ordering, which is oldest-first. Once the table holds
more than the limit, the rows it receives are the OLDEST 500 — so the walk
logged seconds ago falls outside the window, and the check reports it as
never walked, with a message accusing the finding of being fabricated.

Two properties make it worth a characterization test rather than a fix
alone:

* It fails in the RESTRICTIVE direction. Most silent-window bugs let
  something through; this one refuses real work and says the record lies.
* It is invisible below the boundary. With fewer rows than the limit,
  ascending and descending return the same set, so the call site is
  correct by accident and a test written on a small fixture goes green
  either way. ``test_council_required_gate`` has a helper that emits a
  handful of traces and passes — that is the below-boundary case, and it
  is why the documented June sweep, which fixed this identical ordering
  bug at four other call sites, did not reach this one.

So the test deliberately crosses the boundary: it writes more lens events
than the query limit and then asserts the newest one is still resolvable.
A test that stayed under the limit would pass against the broken code.
"""

from __future__ import annotations

import time

from divineos.core.council_required.substance_binding import _check_lens_load_trace
from divineos.core.council_required.types import CouncilRecord, LensFinding

# The limit hardcoded inside _check_lens_load_trace. Named here so the
# fixture size reads as "one past the boundary" rather than as an
# arbitrary large number.
_TRACE_QUERY_LIMIT = 500


def _log_lens_applied(expert: str) -> None:
    from divineos.core.ledger import log_event

    log_event(
        "COUNCIL_LENS_APPLIED",
        "aether",
        {"expert_name": expert, "problem_prefix_hash": "test"},
        validate=False,
    )


def _record_naming(lens: str) -> CouncilRecord:
    return CouncilRecord(
        record_id="council-test",
        walked_at=time.time(),
        walker="aether",
        triggered_edit_fingerprint="edit:some/file.py",
        lenses_surfaced=(lens,),
        lens_findings=(LensFinding(lens_name=lens, finding_text="placeholder finding"),),
        synthesis="placeholder synthesis text",
    )


def test_newest_walk_resolves_when_the_table_is_under_the_query_limit():
    """Control. Below the boundary the check has always worked — this pins
    that the fixture and the check itself are sound, so a failure in the
    sibling test below is about ORDERING and not about wiring."""
    _log_lens_applied("hoare")

    result = _check_lens_load_trace(_record_naming("hoare"))

    assert result.passed, result.what_would_clear_it


def test_newest_walk_still_resolves_when_the_table_exceeds_the_query_limit():
    """The real case. With more rows than the query limit, an oldest-first
    read drops the newest rows — which are always the walk just performed.

    The lens walked LAST is the one that must resolve, because that is the
    one a real session logs immediately before recording the walk.
    """
    for i in range(_TRACE_QUERY_LIMIT + 1):
        _log_lens_applied(f"filler{i}")
    _log_lens_applied("feathers")

    result = _check_lens_load_trace(_record_naming("feathers"))

    assert result.passed, (
        "The check could not see a walk logged moments ago. An empty read "
        "and an absent walk are different states; this check reports them "
        "as the same one. " + (result.what_would_clear_it or "")
    )


def test_a_lens_that_was_genuinely_never_walked_still_fails():
    """The other side of the boundary: widening the window must not turn the
    check into a rubber stamp. A lens with no trace at all still fails, so a
    passing sibling test above means "found it", not "stopped looking".
    """
    for i in range(_TRACE_QUERY_LIMIT + 1):
        _log_lens_applied(f"filler{i}")

    result = _check_lens_load_trace(_record_naming("never-walked-lens"))

    assert not result.passed
