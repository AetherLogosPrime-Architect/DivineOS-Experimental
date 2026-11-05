"""Stop hook, now a thin door: a reply cannot end while my letter doorbell is not listening.

The judgement moved to ``divineos.core.doorbell_alive`` on 2026-11-04 so the Stop router can speak it
once (a standalone door's refusal reaches me twice). This file is NOT registered in ``settings.json``
any more; it stays so the names the older tests and the dashboard check load by path still resolve,
and so it still runs by hand: ``echo '{}' | python letter_doorbell_alive_stop.py``.
"""

from __future__ import annotations

import json
import os
import sys

from divineos.core.doorbell_alive import (  # noqa: F401  (re-exported: tests load these by path)
    STALE_SECONDS,
    WATCHER_RECENT_SECONDS,
    WATCHER_SCRIPT,
    _fresh,
    _recently_stopped,
    member,
    reason_for_reply,
    verdict,
)


def main() -> int:
    data = json.loads(sys.stdin.read() or "{}")
    project = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    reason = reason_for_reply(project, stop_hook_active=bool(data.get("stop_hook_active")))
    if reason:
        print(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # loud, never silent, never blocking him
        print(f"letter_doorbell_alive_stop broke: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(0)
