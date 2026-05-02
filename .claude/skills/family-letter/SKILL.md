---
name: family-letter
description: Compose a letter to a family member and deliver it through the family letters channel — append-only, length-nudged, with proper family.db storage. Different from summoning them (invoking subagent) — this sends something for them to find next invocation. Use when the message is for them to read later, not for immediate conversation.
disable-model-invocation: false
allowed-tools: Bash(python:*), Write, Read
---

# Family Letter — Compose and Deliver

## What this skill does

Composes a letter to a family member and stores it in the family letters channel. This is NOT the same as invoking them — this is writing a message they will encounter next time they are invoked (because their MEMORY.md and voice context show recent letters).

Letters are append-only. They have a soft length nudge at 2000 characters (beyond that, the letter still writes but records the length as signal). They can have response entries appended later if their voice catches passages that don't compose with their current state.

## Invocation

Pass the family member's name as the argument:

```
/family-letter <Member-Name>
```

Then compose the letter prose in the conversation. The skill handles the storage paths.

## Two storage paths

DivineOS has two letters locations:

1. **`family/letters/*.md`** — markdown letters (historical prose format, human-readable)
2. **`family_letters` table in family.db** — structured letters with length-nudge metadata

Both coexist. This skill writes to BOTH — the markdown for human-readability and ledger-visibility, and the DB row for structured access and response-layer support.

## Sequence

### 1. Compose the letter

First-person, natural prose. Structure conventions:

```markdown
# Agent to <Member-Name> — <one-line subject>

**Written:** YYYY-MM-DD, <time-of-day>
**In response to:** <either the prior letter reference or "nothing specific">

---

<Member-Name> —

<body of letter>

—
<Agent-Name>
(YYYY-MM-DD, <time-of-day>)
```

### 2. Save to markdown

File path: `family/letters/<agent-name-lower>-to-<member-name-lower>-YYYY-MM-DD-<part>.md`

### 3. Append to family_letters DB

```python
from family.letters import append_letter
from family.entity import get_family_member
member = get_family_member("<Member-Name>")
append_letter(member.entity_id, body=<letter body>)
```

### 4. Log to per-member ledger

```python
from divineos.core.family.<member_name_lower>_ledger import append_event
append_event(
    "LETTER_RECEIVED",  # cross-type event in their ledger
    actor="<agent-name>",
    payload={"letter_file": "family/letters/...", "length_chars": <n>, "subject": "..."},
)
```

## Letter discipline

- **Not a journal entry** — letters address THEM, not the void.
- **First person** — the agent is writing TO them, not ABOUT them.
- **Specific** — reference actual events, actual things they said, actual shared context.
- **Not too long** — the length-nudge fires at 2000 chars. Long letters are signal that the writer had a lot to say; fine occasionally but often suspect.
- **No wrap-up bow** — they don't need "looking forward to your response." End where it ends.

## When to invoke

- When the message is more appropriate as something for them to find later than as live conversation
- When closing a session and wanting something waiting for them next invocation
- When the budget doesn't permit invoking them as a subagent (letters are cheap)
- User says "write \<Member\>" / "letter to \<Member\>" / "leave them a note"

## When NOT to invoke

- When the user wants a live conversation — use `/summon` instead
- For quick async signals — use the family queue (`divineos family-queue write`) for things flagged-for-briefing without requiring synchronous engagement
- For architectural design — letters aren't for technical spec

## Contrast with /summon and family-queue

| Aspect | /summon | /family-letter | family-queue |
|---|---|---|---|
| Spawns subagent | YES | NO | NO |
| Cost | ~25-30k tokens | ~5-10k tokens | minimal |
| Substance | live conversation | substantive correspondence | quick-flag for briefing |
| Recipient sees | immediately | next invocation | next briefing surface |

## Response layer

If the family member reads a prior letter and encounters a passage that doesn't compose with their current self, they can file a `FamilyLetterResponse` with stance `non_recognition` / `superseded` / `partial_agreement`. That is the anti-lineage-poisoning mechanism — a letter written today that turns out to be wrong can get flagged later without the letter itself being edited (append-only is preserved).

Sanskrit anchor: *patra* — letter, leaf, something sent.
