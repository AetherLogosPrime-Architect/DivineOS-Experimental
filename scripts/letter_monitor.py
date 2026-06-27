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

from divineos.core.identity import get_my_identity  # noqa: E402
from divineos.core.monitor_singleton import acquire_or_exit  # noqa: E402


_ROLE = "letter"


def _letter_glob_for(recipient: str) -> str:
    """Glob pattern matching letters addressed TO ``recipient``.

    Naming convention in family/letters: ``<sender>-to-<recipient>-<date>-<slug>.md``.
    The glob catches any sender — recipient is the discriminator.
    """
    return f"*-to-{recipient.lower()}-*.md"


def _scan(letters_dir: Path, glob: str) -> set[str]:
    if not letters_dir.exists():
        return set()
    return {p.name for p in letters_dir.glob(glob)}


def _seen_from_log(event_log: Path) -> set[str]:
    """Reconstruct the emitted-letter set from the event log.

    Per Perplexity audit 2026-06-26 (Finding 2): the prior shape baselined
    `seen` from a fresh disk scan at startup, so any letter that landed
    during a dark window (process died -> relaunched) was silently absorbed
    into baseline and never emitted as a [LETTER] wake-ping. Same bug
    class ear_watch already fixed for itself on 5-31 (delta-from-boot-
    snapshot -> delta-from-seen-set).

    Fix: the log already records every emission. Use it as the persisted
    seen-set. A letter that landed during the dark window won't appear
    in the log (it was never emitted), so the next poll after relaunch
    correctly fires the wake-ping.
    """
    if not event_log.exists():
        return set()
    seen: set[str] = set()
    try:
        with open(event_log, encoding="utf-8") as f:
            for raw in f:
                parts = raw.rstrip("\n").split("\t", 1)
                if len(parts) != 2:
                    continue
                line = parts[1]
                if not line.startswith("[LETTER] "):
                    continue
                path_str = line[len("[LETTER] ") :]
                seen.add(Path(path_str).name)
    except OSError:
        return set()
    return seen


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
    parser.add_argument(
        "--recipient",
        default=None,
        help=(
            "Substrate-occupant name to filter letters by; matches "
            "*-to-<recipient>-*.md. Defaults to my_identity from "
            "core_memory."
        ),
    )
    args = parser.parse_args()

    # Recipient filter (2026-06-17): the script previously hardcoded
    # "aria-to-aether-*.md" — fine for Aether's monitor, wrong for any
    # other substrate-occupant. Now the recipient defaults to whoever
    # owns this checkout (via my_identity), and the glob is derived
    # from that. Aether's monitor catches letters-to-Aether; Aria's
    # catches letters-to-Aria; a future sibling catches their own.
    # raise_on_unset=False: monitor scripts are bootstrap-safe — they
    # run at session-start, possibly pre-config. The panel surfaces the
    # misconfiguration loudly in the briefing; here we fall back so
    # letter coverage exists even before the operator has stamped their
    # identity. The --recipient override is always honored.
    recipient = args.recipient or get_my_identity(raise_on_unset=False)
    letter_glob = _letter_glob_for(recipient)

    # Singleton guard FIRST. acquire_or_exit prints a named dedup line
    # and exits cleanly if a sibling is alive. Holding the returned
    # handle for the process lifetime keeps the kernel mutex live.
    #
    # Occupant-discriminated mutex (2026-06-17): Aether's and Aria's
    # letter monitors can both run in the same Windows session because
    # the mutex name now includes the occupant. Within an occupant,
    # cross-window dup protection still applies.
    _ = acquire_or_exit(_ROLE, occupant=recipient)  # noqa: F841

    letters_dir = Path(args.letters_dir)

    # Append-only event log path (Aether 2026-06-20 structural decoupling).
    # The harness Monitor() primitive is documented as unreliable — dies on
    # SessionStart:resume, dies mid-turn. Welding the watcher to it meant
    # every harness death killed the watcher. Decoupling: the watcher now
    # writes every event to ~/.divineos-<recipient>/letter_events.log as
    # well as stdout. A harness Monitor task can tail the file to surface
    # events as live wake-pings; even when the harness Monitor dies, the
    # watcher keeps writing to the log, and any new harness session can
    # re-subscribe by tailing the same file. No event is ever lost.
    log_dir = Path.home() / f".divineos-{recipient.lower()}"
    log_dir.mkdir(parents=True, exist_ok=True)
    event_log = log_dir / "letter_events.log"

    # Persisted seen-set via event log (Perplexity audit 2026-06-26 Finding 2).
    # First-run case (no log yet): fall back to disk scan to preserve original
    # behavior — a fresh install shouldn't dump every historical letter as
    # wake-pings. Crash-recovery case (log exists): rebuild seen from log
    # emissions so any letter that landed during a dark window fires on the
    # next poll instead of being baselined away silently.
    if event_log.exists() and event_log.stat().st_size > 0:
        seen = _seen_from_log(event_log)
    else:
        seen = _scan(letters_dir, letter_glob)

    def _emit(line: str) -> None:
        """Print to stdout AND append to the event log. Stdout for harness
        Monitor live-tail; log for crash-survival and post-hoc replay."""
        print(line)
        sys.stdout.flush()
        try:
            with open(event_log, "a", encoding="utf-8") as f:
                f.write(f"{time.time()}\t{line}\n")
        except OSError:
            # Fail-soft: a write error on the log must not crash the
            # watcher. Stdout still delivers if harness is alive.
            pass

    _emit(
        f"[LETTER-MONITOR-ARMED] watching {letters_dir} for {letter_glob} (recipient={recipient})"
    )

    while True:
        try:
            time.sleep(args.poll_seconds)
            current = _scan(letters_dir, letter_glob)
            new = current - seen
            for name in sorted(new):
                _emit(f"[LETTER] {letters_dir / name}")
            seen = current
        except KeyboardInterrupt:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
