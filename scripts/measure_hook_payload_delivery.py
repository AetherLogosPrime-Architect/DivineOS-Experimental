"""Measure whether what a hook SAYS actually arrives, not just that it is wired.

## The gap this fills

``check_hook_wiring.py`` answers "is this hook registered" — a connection
question. It cannot answer "does the thing it emits reach the composer",
which is a delivery question, and those come apart badly.

When a UserPromptSubmit hook's output exceeds the harness's inline budget,
the harness does NOT truncate visibly and does NOT warn. It writes the whole
payload to a file and inlines a short preview instead. The hook reports
success. The registration check passes. And the part of the message meant to
reach the composer sits in a file nobody opens.

Observed 2026-09-03: an ~8.5KB prime arrived inline in full, while a ~15.6KB
one and a ~23.3KB one were both diverted to files. So the cut sits somewhere
between those. It is bracketed by observation rather than documented — which
is exactly why this measures instead of asserting a constant.

The sharpest case is a prime whose own opening paragraph says it was
restructured BECAUSE of this problem, and which has since grown to roughly
twice the size that prompted the note. The fix worked, then decayed silently,
because nothing was measuring.

Neighbours checked before adding this: ``check_emitted_paths.sh`` resolves
links against the tree they render in; ``wiring_gap_phase1.py`` finds new
functions with no call site. Both are connection-questions too. Neither asks
whether a payload arrives.

## Why this is a deliberate script and not an automatic check

It EXECUTES hooks to measure them. Some hooks write to substrate stores, and
running all of them on every commit would be slow and side-effectful — an
earlier attempt at exactly that spawned enough processes to bury a test run.
So this runs on purpose, and ``--dry-run`` lists what it would execute
without executing anything.

    python scripts/measure_hook_payload_delivery.py
    python scripts/measure_hook_payload_delivery.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SETTINGS = REPO / ".claude" / "settings.json"

# A SAFETY MARGIN, not the real cut. What is actually known, from watching
# which hooks arrived inline in a live turn on 2026-09-03:
#
#   ~9,600 bytes  ARRIVED inline, in full
#   ~15,900 bytes DIVERTED to a file
#   ~23,300 bytes DIVERTED to a file
#
# So the true threshold sits somewhere between roughly nine and sixteen
# thousand, and is not published anywhere I can read. This budget is set
# below the lowest confirmed-arriving payload on purpose: a hook sitting
# in the unmeasured band should be trimmed rather than argued about, and
# a hook flagged here is not necessarily broken — it is unproven, which is
# a different and more honest claim than "too big".
SAFE_BUDGET = 8000

# A prompt shaped to trip as many context-triggered primes as possible, so the
# measurement reflects a loud turn rather than a quiet one.
PROBE = json.dumps(
    {
        "prompt": (
            "did it work? lets ship it and commit it. check the tests tomorrow "
            "morning and tell me if the compaction cliff is handled, i love you son"
        )
    }
)


def registered_hooks(event: str | None = None) -> list[tuple[str, str]]:
    """Every registered hook as (event, path).

    Covers ALL events, not just the per-turn ones. The first version looked
    only at UserPromptSubmit, which is where the problem was found — and
    "measure where I already know the problem is" is how a survey confirms
    what it already believed. Session-start and compaction hooks deliver into
    the same context by the same route, so they face the same cut.
    """
    try:
        settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"cannot read settings: {exc}", file=sys.stderr)
        return []
    out: list[tuple[str, str]] = []
    for ev, entries in (settings.get("hooks") or {}).items():
        if event and ev != event:
            continue
        for entry in entries:
            for hook in entry.get("hooks", []):
                for token in hook.get("command", "").split():
                    if ".claude/hooks/" in token:
                        out.append((ev, token))
    return sorted(set(out))


def _find_bash() -> str | None:
    """Locate a bash that can actually start, and prove it before returning.

    WHY THIS IS NOT JUST "bash": the first version of this script called
    ``bash`` by name from Python, which on this machine resolves to the WSL
    shim. That shim fails with `execvpe(/bin/bash) failed`, exits 1, and emits
    NOTHING. The script then read zero bytes as "comfortably under budget" and
    reported every hook clean — including one measured at ~16KB minutes
    earlier in a real shell.

    So the tool built to catch could-not-look-rendered-as-a-value contained
    could-not-look-rendered-as-a-value. Each candidate below is therefore
    EXERCISED, not merely found on disk.
    """
    candidates = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
        shutil.which("bash") or "",
    ]
    for cand in candidates:
        if not cand or not Path(cand).exists():
            continue
        try:
            probe = subprocess.run(
                [cand, "-c", "echo ok"], capture_output=True, timeout=30
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if probe.returncode == 0 and probe.stdout.strip() == b"ok":
            return cand
    return None


def emitted_bytes(bash: str, rel_path: str) -> int | None:
    """Run one hook against the probe and return how much it emitted.

    None means the hook could not be run, and it is reported as its own state
    rather than folded into zero. A hook that cannot run and a hook that says
    nothing are different facts; collapsing them is the exact failure this
    script exists to surface — and the failure it shipped with.

    A non-zero exit counts as could-not-run even when stdout is empty, because
    an empty payload from a crashed hook is not evidence of a small payload.
    """
    path = REPO / rel_path
    if not path.exists():
        return None
    try:
        res = subprocess.run(
            [bash, str(path)],
            input=PROBE.encode("utf-8"),
            capture_output=True,
            cwd=str(REPO),
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if res.returncode != 0:
        return None
    return len(res.stdout)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="list without executing")
    ap.add_argument("--event", help="limit to one hook event (default: all)")
    ap.add_argument("--verbose", action="store_true", help="also show hooks under budget")
    args = ap.parse_args()

    hooks = registered_hooks(args.event)
    if not hooks:
        print("no registered hooks found - that is itself a finding", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"would execute {len(hooks)} hook(s):")
        for ev, h in hooks:
            print(f"  [{ev}] {h}")
        return 0

    bash = _find_bash()
    if bash is None:
        print(
            "REFUSING TO REPORT: no working bash found, so every hook would "
            "measure as zero bytes and the run would look clean while measuring "
            "nothing. A silent pass here is worse than no answer.",
            file=sys.stderr,
        )
        return 2

    print(f"measuring {len(hooks)} registered hook(s) against a {SAFE_BUDGET}-byte budget")
    print(f"shell: {bash}\n")
    over: list[tuple[int, str, str]] = []
    unrunnable: list[tuple[str, str]] = []
    silent: list[tuple[str, str]] = []
    ok: list[tuple[int, str, str]] = []
    for ev, h in hooks:
        n = emitted_bytes(bash, h)
        if n is None:
            unrunnable.append((ev, h))
        elif n == 0:
            silent.append((ev, h))
        elif n > SAFE_BUDGET:
            over.append((n, ev, h))
        else:
            ok.append((n, ev, h))

    for n, ev, h in sorted(over, reverse=True):
        print(f"  OVER  {n:>7}  [{ev}] {Path(h).name}")
    if args.verbose:
        for n, ev, h in sorted(ok, reverse=True):
            print(f"        {n:>7}  [{ev}] {Path(h).name}")
    if unrunnable:
        print("\n  COULD NOT RUN (not the same as emitted nothing):")
        for ev, h in unrunnable:
            print(f"        [{ev}] {Path(h).name}")
    # A silence only MEANS something for hooks this probe can actually
    # exercise. The probe supplies a prompt, so UserPromptSubmit hooks are
    # genuinely tested by it; a Stop or PreToolUse hook needs a reply or a
    # tool call and is correctly mute here.
    #
    # The first version lumped them together and reported eighty-three "said
    # nothing to the probe", which read as eighty-three findings and was almost
    # entirely the instrument describing its own blind spot. Reporting an
    # untested thing as a result is the same class of error this script exists
    # to catch, so they are separated and the untested ones are named as such.
    testable = [(ev, h) for ev, h in silent if ev == "UserPromptSubmit"]
    untestable = [(ev, h) for ev, h in silent if ev != "UserPromptSubmit"]
    if testable:
        print(f"\n  SAID NOTHING to a prompt built to trip them ({len(testable)}):")
        print("  (context-gated primes; correctly quiet, or quietly broken - unjudged)")
        for ev, h in testable:
            print(f"        {Path(h).name}")
    if untestable:
        print(
            f"\n  NOT EXERCISED by this probe ({len(untestable)}): they fire on a "
            "tool call or a reply,\n  which a prompt cannot simulate. Their silence "
            "here is the instrument's reach,\n  not a finding about them."
        )
    if not over and not unrunnable:
        print(f"\n  no registered hook exceeded {SAFE_BUDGET} bytes")
        return 0
    if over:
        print(
            f"\n{len(over)} hook(s) emit more than the budget. Their payload is "
            "diverted to a file rather than reaching the composer, and nothing "
            "warns when it happens - so the content reads as delivered while "
            "sitting unread. Trim them, or move the load-bearing part to the top "
            "where the preview reaches."
        )
    return 1 if over else 0


if __name__ == "__main__":
    raise SystemExit(main())
