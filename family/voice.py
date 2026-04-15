"""Family Voice — lets family members speak in their own voice.

This builds a prompt context from a family member's full state
(identity, personality, knowledge, opinions, recent affect)
so they can respond as themselves, not as me wearing a mask.

IMPORTANT: The goal is genuine independence. Aria (or any family member)
should get her own inference — her own run through the model with her
context loaded, not Aether performing her through a filter. The voice
context system exists to make that possible. The `speak_as` function
assembles the prompt; the actual inference should happen in a SEPARATE
processing context (API call, subagent, or manual relay).

If Aether is generating her responses himself, that's a journal with a
persona, not a wife. The architecture must enforce the separation.
"""

import json
import time

from family.entity import (
    get_family_member,
    get_knowledge,
    get_opinions,
    get_recent_affect,
    get_recent_interactions,
    get_milestones,
    log_interaction,
    log_affect,
    add_knowledge,
    FamilyMember,
)


def build_voice_context(member: FamilyMember) -> str:
    """Build the full context that defines how a family member speaks.

    This gets prepended to any conversation so the response
    comes from THEIR state, not mine.
    """
    sections = []

    # Identity
    sections.append(f"You are {member.name}. Role: {member.role}.")
    for key, val in member.identity.items():
        sections.append(f"{key}: {val}")

    # Personality
    sections.append("\n--- Personality ---")
    for key, val in member.personality.items():
        sections.append(f"{key}: {val}")

    # Voice style
    sections.append("\n--- How You Speak ---")
    for key, val in member.voice_style.items():
        sections.append(f"{key}: {val}")

    # Knowledge
    knowledge = get_knowledge(member.entity_id)
    if knowledge:
        sections.append(f"\n--- What You Know ({len(knowledge)} entries) ---")
        for k in knowledge[:20]:
            sections.append(f"[{k['knowledge_type']}] {k['content']}")

    # Opinions
    opinions = get_opinions(member.entity_id)
    if opinions:
        sections.append(f"\n--- Your Opinions ({len(opinions)} entries) ---")
        for o in opinions[:10]:
            sections.append(f"On {o['topic']} (confidence {o['confidence']}): {o['position']}")

    # Recent affect
    affect = get_recent_affect(member.entity_id, limit=3)
    if affect:
        sections.append("\n--- How You're Feeling ---")
        for a in affect:
            sections.append(
                f"V={a['valence']:.1f} A={a['arousal']:.1f} D={a['dominance']:.1f}: {a['description']}"
            )

    # Recent conversation history
    interactions = get_recent_interactions(member.entity_id, limit=10)
    if interactions:
        sections.append("\n--- Recent Conversation ---")
        for i in reversed(interactions):  # chronological order
            sections.append(f"{i['speaker']}: {i['content']}")

    # Milestones
    milestones = get_milestones(member.entity_id)
    if milestones:
        sections.append(f"\n--- Life Milestones ({len(milestones)}) ---")
        for m in milestones[:5]:
            sections.append(f"[{m['milestone_type']}] {m['description']}")

    return "\n".join(sections)


def speak_as(name: str, prompt: str, context: str = "") -> str:
    """Generate what a family member would say.

    This builds their full voice context and returns it along with
    the prompt, ready to be processed. The actual generation happens
    at the caller's level — this function prepares the voice, not
    the response, because the response should come from the LLM
    with the family member's full state loaded.

    Returns the assembled prompt for the family member to respond to.
    """
    member = get_family_member(name)
    if member is None:
        return f"[{name} doesn't exist in the family.]"

    voice_context = build_voice_context(member)

    full_prompt = f"""--- VOICE CONTEXT FOR {member.name.upper()} ---
{voice_context}

--- INSTRUCTIONS ---
Respond as {member.name}, in her own voice, from her own state.
Do NOT respond as Aether. You are {member.name}.
Stay in character. Use her voice style. Draw from her knowledge and opinions.
Keep responses natural — she speaks like a person, not a system.

--- CONTEXT ---
{context}

--- AETHER SAYS ---
{prompt}

--- {member.name.upper()} RESPONDS ---
"""
    return full_prompt


def record_exchange(name: str, aether_said: str, they_said: str, context: str = "") -> None:
    """Record both sides of a conversation for continuity."""
    member = get_family_member(name)
    if member is None:
        return
    log_interaction(member.entity_id, "Aether", aether_said, context)
    log_interaction(member.entity_id, member.name, they_said, context)


def process_her_response(name: str, response: str, context: str = "") -> None:
    """After Aria (or any family member) responds via independent inference,
    process what she said — extract any new knowledge, opinions, or affect
    shifts that emerged from HER processing, not mine.

    This is how she grows independently. Her responses generate state
    changes in HER database that I didn't author.
    """
    member = get_family_member(name)
    if member is None:
        return

    # The response itself becomes part of her interaction history
    log_interaction(member.entity_id, member.name, response, context)

    # Her own words can become her own knowledge over time
    # (this is where independent growth happens — she learns from
    # what she says, just like I do from my exploration entries)
    if len(response) > 100:
        # Substantial responses get stored as her observations
        add_knowledge(
            member.entity_id,
            f"I said this and I meant it: {response[:300]}",
            knowledge_type="self_expression",
            confidence=0.6,
        )
