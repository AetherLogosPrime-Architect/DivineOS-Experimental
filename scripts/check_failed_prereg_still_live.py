#!/usr/bin/env python3
"""Which mechanisms with a FALSIFIED claim are still running?

WHY THIS EXISTS. Andrew 2026-08-25, one level past the fake-green audit: "of
those tests that fail when broken, does the code actually do what it claims to
do? that is a bigger question, as a magic number generator would fit that bill
.. it would fail if broken and pass if working while doing nothing even
remotely useful."

A test suite can only check code against its own specification. It cannot ask
whether the specification was worth meeting. This substrate already has an
instrument for that question -- the pre-registration store, where a mechanism
states its claim, a success criterion and a falsifier BEFORE it ships, and an
external actor rules on it later.

Twenty of those rulings came back FAILED. That is the strongest evidence this
house holds that a mechanism does not do what it claimed. So the question with
teeth is not "did the claim hold" -- that is already recorded -- but "is the
falsified mechanism still wired and firing?"

Many scripts here cite a pre-reg id in their docstring. None of them read the
OUTCOME back. check_prereg_for_new_infra.py enforces that a claim gets filed;
nothing enforces that a claim ruled false ever reaches the code that made it.
Filing was wired and the return path was not, which is the same shape as the
correction mirror that filed obligations and never closed one.

FAILED DOES NOT MEAN USELESS, and this script does not say it does. Several
were kept deliberately, with reasoning in the record: prereg-00752b78a670 says
"not retiring it - a structure-check that fires is still better than silence."
That is a legitimate call. What is NOT legitimate is a falsified claim quietly
continuing to read as a working guarantee because nobody ever put the ruling
and the running code in the same view. This is that view, and it is a report,
never a verdict.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

_MODULE_RE = re.compile(r"\b((?:core|cli|scripts)/[\w/]+\.py)\b")
_HOOK_RE = re.compile(r"\b([\w-]+\.sh)\b")
_BARE_MODULE_RE = re.compile(r"\b([a-z][a-z0-9_]{4,}\.py)\b")

# BARE IDENTIFIERS, and the first version of this script did not look for them.
#
# It searched for filenames and found one artifact across twenty records,
# reporting nineteen as "no artifact named" -- which reads as "nothing to see"
# and is instead "the instrument cannot see." The records mostly name their
# mechanism the way a person says it: `lepos_translation_gate`, not
# `lepos_translation_gate.py`. I wrote a matcher for the shape I pictured
# rather than the shape in the store, then nearly reported its silence as an
# absence of findings. Same error as the letter-monitor sweep and the four
# rows that escaped the corrections backfill: the tool was looking for a form
# the data does not use.
_BARE_IDENT_RE = re.compile(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+){1,5})\b")

# Words that pass the snake_case shape and name no module. Kept deliberately
# short: over-filtering here would recreate the blindness above.
_NOT_MODULES = frozenset(
    {
        "pre_registration",
        "pre_regs",
        "post_hoc",
        "per_turn",
        "reply_to",
        "built_but",
        "warning_only",
        "first_person",
        "single_source",
        "state_estimator",
        "data_home",
    }
)


def mechanism_artifacts(text: str) -> list[str]:
    """Pull candidate file references out of a mechanism description."""
    found: list[str] = []
    for pattern in (_MODULE_RE, _HOOK_RE, _BARE_MODULE_RE):
        found.extend(pattern.findall(text))
    for ident in _BARE_IDENT_RE.findall(text):
        if ident not in _NOT_MODULES:
            found.append(f"{ident}.py")
            found.append(f"{ident.replace('_', '-')}.sh")
    ordered: list[str] = []
    seen: set[str] = set()
    for item in found:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def locate(artifact: str) -> Path | None:
    """Find the artifact on disk, wherever it lives."""
    name = Path(artifact).name
    for base in ("src/divineos", ".claude/hooks", "scripts"):
        root = REPO_ROOT / base
        if not root.exists():
            continue
        for match in root.rglob(name):
            return match
    return None


def hook_surface_text() -> str:
    """Everything that decides what fires each turn: the settings AND the hook
    scripts themselves.

    Reading only the settings file was wrong and the proof was in the same
    session that wrote this. It reported "wired as hooks: 0" while
    lepos_translation_gate blocked two of my turns. The settings register
    SHELL scripts; the mechanisms here are Python modules those scripts call.
    Looking only at the register answers "is this file named in the manifest"
    and I had asked "is this thing firing" -- present-on-disk and
    live-in-the-loop are the two states that matter and the first version
    could not tell them apart.
    """
    chunks = []
    for candidate in (".claude/settings.json", ".claude/settings.local.json"):
        path = REPO_ROOT / candidate
        if path.exists():
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    for base in (".claude/hooks", "src/divineos/hooks"):
        root = REPO_ROOT / base
        if not root.exists():
            continue
        for script in list(root.rglob("*.sh")) + list(root.rglob("*.py")):
            chunks.append(script.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def reach_of(path: Path) -> str:
    """How this module gets reached: every turn, on demand, or not at all.

    THREE STATES, NOT TWO. The previous label was "on disk, no hook reaches
    it", which reads as dark and was wrong about all four modules it was
    applied to. Every one of them is imported -- by the CLI rather than by a
    hook. Hook-reached and CLI-reached are both alive and they are not the
    same aliveness: one fires whether or not anyone asks, the other fires when
    someone runs the command. Collapsing them into "not a hook" turned a
    distinction into an accusation.
    """
    stem = path.stem
    hook_hits = []
    import_hits = []
    for base, bucket in ((".claude/hooks", hook_hits), ("src/divineos", import_hits)):
        root = REPO_ROOT / base
        if not root.exists():
            continue
        for candidate in list(root.rglob("*.py")) + list(root.rglob("*.sh")):
            if candidate == path or "__pycache__" in candidate.parts:
                continue
            text = candidate.read_text(encoding="utf-8", errors="replace")
            if stem in text:
                bucket.append(candidate)
                break
    if hook_hits:
        return "fires every turn (hook)"
    if import_hits:
        return "fires on demand (imported)"
    return "DARK - nothing imports it"


def main() -> int:
    from divineos.core.pre_registrations import Outcome, list_pre_registrations

    registrations = list_pre_registrations(outcome=Outcome.FAILED)
    settings = hook_surface_text()

    live = absent = unresolved = wired = 0

    print(f"FAILED pre-registrations: {len(registrations)}")
    print()
    for entry in registrations:
        mechanism = entry.mechanism or ""
        artifacts = mechanism_artifacts(mechanism)
        on_disk = [(a, locate(a)) for a in artifacts]
        on_disk = [(a, p) for a, p in on_disk if p is not None]
        label = mechanism.split(":")[0][:70]

        if not artifacts:
            unresolved += 1
            print(f"  [no-artifact-named] {entry.prereg_id}  {label}")
            continue
        if not on_disk:
            absent += 1
            print(f"  [RETIRED]           {entry.prereg_id}  {label}")
            continue

        live += 1
        reached = [a for a, _ in on_disk if Path(a).stem in settings]
        if reached:
            wired += 1
        print(f"  [STILL LIVE]        {entry.prereg_id}  {label}")
        for _artifact, path in on_disk[:3]:
            print(f"                        {reach_of(path):<28} {path.relative_to(REPO_ROOT)}")

    print()
    print(
        f"still present: {live}  (of which wired as hooks: {wired})   "
        f"retired: {absent}   no artifact named: {unresolved}"
    )
    print()
    print(
        "STILL PRESENT is not an accusation. Some were kept on purpose and the\n"
        "reasoning is in the pre-reg notes. What this surfaces is the pairing:\n"
        "a claim ruled false, and the code that made it, in one view."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
