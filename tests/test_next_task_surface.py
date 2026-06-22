"""Tests for the auto-next-task surface (core/next_task_surface.py).

Per prereg-d99b6b8a442b: every turn should carry a NEXT TASK line in
pre-response context so the agent works the named task without asking
what to do. The surface pulls from the unified todos backlog (preregs,
audit findings, corrections, structural-pending-fixes) in priority order.
"""

from __future__ import annotations

from divineos.core.next_task_surface import build_next_task_surface


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
        finding_id = watchmen_store.submit_finding(
            round_id=round_id,
            actor="user",
            title="Test finding for next-task surface",
            severity=Severity.HIGH,
            category=FindingCategory.BEHAVIOR,
            description="A high-severity finding the surface should pick up.",
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
