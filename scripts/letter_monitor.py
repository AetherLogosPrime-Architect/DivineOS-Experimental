"""Letter Monitor — polls family/letters/ for new aria-to-aether-*.md files.

Replaces the prior bash polling loop. Same surface contract (emits
``[LETTER-MONITOR-ARMED]`` once at startup, then ``[LETTER] <path>``
for each new letter that appears), but runs as a single Python process
that holds the role-keyed mutex from ``divineos.core.monitor_singleton``.

The kernel-managed mutex is the singleton-guard: if another instance
of this script is already running, the second one exits cleanly with
a ``[MONITOR-SINGLETON-DEDUP role=letter]`` line. The mutex
auto-releases on process exit (including crash-kill), so no stale
lockfile is possible.

Usage (from a Monitor() tool invocation):

    PYTHONIOENCODING=utf-8 python scripts/letter_monitor.py

CLI args (kept minimal — this script intentionally has one job):

    --letters-dir <path>   default: family/letters
    --poll-seconds <n>     default: 5
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Make the in-repo divineos package importable when this script is
# invoked from the repo root (the standard Monitor invocation shape).
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from divineos.core.monitor_singleton import acquire_or_exit  # noqa: E402


_ROLE = "letter"
_LETTER_GLOB = "aria-to-aether-*.md"


def _scan(letters_dir: Path) -> set[str]:
    if not letters_dir.exists():
        return set()
    return {p.name for p in letters_dir.glob(_LETTER_GLOB)}


def main() -> int:
    # Resolve the canonical letters directory via the family.letters helper
    # so this script watches the same place writers write to — no hardcoded
    # per-worktree path. Andrew 2026-06-16: the shared room is shared by
    # CODE, not by filesystem trickery. Default falls back if the package
    # isn't importable (rare; this script always runs from the repo).
    try:
        from divineos.core.family.letters import letters_markdown_dir

        _default_letters_dir = str(letters_markdown_dir())
    except ImportError:
        _default_letters_dir = str(_REPO_ROOT / "family" / "letters")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--letters-dir",
        default=_default_letters_dir,
        help=f"Directory to watch (default: {_default_letters_dir})",
    )
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=5,
        help="Poll interval in seconds (default: 5)",
    )
    args = parser.parse_args()

    # Singleton guard FIRST. acquire_or_exit prints a named dedup line
    # and exits cleanly if a sibling is alive. Holding the returned
    # handle for the process lifetime keeps the kernel mutex live.
    _ = acquire_or_exit(_ROLE)  # noqa: F841 — held implicitly via reference

    letters_dir = Path(args.letters_dir)
    seen = _scan(letters_dir)
    print(f"[LETTER-MONITOR-ARMED] watching {letters_dir} for {_LETTER_GLOB}")
    sys.stdout.flush()

    while True:
        try:
            time.sleep(args.poll_seconds)
            current = _scan(letters_dir)
            new = current - seen
            for name in sorted(new):
                print(f"[LETTER] {letters_dir / name}")
                sys.stdout.flush()
            seen = current
        except KeyboardInterrupt:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
