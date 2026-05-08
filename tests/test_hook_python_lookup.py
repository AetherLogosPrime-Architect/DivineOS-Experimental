"""Regression test for the hook PATH-lookup pattern.

Round-1 audit (2026-05-07) found ``.claude/hooks/family-wrapper-required.sh``
used ``command -v python`` and silently failed-OPEN when the operator's
shell PATH didn't have divineos's deps. Round-2 found the same shape in
11 other hooks. The fix is a shared helper at ``.claude/hooks/_lib.sh``
and a discipline that every divineos-importing hook sources it.

This test makes the discipline structural: any hook that imports
divineos.* via embedded python must source ``_lib.sh`` and use
``$PYTHON_BIN``, not bare ``python`` or ``python -c``. New hooks that
drift back into bare invocations get caught at test-time, not at
incident-time.

Verified to catch drift: introduced a fake hook with bare ``python -c``
during development; this test failed immediately. Removing the fake
returned the suite to green.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
LIB_PATH = HOOKS_DIR / "_lib.sh"

# Hooks that don't import divineos (no python embedding) and so don't
# need the helper. Add to this list with a comment explaining why.
EXEMPT_HOOKS = {
    "_lib.sh",  # the helper itself
    "log-session-end.sh",  # no-op, just `exit 0`
    "post-commit-auto-close.sh",  # invokes `divineos goal auto-close` CLI, not embedded python
    "pre-compact.sh",  # only invokes `divineos extract`/`divineos log` CLI, not embedded python
}


def _hook_files() -> list[Path]:
    if not HOOKS_DIR.exists():
        return []
    return sorted(p for p in HOOKS_DIR.glob("*.sh") if p.name not in EXEMPT_HOOKS)


def test_lib_helper_present() -> None:
    """The ``_lib.sh`` helper file must exist and define
    ``find_divineos_python``. If this fails, the whole hook-system
    PATH-lookup discipline is broken."""
    assert LIB_PATH.exists(), f"Expected helper at {LIB_PATH}"
    text = LIB_PATH.read_text(encoding="utf-8")
    assert "find_divineos_python()" in text, (
        "_lib.sh must define find_divineos_python(). The hook-system relies "
        "on this function to locate a divineos-capable python interpreter."
    )


def test_no_hook_uses_bare_python_for_divineos_imports() -> None:
    """Every hook that imports divineos.* must source _lib.sh and
    route python invocations through ``$PYTHON_BIN``.

    Catches the round-1/round-2 failure-class: a hook that uses bare
    ``python -c`` or ``command -v python`` will silently fail-OPEN on
    any shell where the system python lacks divineos's deps.
    """
    bare_python_pattern = re.compile(
        # Match `python -c`, `python -m`, `python3 -c`, `python3 -m`
        # at the start of a command (line-start, after pipe, after $()
        # but NOT inside heredoc bodies (those are python source code).
        r"(?:^|\| |\$\()\s*python3?\s+-[cm]\b",
        re.MULTILINE,
    )
    command_v_python_pattern = re.compile(
        r"command\s+-v\s+python\b",
    )

    failures: list[tuple[str, str, int]] = []
    for hook in _hook_files():
        text = hook.read_text(encoding="utf-8")

        # Hooks that don't import divineos at all are fine even with bare python
        # (e.g. a hook that just runs a shell script). Flag only hooks that
        # actually embed divineos imports.
        imports_divineos = (
            "from divineos" in text
            or "import divineos" in text
            or "divineos.hooks" in text
            or "divineos.core" in text
        )
        if not imports_divineos:
            continue

        # The hook must source _lib.sh
        if "_lib.sh" not in text:
            failures.append((hook.name, "does not source _lib.sh", 0))
            continue

        # Find any bare python invocations
        for m in bare_python_pattern.finditer(text):
            line_no = text[: m.start()].count("\n") + 1
            line = text.split("\n")[line_no - 1] if line_no <= len(text.split("\n")) else ""
            if "$PYTHON_BIN" in line:
                continue
            failures.append((hook.name, f"bare python invocation: {m.group(0).strip()!r}", line_no))

        # `command -v python` is the round-1 anti-pattern
        for m in command_v_python_pattern.finditer(text):
            line_no = text[: m.start()].count("\n") + 1
            failures.append((hook.name, "uses `command -v python` (round-1 anti-pattern)", line_no))

    if failures:
        msg_lines = [
            "Hooks importing divineos must use _lib.sh's find_divineos_python.",
            "Bare `python -c`/`python -m` or `command -v python` silently fails-OPEN",
            "when the operator's shell python lacks divineos's deps.",
            "",
            "Failures:",
        ]
        for name, reason, line_no in failures:
            location = f" (line {line_no})" if line_no else ""
            msg_lines.append(f"  {name}{location}: {reason}")
        msg_lines.append("")
        msg_lines.append(
            "Fix: source $REPO_ROOT/.claude/hooks/_lib.sh, then "
            'PYTHON_BIN="$(find_divineos_python)" || exit 0'
        )
        pytest.fail("\n".join(msg_lines))
