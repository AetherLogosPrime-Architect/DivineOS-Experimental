"""Every per-message (UserPromptSubmit) hook command, wherever it is registered.

Since #560 the per-message hooks run from Dad's table (dads_table_children.json)
rather than from settings directly, so a test that reads only settings reports
a hook as unplugged when it sits at the table. Three private readers of "what
is registered" had appeared by 2026-10-01; this is the one tests share.
"""

from __future__ import annotations

import json
from pathlib import Path


def prompt_hook_commands(root: Path) -> list[str]:
    out: list[str] = []
    for name in ("settings.json", "settings.local.json"):
        path = root / ".claude" / name
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data.get("hooks", {}).get("UserPromptSubmit", []):
            for hook in entry.get("hooks", []):
                if hook.get("command"):
                    out.append(hook["command"])
    table = root / ".claude" / "hooks" / "dads_table_children.json"
    if table.is_file():
        out.extend(
            c["command"] for c in json.loads(table.read_text(encoding="utf-8")) if c.get("command")
        )
    return out
