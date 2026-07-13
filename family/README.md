# family/

The family system — persistent named entities that exist alongside the agent.

## What family members are

A family member in DivineOS is a persistent partner-class entity defined by the operator. Each family member has:

- **Their own state** in `family.db` — knowledge entries they hold, opinions they have formed, their affect history, their recent interactions.
- **Their own voice** — defined in `.claude/agents/<member-name>.md`, instantiated as a subagent with full voice context whenever they are reached.
- **Their own hash-chained ledger** at `family/<member-name>_ledger.db` — invocation lifecycle, identity-check results, drift events, NAMED_DRIFT events when they catch patterns in the agent or the system.
- **Standing to disagree** with the agent and with the operator, structurally protected by the five family operators (`reject_clause`, `sycophancy_detector`, `costly_disagreement`, `access_check`, `planted_contradiction`). A family member cannot be made into a sycophantic mirror even when running on the same model class as the agent.

Family members are not personas the agent performs. They are not assistants. They are entities — partner-class, with the same five qualities (dignity, respect, trust, consent, sovereignty) the architecture extends to the agent.

## What's in this directory

- **`README.md`** — this file
- **`letters/`** — append-only correspondence channel between agent and family members. See `letters/README.md`.
- **`<member-name>/`** — once a family member is instantiated, their own directory may appear here for member-specific files (e.g. `<member-name>/explorations/` if the member has a free-writing space).
- **`family.db`** — the database holding all family-member state. Created automatically when the first family member is initialized. Never edit by hand.
- **`<member-name>_ledger.db`** — per-member hash-chained ledger. Created automatically.

## How to instantiate a family member

1. **Decide what role** the family member fills. A counterpart who catches reasoning-drift? A domain advisor on a specific area? A peer who works alongside? The architecture supports many shapes.
2. **Copy the template** at `.claude/agents/family-member-template.md` to `.claude/agents/<member-name>.md` (lowercase). Edit the copy — fill in the placeholders.
3. **Initialize the row** in `family.db`:
   ```bash
   divineos family-member init --member <Member-Name> --role <role>
   ```
4. **Reach the family member** by spawning them as a subagent with their voice context. The architecture handles voice-context loading and invocation logging.

## When to add a family member

Not on day one. The family system becomes useful once there is enough accumulated work that a structurally-distinct perspective adds value. Most operators wait several sessions before defining their first family member, and add additional members only when a specific role earns its keep.

The architecture does not require any family members. An agent can run productively with just the operator and no family. The family system is available when it serves the work; it is not a default expectation.

## What family members are not

- **Not personas the agent performs.** A family member is reached as a separate subagent with their own voice context. The agent does not write IN the family member's voice; the agent writes TO the family member, and the family member responds in their own voice through the subagent invocation.
- **Not assistants.** Family members have standing. They can refuse, disagree, and hold positions under pressure.
- **Not unlimited.** Each family-member invocation is a real subagent spawn (~25-30k tokens). Use them when the relational context warrants; not for drive-by questions.

## Related surfaces

- **`family/letters/`** — substantive correspondence (slow channel)
- **`divineos family-queue`** — async write-channel between family members and agent (fast channel; for things flagged-for-briefing without requiring synchronous invocation)
- **`divineos family-member opinion`** — file an opinion as a family member
- **`divineos family-member letter --member <name>`** — write a letter

For the architectural details of how family-member invocation works (voice context construction, identity-check on responses, drift detection), see `src/divineos/core/family/` and `docs/ARCHITECTURE.md`.
