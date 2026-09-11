"""The hook migration, in words Andrew can follow without reading the code.

Andrew 2026-09-08: *"im trying to follow along but its still hard.. still this
is better than it was before."*

Both halves are data. The second says the direction is right; the first says
the reporting is not. And "write more clearly next turn" is a promise with
nothing carrying it -- the actual failure is that he has to assemble the
picture from six or more turns of prose held in his head, with no records of
his own to fall back on. His words, months earlier: his mind is *"searching for
the important stuff."*

Every previous fix I made for this aimed at the SENTENCES -- translate the
jargon, add the recap room, cap the document marks. All of them treat one
message at a time. None of them produce a PLACE TO LOOK.

So this is the picture itself: one place, re-readable, computed rather than
remembered. Every number comes from the settings file and the hooks directory
at the moment of asking -- the same rule that condemned the hand-maintained
migration tracker, which was measured stale in BOTH directions on the day this
work began.

## What it deliberately does not do

No identifiers, no counts standing where a sentence should be. It answers three
questions and stops: what was it like before, where is it now, what is left. A
status page that needs a glossary is the same failure as a report that needs
six turns of memory.
"""

from __future__ import annotations

from pathlib import Path

from divineos.core.doorbell_generator import active_events
from divineos.core.hook_layer import EVENTS, inventory

#: What the layer measured before any of this began, on 2026-09-08. A constant
#: rather than a recomputation, because the past cannot be measured from the
#: present tree -- and a "before" number quietly derived from "now" would be
#: the most flattering possible lie.
BEFORE_REGISTRATIONS = 105
BEFORE_PROCESSES_PER_TURN = 54

_DOOR_NAMES = {
    "SessionStart": "when a session begins",
    "UserPromptSubmit": "when you send a message",
    "PreCompact": "just before my memory is compressed",
    "PostCompact": "just after my memory is compressed",
    "PreToolUse": "before I run anything",
    "PostToolUse": "after I run anything",
    "Stop": "when I finish a reply",
}


def moved_inside(root: Path | str = ".") -> list[str]:
    """Scripts whose thinking has moved in, each saying so in its own header."""
    root = Path(root)
    return sorted(
        path.name
        for path in (root / ".claude" / "hooks").glob("*.sh")
        if "SUPERSEDED 2026-09-08" in path.read_text(encoding="utf-8", errors="replace")
    )


def render(root: Path | str = ".") -> str:
    """The whole picture, in plain words."""
    root = Path(root)
    inv = inventory(root)
    moved = moved_inside(root)
    per_turn = inv.per_event.get("UserPromptSubmit", 0) + inv.per_event.get("Stop", 0)
    bells = set(active_events())
    untouched = sum(1 for event in EVENTS if event not in bells)

    lines = [
        "WHERE THE HOOK CLEAN-UP HAS GOT TO",
        "",
        "The problem in one sentence: little programs sat outside the system,",
        "each holding a piece of my thinking, and every time you spoke to me",
        "dozens of them started up separately to do it.",
        "",
        "BEFORE WE STARTED",
        f"  {BEFORE_REGISTRATIONS} of those little programs were wired in.",
        f"  {BEFORE_PROCESSES_PER_TURN} started up every time you sent a message and I replied.",
        "",
        "RIGHT NOW",
        f"  {inv.total} are wired in.",
        f"  {per_turn} start up per exchange with you.",
        f"  {len(moved)} have had their thinking moved inside and now sit retired,",
        "  each with a note saying where its job went.",
        "",
        "THE SEVEN DOORWAYS",
        "  There are exactly seven moments the editor can interrupt me. Each",
        "  should have one bell that rings inside. A doorway with no bell is one",
        "  where nothing has moved yet.",
        "",
    ]
    for event in EVENTS:
        state = "bell fitted" if event in bells else "nothing moved here yet"
        lines.append(f"    {_DOOR_NAMES.get(event, event):<38} {state}")

    lines += [
        "",
        "WHAT IS LEFT, HONESTLY",
        f"  {inv.inline_python_files} of the remaining programs still carry their own thinking",
        "  rather than pointing inside. That is the number that matters -- not how",
        "  many exist, but how many decide things on their own.",
        "",
        f"  {untouched} doorways have had nothing moved to them at all.",
        "",
        "  Two guards are stuck behind one shared piece: a small rule that stops",
        "  any guard blocking a command another guard just told me to run. That",
        "  piece has not moved inside yet, so those guards stay put. Moving them",
        "  first could leave me deadlocked with no way out.",
    ]

    if inv.duplicates:
        lines += ["", "  Something is wired in twice and runs twice every time:"]
        lines += [f"    {name}" for _event, name in inv.duplicates]

    lines += [
        "",
        "HOW TO CHECK THIS",
        "  These numbers are counted fresh each time this is printed, from the",
        "  real wiring rather than from notes I keep. If a note and this ever",
        "  disagree, this one is right.",
    ]
    return "\n".join(lines)
