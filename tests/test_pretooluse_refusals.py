"""The migrated gates, proved in their refusing state and through the door.

My own note from 2026-06-07, handed back by the read-gate in the middle of this
migration: *"Building the gate isn't enough; the gate has to be VERIFIED
working. Future gates: write the integration test that exercises the BLOCK case
end-to-end. Not just the matcher logic."* It was written after a gate of mine
was broken from the moment it shipped and stayed broken for six hours.

The matcher logic already has its own files -- test_heredoc_escape_check.py and
test_degraded_detectors.py cover the deciding. This one covers what those
cannot: that the decision still ARRIVES now that it travels through the router
instead of its own shell script. A surface returning a refusal and a doorbell
exiting 2 are two different claims, and only the second one stops a tool call.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from divineos.core import hook_surfaces as hs
from tests._bash_resolver import bash_executable

ROOT = Path(__file__).resolve().parents[1]
BASH = bash_executable()

# The escape has to survive into the heredoc BODY, which is what the checker
# scopes on. Built from chr(92) so no layer of quoting can eat it -- every
# inline attempt to write this mangled it, which is the very defect the gate
# exists to catch, arriving while testing the gate.
_BACKSLASH_N = chr(92) + "n"
REFUSED_COMMAND = "\n".join(
    [
        "python - <<'PY'",
        "from pathlib import Path",
        f'Path("out.txt").write_text("first{_BACKSLASH_N}second")',
        "PY",
    ]
)


def test_the_heredoc_gate_refuses_a_writing_heredoc_and_allows_a_plain_command():
    refused = hs.heredoc_escape_surface(
        {"tool_name": "Bash", "tool_input": {"command": REFUSED_COMMAND}}
    )
    assert refused is not None and refused.refused is True
    assert "HEREDOC" in refused.reason.upper()

    allowed = hs.heredoc_escape_surface({"tool_name": "Bash", "tool_input": {"command": "ls -la"}})
    assert allowed is not None and allowed.refused is False
    assert allowed.state == "nothing-to-say"


def test_the_heredoc_gate_ignores_tools_that_are_not_bash():
    """Scope is part of the behaviour: a gate that fires on every tool gets
    disabled within a day and then guards nothing."""
    for tool in ("Edit", "Write", "Read"):
        outcome = hs.heredoc_escape_surface(
            {"tool_name": tool, "tool_input": {"command": REFUSED_COMMAND}}
        )
        assert outcome is not None and outcome.refused is False


def test_the_degraded_gate_only_looks_at_writes():
    """Reads and searches stay open on purpose -- blocking those would block
    the investigation of the block."""
    for tool in ("Read", "Grep", "Bash"):
        outcome = hs.degraded_detectors_surface({"tool_name": tool})
        assert outcome is not None
        assert outcome.state == "nothing-to-say"
        assert outcome.refused is False


def test_the_degraded_gate_refuses_a_write_when_a_detector_is_degraded(monkeypatch):
    """The refusing branch, forced rather than waited for.

    A real degradation cannot be conjured on demand, so the OS function is
    replaced -- but the SURFACE's own logic (scope, refusal shape, message
    passthrough) is what is under test here, and that part is genuine.
    """
    import divineos.core.degraded_detectors as dd

    monkeypatch.setattr(dd, "blocking_degradations", lambda: [{"name": "example"}])
    monkeypatch.setattr(dd, "format_block", lambda entries: "DEGRADED: example detector is down")

    outcome = hs.degraded_detectors_surface({"tool_name": "Write"})
    assert outcome is not None and outcome.refused is True
    assert outcome.reason == "DEGRADED: example detector is down"

    # Control: same forced degradation, non-writing tool, no refusal.
    assert hs.degraded_detectors_surface({"tool_name": "Read"}).refused is False


def test_a_degraded_check_that_cannot_run_says_so_rather_than_passing(monkeypatch):
    import divineos.core.degraded_detectors as dd

    def boom():
        raise RuntimeError("store unreadable")

    monkeypatch.setattr(dd, "blocking_degradations", boom)
    outcome = hs.degraded_detectors_surface({"tool_name": "Write"})
    assert outcome is not None
    assert outcome.state == "could-not-run"
    assert outcome.error is not None and "store unreadable" in outcome.error
    assert outcome.refused is False  # a broken gate reports; it does not block the work


def test_the_two_pull_request_gates_keep_their_different_protocols():
    """A migration moves WHERE a decision is made, never HOW it lands.

    These two refused differently before -- one through the permission
    decision, one through exit 2 -- and both still do. It matters because the
    create gate spent its entire life exiting 1, which shows the message and
    runs the command anyway: a correct, well-written refusal printed into the
    void while every unready pull request opened regardless. Protocol IS
    behaviour, and this is the assertion that says so.
    """
    merge = hs.pr_merge_gate_surface(
        {"tool_name": "Bash", "tool_input": {"command": "gh pr merge 1"}}
    )
    create = hs.pr_create_gate_surface(
        {"tool_name": "Bash", "tool_input": {"command": "gh pr create --title x --body y"}}
    )
    assert merge is not None and merge.refused is True and merge.json_deny is True
    assert create is not None and create.refused is True and create.json_deny is False


def test_both_pull_request_gates_ignore_commands_that_are_not_theirs():
    for surface in (hs.pr_merge_gate_surface, hs.pr_create_gate_surface):
        assert surface({"tool_name": "Bash", "tool_input": {"command": "ls -la"}}).refused is False
        assert surface({"tool_name": "Read", "tool_input": {}}).state == "nothing-to-say"


def test_a_pull_request_gate_that_raises_says_could_not_run(monkeypatch):
    import divineos.core.pr_merge_gate as pmg

    def boom(_cmd):
        raise RuntimeError("gate module broken")

    monkeypatch.setattr(pmg, "block_reason", boom)
    outcome = hs.pr_merge_gate_surface(
        {"tool_name": "Bash", "tool_input": {"command": "gh pr merge 1"}}
    )
    assert outcome.state == "could-not-run"
    assert outcome.refused is False  # a broken gate reports; it does not block


@pytest.mark.skipif(BASH is None, reason="doorbells are bash; no working interpreter")
def test_the_create_gate_refuses_through_the_doorbell_end_to_end():
    """The one with a real refusing input, driven the whole way."""
    proc = subprocess.run(
        [BASH, ".claude/hooks/doorbell-pre-tool-use.sh"],
        cwd=ROOT,
        input=json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": "gh pr create --title x --body y"}}
        ),
        capture_output=True,
        text=True,
        timeout=180,
    )
    everything = proc.stdout + proc.stderr
    assert proc.returncode in (0, 2)
    assert "pr_create_gate" in everything, everything[:400]


@pytest.mark.skipif(BASH is None, reason="doorbells are bash; no working interpreter")
def test_the_block_case_reaches_the_harness_through_the_doorbell():
    """END TO END, which is the whole reason this file exists.

    ASSERTS THE REFUSAL ARRIVED, NOT ITS EXIT CODE, and that distinction was
    earned rather than designed. The first version demanded exit 2 and failed:
    the doorbell had returned 0 while carrying the refusal in a JSON
    permission-decision instead, because a DIFFERENT surface on the same door
    also refused and used that protocol -- and the router, correctly, speaks
    JSON for all of them once any one of them needs it.

    So the exit code here depends on which of my neighbours are unhappy today,
    which is not a property of this gate at all. What IS this gate's property
    is that its reason reaches the harness. Pinning the code would have made a
    test that passes or fails on unrelated state.
    """
    proc = subprocess.run(
        [BASH, ".claude/hooks/doorbell-pre-tool-use.sh"],
        cwd=ROOT,
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": REFUSED_COMMAND}}),
        capture_output=True,
        text=True,
        timeout=180,
    )
    everything = proc.stdout + proc.stderr
    assert proc.returncode in (0, 2)
    assert "heredoc_escape" in everything, everything[:400]
    assert "HEREDOC-ESCAPE" in everything.upper(), everything[:400]
    if proc.returncode == 0:
        # Then it must be the JSON protocol carrying a real deny, not a pass.
        assert '"permissionDecision": "deny"' in proc.stdout, proc.stdout[:400]


@pytest.mark.skipif(BASH is None, reason="doorbells are bash; no working interpreter")
def test_an_ordinary_command_passes_through_the_same_doorbell():
    """The control. Without it, a doorbell that refused everything would look
    exactly like a working gate.

    AND THE ASSERTION IS ATTRIBUTED, not blanket. I first wrote "no deny
    anywhere", which failed and taught me something: a plain command IS denied
    in a test subprocess -- by the briefing gate, because no briefing is loaded
    there. That is the stack behaving correctly and has nothing to do with the
    gate under test.

    So a blanket no-deny assertion would have been a test of unrelated session
    state wearing the shape of a control. What belongs here is narrower and
    truer: whatever else the door decides, THIS gate stayed quiet.
    """
    proc = subprocess.run(
        [BASH, ".claude/hooks/doorbell-pre-tool-use.sh"],
        cwd=ROOT,
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls -la"}}),
        capture_output=True,
        text=True,
        timeout=180,
    )
    everything = proc.stdout + proc.stderr
    assert proc.returncode in (0, 2)
    assert "heredoc_escape" not in everything
    assert "HEREDOC-ESCAPE" not in everything.upper()
