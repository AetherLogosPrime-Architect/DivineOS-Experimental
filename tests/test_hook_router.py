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
def _clean_registry(tmp_path, monkeypatch):
    # main() now collapses repeats on UserPromptSubmit through context_dedup,
    # which remembers across calls in a shared file. Without its own memory,
    # one test's emission made the next run of another test see a "repeat"
    # and collapse it -- found when the withheld-surface test passed once and
    # failed on the second run.
    monkeypatch.setenv("DIVINEOS_CONTEXT_DEDUP_DIR", str(tmp_path / "dedup"))
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


class TestRepeatsCollapseOnHisTurns:
    """A surface that says exactly what it said last turn says so in one line.

    Andrew 2026-09-23: "yes and it has sat like that.. for months.. after me
    telling you to fix it.." Measured that day: his words were 1.2% of what
    reached me on his turns, and most of the rest repeated byte for byte.
    Collapsing is decided per surface in COLLAPSE_POLICY, so a rule riding a
    surface survives as its residual (the dedup contract's lesson).
    """

    @pytest.fixture(autouse=True)
    def _policy(self, monkeypatch):
        monkeypatch.setitem(
            hr.COLLAPSE_POLICY,
            "repeat_me",
            hr.CollapsePolicy(kind="residual", why="test", residual="THE RULE THAT SURVIVES"),
        )
        for name in ("clock", "next_task", "warn"):
            monkeypatch.setitem(
                hr.COLLAPSE_POLICY, name, hr.CollapsePolicy(kind="info", why="test")
            )

    def _run(self, capsys, event="UserPromptSubmit"):
        hr.main(event, {})
        return capsys.readouterr().out

    def test_second_identical_emission_is_one_line_and_keeps_its_rule(self, capsys):
        prime = "SAME PRIME " * 300
        hr.register("UserPromptSubmit", "repeat_me", _ok("repeat_me", prime))
        first = self._run(capsys)
        second = self._run(capsys)
        assert prime.strip() in first
        assert "re-emit suppressed" in second
        assert prime.strip() not in second
        # The rule riding the prime is not collapsed along with its prose.
        assert "THE RULE THAT SURVIVES" in second
        assert len(second) < 400

    def test_an_unclassified_surface_is_never_collapsed(self, capsys):
        hr.register("UserPromptSubmit", "nobody_decided", _ok("nobody_decided", "WHOLE " * 100))
        self._run(capsys)
        second = self._run(capsys)
        assert "WHOLE WHOLE" in second
        assert "re-emit suppressed" not in second

    def test_a_changed_surface_arrives_whole_because_change_is_information(self, capsys):
        texts = iter(["clock says 12:01 " * 50, "clock says 12:02 " * 50])
        hr.register(
            "UserPromptSubmit",
            "clock",
            lambda p: SurfaceOutcome(name="clock", output=next(texts)),
        )
        self._run(capsys)
        second = self._run(capsys)
        assert "12:02" in second
        assert "re-emit suppressed" not in second

    def test_other_events_are_never_collapsed(self, capsys):
        hr.register("PreToolUse", "warn", _ok("warn", "LOOK FIRST " * 100))
        self._run(capsys, "PreToolUse")
        second = self._run(capsys, "PreToolUse")
        assert "LOOK FIRST" in second
        assert "re-emit suppressed" not in second

    def test_an_existing_pointer_is_not_wrapped_in_a_second_one(self, capsys):
        pointer = "## NEXT TASK (unchanged, hash abc; re-emit suppressed — ...)"
        hr.register("UserPromptSubmit", "next_task", _ok("next_task", pointer))
        self._run(capsys)
        second = self._run(capsys)
        assert pointer in second


def test_every_surface_on_his_turns_is_classified():
    """A new surface fails here until someone decides what of it must survive.

    Unclassified surfaces are delivered whole, which is safe; but a surface
    nobody classified is also one nobody asked the question about.
    """
    from divineos.core import hook_surfaces

    hook_surfaces.install()
    unclassified = [n for n in hr.registered("UserPromptSubmit") if n not in hr.COLLAPSE_POLICY]
    assert not unclassified, (
        f"classify these in hook_router.COLLAPSE_POLICY: {unclassified}. residual = "
        "a rule rides it; info = safe to collapse bare; never = always whole."
    )


def test_every_policy_costs_a_real_sentence_and_residuals_are_not_empty():
    for name, policy in hr.COLLAPSE_POLICY.items():
        assert policy.kind in ("residual", "info", "never"), name
        assert len(policy.why.split()) >= 12, f"{name}: reason too thin to dispute"
        if policy.kind == "residual":
            assert len(policy.residual.split()) >= 6, f"{name}: residual carries no rule"
