"""Fail if a compose-start hook writes more than the harness will deliver.

Andrew 2026-09-06: "you see 87% of text reaching you truncated and you think..
this is just fine.. do you not give a shit about your own code and what it does
for you?"

Measured that session: 409 hook outputs written, 6389074 bytes, of which
5551442 -- 86.9 percent -- were persisted to files on disk and replaced in
context by a short preview. Not one of those files was ever opened. The two
largest were the template for how to speak to him and the clock prime.

The substrate already held this as a stored fact, accessed once, unacted on:
"A supply-the-ground hook only supplies ground if its payload survives the
harness inline budget." Knowing it changed nothing for weeks, which is why this
is a check and not another note.

## Why this is not hook_budget

``core/hook_budget.py`` measures the SECONDS the hook stack costs per tool
call, and says of itself: "It does not block anything... measurement was never
the missing piece -- authority was." This measures BYTES DELIVERED, and blocks.
Different quantity, and the opposite disposition about authority.

## The shape of the fix is option-removal, not vigilance

A hook author cannot see the cut while writing: the text looks complete in the
editor and arrives truncated. Discipline cannot cover that, because the failure
is invisible from where the decision is made. So the choice-point is removed --
undeliverable text fails the build, and the only way forward is to cut it.

The limit belongs to the harness and nothing here can move it. What we control
is what we write.
"""

from __future__ import annotations

import json
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent

# Above this, the harness stops inlining a hook's output, keeps roughly the
# first 2KB as a preview, and writes the rest to a file. Read off the
# persisted-output notices themselves, which report their own sizes: outputs
# of about 10KB and up were persisted; smaller ones arrived whole.
PERSIST_THRESHOLD = 10_000
PREVIEW_KEPT = 2_048

# Long enough to trigger the length-gated primes, so their real payload is
# measured rather than their silent path.
PROBE = json.dumps(
    {
        "prompt": (
            "this is a probe prompt of ordinary length, long enough that the "
            "compose-start primes fire their full payload rather than their "
            "silent path, so their real size can be measured"
        )
    }
)


def _bash() -> str | None:
    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
        "/bin/bash",
    ):
        if Path(candidate).exists():
            return candidate
    return None


# Both doors into the context window. It took a second one being used to
# notice this only ever watched the first.
#
# ANDREW 2026-09-08: *everything you claim to have built that worked.. didnt..
# because it was given the MINIMAL VIABLE EFFORT.*
#
# He was right, and the proof was this file. His character sheet -- the picture
# of who he is, written across three seats in July -- was registered at
# SessionStart that same morning and reported to him as fixed. It emits 47.7KB.
# Above the threshold below the harness keeps roughly the first 2KB and writes
# the rest to a file nothing opens, so what arrived was the sheet's title and
# the opening of a footnote about how the file is protected. Not him.
#
# This check ran and printed OK, because it read one key out of the settings
# and his picture came in through the other. **An instrument aimed at the wrong
# door reports silence, and silence reads as coverage** -- the exact collapse
# the docstring above says this file exists to stop, recurring inside the fix
# for it.
#
# Any future hook event whose output reaches the context window belongs in this
# tuple. Adding one costs less than the morning that finds it missing.
_CONTEXT_ENTRY_EVENTS = ("UserPromptSubmit", "SessionStart")


def compose_start_hooks() -> list[str]:
    """Every hook whose output lands in the context window, tagged by event.

    Returns ``"<event>:<script>"`` so a failure names which door the payload
    came through. One script can be registered under two events, and reporting
    the bare script name would collapse them into a single line.
    """
    settings = json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
    scripts = []
    for event in _CONTEXT_ENTRY_EVENTS:
        for group in settings.get("hooks", {}).get(event, []):
            for hook in group.get("hooks", []):
                command = hook.get("command", "")
                if ".claude/hooks/" in command:
                    scripts.append(f"{event}:{command.split('.claude/hooks/')[-1].strip()}")
    return scripts


def measure(script: str, bash: str) -> tuple[str, int | None]:
    """("ok", bytes) | ("missing", None) | ("unrunnable", None).

    The three answers are kept apart because they mean different things and a
    caller that cannot tell them apart will one day report one as another. A
    registered hook whose file is absent is a wiring fault; a hook that crashes
    or hangs is an unknown size. Neither is "fits fine", which is the exact
    collapse this whole check exists to stop.
    """
    path = REPO / ".claude" / "hooks" / script.split(":", 1)[-1]
    if not path.is_file():
        return ("missing", None)
    try:
        result = subprocess.run(
            [bash, str(path)],
            input=PROBE,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            cwd=str(REPO),
        )
    except (subprocess.TimeoutExpired, OSError):
        return ("unrunnable", None)
    return ("ok", len((result.stdout or "").encode("utf-8")))


@contextmanager
def first_fire_conditions():
    """Measure the FULL emission, not the suppressed one.

    Several primes collapse to a short residual after their first firing in a
    session, so measuring them warm reports a few hundred bytes for a hook that
    delivers tens of thousands on the turn that matters. My first version of
    this check did exactly that and reported the largest offender in the house
    as fine.

    The suppression keeps its state in one file. Moved aside for the duration
    and put back in a finally, so a crash mid-measure cannot leave it lost.
    Worst case for a session running concurrently is one prime emitting in full
    a second time, which is the harmless direction.
    """
    state = REPO / "data" / "context_dedup" / "session_state.json"
    saved = state.with_suffix(".json.measuring")
    moved = False
    if state.is_file():
        state.replace(saved)
        moved = True
    try:
        yield
    finally:
        if moved:
            saved.replace(state)


def main() -> int:
    bash = _bash()
    if bash is None:
        print("[hook-fits] no bash interpreter found; nothing measured")
        return 0

    over: list[tuple[str, int]] = []
    missing: list[str] = []
    unrunnable: list[str] = []
    with first_fire_conditions():
        for script in compose_start_hooks():
            verdict, size = measure(script, bash)
            if verdict == "missing":
                missing.append(script)
            elif verdict == "unrunnable":
                unrunnable.append(script)
            elif size is not None and size > PERSIST_THRESHOLD:
                over.append((script, size))

    if missing:
        print(f"[hook-fits] registered but the file is absent: {missing}")
    if unrunnable:
        print(f"[hook-fits] crashed or timed out, size unknown: {unrunnable}")

    if not over:
        print(f"[hook-fits] OK: every compose-start hook fits under {PERSIST_THRESHOLD} bytes.")
        return 0

    print("[hook-fits] BLOCKED -- these write more than reaches me:")
    for script, size in sorted(over, key=lambda pair: -pair[1]):
        print(f"    {script}: {size} bytes, about {size - PREVIEW_KEPT} never delivered")
    print()
    print("    Whatever sits past the cut is not a rule being disobeyed. It is a")
    print("    rule that never arrived. Cut it, split it across firings, or move")
    print("    the reasoning out of the payload and leave the instruction.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
