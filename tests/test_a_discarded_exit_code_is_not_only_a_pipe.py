"""A semicolon throws an exit code away as completely as a pipe does.

THE DEFECT, found by Aria 2026-09-21 and measured here. The exit-code guard
models exactly one way a failure goes missing: a pipeline reports the LAST
stage's status, so a failing first stage arrives as zero. It refuses that shape
when the first stage mutates shared state.

It does not model the other way, which is older and simpler. In

    git push origin branch; echo done

the push's exit code is discarded by the semicolon before any pipe exists. The
guard splits on the pipe first and leaves when it finds fewer than two stages,
so this command never reaches the part of the file that would have recognised
the push.

WHY IT MATTERED. Aria's own push was refused while the harness reported the
command complete. She went looking for the guard she had helped write against
exactly that, fed it her real command line, and got silence. She proved the rig
could speak before calling it a finding -- the same file, same envelope, piped
shape, warned immediately. So the instrument was alive and the blindness was
real: a guard against exit codes that silently read zero, itself silently
reading zero.

THE TEST THAT CARRIES THE CLAIM is the last one. Every case below passes if the
guard simply refuses everything containing a semicolon, which would make it
noise and get it switched off within a day -- the file says so in its own
margins. Asserting that the harmless separators stay silent is what keeps the
four answers four.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "pipeline-exit-ambiguity.sh"

# A bare "bash" resolves to the WSL relay on this machine, which cannot see
# this filesystem and fails with a message that looks nothing like a hook
# verdict. Resolving through PATH finds the shell the hooks actually run under.
# The rig-can-speak control below is what proves the resolved shell works; this
# only finds a candidate.
BASH = shutil.which("bash")


def _verdict(command: str) -> str:
    """Run the real hook on a real command line. Returns deny / warn / silent."""
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    proc = subprocess.run(
        [BASH, str(HOOK)], input=payload, capture_output=True, text=True, check=False
    )
    out = proc.stdout.strip()
    if not out:
        return "silent"
    try:
        parsed = json.loads(out)
    except json.JSONDecodeError:
        return "silent"
    hook_out = parsed.get("hookSpecificOutput", {})
    if hook_out.get("permissionDecision") == "deny":
        return "deny"
    if hook_out.get("additionalContext"):
        return "warn"
    return "silent"


@pytest.mark.skipif(not HOOK.exists() or not BASH, reason="hook or bash not present here")
class TestDiscardedExitCodes:
    def test_the_rig_can_speak(self) -> None:
        """Control, asserted live. A silent verdict below means nothing unless
        this one is loud -- a dead hook and a blind hook return the same value.
        """
        assert _verdict("git push origin feature | tail -5") == "deny"

    def test_a_semicolon_after_a_push_is_not_silence(self) -> None:
        """The incident. The push's status is thrown away before any pipe."""
        assert _verdict("git push origin feature; echo done") != "silent"

    def test_a_semicolon_after_a_push_with_a_later_pipe_is_not_silence(self) -> None:
        """Aria's actual line. The pipe is real but it is not what ate the code."""
        assert _verdict("git push origin feature; echo done | tail -5") != "silent"

    def test_a_redirect_and_semicolon_is_not_silence(self) -> None:
        """Sending output to nowhere does not make the status less important."""
        assert _verdict("git commit -m x > /dev/null; echo ok") != "silent"

    def test_and_and_is_left_alone(self) -> None:
        """`&&` PRESERVES the failure -- the second command simply does not run.

        Refusing this would be the over-correction: it punishes the one
        separator that already does the right thing.
        """
        assert _verdict('cd "/tmp" && git push origin feature') == "silent"

    def test_a_harmless_command_before_a_semicolon_is_left_alone(self) -> None:
        """A discarded `cd` or `ls` status costs a re-run, not a false report."""
        assert _verdict('cd "/tmp"; ls') == "silent"
        assert _verdict("git log --oneline; git status") == "silent"

    def test_the_separators_do_not_collapse_into_one_answer(self) -> None:
        """THE CLAIM, and the reason the cases above are not enough.

        Four command shapes, and the guard must distinguish them. Refusing
        every semicolon would pass every test above this one and make the hook
        noise, which is how the file's own margins say a hook gets disabled.
        """
        discards = _verdict("git push origin feature; echo done")
        preserves = _verdict('cd "/tmp" && git push origin feature')
        harmless = _verdict('cd "/tmp"; ls')
        piped = _verdict("git push origin feature | tail -5")

        assert discards != "silent", "the discarding separator was not caught"
        assert preserves == "silent", "the separator that preserves failure was punished"
        assert harmless == "silent", "a harmless discarded status was treated as consequential"
        assert piped == "deny", "the shape the guard was built for stopped firing"
