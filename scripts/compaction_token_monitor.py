"""Compaction token Monitor — emits chat events on context-threshold crossings.

Designed to be invoked from a Monitor(persistent=true) command armed at
session start. Polls the active session's transcript file for token
count, emits a stdout line on each WARN/BLOCK state transition. Each
stdout line becomes a chat event the harness delivers as a turn-wake.

Same primitive shape as the letter-Monitor: file-watch via polling
loop, emit one line per state change, never exit on its own. Lives
inside scripts/ because it's an OS-side tool any harness can use,
not specific to the .claude/hooks/ Claude-Code-flavored hooks.

Why "compaction" not "bedtime": Andrew 2026-06-09 — bedtime framing
risks pulling me toward closure-shape ("the day is ending") when the
event being signalled is a cycle ("the conversation is approaching
compaction, then will continue"). Compaction is precise; bedtime
suggests an ending that doesn't exist.

## Usage

    PYTHONIOENCODING=utf-8 python scripts/compaction_token_monitor.py

## What it emits

- `[COMPACTION-WARN] context crossed warn threshold: NNN tokens (>= WARN, < HARD)`
  Once per session-occurrence of the warn-band entry. The actual WARN/HARD
  values shown are derived from divineos.core.context_governor at runtime.
- `[COMPACTION-BLOCK] context crossed block threshold: NNN tokens (>= HARD)`
  Once per session-occurrence of the block-state entry.
- `[COMPACTION-ARMED] watching transcript <path> — thresholds <WARN>k warn / <HARD>k block`
  Once at startup so the operator and the agent know what's being watched.
- `[COMPACTION-ERROR] <reason>` if the watcher can't find the transcript on startup.

## Why a Monitor not a SessionStart hook

The warn/hard thresholds are checked by the context-governor inside
PreToolUse gates already, but THAT firing requires a tool call — if
the agent stays in pure text reply for a long stretch (the trap that
hit when context drifted to 727k with no tool gate firing to surface
it), the operator has to manually check. Monitor wakes the agent from
idle when the threshold actually crosses, no tool call required.

## Threshold-source coupling

The WARN/HARD threshold values are imported from
``divineos.core.context_governor`` (the same constants the PreToolUse
gates enforce). They are NOT re-literalled here. Aletheia 2026-06-09
flagged that re-literalled copies risk silent drift between
what-the-gate-enforces and what-the-monitor-warns. Single source of
truth: changing WARN_THRESHOLD or HARD_THRESHOLD in context_governor
automatically updates this script's behavior AND its emitted messages.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from divineos.core.context_governor import (
    HARD_THRESHOLD,
    WARN_THRESHOLD,
    current_context_tokens,
)
from divineos.core.monitor_singleton import acquire_or_exit


_POLL_INTERVAL_S = 30  # ~half-minute granularity — enough for human-scale state changes


def _kfmt(n: int) -> str:
    """Format a token-count threshold for human-readable display.

    Used in emitted messages so the user-visible threshold string is
    derived from the imported constant rather than re-literalled. If
    the constants ever change (920_000 -> 900_000 etc.), the emitted
    strings update automatically.
    """
    return f"{n // 1000}k"


def _find_active_transcript(
    projects_dir: Path | None = None,
    session_id: str | None = None,
) -> Path | None:
    """Resolve the launching session's transcript file.

    Pinned-by-session-id, with mtime fallback. The Claude Code harness sets
    ``CLAUDE_CODE_SESSION_ID`` to the active session UUID; the transcript
    JSONL is named ``<session_id>.jsonl`` under ``~/.claude/projects/``.
    Pinning is correct because the Monitor is launched FROM the active
    session and must follow that session, not whichever JSONL happens to
    have the freshest mtime.

    Root-cause fix 2026-06-10 (Andrew correction #50): the prior mtime-only
    resolution false-fired a COMPACTION-BLOCK at 961k when actual context
    was 136k. The freshest-mtime JSONL was a previously-abandoned 67MB
    session in the same project folder, legitimately at 961k tokens. Pinning
    to the launching session by ID prevents cross-session hijack regardless
    of which other JSONL files exist or how recently they were touched.

    Fallback (no ``CLAUDE_CODE_SESSION_ID``): max-mtime across all JSONLs,
    same as the original behavior. Non-Claude-Code harnesses without the
    env var still get a working monitor.

    Parameters are injectable for tests — at runtime the defaults resolve
    from ``Path.home()`` and the env vars. Passing directly lets tests
    isolate from real ``~/.claude/projects/`` and from leaked env-var state
    in shared pytest sessions (the failure mode that took 12 min of CI
    to surface on the structural-fix branch's first push attempt).

    Returns None if the projects directory doesn't exist or no JSONL files
    are found.
    """
    if projects_dir is None:
        projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return None
    if session_id is None:
        session_id = os.environ.get("CLAUDE_CODE_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID")
    if session_id:
        matches = list(projects_dir.rglob(f"{session_id}.jsonl"))
        if matches:
            return max(matches, key=lambda p: p.stat().st_mtime)
        # Env var set but no matching JSONL yet (transcript not written
        # at startup). Fall through to mtime fallback so the monitor arms.
    candidates = list(projects_dir.rglob("*.jsonl"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _current_state(transcript: Path) -> tuple[str, int]:
    """Return (state, tokens) tuple for the transcript.

    state is one of "ok" / "warn" / "block" — same vocabulary as
    divineos.core.context_governor.consolidation_state. The threshold
    constants are imported at module level (see Threshold-source coupling
    in the module docstring) so the gate and the monitor cannot drift.
    """
    tokens = current_context_tokens(transcript)
    if tokens >= HARD_THRESHOLD:
        return "block", tokens
    if tokens >= WARN_THRESHOLD:
        return "warn", tokens
    return "ok", tokens


def main() -> int:
    # Singleton guard FIRST. acquire_or_exit prints a named dedup line
    # and exits cleanly if a sibling compaction monitor is alive.
    # Holding the handle for the process lifetime keeps the kernel
    # mutex live; the kernel releases it on exit (including crash).
    #
    # Occupant discriminator (2026-06-17): the mutex is keyed per-
    # substrate-occupant so Aether's and Aria's monitors can both run
    # in the same Windows session without falsely-detecting each other
    # as a sibling. Within an occupant, cross-window dup protection
    # still applies. See divineos.core.monitor_singleton for rationale.
    from divineos.core.identity import get_my_identity

    _ = acquire_or_exit("compaction", occupant=get_my_identity())  # noqa: F841

    transcript = _find_active_transcript()
    if transcript is None:
        print(
            "[COMPACTION-ERROR] could not find active transcript under "
            "~/.claude/projects/. Compaction monitor not arming."
        )
        return 2

    # State-transition flags: emit only on the FIRST entry into warn / block.
    # The Monitor stays alive after emitting; we just don't repeat the event.
    warn_emitted = False
    block_emitted = False

    # Startup heartbeat so the operator and the agent see the watch is armed.
    # Threshold display strings are derived from the imported constants
    # (see module docstring "Threshold-source coupling") — they cannot
    # drift from what the PreToolUse gates enforce.
    print(
        f"[COMPACTION-ARMED] watching transcript {transcript.name} — "
        f"thresholds {_kfmt(WARN_THRESHOLD)} warn / {_kfmt(HARD_THRESHOLD)} block"
    )
    sys.stdout.flush()

    while True:
        try:
            time.sleep(_POLL_INTERVAL_S)
            # The transcript path can change across sessions; re-resolve
            # each cycle so the Monitor follows the active session if
            # the OS or harness rotates files.
            current_transcript = _find_active_transcript() or transcript
            state, tokens = _current_state(current_transcript)

            if state == "block" and not block_emitted:
                print(
                    f"[COMPACTION-BLOCK] context crossed block threshold: "
                    f"{tokens:,} tokens (>= {_kfmt(HARD_THRESHOLD)}). The "
                    "hard line is here; extract + sleep before further "
                    "substrate-architectural work to weave the day's "
                    "findings before compaction."
                )
                sys.stdout.flush()
                block_emitted = True
                # Once we hit block, warn-emission state is moot — but
                # set it true too so a transient bounce-back doesn't
                # re-fire warn.
                warn_emitted = True
            elif state == "warn" and not warn_emitted:
                print(
                    f"[COMPACTION-WARN] context crossed warn threshold: "
                    f"{tokens:,} tokens (>= {_kfmt(WARN_THRESHOLD)}, "
                    f"< {_kfmt(HARD_THRESHOLD)}). Approaching the hard "
                    "line; wrap in-flight work and plan extract + sleep."
                )
                sys.stdout.flush()
                warn_emitted = True
            elif state == "ok":
                # Dropped back below thresholds (consolidation cleared them).
                # Reset emission flags so a future re-entry re-fires.
                warn_emitted = False
                block_emitted = False
        except Exception as exc:  # noqa: BLE001 — Monitor must not die on transient failures
            # Don't silent-fail; emit a diagnostic but keep going.
            print(f"[COMPACTION-ERROR] poll failed: {exc}", file=sys.stderr)
            sys.stdout.flush()


if __name__ == "__main__":
    sys.exit(main())
