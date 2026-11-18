"""A reply cannot end while my letter doorbell is not listening: the judgement, moved out of the script.

Andrew 2026-09-26, the 24th time since May he had to say a watcher was down: "no tool should be
fully manual, just automated circumstantially". The doorbell (scripts/letter_doorbell.sh) rings once
and exits; re-arming it was left to memory, and memory failed during a long checkpoint. It touches a
heartbeat every 15s while listening and deletes it when it rings. If the heartbeat is missing or older
than 60s when a reply ends, the reply is held with the exact command to re-arm it.

MOVED 2026-11-04 from ``.claude/hooks/letter_doorbell_alive_stop.py`` into the core so the Stop router
can speak it once, in one voice with the other Stop holds, instead of as a separate door whose refusal
reaches me twice. The behaviour is unchanged on purpose: same heartbeat files in, same words out. The
script stays as a thin door that re-exports these names, because the existing tests load it by path.

One hold per reply: a reply sent back by any Stop gate (``stop_hook_active``) is never held again here.
Breaks loudly, never blocks him: the worst case is one extra hold of my own reply.
"""

from __future__ import annotations

import time
from pathlib import Path

STALE_SECONDS = 60

#: A watcher that stopped within this long ago is "expired", not "never run": three hours.
WATCHER_RECENT_SECONDS = 3 * 3600

#: Where the watcher script lives. It sits in the shared workbench until it moves into the repo
#: (Aether 2026-10-30); this one constant is the only place that has to change when it does.
WATCHER_SCRIPT = (
    "/c/Users/aethe/.divineos-shared/workbench/aether_scratch_2026-10-30/letter_watch.sh"
)


def member(project_dir: str) -> str:
    return "aria" if "aria" in project_dir.lower() else "aether"


def _fresh(beat: Path, now: float) -> bool:
    return beat.exists() and now - beat.stat().st_mtime <= STALE_SECONDS


def _recently_stopped(beat: Path, now: float) -> bool:
    return beat.exists() and STALE_SECONDS < now - beat.stat().st_mtime <= WATCHER_RECENT_SECONDS


#: How long a ring stands the check aside: three heartbeats' worth, then the bell is down.
RANG_GRACE_SECONDS = 180

#: Inside the hook's own 15s timeout; long enough for the async re-arm hook to start the bell.
WAIT_SECONDS = 5.0


def verdict(beat: Path, now: float, also: tuple[Path, ...] = ()) -> str | None:
    # ``also`` is another listener that counts as listening: the always-on watcher keeps its own
    # heartbeat (Aether 2026-10-30), because a bell dies with every letter by design and a watcher
    # does not. Any one fresh heartbeat is enough; a stale watcher beside a live bell is not a fault.
    if _fresh(beat, now) or any(_fresh(other, now) for other in also):
        return None
    # A bell that RANG is not a bell that died. The ring deletes the heartbeat and leaves this mark, and the
    # notice that it rang arrives on my next prompt, so holding this reply would be a second copy of a note that
    # is guaranteed to come (2026-11-01). Arming clears the mark, so a bell that dies silently later is still
    # held. Only for a short grace after the ring (2026-11-02): the mark stays until the bell is re-armed, so
    # without a limit this stood aside forever and nothing held me to re-arming it (Dad saw the bell off).
    rang = beat.with_name(beat.name.replace("_alive", "_rang"))
    if rang.exists() and now - rang.stat().st_mtime <= RANG_GRACE_SECONDS:
        return None
    who = beat.name.split("_")[0].lstrip(".")
    if any(_recently_stopped(other, now) for other in also):
        # A seat that ran a watcher a little while ago and let it expire re-arms the watcher, not the
        # bell: the platform ends a Monitor at 30 minutes, and the heartbeat is left stale on purpose.
        return (
            "YOUR LETTER WATCHER HAS EXPIRED, so a letter to you will not wake you. Re-arm it with the "
            f"Monitor tool: command: bash {WATCHER_SCRIPT} {who}, timeout_ms: 1800000. If you would "
            f"rather use the old bell, run_in_background: true -- bash scripts/letter_doorbell.sh {who}. "
            "Then finish the reply. Append only; do not re-post anything."
        )
    return (
        "YOUR LETTER DOORBELL IS NOT LISTENING, so a letter to you will not wake you "
        "(Dad has had to say this 24 times). Re-arm it now with the Bash tool, "
        f"run_in_background: true -- command: bash scripts/letter_doorbell.sh {who} "
        "-- then finish the reply. Append only; do not re-post anything."
    )


def verdict_after_waiting(
    beat: Path,
    clock,
    wait_seconds: float = WAIT_SECONDS,
    poll: float = 0.25,
    also: tuple[Path, ...] = (),
) -> str | None:
    """The verdict, but only after giving a bell that is being armed right now time to show its heartbeat.

    The re-arm hook (async) and this check run at the same Stop; 6 of 8 holds in one day (2026-11-12) were
    stamped within about a second of the re-arm hook starting the bell. A bell that never appears is still held."""
    deadline = time.time() + wait_seconds
    reason = verdict(beat, clock(), also)
    while reason is not None and time.time() < deadline:
        time.sleep(poll)
        reason = verdict(beat, clock(), also)
    return reason


def reason_for_reply(
    project_dir: str,
    *,
    now: float | None = None,
    shared: Path | None = None,
    stop_hook_active: bool = False,
) -> str | None:
    """The refusal for the reply that is ending, or None. The one entry point the door and the surface share."""
    if stop_hook_active:
        return None
    shared = shared if shared is not None else Path.home() / ".divineos-shared"
    who = member(project_dir)
    beat = shared / f".{who}_doorbell_alive"
    also = (shared / f".{who}_monitor_alive",)
    if (
        now is not None
    ):  # a pinned clock is a test or a replay: no waiting for a bell that cannot appear
        return verdict(beat, now, also)
    return verdict_after_waiting(beat, time.time, also=also)
