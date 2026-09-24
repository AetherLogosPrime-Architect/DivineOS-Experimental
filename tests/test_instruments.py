"""Tests for the instruments index.

The load-bearing behaviour is the SILENCE RULE: an instrument that has recorded
nothing must never read as healthy. Both of the failures that motivated this
module looked exactly like health from outside — a liveness check that reported
armed for two months while scanning for itself, and two verifiers that logged
nothing across 652 runs of their parent. So the empty and stale cases get
tested first and hardest.
"""

from __future__ import annotations

import inspect
import time
from pathlib import Path

import pytest

from divineos.core import instruments


@pytest.fixture
def home(tmp_path, monkeypatch):
    """An isolated instruments home, with the per-member home pointed elsewhere."""
    member = tmp_path / ".divineos-testmember"
    member.mkdir()
    monkeypatch.setenv("DIVINEOS_MEMBER", "testmember")
    monkeypatch.setattr(instruments, "unrouted_member_home", lambda: member)
    d = tmp_path / ".divineos"
    d.mkdir()
    return d


def test_empty_file_is_never_live(home):
    """A file that exists but recorded nothing is the never-fired case."""
    (home / "hook_timing.jsonl").write_text("", encoding="utf-8")
    r = instruments.read_instrument("hook_timing.jsonl", "q", home)
    assert r.status == "EMPTY"
    assert r.records == 0
    assert "NOTHING" in r.note


def test_stale_file_reads_silent_not_live(home):
    """Old enough is a question, regardless of how many records it holds."""
    p = home / "bypass_events.jsonl"
    p.write_text('{"a":1}\n' * 500, encoding="utf-8")
    old = time.time() - (instruments.SILENT_AFTER_DAYS + 10) * 86400
    import os

    os.utime(p, (old, old))
    r = instruments.read_instrument("bypass_events.jsonl", "q", home)
    assert r.status == "SILENT"
    assert r.records == 500  # plenty of records, still not answering


def test_fresh_file_with_records_is_live(home):
    (home / "hook_timing.jsonl").write_text('{"a":1}\n{"b":2}\n', encoding="utf-8")
    r = instruments.read_instrument("hook_timing.jsonl", "q", home)
    assert r.status == "LIVE"
    assert r.records == 2


def test_missing_file_reports_missing(home):
    r = instruments.read_instrument("nope.jsonl", "q", home)
    assert r.status == "MISSING"
    assert not r.exists


def test_blank_lines_do_not_count_as_records(home):
    (home / "hook_timing.jsonl").write_text("\n\n   \n", encoding="utf-8")
    assert instruments.read_instrument("hook_timing.jsonl", "q", home).status == "EMPTY"


def test_resolve_prefers_the_fresher_copy_not_the_member_home(home, monkeypatch):
    """The bug this tool caught in itself, pinned.

    Preferring the per-member home unconditionally made a stale duplicate
    outrank a shared file that was being written every turn. Freshness decides.
    """
    import os

    member = instruments.unrouted_member_home()
    shared_file = home / "bypass_events.jsonl"
    member_file = member / "bypass_events.jsonl"
    shared_file.write_text('{"fresh":1}\n', encoding="utf-8")
    member_file.write_text('{"stale":1}\n' * 99, encoding="utf-8")
    old = time.time() - 40 * 86400
    os.utime(member_file, (old, old))

    resolved = instruments._resolve("bypass_events.jsonl", home)
    assert resolved == shared_file, "the freshly-written copy must win"

    r = instruments.read_instrument("bypass_events.jsonl", "q", home)
    assert r.status == "LIVE"
    assert r.records == 1  # read the fresh one, not the 99-record stale one


def test_resolve_finds_a_surface_that_moved_to_the_member_home(home):
    """The other half: a writer that relocated must still be found."""
    (instruments.unrouted_member_home() / "last_pre_push_pytest.log").write_text(
        "ok\n", encoding="utf-8"
    )
    r = instruments.read_instrument("last_pre_push_pytest.log", "q", home)
    assert r.status == "LIVE"


def test_survey_reports_undocumented_surfaces(home):
    """An instrument nobody named is one nobody reaches for."""
    (home / "mystery_thing.jsonl").write_text('{"a":1}\n', encoding="utf-8")
    names = {r.name: r for r in instruments.survey(home)}
    assert "mystery_thing.jsonl" in names
    assert "UNDOCUMENTED" in names["mystery_thing.jsonl"].question


def test_survey_orders_problems_before_healthy(home):
    (home / "hook_timing.jsonl").write_text('{"a":1}\n', encoding="utf-8")
    (home / "bypass_events.jsonl").write_text("", encoding="utf-8")
    statuses = [r.status for r in instruments.survey(home)]
    assert statuses.index("EMPTY") < statuses.index("LIVE")


def test_briefing_block_is_silent_when_all_answering(home):
    """An alarm says nothing when nothing is wrong."""
    for name in instruments.KNOWN_INSTRUMENTS:
        # parents=True since 2026-08-24: the registry legitimately holds
        # nested paths now (data/logs/divineos.log), because the index went
        # recursive after reading a top-level orphan for 158 days while the
        # real log sat one directory down with 699,000 records in it.
        f = home / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text('{"a":1}\n', encoding="utf-8")
    assert instruments.briefing_block(home) is None


def test_briefing_block_speaks_when_an_instrument_goes_quiet(home):
    for name in instruments.KNOWN_INSTRUMENTS:
        # parents=True since 2026-08-24: the registry legitimately holds
        # nested paths now (data/logs/divineos.log), because the index went
        # recursive after reading a top-level orphan for 158 days while the
        # real log sat one directory down with 699,000 records in it.
        f = home / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text('{"a":1}\n', encoding="utf-8")
    (home / "hook_timing.jsonl").write_text("", encoding="utf-8")

    block = instruments.briefing_block(home)
    assert block is not None
    assert "hook_timing.jsonl" in block
    assert "divineos instruments" in block


def test_unreadable_file_does_not_hide_the_others(home, monkeypatch):
    """One broken reader must not take the survey down with it."""
    (home / "hook_timing.jsonl").write_text('{"a":1}\n', encoding="utf-8")

    real_count = instruments._count_records

    def boom(path):
        if path.name == "hook_timing.jsonl":
            raise OSError("simulated read failure")
        return real_count(path)

    monkeypatch.setattr(instruments, "_count_records", boom)
    # survey() must still return every instrument rather than raising
    assert len(instruments.survey(home)) >= len(instruments.KNOWN_INSTRUMENTS)


# ---------------------------------------------------------------------------
# WHERE THE INDEX LOOKS WHEN NOBODY HANDS IT A HOME.
#
# Every test above passes `home` in explicitly, so not one of them ever
# exercises the module's own resolution -- which is exactly why a hand-rolled
# `divineos_home()` that expanded `~` and honoured no override survived here
# from the module's first day. The suite could not have caught it by
# construction, and that is the finding underneath the finding.
#
# The cost: the index is the audit channel reporting which instruments are
# LIVE, EMPTY, SILENT or MISSING. Run from Aria's checkout it surveyed MY
# rooms, so her dead instrument would read LIVE because mine is. Beer,
# walk-3b65af27c439: an audit channel whose agreement between observers is
# manufactured by its own blindness is worse than one that disagrees.
# ---------------------------------------------------------------------------


def test_the_index_follows_the_home_override(tmp_path, monkeypatch):
    """No home handed in -- the module must resolve the one it was GIVEN."""
    from divineos.core.paths import divineos_home as canonical_home

    probe = tmp_path / "somebody-elses-house"
    probe.mkdir()
    monkeypatch.setenv("DIVINEOS_HOME", str(probe))

    assert canonical_home() == probe, "the probe itself must work, or this proves nothing"

    # A Reading carries no path, so the probe has to be a file the real home
    # CANNOT contain. A known instrument will not do: the first version of
    # this test used hook_timing.jsonl and passed against the broken module,
    # because the real home has a live one of that name. A test that passes
    # from the wrong house is not a test.
    #
    # survey() also reports undocumented surfaces found on disk, so a
    # uniquely-named file appears in the output only if this home was read.
    marker = "probe-only-in-the-given-home.jsonl"
    (probe / marker).write_text('{"probe":1}\n', encoding="utf-8")

    names = {r.name for r in instruments.survey()}
    assert marker in names, (
        "the index did not read the home it was given -- a file present only "
        f"there did not appear in the survey. Saw: {sorted(names)[:5]}"
    )


def test_the_module_keeps_no_private_home_resolver():
    """The invariant is ONE answerer, and a second definition breaks it by existing.

    Dijkstra, same walk: the invariant is false before any call is made, so
    the proof is the absence of a second definition rather than a passing
    behaviour check.
    """
    source = Path(inspect.getsourcefile(instruments)).read_text(encoding="utf-8")
    assert "def divineos_home(" not in source, (
        "a private divineos_home has returned to instruments.py -- the whole defect"
    )


def test_the_unrouted_sibling_still_ignores_the_override(tmp_path, monkeypatch):
    """The deliberate divergence stays deliberate.

    `unrouted_member_home` sits directly below the repaired function and MUST
    keep its hand-rolled path: its whole job is the unrouted directory the
    resolver routes AWAY from. Deleting one hand-rolled resolver while keeping
    the other is the entire judgement, and a sweep matching on shape rather
    than intent would take both (Hawking, same walk).
    """
    probe = tmp_path / "not-where-orphans-landed"
    probe.mkdir()
    monkeypatch.setenv("DIVINEOS_HOME", str(probe))
    monkeypatch.setenv("DIVINEOS_MEMBER", "testmember")

    unrouted = Path(instruments.unrouted_member_home())
    assert probe != unrouted and probe not in unrouted.parents, (
        "unrouted_member_home must NOT route -- its job is the unrouted directory"
    )
