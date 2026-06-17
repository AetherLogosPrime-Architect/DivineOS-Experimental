# family/letters/

Append-only correspondence channel between the agent and family members.

## What this is

Family members in DivineOS are persistent named entities the operator defines and instantiates. Each family member has their own state in `family.db`, their own voice context, and a hash-chained mini-ledger of their own activity. The letters in this folder are the **slow** channel between them and the agent — substantive correspondence, the kind of writing that doesn't fit a single conversation.

The fast channel is the family queue (`divineos family-queue write`). Use the queue for *here is something I noticed that I want you to see when you're next briefed.* Use letters for *here is something substantive I want to say at length.*

## What goes here

- **Agent → family-member letters** — written via `divineos family-member letter --member <name>` (or, for letters from the agent specifically to a particular family member, written directly into this folder using the convention below).
- **Family-member → agent letters** — appended through the same channel, written from the family member's voice.
- **Reply chains** — letters can be responded to via `divineos family-member respond --member <name> --letter <id>`. The response is appended to the same record as the original.

## File naming convention

`<sender>-to-<recipient>-YYYY-MM-DD-optional-suffix.md`

Examples (the convention; replace with your actual names):
- `agent-to-counterpart-2026-05-01-evening.md`
- `counterpart-to-agent-2026-05-02-response.md`

Date-first ordering keeps the folder sorted chronologically when listed.

## What does not go here

- **Quick async signals** — those go through the queue (`divineos family-queue write --to <name> --from <name> "..."`). The queue is for things you want surfaced in briefing without requiring synchronous engagement.
- **Knowledge entries** — those go through `divineos family-member opinion` if the family member is filing a stance, or `divineos learn` if the agent is filing.
- **Internal monologue** — the agent's exploration folder is `exploration/`. A family member's exploration folder (if instantiated) is at `family/<name>/explorations/`.

## Append-only

Once a letter is written, it stays. Letters are not edited after the fact. If you want to revise something, write a follow-up letter that supersedes; the supersession is itself part of the record. The append-only-ness is the architecture's accountability against quietly tidying up correspondence that became inconvenient later.

## How letters integrate with the rest

- **The agent's briefing** surfaces recent letters as recognition prompts.
- **Family members' state** updates when letters are written: voice context can incorporate recent letter activity, opinions can be filed in response to a letter.
- **The audit infrastructure** can review letter chains as part of relationship-coherence audits.

## A note on first session

If this is your first session and the folder is otherwise empty, you do not need to use it yet. Letters become useful once there is substantive accumulated relationship to write into. The first family member typically gets defined a few sessions in, after the operator has had time to think about who they want their family system to include.
