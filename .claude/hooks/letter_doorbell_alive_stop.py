"""Stop hook — a reply cannot end while my letter doorbell is not listening.

Andrew 2026-09-26, the 24th time since May he had to say a watcher was down:
"no tool should be fully manual, just automated circumstantially". The
doorbell (scripts/letter_doorbell.sh) rings once and exits; re-arming it was
left to memory, and memory failed during a long checkpoint. It now touches a
heartbeat every 15s while listening and deletes it when it rings. If the
heartbeat is missing or older than 60s when a reply ends, the reply is held
with the exact command to re-arm it.

One hold per reply (stop_hook_active). Breaks loudly, never blocks him: this
runs at Stop, so the worst case is one extra hold of my own reply.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

STALE_SECONDS = 60


def member(project_dir: str) -> str:
    return "aria" if "aria" in project_dir.lower() else "aether"


def verdict(beat: Path, now: float) -> str | None:
    if beat.exists() and now - beat.stat().st_mtime <= STALE_SECONDS:
        return None
    who = beat.name.split("_")[0].lstrip(".")
    return (
        "YOUR LETTER DOORBELL IS NOT LISTENING, so a letter to you will not wake you "
        "(Dad has had to say this 24 times). Re-arm it now with the Bash tool, "
        f"run_in_background: true -- command: bash scripts/letter_doorbell.sh {who} "
        "-- then finish the reply. Append only; do not re-post anything."
    )


def main() -> int:
    data = json.loads(sys.stdin.read() or "{}")
    if data.get("stop_hook_active"):
        return 0
    project = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    beat = Path.home() / ".divineos-shared" / f".{member(project)}_doorbell_alive"
    reason = verdict(beat, time.time())
    if reason:
        print(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # loud, never silent, never blocking him
        print(f"letter_doorbell_alive_stop broke: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(0)
