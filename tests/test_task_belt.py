"""The task belt: rank the pile, pull a small current list, archive and refill on done.

Andrew 2026-09-23 designed it: "critical, severe or tasks that have wide reach
get chosen first.. something should pull from the todo list.. erase it from
the todo list as it goes into your current todo folder.. when you complete the
task it should mark it complete.. archive it.. and go pull another one".

Real stores in an isolated DIVINEOS_HOME throughout; the drawers are the real
modules, not stand-ins, because the joints between them are the whole build.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from divineos.core import task_belt as belt
from divineos.core.unified_todos import TodoItem


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    return tmp_path


def _item(source: str, item_id: str, age: float, **extra: object) -> TodoItem:
    return TodoItem(
        source=source,
        item_id=item_id,
        summary=f"{source} {item_id}",
        age_days=age,
        priority=0,
        extra=dict(extra),
    )


class TestRanking:
    def test_severity_then_reach_then_age(self) -> None:
        pile = [
            _item("structural-fix", "old-medium", 90),
            _item("audit", "critical", 1, severity="CRITICAL"),
            _item("structural-fix", "came-back-four-times", 2, occurrences=4),
            _item("correction", "high", 10),
        ]
        order = [i.item_id for i in sorted(pile, key=belt.rank)]
        assert order == ["critical", "high", "came-back-four-times", "old-medium"]

    def test_the_last_slot_goes_to_the_oldest_item_below_the_top_tier(self, home: Path) -> None:
        # Hundreds of HIGH corrections must not starve the MEDIUM repairs:
        # the August starvation, carried into the new design.
        pile = [_item("correction", f"c{n}", 10 + n) for n in range(5)]
        pile += [_item("structural-fix", "young", 1), _item("structural-fix", "oldest", 200)]
        current = belt._refill([], pile)
        assert [c["item_id"] for c in current] == ["c4", "c3", "oldest"]
        assert [c["reserved"] for c in current] == [False, False, True]

    def test_not_yet_due_and_acknowledgements_are_not_tasks(self) -> None:
        assert not belt._is_due(_item("prereg", "p", 1, overdue_days=0))
        assert belt._is_due(_item("prereg", "p", 1, overdue_days=3))
        assert not belt._is_due(_item("audit", "a", 1, severity="INFO"))


def _psf(content: str) -> str:
    from divineos.core.structural_fix_tracker import record_pending_fix

    return record_pending_fix(content, trigger="structural fix")


class TestTheFlow:
    def test_pull_moves_items_into_current_and_out_of_the_pile(self, home: Path) -> None:
        from divineos.core.structural_fix_tracker import list_current, list_pending

        ids = [_psf(f"structural fix: repair number {n} of the belt test") for n in range(4)]
        current = belt.pull()
        assert len(current) == belt.CURRENT_MAX
        picked = {c["item_id"] for c in current}
        # Erased from the pile as it goes into the current folder -- his words.
        assert picked == {e["id"] for e in list_current()}
        assert not picked & {e["id"] for e in list_pending()}
        assert len(list_pending()) == len(ids) - belt.CURRENT_MAX

    def test_done_archives_it_and_pulls_the_next(self, home: Path) -> None:
        for n in range(4):
            _psf(f"structural fix: repair number {n} of the belt test")
        first = belt.pull()[0]
        closed, current = belt.done(first["key"], "fixed in src/divineos/core/task_belt.py")
        assert closed["key"] == first["key"]
        assert first["key"] not in {c["key"] for c in current}
        assert len(current) == belt.CURRENT_MAX  # the next one came in
        rows = [
            json.loads(ln) for ln in (home / "task_belt_archive.jsonl").read_text().splitlines()
        ]
        assert [(r["key"], r["closed_how"]) for r in rows] == [(first["key"], "done")]

    def test_closed_at_its_own_source_is_noticed_and_archived(self, home: Path) -> None:
        from divineos.core.structural_fix_tracker import mark_done

        _psf("structural fix: the one that gets closed elsewhere")
        entry = belt.pull()[0]
        mark_done(entry["item_id"], note="closed with psf mark-done directly")
        assert belt.pull() == []
        rows = [
            json.loads(ln) for ln in (home / "task_belt_archive.jsonl").read_text().splitlines()
        ]
        assert rows[0]["closed_how"] == "closed at source"

    def test_a_drawer_that_cannot_be_read_closes_nothing(
        self, home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Could-not-look must never read as closed: that would archive a whole
        # drawer the first time its store failed to open.
        belt._save_current(
            [
                {
                    "key": "correction:7",
                    "source": "correction",
                    "item_id": "7",
                    "summary": "x",
                    "severity": "HIGH",
                    "prompts": 3,
                }
            ]
        )

        def broken() -> list:
            raise OSError("store unreadable")

        monkeypatch.setattr("divineos.core.andrew_correction_tracker.list_open", broken)
        assert [c["key"] for c in belt.pull(pile=[])] == ["correction:7"]
        assert not (home / "task_belt_archive.jsonl").exists()

    def test_a_correction_closes_only_through_the_tracker_and_its_rules(self, home: Path) -> None:
        from divineos.core.andrew_correction_tracker import file_correction, list_open

        cid = file_correction("belt test correction: the thing he asked for")
        entry = belt.pull()[0]
        assert entry["key"] == f"correction:{cid}"
        with pytest.raises(ValueError, match="refused"):
            belt.done(entry["key"], "I will remember to do better next time")  # prose only
        assert cid in {r["id"] for r in list_open()}
        belt.done(entry["key"], "fixed in src/divineos/core/task_belt.py, tests/test_task_belt.py")
        assert cid not in {r["id"] for r in list_open()}


class TestRefusals:
    def test_done_needs_the_item_on_the_current_list(self, home: Path) -> None:
        with pytest.raises(ValueError, match="not on the current list"):
            belt.done("structural-fix:psf-nope", "src/divineos/core/task_belt.py")

    def test_done_needs_real_evidence(self, home: Path) -> None:
        _psf("structural fix: evidence required")
        entry = belt.pull()[0]
        with pytest.raises(ValueError, match="real commit or an existing file"):
            belt.done(entry["key"], "trust me, it is done")

    def test_a_prereg_closes_with_its_own_command(self, home: Path) -> None:
        belt._save_current(
            [
                {
                    "key": "prereg:p1",
                    "source": "prereg",
                    "item_id": "p1",
                    "summary": "x",
                    "severity": "MEDIUM",
                    "prompts": 0,
                }
            ]
        )
        with pytest.raises(ValueError, match="prereg assess p1"):
            belt.done("prereg:p1", "src/divineos/core/task_belt.py")


class TestTheSurface:
    def test_the_block_is_still_between_milestones_and_speaks_when_one_is_crossed(
        self, home: Path
    ) -> None:
        # Aria's reading: a counter rising by one each prompt carries no news
        # and only defeats dedup. The block changes on the crossing prompt.
        _psf("structural fix: the stuck one")
        first, second = belt.surface(), belt.surface()
        assert first == second and "new on the list" in first
        for _ in range(2):  # prompts three and four
            belt.surface()
        crossed = belt.surface()  # the fifth prompt
        assert "!! this prompt it crossed 5 prompts" in crossed
        after = belt.surface()
        assert "stuck past 5 prompts" in after and "!!" not in after

    def test_the_residual_names_every_current_item(self, home: Path) -> None:
        # What survives dedup's "unchanged": the list, still named.
        for n in range(2):
            _psf(f"structural fix: residual item {n}")
        belt.surface()
        line = belt.residual()
        assert line.count("build structural-fix:psf-") == 2

    def test_a_correction_filed_twice_takes_one_slot_and_closes_whole(self, home: Path) -> None:
        # Aria found two of three slots spent on one correction, filed raw and
        # again under "Andrew verbatim:".
        from divineos.core.andrew_correction_tracker import file_correction, list_open

        raw = "first thats not the dream lol go look at your actual apple dream lol and read it"
        a = file_correction(raw)
        b = file_correction(f"Andrew verbatim: {raw}")
        file_correction("a different correction entirely, about something else he said")
        current = belt.pull()
        holders = [c for c in current if str(a) in [c["item_id"], *c["twins"]]]
        assert len(holders) == 1 and sorted(
            [holders[0]["item_id"], *holders[0]["twins"]]
        ) == sorted([str(a), str(b)])
        belt.done(
            holders[0]["key"], "fixed in src/divineos/core/task_belt.py, tests/test_task_belt.py"
        )
        still = {r["id"] for r in list_open()}
        assert a not in still and b not in still

    def test_each_line_says_what_to_do_and_how_to_close_it(self, home: Path) -> None:
        _psf("structural fix: say the close command")
        out = belt.surface()
        assert "work this, don't ask" in out
        assert "build psf-" in out
        assert "divineos belt done structural-fix:psf-" in out

    def test_silent_when_every_drawer_is_empty(self, home: Path) -> None:
        assert belt.surface() == ""


class TestThePileItReads:
    def test_audit_severity_is_read_from_the_enum_value(self, home: Path) -> None:
        # It was stringified before .value was read, so every finding became
        # "Severity.HIGH" and matched no rank.
        from divineos.core.unified_todos import _audit_todos
        from divineos.core.watchmen import store
        from divineos.core.watchmen.types import FindingCategory, Severity

        round_id = store.submit_round(actor="user", focus="belt test round")
        store.submit_finding(
            round_id=round_id,
            actor="user",
            title="belt test finding",
            severity=Severity.HIGH,
            category=FindingCategory.BEHAVIOR,
            description="a high finding the pile must rank as HIGH",
            auto_route=False,
        )
        [item] = _audit_todos()
        assert item.extra["severity"] == "HIGH"
        assert item.priority == 1

    def test_a_correction_has_its_real_age(self, home: Path) -> None:
        from divineos.core.andrew_correction_tracker import file_correction
        from divineos.core.unified_todos import _correction_todos

        file_correction("belt test correction with an age")
        [item] = _correction_todos(now=__import__("time").time() + 86400 * 3)
        assert item.age_days is not None and item.age_days > 2.9

    def test_the_todos_label_table_covers_every_drawer(self) -> None:
        from divineos.cli.todos_commands import _SOURCE_HEADER
        from divineos.core.unified_todos import SOURCES

        assert set(_SOURCE_HEADER) == set(SOURCES)

    def test_todos_counts_only_runs(self, home: Path) -> None:
        # Only the todos command is registered: importing the whole CLI cold
        # can outlast the per-test timeout on its own, which made this test
        # fail by run order rather than by anything it checks.
        import click
        from click.testing import CliRunner

        from divineos.cli import todos_commands

        group = click.Group()
        todos_commands.register(group)
        result = CliRunner().invoke(group, ["todos", "--counts-only"])
        assert result.exit_code == 0, result.output
        assert "structural-fix" in result.output
