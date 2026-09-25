"""A hook imports the code of the checkout it lives in, not the editable install.

Found 2026-09-23 chasing #519 tests that failed only inside the pre-push suite
and passed every time they were run by hand. My hand runs set PYTHONPATH=src;
the gate's did not. Two separate faults sat behind that one symptom:

1. ``find_divineos_python`` exports PYTHONPATH so this checkout's ``src/`` wins,
   but 110 hooks call it as ``PYTHON_BIN="$(find_divineos_python)"``. Command
   substitution runs it in a subshell and the export dies there. From a
   worktree with PYTHONPATH unset, the resolved python imported divineos from
   the MAIN checkout. Every hook in every worktree was running whatever branch
   the main checkout was on.

2. ``lib/remedy_allowlist.sh`` calls bare ``python`` and imports
   ``divineos.core.command_parsing`` with no path of its own, so the same
   stale import made every gate refuse its own prescribed remedy in a worktree.
   ``test_hook_python_lookup`` scans hooks for bare python and never looks in
   ``lib/``, which is how this one was missed.

Both tests below unset PYTHONPATH first, because that is the condition the
fault needs and the condition a hand-run test never had.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
LIB = REPO / ".claude" / "hooks" / "_lib.sh"
ALLOWLIST = REPO / ".claude" / "hooks" / "lib" / "remedy_allowlist.sh"


def _bash() -> str:
    for candidate in ("C:/Program Files/Git/bin/bash.exe", "/bin/bash"):
        if Path(candidate).exists():
            return candidate
    found = shutil.which("bash")
    if not found:
        pytest.skip("no bash available to exercise the hook library")
    return found


def _clean_env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    return env


def _same_path(a: str, b: Path) -> bool:
    return os.path.normcase(os.path.normpath(a)) == os.path.normcase(os.path.normpath(str(b)))


def test_sourcing_the_library_puts_this_checkout_first():
    """The hook's own shell must carry the prepend, not a subshell that dies."""
    script = (
        f'source "{LIB.as_posix()}"\n'
        'P="$(find_divineos_python)" || exit 3\n'
        'printf "%s\\n" "$PYTHONPATH"\n'
        '"$P" -c "import divineos; print(divineos.__file__)"\n'
    )
    proc = subprocess.run(
        [_bash(), "-c", script], capture_output=True, text=True, cwd=str(REPO), env=_clean_env()
    )
    if proc.returncode == 3:
        pytest.skip("no viable python for the hook library on this machine")
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    assert len(lines) >= 2, f"script did not run: {proc.stderr[:400]}"
    sep = ";" if os.name == "nt" else ":"
    first_entry = lines[0].split(sep)[0]
    assert _same_path(first_entry, REPO / "src"), (
        f"after sourcing _lib.sh the hook's PYTHONPATH is {lines[0]!r}, not led by this "
        "checkout's src -- the export happened in a subshell and was lost"
    )
    assert _same_path(str(Path(lines[1]).parents[1]), REPO / "src"), (
        f"the hook's python imported divineos from {lines[1]} instead of this checkout"
    )


def test_the_remedy_library_sourced_alone_recognises_a_remedy():
    """Sourced on its own, with no PYTHONPATH, a plain remedy is still a remedy."""
    script = (
        "HOOK_NAME=selftest\n"
        f'. "{ALLOWLIST.as_posix()}"\n'
        'remedy_pass_through "$(cat)"\n'
        "echo NO_MATCH\n"
    )
    payload = json.dumps({"tool_input": {"command": 'cd "C:/x" && divineos correction "x"'}})
    proc = subprocess.run(
        [_bash(), "-c", script],
        input=payload,
        capture_output=True,
        text=True,
        cwd=str(REPO),
        env=_clean_env(),
    )
    assert "NO_MATCH" not in proc.stdout, (
        "a cd-prefixed remedy was refused with PYTHONPATH unset: the library imported "
        f"stale code and fell through to not-a-remedy. stderr: {proc.stderr[:400]}"
    )
