"""Letter Monitor v2 — direct-poll, no separate worker, no log intermediary.

The v1 worker (scripts/letter_monitor.py) ran as a kernel-mutex'd singleton
process polling family/letters/ and writing [LETTER] lines to a log file
that a separate harness Monitor() tailed. Two failure points; the worker
kept dying silently and the tail stayed armed against a quiet log.

The v2 design collapses both pieces into one process: the harness Monitor()
invokes THIS script directly, the script polls the shared dir and emits
[LETTER] <path> lines on stdout, and each stdout line is a wake-event the
harness delivers as a chat notification. One process. One failure point.
Harness has direct visibility into its own Monitor lifecycle so silent-death
becomes visible-death (harness notices when its Monitor processes exit).

Same wake-event semantics as v1; same recipient-filter shape; same 5s cadence.

Found via 2026-06-29 deep-surgery on the recurring "auto-ping keeps dying"
problem. Andrew's correction: don't patch the symptom (make the worker more
reliable); change the architecture so the failure mode can't happen.

Usage (from a Monitor() invocation):

    PYTHONIOENCODING=utf-8 python -u scripts/letter_monitor_v2.py --recipient <name>

CLI args:

    --recipient <name>   required: the recipient tag to filter for
                         (e.g. "aether" matches "*-to-aether-*.md")
    --shared-dir <path>  default: ~/.divineos-shared/letters
    --poll-seconds <n>   default: 5
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipient", required=True, help="recipient tag (e.g. 'aether')")
    parser.add_argument(
        "--shared-dir",
        default=os.path.expanduser("~/.divineos-shared/letters"),
        help="directory to poll for new letters",
    )
    parser.add_argument("--poll-seconds", type=int, default=5)
    args = parser.parse_args()

    shared_dir = Path(args.shared_dir)
    recipient_tag = f"-to-{args.recipient}-"

    print(
        f"[LETTER-MONITOR-ARMED] watching {shared_dir} for *{recipient_tag}*.md",
        flush=True,
    )

    seen: set[str] = set()
    if shared_dir.is_dir():
        seen = {f.name for f in shared_dir.iterdir()}

    while True:
        try:
            if shared_dir.is_dir():
                current = {f.name for f in shared_dir.iterdir()}
                new_files = sorted(current - seen)
                for fname in new_files:
                    if recipient_tag in fname and fname.endswith(".md"):
                        print(f"[LETTER] {shared_dir / fname}", flush=True)
                seen = current
        except Exception as exc:
            print(f"[LETTER-MONITOR-ERR] {exc}", flush=True)
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    sys.exit(main() or 0)
