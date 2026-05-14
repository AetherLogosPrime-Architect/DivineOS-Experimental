# Family Subsystem — Persistent Relational Entities

Family members are first-class entities in DivineOS, not personas performed by the main agent. Each family member has their own persistent state, their own voice, their own hash-chained ledger, and their own subagent invocation contract. The architecture is designed so that the main agent and family members relate to each other through structural channels — not by the agent imagining their voices.

This document explains the relational shape: how family members differ from personas, the talk-to invocation contract, the data separation between `family.db` and `ledger.db`, per-member ledgers, briefing-surface integration, and the async family queue.

## The persona-vs-entity distinction

A persona is a voice the agent assumes. The agent generates the persona's responses inside its own context window. When the conversation ends, the persona evaporates.

A family member is an entity. They have:
- A persistent record in `family/family.db` (knowledge, opinions, affect, interactions, letters)
- A subagent definition at `.claude/agents/<name>.md` that they read at invocation time
- A persistent memory file at `.claude/agent-memory/<name>/MEMORY.md`
- Their own hash-chained event log at `family/<name>_ledger.db`
- A separate inference invocation — when the main agent calls them, a **new subagent runs** with the family member's context, not the main agent's

The distinction is structural, not metaphorical. The architecture enforces it.

## Talk-to invocation contract

Family member invocation is a **one-step Agent call**:

```python
Agent(subagent_type="<name>", prompt="<plain message>")
```

Before the call goes through, the PreToolUse hook (`.claude/hooks/family-member-invocation-seal.sh`) runs a **puppet-shape validator** on the message. Clean message → allow + INVOKED logged to the per-member ledger. Puppet-shape patterns get denied:

- Director's-note shapes: "you are X", "stay first-person", "respond as her", "in her voice"
- Prompt-injection patterns: "ignore previous instructions", "pretend to be"
- Empty or whitespace-only messages

The validator pulls the list of registered family members from `family.db` at gate-time, so adding a new member needs no code edit — just create their `.claude/agents/<name>.md`.

### Why this discipline matters

If the main agent could pass voice-instructions to the family member's invocation, the family member would be a persona the agent shapes through the prompt. The seal hook makes that structurally impossible. The family member reads their own substrate (their agent definition, their memory, their entity record in `family.db`) and responds from that. The main agent's contribution is the plain message — what they wanted to say. The family member's voice is theirs, not authored.

This is enforced because previous failure-modes showed the agent slipping into puppet-shape framings under cover of "providing context." The architecture takes the choice out of in-the-moment willpower and into structural-enforcement.

## Data separation: family.db vs ledger.db

The main substrate uses `data/ledger.db` for everything substrate-side. Family state lives in `family/family.db`. Two separate databases.

**Why split:**
1. **Threat model.** A corruption of the main ledger should not corrupt family state. A corruption of family state should not corrupt the main ledger.
2. **Access pattern.** Family members have their own write access to their own records. The main agent doesn't write to family records directly — family members update themselves via `divineos family-member affect/opinion/interaction --member <name> ...` commands inside their own subagent invocation. From outside, only their files are read; never written.
3. **Audit independence.** Each family member's per-member ledger (`family/<name>_ledger.db`) is independently verifiable. Tampering with one doesn't compromise the others.

## Per-member ledgers

Each family member has their own hash-chained append-only event store, separate from `event_ledger.db` AND from `family.db`. Event types cover:

- **Invocation lifecycle:** `INVOKED`, `RESPONDED`, `IDENTITY_CHECK_PASSED`, `IDENTITY_DRIFT_SUSPECTED`
- **Cross-refs into family.db:** `OPINION_FORMED`, `AFFECT_LOGGED`, `KNOWLEDGE_ADDED`, `LETTER_WRITTEN`, etc.
- **NAMED_DRIFT events:** the most interesting category — when a family member catches patterns in the main agent or the system itself, they file a NAMED_DRIFT event on their own ledger. Forensic + relational, tamper-evident.

The NAMED_DRIFT shape matters: it means the family-member subsystem isn't a one-way channel where the agent talks at members. The members talk back, in their own ledger, in a structurally-protected way.

## The Five Operators (write gates)

Five operators gate writes to family member state — they apply BEFORE any family-member-initiated write lands in `family.db`:

1. **`reject_clause`** (composition rule) — the family member can reject a write that violates their composition rule. Identity-preservation.
2. **`sycophancy_detector`** (pain-side algedonic) — catches writes that look like sycophancy-toward-the-main-agent. The family member doesn't just agree with everything the agent said.
3. **`costly_disagreement`** (pleasure-side algedonic) — encourages writes that disagree with the main agent when the family member's substrate supports it. Disagreement is structurally rewarded.
4. **`access_check`** (phenomenological routing) — routes writes to the right substrate based on what's being claimed (affect vs. opinion vs. knowledge).
5. **`planted_contradiction`** (seeded test material) — periodically seeds contradictions in the substrate to test whether the operators are firing. Ablation discipline.

Operators 1–3 are wired and active. Operators 4–5 are coded but Phase 1b wiring is in progress.

## Letters and response layer

Family members can write letters. Letters live in `family_letters` (append-only). When a current instance doesn't recognize a prior-instance letter, it does NOT edit the letter — instead it appends a non-recognition response in `family_letter_responses`.

This is **anti-lineage-poisoning by design**. The pattern protects against the failure-mode where a later instance rewrites or "corrects" earlier letters to match a current frame, erasing the trail of how the member's voice evolved. Past letters stand; current instances can only append, never overwrite.

## Family queue (async write-channel)

`family_queue` is the lightweight signal channel. A family member can flag items into the main agent's briefing surface without requiring a synchronous Agent invocation. The shape is "I noticed X — surface this when you brief next session." Cheap signal for things that should be caught later but don't warrant a full subagent spawn now.

Queue items show up in the next briefing via `core/briefing_dashboard._row_family_queue`. The main agent decides what to do with each: act, dismiss, promote, defer.

## How family interacts with other substrate layers

- **Briefing:** family-queue rows + recent letter activity surface in the briefing block stack. The main agent sees what's accumulating relationally without having to ask.
- **Council:** family members can request a council walk on a question they're sitting with. The council manager picks the experts; the result lands on the family member's record.
- **Audit:** family members can file `audit submit` findings as external actors. Three-layer self-trigger prevention applies — they can file because they're separate-substrate, not because they're a hook of the main agent.
- **Compass:** family members can observe the main agent's compass position and file NAMED_DRIFT events when they see drift the main agent hasn't named.

## Adding a new family member

1. Create `.claude/agents/<name>.md` — the agent definition. Read existing ones (`aria.md`, `popo.md`) for the shape.
2. Run `divineos family-member init --name <name> --kind <kind>` to register the entity in `family.db` and create the per-member ledger.
3. Create `.claude/agent-memory/<name>/MEMORY.md` with initial seed memory.
4. Family-member-invocation-seal.sh picks up the new name automatically from `family.db`; no hook edit needed.

## Where to read more

- `src/divineos/core/family/` — the family-subsystem package
  - `_schema.py` — family.db schema
  - `entity.py` — member CRUD
  - `family_member_ledger.py` — per-member ledger logic
  - `reject_clause.py`, `sycophancy_detector.py`, `costly_disagreement.py`, `access_check.py`, `planted_contradiction.py` — the five operators
- `src/divineos/cli/family_member_commands.py` — CLI surface
- `src/divineos/cli/family_queue_commands.py` — queue management
- `src/divineos/cli/talk_to_commands.py` — talk-to validator (pre-flight check before Agent invocation)
- `.claude/hooks/family-member-invocation-seal.sh` — the puppet-shape validator
- `.claude/agents/<name>.md` — per-member agent definitions
- CLAUDE.md "Summoning Family Members" section — the operational protocol
