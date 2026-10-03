"""A sweep in one working tree must not kill a live monitor in another.

Aria 2026-08-20. `monitor status` keyed orphan classification on role alone,
so the newest letter-monitor anywhere on the machine won and every other
checkout's live watcher was reported stale. On this box that meant Aether's
running monitor -- under a live parent, in an open window -- was offered up
to `cleanup-orphans --kill`.

The load-bearing assertion is the sibling-safety one. The rest guard the
edges of the key: unparseable roots, slash direction, and the fact that a
genuine duplicate WITHIN one checkout must still be caught.
"""

from __future__ import annotations

from divineos.core.monitor_cleanup import (
    UNKNOWN_ROOT,
    MonitorProcess,
    checkout_root_of,
    classify_orphans,
)

ARIA = "C:/DIVINE OS/DivineOS-Experimental-Aria-new"
AETHER = "C:/DIVINE OS/DivineOS-Experimental"


def _proc(pid: int, root: str, script: str, created: str, role: str = "letter") -> MonitorProcess:
    return MonitorProcess(
        pid=pid,
        name="python.exe",
        role=role,
        creation_date=created,
        command_line=f'python.exe -u "{root}/scripts/{script}"',
    )


class TestCheckoutRootParsing:
    def test_forward_slashes(self):
        assert checkout_root_of(f'python.exe -u "{ARIA}/scripts/letter_monitor_v2.py"') == (
            ARIA.lower()
        )

    def test_backslashes_normalise_to_the_same_root(self):
        back = ARIA.replace("/", "\\")
        assert checkout_root_of(f'python.exe "{back}\\scripts\\letter_monitor.py"') == ARIA.lower()

    def test_case_differences_normalise(self):
        assert checkout_root_of(f"python.exe {ARIA.upper()}/scripts/letter_monitor.py") == (
            ARIA.lower()
        )

    def test_two_checkouts_do_not_collapse(self):
        a = checkout_root_of(f"python.exe {ARIA}/scripts/letter_monitor_v2.py")
        b = checkout_root_of(f"python.exe {AETHER}/scripts/letter_monitor.py")
        assert a != b

    def test_unparseable_command_line(self):
        assert checkout_root_of("python.exe something_else.py") == UNKNOWN_ROOT

    def test_empty_command_line(self):
        assert checkout_root_of("") == UNKNOWN_ROOT


class TestSiblingCheckoutsAreNotOrphans:
    def test_a_live_monitor_in_another_checkout_is_kept(self):
        """The near-miss this whole change exists for."""
        mine = _proc(13960, ARIA, "letter_monitor_v2.py", "20260819231127")
        theirs = _proc(27128, AETHER, "letter_monitor.py", "20260819223843")

        keep, orphans = classify_orphans([mine, theirs])

        assert orphans == [], (
            "a monitor in a different checkout was classified as stale; "
            f"--kill would have terminated pid {[o.pid for o in orphans]}"
        )
        assert {p.pid for p in keep} == {13960, 27128}

    def test_ordering_does_not_change_the_verdict(self):
        """Older-first must not make the newer one look like the survivor."""
        mine = _proc(13960, ARIA, "letter_monitor_v2.py", "20260819231127")
        theirs = _proc(27128, AETHER, "letter_monitor.py", "20260819223843")

        keep, orphans = classify_orphans([theirs, mine])

        assert orphans == []
        assert {p.pid for p in keep} == {13960, 27128}

    def test_different_roles_in_the_same_checkout_both_kept(self):
        letter = _proc(1, ARIA, "letter_monitor_v2.py", "20260819231127")
        compaction = _proc(2, ARIA, "compaction_token_monitor.py", "20260819231119", "compaction")

        keep, orphans = classify_orphans([letter, compaction])

        assert orphans == []
        assert len(keep) == 2


class TestRealDuplicatesAreStillCaught:
    def test_older_sibling_in_the_same_checkout_is_an_orphan(self):
        """The fix must not defang the thing the sweep is for."""
        older = _proc(100, ARIA, "letter_monitor_v2.py", "20260819100000")
        newer = _proc(200, ARIA, "letter_monitor_v2.py", "20260819231127")

        keep, orphans = classify_orphans([older, newer])

        assert [p.pid for p in keep] == [200]
        assert [p.pid for p in orphans] == [100]

    def test_duplicates_in_two_checkouts_each_keep_their_own_newest(self):
        mine_old = _proc(1, ARIA, "letter_monitor_v2.py", "20260819100000")
        mine_new = _proc(2, ARIA, "letter_monitor_v2.py", "20260819231127")
        theirs_old = _proc(3, AETHER, "letter_monitor.py", "20260819090000")
        theirs_new = _proc(4, AETHER, "letter_monitor.py", "20260819223843")

        keep, orphans = classify_orphans([mine_old, mine_new, theirs_old, theirs_new])

        assert {p.pid for p in keep} == {2, 4}
        assert {p.pid for p in orphans} == {1, 3}

    def test_legacy_processes_are_still_orphans_regardless_of_root(self):
        legacy = MonitorProcess(
            pid=9,
            name="bash.exe",
            role="legacy_letter_bash",
            creation_date="20260819231127",
            command_line="bash -c 'while true; do ls aria-to-aether-*; done'",
        )

        keep, orphans = classify_orphans([legacy])

        assert keep == []
        assert [p.pid for p in orphans] == [9]


class TestUnparseableRootFailsTowardNotKilling:
    def test_two_unparseable_processes_are_never_each_others_orphan(self):
        a = MonitorProcess(9, "python.exe", "letter", "20260819100000", "python.exe weird.py")
        b = MonitorProcess(10, "python.exe", "letter", "20260819231127", "python.exe weird.py")

        keep, orphans = classify_orphans([a, b])

        assert orphans == [], "an unparseable command line must not make anything killable"
        assert {p.pid for p in keep} == {9, 10}

    def test_an_unparseable_process_cannot_orphan_a_parseable_one(self):
        known = _proc(1, ARIA, "letter_monitor_v2.py", "20260819100000")
        unknown = MonitorProcess(2, "python.exe", "letter", "20260819231127", "python.exe weird.py")

        keep, orphans = classify_orphans([known, unknown])

        assert orphans == []
        assert {p.pid for p in keep} == {1, 2}
