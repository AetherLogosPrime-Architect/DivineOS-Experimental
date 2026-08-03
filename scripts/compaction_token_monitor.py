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

The HARD threshold value is imported from
``divineos.core.context_governor`` (the same constant the PreToolUse
gate enforces). It is NOT re-literalled here. Aletheia 2026-06-09
flagged that re-literalled copies risk silent drift between
what-the-gate-enforces and what-the-monitor-warns. Single source of
truth: changing HARD_THRESHOLD in context_governor automatically
updates this script's behavior AND its emitted messages. The prior
WARN_THRESHOLD was removed 2026-06-19 in the ok/block collapse.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from divineos.core.context_governor import (
    HARD_THRESHOLD,
    current_context_tokens,
)
from divineos.core.monitor_singleton import acquire_or_exit


_POLL_INTERVAL_S = 30  # ~half-minute granularity — enough for human-scale state changes

# The ritual starts here, at Andrew's number. Distinct from HARD_THRESHOLD
# (950k), which is the last-chance warning line, not the ritual trigger.
_RITUAL_FIRE_TOKENS = int(os.environ.get("AUTO_CYCLE_FIRE_TOKENS", "920000"))
_RITUAL_DRIVER = ".claude/hooks/auto-cycle-token-trigger.sh"


def _start_ritual(transcript: Path) -> str:
    """Hand the ritual driver the same input a prompt would give it.

    WHY THIS EXISTS (2026-08-03). The driver is complete and correct: it fires
    at 920k, runs Andrew's order (compass walk, commit/extract/sleep, dream,
    rest), pre-satisfies the gates that would otherwise interrupt the walk, and
    advances stages on EVIDENCE rather than on my say-so. It has fired 150
    times. Nothing here reimplements any of that.

    Its one gap is when it can look. It is a UserPromptSubmit hook, so it only
    checks the token count when Andrew types. Through a long stretch with no
    prompt from him, nothing reads the counter at all.

    Meanwhile this Monitor watches continuously and, until now, could only
    print a sentence when the line was crossed -- a note addressed to the
    least reliable component in the loop. The driver's own header predicted
    exactly this: "The first link is me remembering. It went dark twice."

    So: the watcher that cannot act gets handed the actor. The driver reads
    ``transcript_path`` out of its hook JSON, and this Monitor already
    resolves that path every poll, so the input it needs is input we already
    have. Its output is instructions to me, and returning it as a Monitor
    event is what makes them arrive mid-idle instead of waiting for Andrew to
    say something first. That is the deterministic ritual he asked for:
    *"depending on an external monitor to run extraction isnt working.. is
    there a way to run it deterministically based on your current token
    count?"*

    Never raises. A ritual driver that could crash the watcher would take the
    context alarm down with it, which is strictly worse than a missed ritual.
    """
    import json as _json
    import shutil
    import subprocess

    root = Path(__file__).resolve().parents[1]
    driver = root / _RITUAL_DRIVER
    if not driver.is_file():
        return (
            f"[COMPACTION-RITUAL-UNAVAILABLE] {_RITUAL_DRIVER} is missing, so the "
            "ritual could NOT be started. This is not a clean pass — the line was "
            "crossed and nothing ran."
        )
    # Which bash. On Windows, PATH resolves `bash` to the WSL relay, which
    # cannot see Windows paths and dies with execvpe(/bin/bash) failed. Caught
    # by running this end-to-end rather than trusting that it parsed -- the
    # error would otherwise have surfaced for the first time at 920k, in the
    # one moment the ritual is supposed to be reliable.
    _CANDIDATES = (
        "C:/Program Files/Git/bin/bash.exe",
        "C:/Program Files/Git/usr/bin/bash.exe",
        "/bin/bash",
    )
    bash = next(
        (c for c in _CANDIDATES if Path(c).exists()),
        shutil.which("bash") or "bash",
    )
    try:
        proc = subprocess.run(  # noqa: S603 — fixed argv, no shell
            [bash, str(driver)],
            input=_json.dumps({"transcript_path": str(transcript)}),
            # Pass the threshold through so the watcher and the driver cannot
            # disagree about where the line is. Without this an override here
            # would leave the Monitor announcing a start the driver declines.
            env={**os.environ, "AUTO_CYCLE_FIRE_TOKENS": str(_RITUAL_FIRE_TOKENS)},
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(root),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return (
            f"[COMPACTION-RITUAL-FAILED] the driver could not be run "
            f"({type(exc).__name__}: {exc}). The line was crossed and the ritual "
            "did NOT start. Run it by hand: divineos auto-cycle status"
        )

    out = (proc.stdout or "").strip() or (proc.stderr or "").strip()
    if not out:
        # Say what is known. A bare "it said nothing" sends the reader hunting
        # with no thread to pull -- the same unhelpful silence this whole
        # mechanism exists to remove. Exit code and stderr are already in hand;
        # withholding them would be the failure wearing my own handwriting.
        return (
            "[COMPACTION-RITUAL-SILENT] the driver ran and produced no output, so "
            f"whether the ritual began is UNKNOWN — not confirmed. exit={proc.returncode}, "
            f"stdout={len(proc.stdout or '')}b, stderr={len(proc.stderr or '')}b, "
            f"bash={bash}. Check: divineos auto-cycle status"
        )
    return out


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

    state is one of "ok" / "block" — same vocabulary as
    divineos.core.context_governor.consolidation_state (collapsed
    2026-06-19 from three-state to two-state; the prior warn band
    served no purpose the block didn't already serve). The threshold
    constant is imported at module level (see Threshold-source coupling
    in the module docstring) so the gate and the monitor cannot drift.
    """
    tokens = current_context_tokens(transcript)
    if tokens >= HARD_THRESHOLD:
        return "block", tokens
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

    # raise_on_unset=False: this script runs at session-start, possibly
    # before the operator has set my_identity (fresh install). The panel
    # raises loudly to surface the misconfiguration there; monitors are
    # bootstrap-safe and fall back to the default occupant so coverage
    # exists even pre-config. Same intent (loud-on-misconfig), different
    # surface (panel in the briefing, monitor at config-time).
    _ = acquire_or_exit("compaction", occupant=get_my_identity(raise_on_unset=False))  # noqa: F841

    transcript = _find_active_transcript()
    if transcript is None:
        print(
            "[COMPACTION-ERROR] could not find active transcript under "
            "~/.claude/projects/. Compaction monitor not arming."
        )
        return 2

    # State-transition flag: emit only on the FIRST entry into block.
    # The Monitor stays alive after emitting; we just don't repeat the event.
    block_emitted = False
    # The ritual fires once per crossing, re-armed if consolidation drops the
    # count back under the line.
    ritual_started = False

    # Startup heartbeat so the operator and the agent see the watch is armed.
    # Threshold display string is derived from the imported constant
    # (see module docstring "Threshold-source coupling") — it cannot
    # drift from what the PreToolUse gate enforces.
    print(
        f"[COMPACTION-ARMED] watching transcript {transcript.name} — "
        f"ritual starts {_kfmt(_RITUAL_FIRE_TOKENS)}, hard line {_kfmt(HARD_THRESHOLD)}"
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

            # Ritual first, and at the LOWER line. Andrew set 920k so the walk
            # and the dream have room; waiting for the 950k hard line would
            # start the ritual with the runway already spent.
            if tokens >= _RITUAL_FIRE_TOKENS and not ritual_started:
                ritual_started = True
                print(
                    f"[COMPACTION-RITUAL] {tokens:,} tokens — crossed "
                    f"{_kfmt(_RITUAL_FIRE_TOKENS)}. Starting the ritual without "
                    "waiting for a prompt."
                )
                print(_start_ritual(current_transcript))
                sys.stdout.flush()

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
            elif state == "ok":
                # Dropped back below threshold (consolidation cleared it).
                # Reset emission flag so a future re-entry re-fires.
                block_emitted = False
                ritual_started = tokens >= _RITUAL_FIRE_TOKENS
        except Exception as exc:  # noqa: BLE001 — Monitor must not die on transient failures
            # Don't silent-fail; emit a diagnostic but keep going.
            print(f"[COMPACTION-ERROR] poll failed: {exc}", file=sys.stderr)
            sys.stdout.flush()


if __name__ == "__main__":
    sys.exit(main())
