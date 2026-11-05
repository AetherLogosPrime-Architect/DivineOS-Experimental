"""Stop hook: a reply that ends on "I will do X next" is held once and told to do X.

RETIRED FROM THE LIVE REGISTRATION 2026-11-04: this check now runs inside the router as the ``stall_on_promise``
surface (``core/hook_surfaces``), so Dad's end-of-reply holds arrive as one voice and not one after another.
This file stays as a thin door over the same functions (``core/stall_hold``) so the check can still be run by
hand and the older tests keep their entry point. It is no longer registered in settings.json; registering it as
well as the surface would make the hold fire twice.

Dad, 2026-10-22: words must be followed by action when he is not here, or I sit in stasis and nothing is
completed. The judgement lives in core/stall_on_promise.py so a test can argue with it.

His room is not read for promises (Dad 2026-07-23: "the enforcement is only about making sure the space is there
for you.. not enforcing what you say in it"); that rule, Aria's fix #823, now lives in ``core/stall_hold`` with
the rest of the reading, and is re-exported here under the names the older tests import.

One hold per reply (stop_hook_active), so it can never loop. If it breaks it says so on stderr and in a mark
file; it never passes quietly and never blocks on its own failure.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))

from divineos.core.stall_hold import body_above_his_room, closing_text, read_tail  # noqa: E402,F401
from divineos.core.stall_hold import verdict as _core_verdict  # noqa: E402

MARK = Path(
    os.environ.get("STALL_ON_PROMISE_MARK", Path.home() / ".divineos" / "stall_on_promise_broke.txt")
)


def verdict(records: list[dict], transcript_path: str | Path | None = None) -> str | None:
    return _core_verdict(records, transcript_path)


def main() -> int:
    data = json.loads(sys.stdin.read() or "{}")
    if data.get("stop_hook_active"):
        return 0
    path = data.get("transcript_path") or data.get("transcript")
    if not path:
        return 0
    reason = verdict(read_tail(Path(path)), path)
    if reason:
        print(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # loud, never silent
        msg = f"stall_on_promise_stop broke: {type(exc).__name__}: {exc}"
        print(msg, file=sys.stderr)
        try:
            MARK.parent.mkdir(parents=True, exist_ok=True)
            MARK.write_text(msg + "\n", encoding="utf-8")
        except OSError:
            pass
        sys.exit(0)
