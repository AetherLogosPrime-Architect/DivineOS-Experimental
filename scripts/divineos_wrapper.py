"""divineos wrapper — dispatches `divineos <cmd>` to the CWD's sealed venv.

The pip ping-pong fix at the CLI-dispatch layer. See
`docs/pip_pingpong_wrapper_design.md` for the full design.

Detection algorithm:
    1. Walk up from CWD looking for `.envrc` marker (Aria's hook convention).
    2. If found: expected sealed CLI is `<marker_dir>/.direnv/python-*/Scripts/divineos.exe`
       on Windows, `<marker_dir>/.direnv/python-*/bin/divineos` on Unix.
    3. If sealed CLI exists: os.execv (Unix) or subprocess (Windows). Transparent
       — args, stdin/stdout, exit code all pass through unchanged.
    4. If missing: FAIL LOUD. Never silently fall back to system install (that
       would reintroduce the ping-pong shape at the wrapper layer).

Why fail-loud, not fallback: the whole point is preventing silent
wrong-code execution. Anyone who wants the system-wide install can
invoke it by explicit path (`python -m divineos ...`); the shell-fronting
`divineos` command MUST route through the wrapper.

What this does NOT solve (per Aria's second-seat 2026-07-19):
    - `.pth` module-import collision (`import divineos` from Python code).
      Wrapper controls CLI dispatch, not module-import resolution.
    - `python -m divineos` or `python -c "from divineos import ..."` bypass
      the entry-point entirely.
    - Pip-install-time isolation itself. Wrapper works around this at the
      dispatch layer; full pip-side fix is a separate follow-on.
"""

from __future__ import annotations

import glob
import os
import sys
from pathlib import Path

_MARKER_FILENAME = ".envrc"
_VENV_ROOT_NAME = ".direnv"


def find_marker_dir(start: Path) -> Path | None:
    """Walk up from start looking for a `.envrc` marker file.

    Returns the directory containing the marker, or None if not found
    before reaching filesystem root.
    """
    current = start.resolve()
    while True:
        if (current / _MARKER_FILENAME).is_file():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def find_sealed_cli(marker_dir: Path) -> Path | None:
    """Return the sealed `divineos` executable path if it exists, else None.

    Checks two conventions:
      1. Aria's hook convention: ``.direnv/python-<ver>/Scripts/`` on
         Windows, ``.direnv/python-<ver>/bin/`` on Unix. If multiple
         python-* dirs exist (upgrade scenario), take first glob match.
      2. Plain ``.venv/`` convention: some checkouts (Experimental) use
         a bare ``.venv/`` rather than ``.direnv/python-*/``. Same
         semantics — sealed local venv with a divineos entry point.

    Added 2026-07-19 during LEPOS-crisis: my Experimental checkout has
    a working ``.venv/Scripts/divineos.exe`` but the wrapper only looked
    in ``.direnv/`` so bare ``divineos`` bounced with "sealed venv not
    populated" and I could not clear engagement gates. Both patterns
    are equally sealed-local; supporting both is correct.
    """
    # Convention 1: .direnv/python-<ver>/
    venv_root = marker_dir / _VENV_ROOT_NAME
    if venv_root.is_dir():
        matches = sorted(glob.glob(str(venv_root / "python-*")))
        if matches:
            venv = Path(matches[0])
            if (venv / "Scripts").is_dir():
                cli = venv / "Scripts" / "divineos.exe"
            else:
                cli = venv / "bin" / "divineos"
            if cli.exists():
                return cli
    # Convention 2: .venv/
    dot_venv = marker_dir / ".venv"
    if dot_venv.is_dir():
        if (dot_venv / "Scripts").is_dir():
            cli = dot_venv / "Scripts" / "divineos.exe"
        else:
            cli = dot_venv / "bin" / "divineos"
        if cli.exists():
            return cli
    return None


def fail_loud(marker_dir: Path | None, cwd: Path) -> int:
    """Emit a plain-language error and return non-zero exit code."""
    if marker_dir is None:
        msg = (
            f"divineos: no sealed venv found. Walked up from {cwd} looking for "
            f"a `{_MARKER_FILENAME}` marker file — none found in this checkout "
            "or any parent directory.\n\n"
            "This shell isn't inside a DivineOS checkout, OR the checkout is "
            "missing its `.envrc` marker file.\n\n"
            "Fix: `cd` into your DivineOS checkout root, then rerun. If the "
            f"marker is genuinely missing, `touch {_MARKER_FILENAME}` at the "
            "checkout root.\n\n"
            "The wrapper deliberately does NOT fall back to a system-wide "
            "install — that would reintroduce the pip ping-pong bug it exists "
            "to prevent."
        )
    else:
        expected_scripts = marker_dir / _VENV_ROOT_NAME / "python-*" / "Scripts" / "divineos.exe"
        expected_bin = marker_dir / _VENV_ROOT_NAME / "python-*" / "bin" / "divineos"
        msg = (
            f"divineos: sealed venv not populated. Marker found at "
            f"{marker_dir / _MARKER_FILENAME} but no sealed `divineos` CLI at "
            f"either:\n  {expected_scripts}\n  {expected_bin}\n\n"
            "Fix: open git-bash in this checkout (Aria's cd-hook will build the "
            "sealed venv on first cd), then `pip install -e .` inside that "
            "activated shell. After that, any shell (PowerShell, cmd, IDE "
            "terminal) invoking `divineos` will find the sealed CLI via this "
            "wrapper.\n\n"
            "The wrapper deliberately does NOT fall back to a system-wide "
            "install — that would reintroduce the pip ping-pong bug it exists "
            "to prevent."
        )
    print(msg, file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    """Wrapper entry point. Returns exit code (non-zero on fail-loud)."""
    if argv is None:
        argv = sys.argv[1:]
    cwd = Path.cwd()
    marker_dir = find_marker_dir(cwd)
    if marker_dir is None:
        return fail_loud(None, cwd)
    sealed_cli = find_sealed_cli(marker_dir)
    if sealed_cli is None:
        return fail_loud(marker_dir, cwd)

    # Dispatch — use execv on Unix (replaces this process), subprocess on
    # Windows (execv semantics on Windows are lossy for stdio inheritance
    # in some shells). Both preserve stdin/stdout/stderr and exit code.
    if os.name == "nt":
        import subprocess

        try:
            result = subprocess.run([str(sealed_cli)] + list(argv), check=False)
            return result.returncode
        except OSError as e:
            print(
                f"divineos: failed to invoke sealed CLI at {sealed_cli}: {e}",
                file=sys.stderr,
            )
            return 3
    else:
        try:
            os.execv(str(sealed_cli), [str(sealed_cli)] + list(argv))
        except OSError as e:
            print(
                f"divineos: failed to invoke sealed CLI at {sealed_cli}: {e}",
                file=sys.stderr,
            )
            return 3
        return 0  # unreachable — execv replaces process


if __name__ == "__main__":
    sys.exit(main())
