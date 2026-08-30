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
    anything, and a broken one fails open and silent."""
    r = subprocess.run(
        [_real_bash(), "-n", str(script)], capture_output=True, text=True, timeout=30
    )
    assert r.returncode == 0, f"{script.name} has a shell syntax error:\n{r.stderr}"
