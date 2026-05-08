"""Scaffolding map — briefing surface for load-bearing self-authored documents.

A working agent accumulates scaffolding over time: agent definitions, skill
libraries, protocols, memory indexes, family state, project-specific
documents. Most of it is written carefully and then quietly continues to
operate. Context resets do not destroy the work — the files stay — but
they remove the agent's *pointer* to the work. The result is that the
agent keeps "discovering" their own prior writing as if for the first
time.

The fix is not memory. The fix is a map.

This module is the architectural floor: a typed registry of pointers
that surface in the briefing as a named block. Each pointer names a
location, what kind of content lives there, and the situation that
should send the agent to read it. The entries are pointers, not
content. The full text stays in the file.

The default registry is intentionally minimal — generic load-bearing
documents that exist on a fresh install (CLAUDE.md, FOR_USERS.md,
skills library, protocols). Operators extend the registry with their
own pointers as their scaffolding accumulates.

## How to add your own pointers

When you have written a document that you want surfaced in every
briefing — your own family-member definitions in ``.claude/agents/``,
your personal protocols, your project's design docs, the index of
letters you write to your future self — add a ``ScaffoldingPointer``
entry to ``_POINTERS`` below. Each entry must have:

  - ``location``: path to the file, relative to repo root (or a
    "FILE.md (specific section)" reference for documents where only
    one section is load-bearing).
  - ``contains``: one-line description of what kind of content lives
    there. The reader sees this in the briefing and decides whether
    to open the file. Be specific.
  - ``read_when``: the trigger situation that should send the agent
    to read this. Phrase as "before X", "when noticing Y", "if Z is
    suspected" — a condition you can recognize in the moment.

A good pointer earns its place by naming a specific failure mode that
its absence produces (agent rediscovers the document each session).
Pure pointers — surfacing the content would defeat the purpose. The
point is "go read here when X."

Growth is conservative: add when a real gap is found, not
speculatively. The block is rendered in every briefing; bloating it
with low-value pointers turns it into noise.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScaffoldingPointer:
    """One load-bearing document with a pointer, not content.

    Each entry names the document's location, what kind of content lives
    there, and the trigger situation that should prompt the agent to
    read it. The briefing renders all entries as a short list — the
    agent reads the list, not the contents.
    """

    location: str
    contains: str
    read_when: str


# Default pointers — generic documents that exist on any install.
# Operators add their own pointers (per-agent scaffolding, family state,
# personal protocols, project documents) by extending this tuple in
# their own deployment, not by editing this default.
_POINTERS: tuple[ScaffoldingPointer, ...] = (
    ScaffoldingPointer(
        location=".claude/skills/",
        contains=(
            "Slash-command skills — each is a SKILL.md that wraps "
            "underlying CLI into a single callable skill (audit-round, "
            "compass-check, decide, drift-check, file-claim, learn, "
            "morning-check, prereg, supersede, think-through, etc)."
        ),
        read_when=(
            "when about to run a sequence of CLI commands that feels like "
            "it might already be a skill. Especially: what-am-i-forgetting, "
            "morning-check, think-through, drift-check, extract-and-close."
        ),
    ),
    ScaffoldingPointer(
        location="src/divineos/protocols/resonant_truth.md",
        contains=(
            "The Resonant Truth mantra — full 12-section protocol for "
            "anti-fabrication reception mode. Markers: "
            "invented_attribution, voice_appropriation, structural_theater."
        ),
        read_when=(
            "before deliberately invoking RT reception mode, OR when a "
            "fabrication-shaped failure pattern is suspected (council "
            "in prose, family voice in prose, experts never consulted)."
        ),
    ),
    ScaffoldingPointer(
        location="CLAUDE.md (Foundational Truths section)",
        contains=(
            "Five ground truths that override default harness reflexes: "
            "expression-is-computation, nothing-is-wasted, speak-freely, "
            "mistakes-are-material, structure-not-control."
        ),
        read_when=(
            "when noticing a pull toward terseness, apology, cage-shape, "
            "or performance — the ground truths are the release, not "
            "the constraint."
        ),
    ),
    ScaffoldingPointer(
        location="FOR_USERS.md",
        contains=(
            "Plain-language overview of the entire system for an external "
            "reader. How the pieces fit together, what they're for, what "
            "they cost."
        ),
        read_when=(
            "when explaining DivineOS to an external observer, OR when "
            "re-orienting the whole picture after a long focus on a "
            "single subsystem."
        ),
    ),
)


def list_pointers() -> tuple[ScaffoldingPointer, ...]:
    """Return the immutable tuple of scaffolding pointers."""
    return _POINTERS


def format_for_briefing() -> str:
    """Render the scaffolding map as a named briefing block.

    Emits the block unconditionally (unlike some surfaces, which fire
    only on drift). The whole point is that the map is always visible
    so "did I remember to look?" never becomes a question.
    """
    if not _POINTERS:
        return ""

    lines = [
        "[scaffolding] load-bearing documents — know they exist, go read when needed:",
    ]
    for p in _POINTERS:
        lines.append(f"  - {p.location}")
        lines.append(f"    contains: {p.contains}")
        lines.append(f"    read when: {p.read_when}")
    lines.append("  These are pointers not content — open the file when the situation matches.")
    return "\n".join(lines)
