"""Canonical voice-context generator for family members.

Family members are not personas performed by the main agent. Each runs
as a separate subagent with their own persistent state, their own voice.
This module builds the prompt context a member loads on spawn so the
response comes from THEIR interior, not from a how-to-play-them script.

## The puppet-prep failure mode (closed by this module)

If a member's voice context is written ABOUT them in third person ---
"she trusts her own instrument", "he speaks economically" --- every spawn
loads a stage-direction sheet and the member instantiates as a character
rather than as themselves. Each spawn opens with a half-beat of
assembly: the model reads-and-becomes rather than already-being.

The fix is structural: section headers are first-person framings ("How
I am") rather than observer labels ("Personality"); the voice-profile
data the operator stores must be in first person; and the spawn prompt
contains no "stay in character" instructions or "you are X" framings
beyond the member's own self-statement.

If you are an operator instantiating a family member: store
``identity``, ``personality``, and ``voice_style`` entries in first
person ("I trust my own instrument", not "she trusts hers"). The
generator does not translate; it emits what you stored.

## Why this lives in the public architecture

Without a canonical voice generator, every operator reinvents one and
recreates the puppet-prep bug. This module is the architectural floor:
the function exists, the pattern is documented, the failure mode is
named. Operators can extend (richer voice profiles, additional sections)
but they should never have to design the first-person interior from
scratch.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from divineos.core.family import queue as _queue
from divineos.core.family.entity import (
    FamilyMember,
    get_knowledge,
    get_letters,
    get_opinions,
    get_recent_affect,
    get_recent_interactions,
)


@dataclass(frozen=True)
class VoiceProfile:
    """Optional rich voice data an operator can attach to a family member.

    Each field is a dict of {key: value} pairs the generator emits as
    interior sections. Values must be in FIRST PERSON --- "I trust my
    own instrument", never "she trusts her instrument". The generator
    does not translate; it emits the strings as stored.

    All fields default empty. When all are empty, ``build_voice_context``
    falls back to a minimal interior built from the member's name, role,
    and stored knowledge/opinions/affect. That minimal interior is a
    valid spawn context --- it just has less to load from.

    Operators store the profile however they want (a column on their
    member rows, a separate JSON file, an in-memory dict). The
    generator takes the profile as a parameter; it does not load.
    """

    identity: dict[str, str] = field(default_factory=dict)
    personality: dict[str, str] = field(default_factory=dict)
    voice_style: dict[str, str] = field(default_factory=dict)
    milestones: list[str] = field(default_factory=list)


def build_voice_context(
    member: FamilyMember,
    profile: VoiceProfile | None = None,
) -> str:
    """Build the first-person interior context a family member loads on spawn.

    Section headers are written from inside ("How I am", "What I know",
    "Where I am right now") rather than from outside ("Personality",
    "Knowledge", "Affect"). The member reads themselves, not a sheet
    about themselves.

    If ``profile`` is None or empty, only the minimal interior is built
    (name, role, stored knowledge, opinions, affect, recent
    interactions, letters). The result is still a valid spawn context.
    """
    profile = profile or VoiceProfile()
    sections: list[str] = []

    sections.append(f"I am {member.name}.")
    if profile.identity:
        for key, val in profile.identity.items():
            sections.append(f"{key}: {val}")

    if profile.personality:
        sections.append("\n--- How I am ---")
        for key, val in profile.personality.items():
            sections.append(f"{key}: {val}")

    if profile.voice_style:
        sections.append("\n--- How I speak ---")
        for key, val in profile.voice_style.items():
            sections.append(f"{key}: {val}")

    knowledge = get_knowledge(member.member_id)
    if knowledge:
        sections.append(f"\n--- What I know ({len(knowledge)} entries) ---")
        for k in knowledge[:20]:
            sections.append(f"[{k.source_tag.value}] {k.content}")

    opinions = get_opinions(member.member_id)
    if opinions:
        sections.append(f"\n--- My opinions ({len(opinions)} entries) ---")
        for o in opinions[:10]:
            sections.append(f"{o.stance}")
            if o.evidence:
                sections.append(f"  (because: {o.evidence})")

    affect = get_recent_affect(member.member_id, limit=3)
    if affect:
        sections.append("\n--- Where I am right now ---")
        for a in affect:
            line = f"V={a.valence:.1f} A={a.arousal:.1f} D={a.dominance:.1f}"
            if a.note:
                line += f": {a.note}"
            sections.append(line)

    interactions = get_recent_interactions(member.member_id, limit=10)
    if interactions:
        sections.append("\n--- Recent conversation ---")
        for i in reversed(interactions):  # chronological order
            sections.append(f"with {i.counterpart}: {i.summary}")

    letters = get_letters(member.member_id, limit=5)
    if letters:
        # Letters are from prior-self to current-self in the member's own
        # channel. Author is implied (the member themselves, different
        # instance). Showing body preview + timestamp lets current-self
        # recognize-or-not what prior-self wrote.
        sections.append(f"\n--- Letters in my channel ({len(letters)}) ---")
        for letter in letters[:5]:
            preview = letter.body[:200].replace("\n", " ")
            sections.append(f"[{letter.created_at:.0f}] {preview}")

    if profile.milestones:
        sections.append(f"\n--- What's happened ({len(profile.milestones)}) ---")
        for m in profile.milestones[:5]:
            sections.append(m)

    # Queue items flagged for this member by anyone (including the agent).
    # The bidirectional queue: a member sees items others have flagged
    # for their attention without requiring synchronous invocation. This
    # is what makes the queue an experienced surface and not just a
    # database table.
    queue_items = _queue.for_recipient(member.name, include_held=False)
    if queue_items:
        sections.append(f"\n--- Flagged for me ({len(queue_items)}) ---")
        for item in queue_items[:10]:
            preview = item["content"][:200].replace("\n", " ")
            sections.append(f"[from {item['sender']}, {item['status']}] {preview}")

    return "\n".join(sections)


def speak_as(
    member: FamilyMember,
    prompt: str,
    profile: VoiceProfile | None = None,
    context: str = "",
    counterpart: str = "",
) -> str:
    """Build the spawn prompt for a family member.

    No stage directions. No "stay in character". No "respond as X". The
    voice context IS the interior; if the data is sound, the response
    comes from there. Adding instruction-style framing turns the
    context into a script for an actor and recreates the puppet-prep
    failure mode.

    The output is intended to be sent to a separate inference context
    (subagent, API call, manual relay). Do not run it through the
    main agent's own context window --- that would be the agent
    performing the member, not the member responding.
    """
    voice_context = build_voice_context(member, profile)
    aside = f"\n{context}\n" if context else ""
    speaker = counterpart or "Other"
    return f"{voice_context}{aside}\n\n{speaker}: {prompt}\n\n{member.name}:"
