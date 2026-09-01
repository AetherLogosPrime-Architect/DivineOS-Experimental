"""Tests for the auto-next-task surface (core/next_task_surface.py).

Per prereg-d99b6b8a442b: every turn should carry a NEXT TASK line in
pre-response context so the agent works the named task without asking
what to do. The surface pulls from the unified todos backlog (preregs,
audit findings, corrections, structural-pending-fixes) in priority order.
"""

from __future__ import annotations

import ast
import importlib
import inspect

from divineos.core.next_task_surface import build_next_task_surface


class TestEveryLaneCanActuallyOpenItsStore:
    """Each lane's import must resolve. A lane that cannot import is silent.

    WHY THIS EXISTS. Until 2026-08-28 the correction lane imported
    ``divineos.core.andrew_corrections`` -- a module that does not exist in
    this tree and never has; the real one is ``andrew_correction_tracker``, and
    seven other files import it correctly. The ImportError landed in the
    lane's observability boundary, so it returned None on every turn it had
    ever run, while the briefing printed two hundred and sixty open
    corrections in the same context window.

    Two surfaces on one subject, one saying two hundred and sixty and one
    saying nothing to do, and the disagreement was invisible because a failed
    read and a drained queue produce identical output.

    Found by Aria on her own seat and relayed; confirmed identical here. This
    guards the CLASS rather than the instance -- any future lane that reaches
    for a module that is not there fails here instead of going quietly silent
    for months.
    """

    def _lane_imports(self) -> list[tuple[str, str]]:
        """Every ``from divineos... import`` inside this module's functions."""
        import divineos.core.next_task_surface as surface

        tree = ast.parse(inspect.getsource(surface))
        found: list[tuple[str, str]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("divineos"):
                for alias in node.names:
                    found.append((node.module or "", alias.name))
        return found

    def test_the_surface_has_lanes_to_check(self):
        """Guard the guard: an empty scan would pass every assertion below.

        A test that iterates nothing is green for the same reason a broken
        lane was -- nothing happened and nothing said so.
        """
        assert len(self._lane_imports()) >= 3

    def test_every_lane_module_exists(self):
        """The failure reports EVERY broken lane, not just the first.

        Stopping at the first would have hidden any sibling of the same
        mistake, which is how one silent lane became months of silence.
        """
        missing = []
        for module_name in sorted({m for m, _ in self._lane_imports()}):
            try:
                importlib.import_module(module_name)
            except ImportError as exc:
                missing.append(f"{module_name} ({exc})")
        assert not missing, f"lanes importing modules that do not exist: {missing}"

    def test_lane_symbol_exists(self):
        """The name imported must exist too, not merely the module.

        The old correction lane was broken twice over: the module was absent,
        AND the row-attribute access below it would have raised even if the
        import had ever resolved. Neither break could surface.
        """
        missing = []
        for module_name, symbol in self._lane_imports():
            module = importlib.import_module(module_name)
            if not hasattr(module, symbol):
                missing.append(f"{module_name}.{symbol}")
        assert not missing, f"lane imports naming absent symbols: {missing}"


class TestBuildNextTaskSurface:
    """The surface's contract: when ANY of the four queues has work, the
    surface returns a NEXT TASK block naming the highest-priority item.
    When all four are empty, it returns the empty string (silent)."""

    def test_returns_string(self, tmp_path, monkeypatch) -> None:
        """Output is always a string (never None, never an exception)."""
        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
        out = build_next_task_surface()
        assert isinstance(out, str)

    def test_silent_when_all_queues_empty(self, tmp_path, monkeypatch) -> None:
        """A fresh isolated DIVINEOS_HOME has no preregs, audit findings,
        corrections, or psfs — surface should be empty string."""
        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
        out = build_next_task_surface()
        assert out == "", f"Expected silent on empty-state; got: {out!r}"

    def test_surfaces_overdue_prereg_when_present(self, tmp_path, monkeypatch) -> None:
        """When an overdue prereg exists, the surface names it."""
        import time

        from divineos.core.pre_registrations import file_pre_registration
        from divineos.core.knowledge import _get_connection

        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))

        prereg_id = file_pre_registration(
            actor="agent",
            mechanism="Test-only mechanism for overdue surface verification",
            claim="Surfaces in the next-task block when overdue.",
            success_criterion="Test passes.",
            falsifier="Surface stays silent despite overdue prereg.",
            review_window_days=30,
        )
        # Force overdue by setting review_ts in the past.
        past = time.time() - (60 * 86400)
        conn = _get_connection()
        conn.execute(
            "UPDATE pre_registrations SET review_ts = ? WHERE prereg_id = ?",
            (past, prereg_id),
        )
        conn.commit()

        out = build_next_task_surface()
        assert "NEXT TASK" in out
        assert prereg_id in out
        assert "assess" in out

    def test_falls_through_to_audit_when_no_overdue_prereg(self, tmp_path, monkeypatch) -> None:
        """When the prereg queue has no overdue items but an open audit
        finding exists, the surface names the audit finding."""
        from divineos.core.watchmen import store as watchmen_store
        from divineos.core.watchmen.types import FindingCategory, Severity

        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))

        round_id = watchmen_store.submit_round(
            actor="user",
            focus="test round for next-task surface fallthrough",
        )
        # auto_route=False: this surface enumerates OPEN findings.
        # Auto-routing (2026-07-07 default) transitions submit -> ROUTED
        # which would move the finding out of the surface's scope.
        finding_id = watchmen_store.submit_finding(
            round_id=round_id,
            actor="user",
            title="Test finding for next-task surface",
            severity=Severity.HIGH,
            category=FindingCategory.BEHAVIOR,
            description="A high-severity finding the surface should pick up.",
            auto_route=False,
        )

        out = build_next_task_surface()
        assert "NEXT TASK" in out
        assert finding_id in out
        assert "resolve" in out

    def test_format_uses_work_dont_ask_framing(self, tmp_path, monkeypatch) -> None:
        """The surface header explicitly names the discipline — this is
        a load-bearing piece of the framing, not decoration. Andrew
        2026-06-20: 'the todo list itself is what needs work, it needs
        automated so you always know what the next task is.'"""
        import time

        from divineos.core.pre_registrations import file_pre_registration
        from divineos.core.knowledge import _get_connection

        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))

        prereg_id = file_pre_registration(
            actor="agent",
            mechanism="any",
            claim="any",
            success_criterion="any",
            falsifier="any",
            review_window_days=30,
        )
        past = time.time() - (60 * 86400)
        conn = _get_connection()
        conn.execute(
            "UPDATE pre_registrations SET review_ts = ? WHERE prereg_id = ?",
            (past, prereg_id),
        )
        conn.commit()

        out = build_next_task_surface()
        assert "work this" in out.lower()
        assert "don't ask" in out.lower() or "dont ask" in out.lower()

    def test_truncates_long_descriptions(self, tmp_path, monkeypatch) -> None:
        """Long mechanism descriptions get truncated so the surface stays
        a pointer (not a wall of text)."""
        import time

        from divineos.core.pre_registrations import file_pre_registration
        from divineos.core.knowledge import _get_connection

        monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))

        long_mechanism = "x" * 500
        prereg_id = file_pre_registration(
            actor="agent",
            mechanism=long_mechanism,
            claim="any",
            success_criterion="any",
            falsifier="any",
            review_window_days=30,
        )
        past = time.time() - (60 * 86400)
        conn = _get_connection()
        conn.execute(
            "UPDATE pre_registrations SET review_ts = ? WHERE prereg_id = ?",
            (past, prereg_id),
        )
        conn.commit()

        out = build_next_task_surface()
        # The body line should be truncated — total length bounded.
        # Account for the header + footer in the bound.
        body_lines = [line for line in out.split("\n") if prereg_id in line]
        assert body_lines, "Expected a body line containing the prereg id"
        assert len(body_lines[0]) <= 200, (
            f"Body line too long ({len(body_lines[0])} chars); truncation should have kicked in"
        )


# TWO FAULTS FOUND TOGETHER, 2026-08-28, after Aether found his own repair
# store starved and asked me to check the same surface on my seat. They are
# tested together because fixing either one alone makes the other worse.


class TestCorrectionFetcherReadsTheLiveStore:
    """The fetcher imported a module that does not exist.

    `divineos.core.andrew_corrections` has never been a module here. The
    ImportError was swallowed by the observability boundary, so the fetcher
    returned None on every turn while the briefing printed 139 open
    corrections in the same context window. A missing store read exactly like
    a drained one, which is why nobody noticed for as long as it existed.
    """

    def test_the_imported_module_actually_exists(self) -> None:
        import importlib

        # The regression is an ImportError swallowed into a false empty. Assert
        # the live module imports rather than asserting the fetcher is truthy —
        # a seat with genuinely zero open corrections must not fail this test.
        assert importlib.import_module("divineos.core.andrew_correction_tracker")

    def test_a_populated_store_reaches_the_surface(self, monkeypatch) -> None:
        from divineos.core import next_task_surface as nts

        monkeypatch.setattr(
            "divineos.core.andrew_correction_tracker.list_open",
            lambda: [
                {"id": "9", "timestamp": "200.0", "text": "newer"},
                {"id": "4", "timestamp": "100.0", "text": "older"},
            ],
        )
        result = nts._top_open_correction()
        assert result is not None
        cid, line = result
        # Oldest first: they have been waiting longest.
        assert cid == "4"
        assert "older" in line

    def test_an_empty_store_is_still_silent(self, monkeypatch) -> None:
        """The must-not-fire direction. A repair that makes a fetcher return
        something unconditionally is not a repair."""
        from divineos.core import next_task_surface as nts

        monkeypatch.setattr(
            "divineos.core.andrew_correction_tracker.list_open",
            lambda: [],
        )
        assert nts._top_open_correction() is None


class TestReservedSlotForTheStarvedClass:
    """Strict priority starves the lowest lane whenever the lanes above it
    hold work that does not drain. One turn in five is reserved so the repair
    queue is reached at all, and the four other turns keep the ordering."""

    def test_the_slot_promotes_the_repair_queue_when_due(self, monkeypatch) -> None:
        from divineos.core import next_task_surface as nts

        monkeypatch.setattr(nts, "_reserved_slot_is_due", lambda: True)
        monkeypatch.setattr(
            nts, "_top_open_correction", lambda: ("99", "integrate correction 99: blocking")
        )
        monkeypatch.setattr(nts, "_top_pending_structural_fix", lambda: ("psf-x", "pick psf-x?"))
        out = nts.build_next_task_surface()
        assert "psf-x" in out
        assert "correction 99" not in out
        assert "reserved slot" in out

    def test_the_ordering_holds_when_the_slot_is_not_due(self, monkeypatch) -> None:
        from divineos.core import next_task_surface as nts

        monkeypatch.setattr(nts, "_reserved_slot_is_due", lambda: False)
        monkeypatch.setattr(
            nts, "_top_open_correction", lambda: ("99", "integrate correction 99: blocking")
        )
        monkeypatch.setattr(nts, "_top_pending_structural_fix", lambda: ("psf-x", "pick psf-x?"))
        out = nts.build_next_task_surface()
        assert "correction 99" in out
        assert "psf-x" not in out

    def test_a_due_slot_with_an_empty_store_falls_through(self, monkeypatch) -> None:
        """The slot must not blank the surface when the reserved lane is empty."""
        from divineos.core import next_task_surface as nts

        monkeypatch.setattr(nts, "_reserved_slot_is_due", lambda: True)
        monkeypatch.setattr(
            nts, "_top_open_correction", lambda: ("99", "integrate correction 99: blocking")
        )
        monkeypatch.setattr(nts, "_top_pending_structural_fix", lambda: None)
        out = nts.build_next_task_surface()
        assert "correction 99" in out

    def test_an_unreadable_ledger_leaves_the_ordering_alone(self, monkeypatch) -> None:
        """Fail toward not-due. Inventing urgency out of a failed read is the
        same fault as the missing-module empty this change also repairs."""
        from divineos.core import next_task_surface as nts

        def _boom():
            raise OSError("ledger unreadable")

        monkeypatch.setattr("divineos.core.ledger.get_connection", _boom)
        assert nts._reserved_slot_is_due() is False
