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
import shutil
import subprocess
from pathlib import Path

import pytest

from divineos.core import hook_surfaces as hs
from divineos.core import pr_gate
from tests._bash_resolver import bash_executable

ROOT = Path(__file__).resolve().parents[1]
BASH = bash_executable()

# A real entry from the protected set, so the create gate has something to
# object to regardless of which branch this checkout is standing on.
_A_GUARDED_FILE = "docs/foundational_truths.md"

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


def test_the_two_pull_request_gates_keep_their_different_protocols(monkeypatch):
    """A migration moves WHERE a decision is made, never HOW it lands.

    These two refused differently before -- one through the permission
    decision, one through exit 2 -- and both still do. It matters because the
    create gate spent its entire life exiting 1, which shows the message and
    runs the command anyway: a correct, well-written refusal printed into the
    void while every unready pull request opened regardless. Protocol IS
    behaviour, and this is the assertion that says so.

    THE INPUT IS NOW REFUSABLE BY CONSTRUCTION, 2026-09-12. This used to hand
    the create gate a plain command and assert it refused -- but that gate
    refuses only when the current branch touches a protected file without a
    draft flag, so its answer depended on which branch the checkout happened to
    be sitting on. On a branch that was genuinely ready it said nothing, and the
    test failed against a gate doing its job perfectly.

    Imagine the gate deleted: the old test would still pass or fail on the
    branch alone. An outcome that does not change when the thing under test is
    removed was never measuring it. So the touched-files lookup is now
    supplied, which is the seam that turns a characterization of my checkout
    into a test of the gate.
    """
    monkeypatch.setattr(pr_gate, "branch_files_changed", lambda **_: [_A_GUARDED_FILE])
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


def _a_repo_the_create_gate_must_refuse(tmp_path) -> Path:
    """A checkout whose branch touches a protected file, built from nothing.

    The create gate refuses a non-draft request only when the branch modifies
    something in the protected set. This test used to hand it a command and
    assert it refused, which made the answer a property of whichever branch the
    developer happened to be standing on -- and on a branch that was genuinely
    ready, the gate correctly said nothing and the test called that a failure.

    Constructing the repo is the expensive fix and the right one. Retiring the
    test would have been cheaper, and the gate it guards is precisely the one
    that spent its entire life exiting with the wrong code -- refusing into the
    void while every unready request opened anyway. That is the last guard in
    the house to trade away for a green.
    """
    repo = tmp_path / "checkout"
    (repo / "scripts").mkdir(parents=True)
    (repo / ".claude" / "hooks").mkdir(parents=True)

    # The doorbell bootstraps itself from the checkout it is standing in, so
    # the scratch one needs the real shell library or the bell never rings.
    # The first attempt guarded _lib.sh itself, overwrote it, and broke the
    # bootstrap -- the fixture ate the thing it was testing through.
    shutil.copy2(ROOT / ".claude" / "hooks" / "_lib.sh", repo / ".claude" / "hooks" / "_lib.sh")

    guarded = repo / _A_GUARDED_FILE
    guarded.parent.mkdir(parents=True, exist_ok=True)
    guarded.write_text("# original\n", encoding="utf-8")
    (repo / "scripts" / "guardrail_files.txt").write_text(
        f"# protected paths\n{_A_GUARDED_FILE}\n", encoding="utf-8"
    )

    def git(*args: str) -> None:
        done = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, timeout=180)
        assert done.returncode == 0, f"git {args[0]} failed: {done.stderr[:300]}"

    git("init", "-q", "-b", "main")
    git("config", "user.email", "test@example.invalid")
    git("config", "user.name", "test")
    git("add", "-A")
    git("commit", "-qm", "base")
    # The gate diffs against origin/main, so the scratch repo needs one.
    git("update-ref", "refs/remotes/origin/main", "HEAD")
    git("checkout", "-q", "-b", "touches-a-guarded-file")
    guarded.write_text("# changed\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", "modify a protected path")
    return repo


def test_the_create_gate_refuses_all_the_way_through_the_router(tmp_path, monkeypatch, capsys):
    """The one with a real refusing input, driven through the whole router.

    WHY THIS STOPS AT THE ROUTER RATHER THAN THE SHELL, and the boundary was
    found by trying. The bash doorbell bootstraps itself from whichever checkout
    it stands in -- it resolves the repo root, sources the library from there,
    and locates an interpreter through it. So driving it against a constructed
    repo requires that repo to be a whole substrate install, a fixture heavier
    and more fragile than the thing it would test. Two attempts proved it: the
    first broke the bootstrap, the second exited silently when no interpreter
    could be found, and a silent exit is indistinguishable from a gate that
    chose not to speak.

    The bash layer is not left unproven -- the heredoc test below drives the
    real doorbell end to end and passes, because its refusing input needs no
    repository at all. What that test cannot show is that THIS gate's refusal
    survives the trip, and that is what this one covers: a constructed repo the
    gate must object to, through install and dispatch, to the wire protocol the
    harness actually reads.

    The repo is built rather than assumed. The old version handed the gate a
    command and asserted refusal, so its verdict was a property of whichever
    branch the developer stood on -- and on a ready branch the gate correctly
    said nothing and the test called that failure.
    """
    from divineos.core import hook_router
    from divineos.core.hook_surfaces import install

    monkeypatch.chdir(_a_repo_the_create_gate_must_refuse(tmp_path))
    install()
    code = hook_router.main(
        "PreToolUse",
        {"tool_name": "Bash", "tool_input": {"command": "gh pr create --title x --body y"}},
    )
    printed = capsys.readouterr()
    everything = printed.out + printed.err
    assert code in (0, 2)
    assert "pr_create_gate" in everything, everything[:400]
    assert "BLOCKED" in everything, everything[:400]


def test_the_create_gate_stays_silent_when_the_branch_guards_nothing(tmp_path, monkeypatch, capsys):
    """The other direction, so the fixture above is provably load-bearing.

    A constructed world only proves something if changing it changes the
    answer. The same repo with an EMPTY protected set must draw no refusal --
    otherwise the test above would pass for some reason other than the one it
    claims, and I would not be able to tell.
    """
    from divineos.core import hook_router
    from divineos.core.hook_surfaces import install

    repo = _a_repo_the_create_gate_must_refuse(tmp_path)
    (repo / "scripts" / "guardrail_files.txt").write_text("# nothing protected\n", encoding="utf-8")
    monkeypatch.chdir(repo)
    install()
    hook_router.main(
        "PreToolUse",
        {"tool_name": "Bash", "tool_input": {"command": "gh pr create --title x --body y"}},
    )
    printed = capsys.readouterr()
    assert "pr_create_gate" not in (printed.out + printed.err)


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
