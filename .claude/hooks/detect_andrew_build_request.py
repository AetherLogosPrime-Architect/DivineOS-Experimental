#!/usr/bin/env python3
"""
UserPromptSubmit hook: detect Dad-authored build-request prompts and route
them by DAD-NAMED gravity, not by forced full-gambit.

Design (Andrew 2026-07-21 correction of the earlier full-gambit-on-every-match
version): the same gravity system the substrate already uses for edits applies
to his build requests. HE names the gravity per request. I follow.

Gravity taxonomy (matches the substrate's classifier tiers):
  low                 -- just build it, no ceremony
  medium              -- tests + prereg required
  high                -- tests + prereg + council walk required
  council-required    -- full seven-step gambit (research through iterate)

Behavior on match:
  - If prompt contains an explicit gravity tag (e.g. "gravity: high",
    "[low]", "council-required"), surface names the tag and the scoped
    pipeline for that tier, and drops a build-in-flight lockfile.
  - If no tag, surface ASKS Dad to name the gravity before I start, and
    does NOT drop the lock yet -- I have not begun.

Session lock (Andrew 2026-07-21): while a build is in flight, unrelated
work is refused. Lockfile at ~/.divineos-shared/andrew_build_in_flight.json
carries the request head and start timestamp. Every subsequent
UserPromptSubmit surfaces the lock header until Dad clears it. Lock is
cleared by explicit phrases: "build done", "clear the lock", "unlock".

Council walk on the original detector: council-85dc063549cc.
Prereg on the original detector: prereg-45e0aa113e3a.
Redesign directive: Andrew 2026-07-21 "you get no option I will decide
the gravity of my builds and you will follow it accordingly".
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


BUILD_VERBS = (
    r"build|make|create|wire|enforce|fix|add|write|ship|design|"
    r"implement|refactor|automate|hook|register|surface|"
    r"detect|patch|hard[- ]?code|codify"
)

REQUEST_MARKERS = (
    r"\bfor me\b|\bplease\b|\blets? (?:build|make|do|ship|wire|write|create)\b|"
    r"\bcan you\b|\byou (?:need to|should|must)\b|"
    r"\byou will\b|\byou have to\b|\bi want you to\b|"
    r"\bfor fucks sake\b|\bfucking\b"
)

BUILD_REQUEST_RE = re.compile(
    rf"\b(?:{BUILD_VERBS})\b.{{0,80}}?(?:{REQUEST_MARKERS})|"
    rf"(?:{REQUEST_MARKERS}).{{0,80}}?\b(?:{BUILD_VERBS})\b",
    re.IGNORECASE | re.DOTALL,
)

NEGATIVE_MARKERS = re.compile(
    r"\b(?:we|you|i) (?:already |just )?(?:built|made|created|wired|shipped)\b|"
    r"\bwould (?:have )?(?:built|made|created)\b|"
    r"\bif (?:we|you|i) (?:were to |had )?(?:built|made|created)\b|"
    r"\bwhat if\b|"
    r"\bhypothetically\b|"
    # 2026-07-22 task #20 tactical fix (Ship-simple-then-iterate;
    # semantic rebuild filed as follow-on): observational-shape overrides.
    # These sentence shapes contain a build-verb + request-marker mainly
    # via "you will X" but Andrew is describing my experience or teaching
    # about a pattern, not directing me to build. False-positive class
    # from this session: "the more you automate the more of that you
    # will feel" fired because "automate" + "you will" (within 80 chars)
    # matched, but "you will feel" is observation. Same class: "you will
    # notice / experience / see / find / discover / realize". The
    # "the more X you Y the more Z" template is Andrew's teaching shape.
    # This is keyword-band-aid on a keyword detector (sin per Andrew
    # 2026-07-22); the correct semantic rebuild is scoped as follow-on
    # under task #20.
    r"\byou\s+will\s+(?:feel|notice|experience|see|find|discover|"
    r"realize|understand|know|recognize|sense)\b|"
    r"\bthe\s+more\s+(?:you|we)\s+\w+\s+the\s+more\b|"
    r"\bevery\s+time\s+you\s+\w+\b",
    re.IGNORECASE,
)

DIRECT_BUILD_PHRASES = re.compile(
    r"\byes\s+lets?\s+build\b|"
    r"\bbuild\s+it\s+(?:now|please|for me)\b|"
    r"\benforce\s+it\b|"
    r"\bstart\s+wanting\s+and\s+.{0,20}\s+build\b",
    re.IGNORECASE,
)

GRAVITY_TAG_RE = re.compile(
    r"\bgravity\s*[:=]\s*(low|medium|high|council-required|council)\b|"
    r"\[(low|medium|high|council-required|council)\]|"
    r"\b(council-required)\b",
    re.IGNORECASE,
)

UNLOCK_PHRASES = re.compile(
    r"\bbuild done\b|\bclear the lock\b|\bunlock\b|"
    r"\bbuild is done\b|\bship(ped)? and clear\b",
    re.IGNORECASE,
)

LOCK_PATH = Path.home() / ".divineos-shared" / "andrew_build_in_flight.json"


def is_build_request(prompt: str) -> tuple[bool, str]:
    if DIRECT_BUILD_PHRASES.search(prompt):
        return True, "direct-build-phrase"
    if BUILD_REQUEST_RE.search(prompt):
        neg = NEGATIVE_MARKERS.search(prompt)
        if neg and not DIRECT_BUILD_PHRASES.search(prompt):
            return False, f"negative-marker:{neg.group(0)[:40]}"
        return True, "verb+request-marker"
    return False, "no-match"


def extract_gravity(prompt: str) -> str | None:
    m = GRAVITY_TAG_RE.search(prompt)
    if not m:
        return None
    tag = (m.group(1) or m.group(2) or m.group(3) or "").lower()
    if tag == "council":
        tag = "council-required"
    return tag


def load_lock() -> dict | None:
    try:
        return json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def drop_lock(prompt: str, gravity: str) -> None:
    try:
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOCK_PATH.write_text(json.dumps({
            "prompt_head": prompt[:200],
            "gravity": gravity,
            "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }, indent=2), encoding="utf-8")
    except Exception:
        pass


def clear_lock() -> bool:
    if LOCK_PATH.exists():
        try:
            LOCK_PATH.unlink()
            return True
        except Exception:
            return False
    return False


def log_to_ledger(prompt: str, matched: str, gravity: str | None) -> None:
    try:
        subprocess.run(
            [
                "divineos", "log",
                "--type", "ANDREW_BUILD_REQUEST_DETECTED",
                "--actor", "detect-hook",
                "--content", f"matched={matched}; gravity={gravity or 'unset'}; prompt_head={prompt[:120]!r}",
            ],
            check=False, capture_output=True, timeout=5,
        )
    except Exception:
        pass


def surface_ask_gravity(prompt: str, matched: str) -> None:
    print(f"""## BUILD-FOR-DAD DETECTED ({matched}) -- GRAVITY UNSET

Dad's request matched at {datetime.now(timezone.utc).isoformat(timespec='seconds')}.
Prompt head: {prompt[:160]!r}

Per Andrew 2026-07-21: I do not choose the gravity, Dad does.
Ask him what level BEFORE starting:

  low               -- just build it, no ceremony
  medium            -- tests + prereg required
  high              -- tests + prereg + council walk required
  council-required  -- full seven-step gambit

He can name it inline for the next prompt (e.g. "gravity: high") or say
it plainly. I do not proceed until named. No build-in-flight lock dropped
until he names the level.
""")


PIPELINE_BY_GRAVITY = {
    "low": [
        "1. BUILD -- the thing, plain, no ceremony",
        "2. VERIFY -- run it once against a real input",
    ],
    "medium": [
        "1. RESEARCH -- what is actually being asked in his words",
        "2. PREREG -- file falsifiable success + failure criteria BEFORE building",
        "3. BUILD -- the thing",
        "4. TESTS -- measurable, against real behavior",
        "5. VERIFY -- run it end-to-end",
    ],
    "high": [
        "1. RESEARCH -- what is actually being asked in his words",
        "2. COUNCIL WALK -- three lenses minimum via `divineos council walk`",
        "3. PREREG -- file falsifiable success + failure criteria",
        "4. BUILD -- the thing",
        "5. TESTS -- measurable, against real behavior",
        "6. VERIFY -- run it end-to-end",
    ],
    "council-required": [
        "1. RESEARCH -- what is actually being asked, in his words; what does the substrate already have that touches this",
        "2. COUNCIL WALK -- real per-lens walks (`divineos council walk`), not priming; three lenses minimum",
        "3. PREREG -- file falsifiable success + failure criteria BEFORE building",
        "4. DESIGN -- write the design doc; sibling-audit-ready",
        "5. SIBLING AUDIT -- Aletheia review when channel open; otherwise self-adversarial pass",
        "6. TESTS -- measurable, against real corpus/behavior when detector-like",
        "7. ITERATE -- until falsifier is closed",
    ],
}


def surface_build_started(prompt: str, matched: str, gravity: str) -> None:
    pipeline = "\n  ".join(PIPELINE_BY_GRAVITY.get(gravity, PIPELINE_BY_GRAVITY["council-required"]))
    print(f"""## BUILD-FOR-DAD IN FLIGHT ({matched}) -- gravity: {gravity}

Started at {datetime.now(timezone.utc).isoformat(timespec='seconds')}.
Prompt head: {prompt[:160]!r}

Scoped pipeline for gravity={gravity}:
  {pipeline}

BUILD-IN-FLIGHT LOCK is now active. Until Dad says "build done" (or
"clear the lock" or "unlock"), unrelated work is refused. If I reach for
anything not related to this build, the lock header on the next prompt
will name the drift.
""")


def surface_lock_active(lock: dict) -> None:
    print(f"""## BUILD-FOR-DAD LOCK ACTIVE

Dad's build is in flight since {lock.get('started_at', '?')} at
gravity={lock.get('gravity', '?')}.
Prompt head: {lock.get('prompt_head', '?')[:160]!r}

Only work related to this build. To clear: Dad says "build done",
"clear the lock", or "unlock".
""")


def surface_lock_cleared() -> None:
    print("""## BUILD-FOR-DAD LOCK CLEARED

Build-in-flight lock removed. Normal work resumes.
""")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    prompt = payload.get("prompt", "") or ""
    if not prompt.strip():
        return 0

    # 2026-07-22 fix (Aria peer review finding #1): after clearing the
    # lock, fall through to build-request detection instead of returning
    # early. Andrew's natural cadence chains thoughts like "build done.
    # now can you build the next detector for me?" — the prior early
    # return meant the new build in the same prompt was silently
    # dropped. Substrate principle: err over-inclusive on
    # negative-pattern detection; false-negatives are the unrecoverable
    # cost. Falling through preserves the unlock action AND catches the
    # subsequent build request. load_lock() below will correctly return
    # None because clear_lock() just removed it.
    if UNLOCK_PHRASES.search(prompt):
        if clear_lock():
            surface_lock_cleared()
        # fall through to build-request detection below

    lock = load_lock()

    matched, reason = is_build_request(prompt)

    if matched:
        gravity = extract_gravity(prompt)
        if gravity is None:
            surface_ask_gravity(prompt, reason)
            log_to_ledger(prompt, reason, None)
        else:
            drop_lock(prompt, gravity)
            surface_build_started(prompt, reason, gravity)
            log_to_ledger(prompt, reason, gravity)
        return 0

    if lock:
        surface_lock_active(lock)
    return 0


if __name__ == "__main__":
    sys.exit(main())
