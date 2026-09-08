"""Tests for the seven-doorbell hook router.

The load-bearing tests are the isolation ones. Consolidating 100 hooks into 7
doorbells trades away the one virtue the current arrangement has — a bug in one
hook affects exactly one surface — so if isolation does not hold, the whole
design is worse than what it replaces.
"""

from __future__ import annotations

import json

import pytest

from divineos.core import hook_router as hr
from divineos.core.hook_router import SurfaceOutcome


@pytest.fixture(autouse=True)
def _clean_registry():
    hr.clear()
    yield
    hr.clear()


def _ok(name, text=""):
    return lambda payload: SurfaceOutcome(name=name, output=text)


def _refuse(name, reason):
    return lambda payload: SurfaceOutcome(name=name, refused=True, reason=reason)


def _boom(name):
    def fn(payload):
        raise RuntimeError(f"{name} exploded")

    return fn


class TestIsolation:
    """One surface must never be able to take another down."""

    def test_a_crashing_surface_does_not_stop_the_others(self):
        hr.register("Stop", "first", _ok("first", "first ran"))
        hr.register("Stop", "boom", _boom("boom"))
        hr.register("Stop", "third", _ok("third", "third ran"))

        r = hr.dispatch("Stop", {})

        assert [o.name for o in r.ran] == ["first", "third"]
        assert [o.name for o in r.errored] == ["boom"]
        assert "first ran" in r.stdout() and "third ran" in r.stdout()

    def test_a_crashing_surface_does_not_block(self):
        """Errors are reported and never refuse the tool call."""
        hr.register("PreToolUse", "boom", _boom("boom"))
        r = hr.dispatch("PreToolUse", {})
        assert r.blocked is False
        assert r.exit_code() == 0
        assert "COULD NOT RUN" in r.stderr()

    def test_error_is_not_reported_as_pass(self):
        """The third word. Crashed is its own state, not success."""
        hr.register("Stop", "boom", _boom("boom"))
        r = hr.dispatch("Stop", {})
        assert r.ran == []
        assert len(r.errored) == 1
        assert "not the same as it passing" in r.stderr()

    def test_router_crash_still_exits_zero(self, monkeypatch):
        """A broken router must never wall me in."""

        def explode(event, payload):
            raise RuntimeError("router itself is broken")

        monkeypatch.setattr(hr, "dispatch", explode)
        assert hr.main("Stop", {}) == 0


class TestNoShortCircuit:
    """Every surface runs even after a refusal; every refusal is reported."""

    def test_all_refusals_are_collected_not_just_the_first(self):
        hr.register("PreToolUse", "gate_a", _refuse("gate_a", "needs a goal"))
        hr.register("PreToolUse", "gate_b", _refuse("gate_b", "needs a briefing"))

        r = hr.dispatch("PreToolUse", {})

        assert [o.name for o in r.refusals] == ["gate_a", "gate_b"]
        err = r.stderr()
        assert "needs a goal" in err and "needs a briefing" in err

    def test_surfaces_after_a_refusal_still_run(self):
        """Short-circuiting would hide the second reason behind the first."""
        hr.register("PreToolUse", "gate", _refuse("gate", "no"))
        hr.register("PreToolUse", "after", _ok("after", "still ran"))

        r = hr.dispatch("PreToolUse", {})

        assert [o.name for o in r.ran] == ["after"]
        assert r.blocked is True

    def test_refusal_blocks_with_exit_two(self):
        hr.register("PreToolUse", "gate", _refuse("gate", "no"))
        assert hr.dispatch("PreToolUse", {}).exit_code() == 2

    def test_no_refusal_allows(self):
        hr.register("PreToolUse", "fine", _ok("fine"))
        assert hr.dispatch("PreToolUse", {}).exit_code() == 0


class TestRegistry:
    def test_seven_events_and_no_more(self):
        assert len(hr.EVENTS) == 7
        assert set(hr.EVENTS) == {
            "SessionStart",
            "UserPromptSubmit",
            "PreCompact",
            "PostCompact",
            "PreToolUse",
            "PostToolUse",
            "Stop",
        }

    def test_unknown_event_refuses_registration_loudly(self):
        with pytest.raises(ValueError, match="unknown hook event"):
            hr.register("NotAnEvent", "x", _ok("x"))

    def test_duplicate_surface_name_refuses(self):
        """Two surfaces with one name is the two-places defect in miniature."""
        hr.register("Stop", "dup", _ok("dup"))
        with pytest.raises(ValueError, match="already registered"):
            hr.register("Stop", "dup", _ok("dup"))

    def test_registration_order_is_run_order(self):
        hr.register("Stop", "a", _ok("a", "A"))
        hr.register("Stop", "b", _ok("b", "B"))
        hr.register("Stop", "c", _ok("c", "C"))
        assert hr.registered("Stop") == ["a", "b", "c"]
        assert hr.dispatch("Stop", {}).stdout().split("\n") == ["A", "B", "C"]

    def test_dispatch_on_unknown_event_errors_rather_than_silently_passing(self):
        r = hr.dispatch("Nope", {})
        assert r.ran == []
        assert r.errored and "unknown event" in r.errored[0].error

    def test_empty_event_is_a_clean_allow(self):
        r = hr.dispatch("Stop", {})
        assert r.exit_code() == 0
        assert r.stdout() == "" and r.stderr() == ""


class TestPayload:
    def test_payload_reaches_the_surface(self):
        seen = {}

        def capture(payload):
            seen.update(payload)
            return SurfaceOutcome(name="cap")

        hr.register("PreToolUse", "cap", capture)
        hr.dispatch("PreToolUse", {"tool_name": "Bash", "tool_input": {"command": "ls"}})
        assert seen["tool_name"] == "Bash"

    def test_a_surface_returning_none_is_silent_not_an_error(self):
        hr.register("Stop", "quiet", lambda payload: None)
        r = hr.dispatch("Stop", {})
        assert r.ran == [] and r.errored == [] and r.exit_code() == 0


class TestWireProtocol:
    """Migrating a hook changes WHERE the decision is made, never HOW it lands.

    Some PreToolUse hooks refuse via the harness JSON permission-decision and
    some via exit 2. Both work. Swapping one for the other during a migration
    would be a silent behaviour change, so the outcome carries the protocol.
    """

    def test_json_deny_emits_the_harness_shape(self, capsys):
        hr.register(
            "PreToolUse",
            "jsongate",
            lambda p: SurfaceOutcome(
                name="jsongate", refused=True, reason="needs briefing", json_deny=True
            ),
        )
        rc = hr.main("PreToolUse", {})
        payload = json.loads(capsys.readouterr().out.strip())
        assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "needs briefing" in payload["hookSpecificOutput"]["permissionDecisionReason"]
        # JSON carries the refusal, so the exit code must NOT also block.
        assert rc == 0

    def test_json_deny_carries_every_refusal_not_just_its_own(self, capsys):
        """The no-short-circuit property has to survive into the protocol.

        A JSON-denying surface and an exit-2 surface can both refuse in one
        dispatch. Emitting only the JSON one's reason would lose the other —
        the same hiding-the-second-reason failure, moved one layer out.
        """
        hr.register(
            "PreToolUse",
            "jsongate",
            lambda p: SurfaceOutcome(
                name="jsongate", refused=True, reason="needs briefing", json_deny=True
            ),
        )
        hr.register(
            "PreToolUse",
            "exitgate",
            lambda p: SurfaceOutcome(name="exitgate", refused=True, reason="needs read"),
        )
        hr.main("PreToolUse", {})
        reason = json.loads(capsys.readouterr().out.strip())["hookSpecificOutput"][
            "permissionDecisionReason"
        ]
        assert "needs briefing" in reason and "needs read" in reason

    def test_exit_two_path_is_unchanged_when_no_surface_wants_json(self):
        hr.register(
            "PreToolUse",
            "exitgate",
            lambda p: SurfaceOutcome(name="exitgate", refused=True, reason="no"),
        )
        assert hr.main("PreToolUse", {}) == 2

    def test_errors_still_reported_on_the_json_path(self, capsys):
        hr.register(
            "PreToolUse",
            "jsongate",
            lambda p: SurfaceOutcome(name="j", refused=True, reason="r", json_deny=True),
        )
        hr.register("PreToolUse", "boom", _boom("boom"))
        hr.main("PreToolUse", {})
        assert "COULD NOT RUN" in capsys.readouterr().err


class TestDeliveryBudget:
    """What actually reaches me, and what gets named instead.

    THE CONSTRAINT, found 2026-09-08 by consolidating six compose-start hooks
    onto one doorbell and watching the byte-checker fail immediately: the
    harness budgets delivery PER HOOK OUTPUT. Six hooks each under the cap
    arrived whole; one hook carrying all six became a preview plus a file
    nobody opens.

    Consolidation does not create the shortage, it makes it honest -- 87
    percent of hook text was already being discarded before any of this,
    spread thin enough across many hooks that every one passed its own check.
    """

    def test_whole_surfaces_are_kept_and_the_oversized_one_is_named(self):
        result = hr.RouterResult(event="UserPromptSubmit")
        result.ran = [
            SurfaceOutcome(name="small_first", output="x" * 100),
            SurfaceOutcome(name="huge", output="y" * hr.DELIVERY_BUDGET),
            SurfaceOutcome(name="small_last", output="z" * 100),
        ]
        text, withheld = result.deliverable()

        assert withheld == ["huge"]
        # NEVER a mid-sentence cut: a prime sliced in half reads as the whole
        # rule, which is worse than one that is absent and says its own name.
        assert "y" not in text
        # And a surface AFTER the oversized one still gets through -- one big
        # payload must not starve everything behind it.
        assert "x" * 100 in text and "z" * 100 in text

    def test_everything_fits_when_it_fits(self):
        result = hr.RouterResult(event="UserPromptSubmit")
        result.ran = [
            SurfaceOutcome(name="a", output="a" * 10),
            SurfaceOutcome(name="b", output="b" * 10),
        ]
        text, withheld = result.deliverable()
        assert withheld == []
        assert "a" * 10 in text and "b" * 10 in text

    def test_the_withheld_are_announced_rather_than_dropped_quietly(self, capsys):
        hr.register(
            "UserPromptSubmit",
            "over",
            lambda p: SurfaceOutcome(name="over", output="q" * (hr.DELIVERY_BUDGET + 1)),
        )
        hr.main("UserPromptSubmit", {})
        captured = capsys.readouterr()
        assert "withheld" in captured.err
        assert "over" in captured.err
        assert "Not silent, not delivered" in captured.err
        # Control: the payload itself did NOT arrive, so this is a real
        # withholding rather than a warning printed beside delivered text.
        assert "q" * 100 not in captured.out

    def test_stdout_still_returns_everything_for_callers_that_want_it_all(self):
        """``deliverable`` is the delivery view; ``stdout`` stays the full
        record, so a test or an audit can still see what the surfaces said."""
        result = hr.RouterResult(event="UserPromptSubmit")
        result.ran = [SurfaceOutcome(name="huge", output="y" * (hr.DELIVERY_BUDGET + 50))]
        assert len(result.stdout()) > hr.DELIVERY_BUDGET
        assert result.deliverable()[0] == ""
