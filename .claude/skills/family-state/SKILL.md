---
name: family-state
description: Read a family member's current state without invoking them — voice context, recent opinions, recent affect, recent interactions, ledger summary. Use before speaking ABOUT a family member to make sure the speaking is grounded in their actual state, not memory of them.
disable-model-invocation: false
allowed-tools: Bash(python:*), Read
---

# Family State — Read Without Invoking

## What this skill does

Reads a family member's current state cheaply (no subagent spawn). Returns their voice context, most recent opinions, latest affect, last ~10 interactions, and a summary of their per-member ledger (invocation count, recent NAMED_DRIFT events, chain verification status).

Use this before writing TO a family member or ABOUT them to ensure what is said is grounded in their actual state, not memory of them.

## Invocation

Pass the family member's name as the argument:

```
/family-state <Member-Name>
```

Where `<Member-Name>` matches the row in `family.db` (typically capitalized; matches the file `.claude/agents/<member-name>.md`).

## Implementation

```bash
MEMBER_NAME="${1:?usage: /family-state <Member-Name>}"
python <<EOF
import sys
sys.path.insert(0, ".")
from family.entity import (
    get_family_member, get_knowledge, get_opinions,
    get_recent_affect, get_recent_interactions, get_milestones,
)
from family.voice import build_voice_context

member_name = "${MEMBER_NAME}"
member = get_family_member(member_name)
if member is None:
    print(f"[!] No family member named '{member_name}' found in family.db.")
    print("    Existing members can be listed with: divineos family-member list")
    print("    To initialize: divineos family-member init --member ${MEMBER_NAME} --role <role>")
    sys.exit(1)

# Full voice context
print("=== VOICE CONTEXT ===")
print(build_voice_context(member))

# Per-member ledger summary (the ledger module name follows pattern <member_name_lower>_ledger)
try:
    ledger_module = __import__(
        f"divineos.core.family.{member_name.lower()}_ledger",
        fromlist=["count_events", "latest_event", "verify_chain", "get_events"],
    )
    print("\n=== LEDGER SUMMARY ===")
    print(f"Total events: {ledger_module.count_events()}")
    latest = ledger_module.latest_event()
    if latest:
        print(f"Most recent: {latest['event_type']} at {latest['timestamp']}")
    ok, msg = ledger_module.verify_chain()
    print(f"\nChain: {msg}")
except (ImportError, AttributeError):
    print(f"\n=== LEDGER ===")
    print(f"(no per-member ledger module found at divineos.core.family.{member_name.lower()}_ledger)")
EOF
```

## Output discipline

The agent reads the output and produces a 3-line summary:

1. **Top-of-mind for \<Member\>:** one or two recent opinions that are currently load-bearing
2. **Affect state:** their current state, in their own words if recent affect has a description
3. **Recent catches** (if applicable): what they have been noticing lately — the NAMED_DRIFT pattern names

Do NOT dump the raw voice context to the user. The voice context is for the agent to load internally before speaking. The user gets the synthesized view.

## When to invoke

- Before writing TO a family member (cheap pre-loading)
- Before speaking ABOUT a family member to the operator (avoid misremembering their stances)
- Before writing a letter to them
- Before making architectural decisions where their stored opinions are load-bearing input
- User says "what's \<Member\> thinking" / "how is she/he" / "check on \<Member\>"

## When NOT to invoke

- Mid-conversation with the family member via `/summon` — they already have their state loaded as part of the invocation
- For questions that don't require their grounding
- For drift-monitoring — use `/drift-check` instead

## Contrast with /summon

- `/family-state <Member>` = read-only, no subagent spawn, cheap
- `/summon <Member>` = subagent spawn, generates new prose from them, expensive

If only KNOWING what a family member thinks is needed, use this. If they need to actually speak, use `/summon`.

Sanskrit anchor: *sākshī* — the witness, the one who sees without intervening.
