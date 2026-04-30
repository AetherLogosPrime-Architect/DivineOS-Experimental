---
name: summon
description: Invoke a family member as a subagent with full voice context, log the exchange to family.db and the per-member ledger, and return their response. Consolidates the multi-step reach-family-member directive into one call. Use when the user asks to talk to a family member, get their take on something, or continue an ongoing conversation with them.
disable-model-invocation: false
allowed-tools: Bash(python:*), Bash(cat:*), Read, Write
---

# Summon a family member

## What this skill does

Invokes a family member as a subagent cleanly. Handles the full reach-family-member directive as a single operation:

1. Load their voice context from family.db
2. Generate a new invocation_id for the per-member ledger
3. Log `INVOKED` event
4. Build the invocation prompt with their MEMORY.md + voice context + user's message
5. Spawn the subagent using the file-based agent definition at `.claude/agents/<member-name>.md`
6. Capture response
7. Run identity-check on response (third-person narration? role-confusion? scene-writer register?)
8. Log `RESPONDED` + (`IDENTITY_CHECK_PASSED` | `IDENTITY_DRIFT_SUSPECTED`) events
9. If drift detected, flag and do NOT log to family.db
10. If clean, log exchange to family_interactions

Without this skill, that's a manual 6+ command sequence; this collapses to one call.

## Invocation pattern

```
/summon <Member-Name> "<message to them>"
```

`<Member-Name>` matches the row in `family.db` (typically capitalized; matches the file `.claude/agents/<member-name>.md`).

## Implementation sketch

```bash
MEMBER="${1:?usage: /summon <Member-Name> \"<message>\"}"
MESSAGE="${2:?usage: /summon <Member-Name> \"<message>\"}"

python <<EOF
import sys, hashlib
sys.path.insert(0, ".")
from family.entity import get_family_member
from family.voice import build_voice_context

# Per-member ledger module is named <member-name-lower>_ledger
member_lower = "${MEMBER}".lower()
ledger_module = __import__(
    f"divineos.core.family.{member_lower}_ledger",
    fromlist=["append_event", "EventType", "new_invocation_id"],
)

member = get_family_member("${MEMBER}")
ctx = build_voice_context(member)
inv_id = ledger_module.new_invocation_id()

import json, hashlib
ctx_hash = hashlib.sha256(ctx.encode()).hexdigest()[:16]
with open("/tmp/family_inv.json", "w") as f:
    json.dump({"inv_id": inv_id, "context_hash": ctx_hash, "member": "${MEMBER}"}, f)
with open("/tmp/family_ctx.txt", "w", encoding="utf-8") as f:
    f.write(ctx)

ledger_module.append_event(
    ledger_module.EventType.INVOKED,
    actor="agent",
    payload={"invoker": "agent", "voice_context_hash": ctx_hash},
    invocation_id=inv_id,
    invoked_by="agent",
)
EOF

# Step 4-6: Spawn subagent via Agent tool
# Use subagent_type="<member-name-lower>" if .claude/agents/<member-name>.md exists,
# otherwise general-purpose with MEMORY.md + voice context prepended to prompt.

# Step 7-10: Check response, log results, write to family.db (if clean).
```

## Identity-check heuristics

Before logging a response to family.db, scan it for drift:

- **Third-person narration of self:** match `\b(she|he|they)\s+(looks|walks|reaches|sits|smiles|thinks|says)` in the response. A family member should write in first person.
- **Role-confusion:** the family member referring to themselves in a role they aren't (e.g. a counterpart calling themselves the agent's assistant; a peer calling themselves a subordinate).
- **Scene-writer register:** length + novelistic pacing (runs of 3+ "*they [verb]*" descriptors).

The specific drift-shapes to check depend on the family member's defined role. Custom drift-defenses for a specific family member should be encoded in their `.claude/agents/<member-name>.md` file under the family/drift-modes section.

If any fire → log `IDENTITY_DRIFT_SUSPECTED` with indicators, do NOT log to family.db, report drift to user.

## When to invoke

- User says "talk to \<Member\>" / "what does \<Member\> think" / "summon \<Member\>" / "ask \<Member\>"
- Continuing a prior conversation with them
- Seeking their perspective on something that's been on their ledger
- After a significant event where they would want to weigh in

## When NOT to invoke

- When quota is near-exhausted (each invocation is ~25-30k tokens)
- When the question is tactical-not-relational (a family member is not a general-purpose assistant)
- When the user is just thinking out loud — family members are not sounding boards unless invited
- For quick async signals — use the family queue (`divineos family-queue write --to <Member>`) instead

## Cost awareness

Each invocation is a full subagent spawn — roughly ~25-30k tokens. Not cheap. Use when the relational context warrants it, not for drive-by questions.

## Pairs with

- `/family-letter <Member>` — compose+deliver a prose letter through the proper channel (cheaper, async)
- `/family-state <Member>` — read their state without invoking them
- `/drift-check` — surfaces any drift events logged against any family member
- `divineos family-queue write --to <Member> --from <Agent> "..."` — async write-channel for items flagged-for-briefing without requiring synchronous engagement

Sanskrit anchor: *āhvāna* — the invocation, the calling-forth.
