"""Regression tests for Fable audit 2026-07-02 findings #2 and #3.

Both findings shared the same root: ``search_events`` had no ``order``
parameter and defaulted to ``timestamp ASC LIMIT`` in SQL. On a mature
ledger with more matching events than the limit, the returned window
was the OLDEST events — silently returning ledger prehistory as if it
were the present.

Finding #2 hit ``active_superpositions()`` — freshest open decision
invisible.
Finding #3 hit ``current_mode()`` / ``mode_history()`` — recency
readers returned oldest transitions.

Root fix: ``search_events`` gains an ``order`` parameter; both callers
pass ``order="desc"``. These tests defend the fix by adversarially
seeding the ledger with more matching events than the limit and
asserting the newest ones surface, not the oldest.
"""

from __future__ import annotations

from divineos.core.ledger import log_event, search_events


class TestSearchEventsOrderParam:
    """The parameter itself — asc/desc control over the window."""

    def test_default_order_is_asc_backwards_compat(self) -> None:
        # Seed 3 events with the same keyword.
        for i in range(3):
            log_event("TEST_EVENT", "test", {"seq": i, "keyword": "kw_asc_default"})
        events = search_events(keyword="kw_asc_default", limit=3)
        assert len(events) == 3
        seqs = [e["payload"]["seq"] for e in events]
        assert seqs == [0, 1, 2], f"ASC default expected [0,1,2], got {seqs}"

    def test_order_desc_returns_newest_first(self) -> None:
        for i in range(3):
            log_event("TEST_EVENT", "test", {"seq": i, "keyword": "kw_desc_test"})
        events = search_events(keyword="kw_desc_test", limit=3, order="desc")
        assert len(events) == 3
        seqs = [e["payload"]["seq"] for e in events]
        assert seqs == [2, 1, 0], f"DESC expected [2,1,0], got {seqs}"

    def test_order_desc_with_limit_returns_newest_N(self) -> None:
        # 5 events, limit=2 with desc → newest 2 (seq 4 and 3).
        for i in range(5):
            log_event("TEST_EVENT", "test", {"seq": i, "keyword": "kw_desc_limit"})
        events = search_events(keyword="kw_desc_limit", limit=2, order="desc")
        assert len(events) == 2
        seqs = [e["payload"]["seq"] for e in events]
        assert seqs == [4, 3], f"expected newest-2 [4,3], got {seqs}"

    def test_order_asc_with_limit_returns_oldest_N_for_backcompat(self) -> None:
        # Prior default behavior — kept working for backward compat.
        for i in range(5):
            log_event("TEST_EVENT", "test", {"seq": i, "keyword": "kw_asc_limit"})
        events = search_events(keyword="kw_asc_limit", limit=2)
        assert len(events) == 2
        seqs = [e["payload"]["seq"] for e in events]
        assert seqs == [0, 1], f"expected oldest-2 [0,1], got {seqs}"

    def test_order_case_insensitive(self) -> None:
        # DESC / desc / Desc all work.
        for i in range(3):
            log_event("TEST_EVENT", "test", {"seq": i, "keyword": "kw_case"})
        for order_val in ("desc", "DESC", "Desc"):
            events = search_events(keyword="kw_case", limit=3, order=order_val)
            seqs = [e["payload"]["seq"] for e in events]
            assert seqs == [2, 1, 0], f"order='{order_val}' failed"

    def test_order_unrecognized_falls_back_to_asc(self) -> None:
        # Defensive — an unknown order string uses ASC (backward-compat
        # default). Callers pass "asc" or "desc"; anything else means
        # something went wrong upstream, so behave predictably.
        for i in range(3):
            log_event("TEST_EVENT", "test", {"seq": i, "keyword": "kw_bogus"})
        events = search_events(keyword="kw_bogus", limit=3, order="banana")
        seqs = [e["payload"]["seq"] for e in events]
        assert seqs == [0, 1, 2]


class TestFinding2ActiveSuperpositions:
    """Adversarial regression: active_superpositions must see the freshest
    open decision even when >500 superposition_ events exist."""

    def test_active_superposition_visible_on_mature_ledger(self) -> None:
        # Import here so the test module doesn't need optional deps at
        # collection time on setups without decision_superposition wired.
        from divineos.core.decision_superposition.superposition import (
            active_superpositions,
        )

        # Seed 260 open+collapse pairs = 520 events (>500 default limit).
        for i in range(260):
            log_event(
                "AGENT_PATTERN",
                "test",
                {"kind": "superposition_open", "superposition_id": f"old-{i}"},
            )
            log_event(
                "AGENT_PATTERN",
                "test",
                {"kind": "superposition_collapse", "superposition_id": f"old-{i}"},
            )
        # Now the fresh open one — well past the ASC-500 window.
        log_event(
            "AGENT_PATTERN",
            "test",
            {"kind": "superposition_open", "superposition_id": "FRESH-active"},
        )

        actives = active_superpositions()
        active_ids = [a.superposition_id for a in actives]
        assert "FRESH-active" in active_ids, (
            "active_superpositions blind to freshest open decision on mature ledger "
            f"(Fable finding #2). Got: {active_ids[:5]}..."
        )


class TestFinding3CurrentMode:
    """Adversarial regression: current_mode must return the newest
    transition even when >(limit*3) transition events exist."""

    def test_current_mode_is_newest_on_mature_ledger(self) -> None:
        from divineos.core.operating_modes.modes import (
            Mode,
            current_mode,
            mode_history,
        )

        # Seed 60 transitions ending with 'rest' — same shape as
        # auditor's reproduction. With mode_history(limit=1) reading
        # limit*3=3 events, ASC-3 would return the OLDEST 3 (all 'task').
        modes_cycle = [Mode.TASK, Mode.STILLNESS, Mode.TASK, Mode.STILLNESS] * 15
        modes_cycle[-1] = Mode.WANDERING
        for i, m in enumerate(modes_cycle):
            log_event(
                "AGENT_PATTERN",
                "test",
                {
                    "kind": "operating_mode_transition",
                    "mode": m.value,
                    "reason": f"transition-{i}",
                    "ts": 1000.0 + i,
                },
            )
        assert current_mode() == Mode.WANDERING, (
            "current_mode returned prehistory instead of newest transition (Fable finding #3)"
        )

        history = mode_history(limit=3)
        assert history, "mode_history returned empty on populated ledger"
        # Newest first: the last-written transition is at index 0.
        assert history[0].mode == Mode.WANDERING, (
            f"mode_history[0] should be newest (Mode.WANDERING), got {history[0].mode}"
        )
