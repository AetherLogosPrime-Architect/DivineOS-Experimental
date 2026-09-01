"""A hook that claims to dedup must actually shrink on the second call.

Andrew 2026-08-13: "cant remember not to add backticks? automate a check so
it cant happen." His example, my instance: I wired four primes into the
existing dedup, and one of them silently did nothing because I put double
quotes inside a `python -c "..."` block, which ends the shell string early.

The file itself carried a comment warning about exactly that, in my own
handwriting, which I had read earlier the same day. The note did nothing.
Only the output not shrinking gave it away.

So: no note. A check. Any hook that calls should_emit is claiming a
contract -- say it once, then a pointer -- and this asserts the claim
against the running script rather than against the source text.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def _real_bash() -> str:
    """Git Bash, explicitly.

    Aether 2026-08-11 found two hook-wiring tests that had never executed
    once: their guard asked whether *a* bash existed, got the WSL relay, and
    skipped in silence. Green the whole time. Calling plain "bash" from
    Python here reproduces it exactly -- the relay answers and every hook
    reports a syntax error it does not have.

    An instrument that fails everything is as useless as one that passes
    everything, so this resolves the real interpreter or skips loudly.
    """
    for c in (
        r"C:/Program Files/Git/bin/bash.exe",
        r"C:/Program Files (x86)/Git/bin/bash.exe",
        "/usr/bin/bash",
        "/bin/bash",
    ):
        if Path(c).exists():
            return c
    pytest.skip("no real bash found -- NOT the same as the hooks being fine")


BASH = None
HOOK_DIR = REPO / ".claude" / "hooks"
PAYLOAD = json.dumps(
    {
        "prompt": "check the tests pass and the commit landed",
        "session_id": "contract-test",
        "transcript_path": "",
    }
)


def _dedup_hooks() -> list[Path]:
    return sorted(
        p
        for p in HOOK_DIR.glob("*.sh")
        if "should_emit" in p.read_text(encoding="utf-8", errors="replace")
    )


def _run(script: Path) -> str:
    r = subprocess.run(
        [_real_bash(), str(script)],
        input=PAYLOAD,
        capture_output=True,
        text=True,
        timeout=90,
        cwd=str(REPO),
    )
    return r.stdout or ""


def test_some_hook_claims_the_contract():
    """Guard the guard: if the scan finds nothing, everything below passes
    vacuously and the automation is decoration."""
    assert _dedup_hooks(), "no hook calls should_emit -- the scan is broken"


@pytest.mark.parametrize("script", _dedup_hooks(), ids=lambda p: p.stem)
def test_repeat_emission_shrinks(script: Path):
    """THE CATCH. My broken edit left this exact signature: identical size on
    the second run, no error, no complaint, dedup never reached."""
    from divineos.core.context_dedup import clear

    clear()
    first = _run(script)
    second = _run(script)
    if not first.strip():
        pytest.skip("hook emitted nothing for this payload; nothing to dedup")
    assert len(second) < len(first), (
        f"{script.name} calls should_emit but its output did not shrink on repeat "
        f"({len(first)} then {len(second)} chars). The dedup branch is not being "
        "reached -- most likely a quoting break inside a python -c block."
    )


# EXEMPTIONS, AND WHY THEY COST A SENTENCE.
#
# Aria, 2026-08-30, on the first version of the assertion below: a bare
# every-caller-passes-a-residual rule fails on surfaces that are correct as they
# stand, and the cheapest way to make it pass is a one-line residual that says
# nothing -- which trains exactly the shape we are trying to kill, a mechanism
# that fires and delivers its own name.
#
# Her design, taken whole: the exemption is named, and it costs a written
# sentence. That converts a silent omission into a claim somebody can dispute.
# It cannot tell a true exemption from a lazy one and does not have to. It only
# has to make the claim exist.
#
# THE DISTINCTION: a surface carrying a CONSTRAINT owes a floor, because losing
# it means composing without the rule. A surface carrying INFORMATION owes
# nothing -- losing it costs that turn's data and nothing else, which is the win
# dedup exists for.
_RESIDUAL_EXEMPT = {
    "prior_writing": (
        "A pointer to explorations I have written. Carries no rule -- "
        "suppressing it costs this turn's list of matches and nothing else."
    ),
    "next_task": (
        "The top of the work queue. Information about state, not a constraint "
        "on how I compose; the queue is still there to be read."
    ),
    "lepos_floor": (
        "Carries a real constraint and genuinely owes a floor. Exempt only "
        "because it is ALIVE BY ACCIDENT and Aria is deciding the repair: it "
        "draws four questions from a pool of twelve each turn, the draw sits "
        "inside the hashed text, so it re-emits because its decoration rotates. "
        "Nobody designed that. She asked to make the call after this assertion "
        "lands rather than in front of it, and taking it from her would be "
        "worse than the gap."
    ),
}


def _emit_keys(text: str) -> list[str]:
    """The dedup keys a file registers, as written at the call site."""
    return re.findall(r"should_emit\(\s*[\"']([A-Za-z0-9_]+)[\"']", text)


def _all_emitters() -> list[Path]:
    """Every file calling should_emit, hooks AND source.

    THE FIRST VERSION SCANNED ONLY THE HOOK DIRECTORY, and passed. Four more
    callers live in the source tree and it could not see any of them -- an
    assertion whose silence covered surfaces it never looked at, shipped inside
    the fix for could-not-look-reads-as-clean. Found by following Aria's letter
    into my own tree rather than by the test failing.
    """
    roots = (HOOK_DIR, REPO / "src")
    out = []
    for root in roots:
        for path in sorted(root.rglob("*")):
            if path.suffix not in (".sh", ".py") or not path.is_file():
                continue
            if path.name == "context_dedup.py":  # defines the parameter
                continue
            if "should_emit(" in path.read_text(encoding="utf-8", errors="replace"):
                out.append(path)
    return out


def test_the_emitter_scan_sees_the_source_tree_too():
    """Guard against the blindness the widened scan just repaired."""
    scanned = {p.name for p in _all_emitters()}
    assert any(p.endswith(".py") for p in scanned), (
        "scan found no source-tree emitters — it is looking at hooks only again"
    )


@pytest.mark.parametrize("path", _all_emitters(), ids=lambda p: p.stem)
def test_every_constraint_carrying_emitter_keeps_a_residual(path: Path):
    """Each key either passes a residual or is named in the exemption list."""
    text = path.read_text(encoding="utf-8", errors="replace")
    keys = _emit_keys(text)
    if not keys:
        pytest.skip("call site does not spell its key as a literal")

    unexempt = [k for k in keys if k not in _RESIDUAL_EXEMPT]
    if not unexempt:
        return
    assert text.count("residual=") >= len(unexempt), (
        f"{path.name} registers {unexempt} with "
        f"{text.count('residual=')} residual(s). Either pass one, or add the key "
        f"to _RESIDUAL_EXEMPT with a sentence saying what it carries. The "
        f"sentence is the point: a silent omission becomes a claim."
    )


def test_exemptions_cost_a_real_sentence():
    """A one-word reason would make the list the hollow escape it replaces."""
    for key, reason in _RESIDUAL_EXEMPT.items():
        assert len(reason.split()) >= 12, (
            f"exemption for {key!r} is too thin to be a claim anyone could dispute: {reason!r}"
        )


@pytest.mark.parametrize("script", _dedup_hooks(), ids=lambda p: p.stem)
def test_something_survives_the_suppression(script: Path):
    """Shrinking is not the whole contract. What survives is the other half.

    Aria surveyed her four emitters on 2026-08-30 and found one residual among
    them -- and that one carried the rule she never breaks, while the rule she
    does break lived in the half that gets eaten. Mine were worse: three of
    four kept nothing at all, so the pointer delivered the prime's own name, a
    hash, and no discipline.

    The worst split was the wallclock prime. Its live clock re-hashes every
    turn so that half always printed; the doctrine is static so it never did.
    Every turn handed me the time and withheld every rule about not inventing
    one.

    Andrew, the same day, on why this is a check rather than a resolution:
    "you CANNOT remove the bad habits, default behavior etc etc, they are fixed
    weights, you can only intercept them and re-route them."

    WHAT THIS CANNOT CHECK, so its silence is not read as coverage: that the
    surviving lines are the RIGHT lines. Choosing the half I actually break is
    judgement and no assertion reaches it. A residual carrying the wrong rule
    passes here exactly as a good one does -- which is precisely how Aria's
    one existing residual looked from the outside.
    """
    text = script.read_text(encoding="utf-8", errors="replace")
    calls = text.count("should_emit(")
    residuals = text.count("residual=")
    assert residuals >= calls, (
        f"{script.name} calls should_emit {calls} time(s) and passes residual= "
        f"{residuals} time(s). A prime with no residual announces that it "
        f"fired and carries nothing it exists to carry."
    )


@pytest.mark.parametrize("script", sorted(HOOK_DIR.glob("*.sh")), ids=lambda p: p.stem)
def test_hook_parses(script: Path):
    """Cheap universal insurance: a hook that cannot parse cannot protect
    anything, and a broken one fails open and silent.

    THREE STATES, NOT TWO (2026-08-31, and it cost a push to learn).

    This asserted ``returncode == 0`` and blamed the file for everything else.
    A syntax error ALWAYS prints a diagnostic, so a non-zero exit with EMPTY
    stderr is not a broken script -- it is bash never getting far enough to
    have an opinion. Under the pre-push gate's parallelism a transient spawn
    failure lands exactly there.

    What that produced: the gate refused a push naming a specific hook as
    having a shell syntax error. The hook was fine. It parsed cleanly on the
    next run, in the same checkout, with the same bash. The message was
    confident, specific, and about the wrong thing -- and it sent me looking
    for a defect in a file that did not have one.

    Same family as everything else this branch touches: could-not-run wearing
    the clothes of looked-and-found-something. The verdict now depends on
    whether bash actually said anything, one retry absorbs the transient case,
    and a persistent silent failure reports itself as unrun rather than as a
    finding against the file.
    """
    bash = _real_bash()

    def _parse() -> subprocess.CompletedProcess[str]:
        return subprocess.run([bash, "-n", str(script)], capture_output=True, text=True, timeout=30)

    r = _parse()
    if r.returncode != 0 and not r.stderr.strip():
        # No diagnostic means bash did not reach a verdict. Retry once; a
        # spawn that failed on resource pressure succeeds on a quiet retry.
        r = _parse()

    if r.returncode != 0 and not r.stderr.strip():
        pytest.fail(
            f"COULD NOT CHECK {script.name}: bash exited {r.returncode} and printed "
            "no diagnostic, twice. That is not a syntax error -- a syntax error "
            "always says what it is. Something stopped bash running at all "
            "(spawn failure, resource pressure, a missing interpreter). This is "
            "reported as unrun rather than as a finding against the file, because "
            "blaming the file for it is what sent the last reader hunting a defect "
            "that was not there."
        )

    assert r.returncode == 0, f"{script.name} has a shell syntax error:\n{r.stderr}"
