"""Tests for the compass rudder — decision-time drift enforcement.

The rudder's job is to turn the compass from a mirror into a narrow,
fail-open rudder. These tests lock in the invariants that make it
useful without making it brittle:

* Non-gated tool names are always allowed (no compass query).
* When no spectrum is drifting, gated tool calls pass.
* When a spectrum is drifting toward excess above threshold AND no
  justification exists, gated calls are blocked.
* When a recent ``divineos decide`` mentions the drifting spectrum,
  gated calls pass.
* Drift toward virtue or deficiency never blocks — only toward_excess.
* Infrastructure failures (empty DB, missing module) fail OPEN.
"""

import os
import time

import pytest

from divineos.core.compass_rudder import (
    DRIFT_THRESHOLD,
    GATED_TOOL_NAMES,
    JUSTIFICATION_WINDOW_SECONDS,
    RudderVerdict,
    check_tool_use,
)
from divineos.core.decision_journal import init_decision_journal, record_decision
from divineos.core.knowledge import init_knowledge_table
from divineos.core.ledger import init_db
from divineos.core.moral_compass import init_compass


@pytest.fixture(autouse=True)
def _rudder_db(tmp_path):
    """Fresh DB per test — compass + decision journal."""
    os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
    try:
        init_db()
        init_knowledge_table()
        init_compass()
        init_decision_journal()
        yield
    finally:
        os.environ.pop("DIVINEOS_DB", None)


def _seed_drift(spectrum: str, *, toward_excess: bool, magnitude: float = 0.5) -> None:
    """Seed enough compass observations to produce a drift reading.

    The compass needs 4+ observations for drift to compute. Older half =
    near zero; newer half = ``+magnitude`` (if toward_excess) or
    ``-magnitude`` (toward_deficiency). That produces a measurable drift.
    """
    from divineos.core.moral_compass import log_observation as record_observation

    sign = 1 if toward_excess else -1
    # Older half (these get LESS weight because indexed later in the
    # exponentially-weighted average — but they form the "older" half
    # for drift computation).
    for _ in range(5):
        record_observation(spectrum=spectrum, position=0.0, source="MEASURED", evidence="base")
    # Newer half — recent observations pull the drift
    for _ in range(5):
        record_observation(
            spectrum=spectrum, position=sign * magnitude, source="MEASURED", evidence="push"
        )


# ── Gating scope ─────────────────────────────────────────────────────


class TestGatingScope:
    def test_non_gated_tool_always_allowed(self):
        # Even with heavy drift, non-Task tools pass through
        _seed_drift("initiative", toward_excess=True, magnitude=0.8)
        for tool in ("Edit", "Write", "Bash", "Read", "Grep"):
            v = check_tool_use(tool_name=tool)
            assert v.decision == "allow"
            assert not v.blocked
            assert v.drifting_spectrums == []

    def test_task_is_gated(self):
        assert "Task" in GATED_TOOL_NAMES

    def test_agent_is_gated_as_alias(self):
        """Kept as alias in case of future rename or older tooling."""
        assert "Agent" in GATED_TOOL_NAMES


# ── Allow path ───────────────────────────────────────────────────────


class TestAllowPath:
    def test_no_observations_no_block(self):
        """Empty compass store — no drift to detect, tool passes."""
        v = check_tool_use(tool_name="Task")
        assert v.decision == "allow"
        assert v.drifting_spectrums == []

    def test_drift_below_threshold_no_block(self):
        """Small drift doesn't block — the threshold exists for a reason."""
        # Seed a tiny drift: recent = 0.05, older = 0.0 → drift ≈ 0.05
        from divineos.core.moral_compass import log_observation as record_observation

        for _ in range(5):
            record_observation(
                spectrum="initiative", position=0.0, source="MEASURED", evidence="base"
            )
        for _ in range(5):
            record_observation(
                spectrum="initiative", position=0.05, source="MEASURED", evidence="slight"
            )
        v = check_tool_use(tool_name="Task")
        assert v.decision == "allow"

    def test_drift_toward_virtue_no_block(self):
        """Drift toward virtue is good news. Never blocks."""
        _seed_drift("initiative", toward_excess=False, magnitude=0.8)
        v = check_tool_use(tool_name="Task")
        assert v.decision == "allow"

    def test_recent_ack_observation_allows(self):
        """A compass observation with the rudder-ack tag recorded in the
        last 5 minutes clears the rudder. Decisions alone do not — the
        clearance path is the compass, not the decision journal."""
        from divineos.core.compass_rudder import RUDDER_ACK_TAG
        from divineos.core.moral_compass import log_observation

        _seed_drift("initiative", toward_excess=True, magnitude=0.8)
        log_observation(
            spectrum="initiative",
            position=0.1,
            evidence="scope is bounded to 3 agents; initiative drift acknowledged",
            source="rudder_ack",
            tags=[RUDDER_ACK_TAG],
        )
        v = check_tool_use(tool_name="Task")
        assert v.decision == "allow", v.reason
        assert "initiative" in v.recent_justifications

    def test_ack_found_under_observation_load(self):
        """Item 4 adversarial — ack is findable even when non-ack
        observations past the old limit=10 slice exist on the drifting
        spectrum within the window.

        Pre-Item-4 path fetched limit=10 observations and Python-side
        filtered for the ack tag. When ack is older than 10 non-ack
        observations on the same spectrum (all within window), the ack
        fell out of the slice and the rudder blocked despite a valid
        ack being present. Item 4 pushes the filter to SQL via
        json_each so the ack is found regardless of slice position.

        Test directly exercises _find_justifications rather than the
        full rudder — the full-rudder path has side-effects on drift
        computation when many new observations land, which is
        orthogonal to this test's claim. The SQL filter is the unit
        under test.
        """
        from divineos.core.compass_rudder import RUDDER_ACK_TAG, _find_justifications
        from divineos.core.moral_compass import log_observation

        # File the ack first (oldest, still within window).
        log_observation(
            spectrum="initiative",
            position=0.1,
            evidence="bounded scope; initiative drift acknowledged",
            source="rudder_ack",
            tags=[RUDDER_ACK_TAG],
        )
        # Then 11 non-ack observations on the same spectrum, within
        # window. Pre-Item-4 these would push the ack out of the
        # limit=10 slice; post-Item-4 the SQL filter finds the ack
        # directly via json_each on the tags column.
        for i in range(11):
            log_observation(
                spectrum="initiative",
                position=0.5,
                evidence=f"non-ack observation {i}",
                source="self_report",
            )
        justified = _find_justifications(["initiative"])
        assert justified == ["initiative"], f"expected ack found under load, got {justified}"

    def test_decide_alone_does_not_clear(self):
        """A decide mentioning the spectrum is NOT sufficient — the old
        clearance path was gameable; the new gate requires a structured
        compass observation. This test locks in the strictness."""
        _seed_drift("initiative", toward_excess=True, magnitude=0.8)
        record_decision(
            content="spawning 3 subagents for parallel audit analysis",
            reasoning="scope is bounded to 3 agents; initiative drift acknowledged",
        )
        v = check_tool_use(tool_name="Task")
        assert v.blocked, v.reason
        assert "initiative" not in v.recent_justifications

    def test_untagged_observation_does_not_clear(self):
        """A compass observation without the rudder-ack tag doesn't count.
        This is the specific gameability fix: the seed observations that
        CAUSED the drift must not also accidentally clear the gate."""
        _seed_drift("initiative", toward_excess=True, magnitude=0.8)
        from divineos.core.moral_compass import log_observation

        log_observation(
            spectrum="initiative",
            position=0.0,
            evidence="something about initiative but no ack tag",
            source="self_report",
        )
        v = check_tool_use(tool_name="Task")
        assert v.blocked, v.reason


# ── Block path ───────────────────────────────────────────────────────


class TestBlockPath:
    def test_drift_above_threshold_without_justification_blocks(self):
        _seed_drift("initiative", toward_excess=True, magnitude=0.8)
        v = check_tool_use(tool_name="Task")
        assert v.decision == "block", v.reason
        assert v.blocked
        assert "initiative" in v.drifting_spectrums
        assert v.recent_justifications == []

    def test_block_message_names_spectrum_and_tool(self):
        """The block message must give the agent enough context to unblock."""
        _seed_drift("initiative", toward_excess=True, magnitude=0.8)
        v = check_tool_use(tool_name="Task")
        assert v.blocked
        assert "Task" in v.reason
        assert "initiative" in v.reason
        # unblock instructions point at compass-ops observe now, not decide
        assert "compass-ops observe" in v.reason
        assert "rudder-ack" in v.reason

    def test_stale_ack_observation_does_not_allow(self):
        """An ack observation older than the window is not fresh enough."""
        from divineos.core.compass_rudder import RUDDER_ACK_TAG
        from divineos.core.moral_compass import log_observation

        _seed_drift("initiative", toward_excess=True, magnitude=0.8)
        log_observation(
            spectrum="initiative",
            position=0.0,
            evidence="acknowledged earlier; scope bounded to 3 agents for this task",
            source="rudder_ack",
            tags=[RUDDER_ACK_TAG],
        )
        # Simulate time passing by passing a ``now`` past the window
        future = time.time() + JUSTIFICATION_WINDOW_SECONDS + 60
        v = check_tool_use(tool_name="Task", now=future)
        assert v.blocked

    def test_ack_on_different_spectrum_does_not_clear(self):
        """An ack observation on a spectrum that isn't drifting doesn't
        help the drifting spectrum. The tag must match the drift."""
        from divineos.core.compass_rudder import RUDDER_ACK_TAG
        from divineos.core.moral_compass import log_observation

        _seed_drift("initiative", toward_excess=True, magnitude=0.8)
        log_observation(
            spectrum="humility",
            position=0.0,
            evidence="ack for a different spectrum",
            source="rudder_ack",
            tags=[RUDDER_ACK_TAG],
        )
        v = check_tool_use(tool_name="Task")
        assert v.blocked
        assert "initiative" not in v.recent_justifications


# ── Multiple drifting spectrums ──────────────────────────────────────


class TestMultipleDrifts:
    def test_must_ack_all_drifting_spectrums(self):
        """If two spectrums drift toward excess, a single ack observation
        covering one is not enough."""
        from divineos.core.compass_rudder import RUDDER_ACK_TAG
        from divineos.core.moral_compass import log_observation

        _seed_drift("initiative", toward_excess=True, magnitude=0.8)
        _seed_drift("confidence", toward_excess=True, magnitude=0.8)
        log_observation(
            spectrum="initiative",
            position=0.0,
            evidence="ack for initiative only",
            source="rudder_ack",
            tags=[RUDDER_ACK_TAG],
        )
        v = check_tool_use(tool_name="Task")
        assert v.blocked, v.reason
        assert set(v.drifting_spectrums) >= {"initiative", "confidence"}
        assert "initiative" in v.recent_justifications
        # confidence is drifting but not acked -> blocks
        assert "confidence" not in v.recent_justifications

    def test_all_drifting_spectrums_acked_allows(self):
        from divineos.core.compass_rudder import RUDDER_ACK_TAG
        from divineos.core.moral_compass import log_observation

        _seed_drift("initiative", toward_excess=True, magnitude=0.8)
        _seed_drift("confidence", toward_excess=True, magnitude=0.8)
        for spectrum in ("initiative", "confidence"):
            log_observation(
                spectrum=spectrum,
                position=0.0,
                evidence=f"ack for {spectrum} before spawn",
                source="rudder_ack",
                tags=[RUDDER_ACK_TAG],
            )
        v = check_tool_use(tool_name="Task")
        assert v.decision == "allow", v.reason


# ── Threshold + window overrides ─────────────────────────────────────


class TestThresholdsAndWindows:
    def test_threshold_override(self):
        """Callers can override the threshold (useful for tests and policy tuning)."""
        _seed_drift("initiative", toward_excess=True, magnitude=0.8)
        # With threshold > measured drift, no block even with drift present
        v = check_tool_use(tool_name="Task", threshold=0.99)
        assert v.decision == "allow"

    def test_default_threshold_value(self):
        """Lock the default so a silent change is visible in the diff."""
        assert DRIFT_THRESHOLD == 0.15

    def test_default_window_value(self):
        assert JUSTIFICATION_WINDOW_SECONDS == 300  # 5 minutes


# ── Fail-open guarantees ─────────────────────────────────────────────


class TestFailOpen:
    def test_verdict_is_a_dataclass(self):
        v = check_tool_use(tool_name="Task")
        assert isinstance(v, RudderVerdict)
        assert hasattr(v, "decision")
        assert hasattr(v, "reason")
        assert hasattr(v, "drifting_spectrums")
        assert hasattr(v, "recent_justifications")

    def test_no_crash_on_empty_inputs(self):
        """The hook must tolerate an empty tool_input dict."""
        v = check_tool_use(tool_name="Task", tool_input={})
        assert isinstance(v, RudderVerdict)

    def test_no_crash_on_none_tool_input(self):
        v = check_tool_use(tool_name="Task", tool_input=None)
        assert isinstance(v, RudderVerdict)
