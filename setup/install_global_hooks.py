"""Install DivineOS hooks into the USER-level Claude settings.

Why this exists (task #48, 2026-05-21): the Claude Code desktop app runs
every session in an auto-created worktree under .claude/worktrees/<name>/.
That worktree's .claude/ has only settings.local.json + agent-memory — NO
settings.json and NO hooks/ — so project-level hooks NEVER FIRE in worktree
sessions. The entire operating-loop enforcement layer was silently inert in
the environment the agent actually runs in (verified: 0 findings entries in
6h of active work).

Fix: register the hooks in the USER-level settings (~/.claude/settings.json),
which Claude Code reads for EVERY session regardless of worktree. Hook
command paths are rewritten to ABSOLUTE so they resolve no matter the cwd.

This is safe for a DivineOS-only operator: every session is DivineOS, so the
hooks always belong. (If you ever open Claude Code on a non-DivineOS project,
the hook scripts self-locate via `git rev-parse --show-toplevel`; outside
DivineOS they fail-soft. If that ever matters, add a cwd guard.)

Idempotent: re-running overwrites the "hooks" key with a fresh copy from the
project settings. A timestamped backup of the user settings is written first.

Usage:
    python setup/install_global_hooks.py
"""

from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path

# Project root = two levels up from this file (setup/ -> repo root).
_REPO_ROOT = Path(__file__).resolve().parent.parent
_PROJECT_SETTINGS = _REPO_ROOT / ".claude" / "settings.json"
_USER_SETTINGS = Path.home() / ".claude" / "settings.json"

# Absolute prefix used inside the bash hook commands. Forward slashes work in
# git-bash even on Windows; quoted because the path contains a space.
_ABS_HOOKS = f"{_REPO_ROOT.as_posix()}/.claude/hooks"

_REL_CMD = re.compile(r"bash \.claude/hooks/(\S+\.sh)")


def _absolutize(command: str) -> str:
    """Rewrite `bash .claude/hooks/X.sh` -> `bash "<abs>/X.sh"`."""
    return _REL_CMD.sub(lambda m: f'bash "{_ABS_HOOKS}/{m.group(1)}"', command)


def install() -> int:
    if not _PROJECT_SETTINGS.exists():
        raise SystemExit(f"project settings not found: {_PROJECT_SETTINGS}")

    project = json.loads(_PROJECT_SETTINGS.read_text(encoding="utf-8"))
    hooks = project.get("hooks", {})

    rewritten = 0
    for _event, groups in hooks.items():
        for group in groups:
            for hook in group.get("hooks", []):
                cmd = hook.get("command")
                if cmd:
                    new = _absolutize(cmd)
                    if new != cmd:
                        rewritten += 1
                    hook["command"] = new

    _USER_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    user: dict = {}
    if _USER_SETTINGS.exists():
        backup = _USER_SETTINGS.with_name(f"settings.json.bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(_USER_SETTINGS, backup)
        print(f"backed up existing user settings -> {backup}")
        user = json.loads(_USER_SETTINGS.read_text(encoding="utf-8"))

    user["hooks"] = hooks
    _USER_SETTINGS.write_text(json.dumps(user, indent=2), encoding="utf-8")
    # Validate round-trip.
    json.loads(_USER_SETTINGS.read_text(encoding="utf-8"))
    print(f"installed {rewritten} hook commands (absolute paths) -> {_USER_SETTINGS}")
    return rewritten


if __name__ == "__main__":
    install()
