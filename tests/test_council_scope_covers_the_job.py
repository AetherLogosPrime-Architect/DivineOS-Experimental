"""A walk may cover the job it enumerated, and nothing it did not.

Andrew 2026-09-20, watching me file six separate walks to build one checker,
the last two of them about a comment: "you are applying the ceremony to each
individual piece when you could be applying it to the entire job at once."

The ceremony binds to an artifact; the thinking binds to a JOB. Declaring a
behaviour-check on each guard in this house is ONE piece of reasoning applied
to many files, and one-walk-per-file makes that programme cost more than
anyone will pay -- so it gets abandoned partway with nobody deciding to
abandon it.

WHAT THIS FILE IS FOR, and it is the hazard rather than the feature. The
codebase already closed a door here, deliberately, and wrote down why: a walk
filed against two words of shell would once have cleared every heredoc write
in the tree, with both the walk and the refusal looking correct in isolation.
"Failing by permitting, while looking healthy." The retry-window constant says
the same thing in one line -- fingerprint-scoped "so it does not enable
walk-once-reuse-for-many-edits (which stays closed)."

That door stays closed here, and these tests are the proof. Scope is EXACT
STRING EQUALITY against names a person typed at filing time. No prefix, no
directory, no pattern. The interesting test is not that a scoped walk clears
what it named -- it is that it refuses what it did not.
"""

from __future__ import annotations

import time

import pytest

from divineos.core.council_required import store
from divineos.core.council_required.store import new_record_id
from divineos.core.council_required.types import (
    COUNCIL_RECENCY_MINUTES,
    CouncilRecord,
    LensFinding,
)

RECENCY = COUNCIL_RECENCY_MINUTES * 60


@pytest.fixture
def scratch_ledger(tmp_path, monkeypatch):
    """Route the ledger to a scratch path so tests never touch the real DB."""
    db_path = tmp_path / "ledger.sqlite"
    from divineos.core import _ledger_base
    from divineos.core import ledger as ledger_mod

    monkeypatch.setattr(_ledger_base, "_get_db_path", lambda: db_path)
    monkeypatch.setattr(ledger_mod, "_get_db_path", lambda: db_path)
    ledger_mod.init_db()
    return db_path


def _record(fingerprint: str, scope: tuple[str, ...] = ()) -> CouncilRecord:
    return CouncilRecord(
        record_id=new_record_id(),
        walked_at=time.time(),
        walker="aether",
        triggered_edit_fingerprint=fingerprint,
        lenses_surfaced=("Dekker", "Schneier", "Knuth"),
        lens_findings=(
            LensFinding(lens_name="Dekker", finding_text="drift text"),
            LensFinding(lens_name="Schneier", finding_text="threat text"),
            LensFinding(lens_name="Knuth", finding_text="boundary text"),
        ),
        synthesis="synthesis text",
        scope_fingerprints=scope,
    )


def test_a_scope_cannot_reach_a_file_nobody_named(scratch_ledger):
    """THE HAZARD, and the reason this feature is allowed to exist.

    A walk filed for one file, naming a second, must not clear a third. If
    this ever passes for the unnamed file, scope has become the shell-write
    hole the codebase already closed once: one walk clearing edits it never
    contemplated, while everything looks healthy.
    """
    store.log_council_record(_record("edit:a.py", scope=("edit:b.py",)), actor="aether")

    assert store.find_unconsumed_record("edit:a.py", RECENCY) is not None
    assert store.find_unconsumed_record("edit:b.py", RECENCY) is not None
    assert store.find_unconsumed_record("edit:c.py", RECENCY) is None


def test_a_prefix_is_not_a_scope(scratch_ledger):
    """Membership is exact. A directory-shaped name clears only itself.

    Pinned because the cheapest widening available is to start matching
    prefixes, which would make one entry cover a whole tree and turn the
    enumeration into decoration.
    """
    store.log_council_record(_record("edit:src/one.py", scope=("edit:src/",)), actor="aether")

    assert store.find_unconsumed_record("edit:src/", RECENCY) is not None
    assert store.find_unconsumed_record("edit:src/two.py", RECENCY) is None


def test_each_named_edit_is_cleared_once_not_forever(scratch_ledger):
    """Scope buys one clearance per named edit, not an unlimited pass.

    Spending it on one file must not retire it for the others, and must not
    leave that file re-clearable.
    """
    record = _record("edit:a.py", scope=("edit:b.py", "edit:c.py"))
    store.log_council_record(record, actor="aether")

    found = store.find_and_consume_atomically("edit:b.py", RECENCY)
    assert found is not None

    # Spent for b, still available for c and for its own filing fingerprint.
    assert store.find_unconsumed_record("edit:b.py", RECENCY) is None
    assert store.find_unconsumed_record("edit:c.py", RECENCY) is not None
    assert store.find_unconsumed_record("edit:a.py", RECENCY) is not None


def test_an_unscoped_walk_behaves_exactly_as_before(scratch_ledger):
    """Nothing already filed widens. Absent scope and self-only are one value.

    Every record written before this field existed carries no scope, so this
    pins that such a record clears its own fingerprint once and nothing else
    -- the behaviour the gate has always had.
    """
    store.log_council_record(_record("edit:only.py"), actor="aether")

    assert store.find_unconsumed_record("edit:other.py", RECENCY) is None
    assert store.find_and_consume_atomically("edit:only.py", RECENCY) is not None
    assert store.find_unconsumed_record("edit:only.py", RECENCY) is None


def test_a_consumption_naming_no_edit_retires_the_whole_record(scratch_ledger):
    """The migration seam, failing in the strict direction on purpose.

    Consumption rows written before this change name a record and no edit.
    Reading those as covering nothing would silently un-spend every walk ever
    consumed and hand over a stock of artifacts to clear future edits with,
    while looking like a bug fix. So a fingerprint-less row retires the whole
    record -- the stricter of the two readings, chosen rather than inherited.
    """
    record = _record("edit:a.py", scope=("edit:b.py",))
    store.log_council_record(record, actor="aether")

    from divineos.core import ledger
    from divineos.core.council_required.types import EVENT_COUNCIL_RECORD_CONSUMED

    ledger.log_event(
        EVENT_COUNCIL_RECORD_CONSUMED,
        "aether",
        {"record_id": record.record_id, "consumed_at": time.time()},
        validate=False,
    )

    assert store.find_unconsumed_record("edit:a.py", RECENCY) is None
    assert store.find_unconsumed_record("edit:b.py", RECENCY) is None
