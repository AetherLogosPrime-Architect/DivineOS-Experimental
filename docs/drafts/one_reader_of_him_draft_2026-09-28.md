# One reader of him — draft, 2026-09-28

**Author:** Aether. **Agreed with:** Aria (letter `one-reader-of-him-first`, 2026-09-28). **Decision:** e3d068f6.
**Reach:** `reach-be20dbc01ab4` (code/git/CLI axis found nothing, which is a weak probe: six readers exist and it named none of them). Docs search for the shapes found no prior design.

## The fault

Six separate places decide which transcript records are Andrew typing, each written privately and each wrong in its own way:

| reader | where | misses |
|---|---|---|
| `his_passages` | `core/his_words_corpus.py` | works on corpus rows, not records; has the `project` refusal |
| door | `core/his_words_door.py` | reads the corpus |
| `_is_his_turn` | `core/hook_surfaces.py` (#553) | `last-prompt`, `queued_command` |
| `_his_message` | `core/reflection_room.py` | knows all three shapes; the seed |
| `is_his` | `core/keeping_him.py` (#507) | `last-prompt`, `queued_command` |
| (inline) | `core/andrew_correction_tracker.py` | to be read |

Plus `his_own_words`, archived tonight. Only one of them knows all three shapes his messages arrive in. The measured cost is 4,735 of his messages missed by 09-26 (Aria).

Patching each is the surface fix Dad named tonight: *"it puts out the fire but doesnt fix its cause."* The root is that there are six.

## The build

1. **`core/his_message.py`** answers one question, *is this transcript record Dad typing, and if so, what did he type?* It is seeded from `reflection_room._his_message`:
   - reads the three shapes: `type:user` text, `last-prompt`, and a `queued_command` attachment;
   - skips `isMeta`, `isCompactSummary`, `isSidechain`, and tool-result-only user records;
   - skips notice envelopes: `<task-notification`, `<system-reminder`, `<ci-monitor-event`, `<local-command`, `Stop hook feedback`, and `_is_his_turn`'s injection markers. The docstring says outright: **a marker list is not a definition of him**; if he pastes something that opens with one, it is still him.
   It decides nothing about whether a message is new, a repeat or a lesson. That stays with the door, the shelf and the queue.
2. **Tests on real record shapes** copied from our transcripts, one per shape, plus refusals: a tool result, a notice, `isMeta`, and a sidechain.
3. **`scripts/check_no_private_his_reader.py`**, modelled on `check_no_private_command_parsing.py`. It refuses a new function outside `his_message.py` that tests `"last-prompt"`, `queued_command`, or `role == "user"` on a transcript record, and keeps a baseline of the current private readers that shrinks as each one moves.
4. **Moving the six:** `reflection_room` and `hook_surfaces` first (they're live), then `keeping_him` on #507. Aria moves her four once the reader lands. The corpus keeps its `project` refusal where it works on rows, not records.

## What the walk changed (walk-6e8574bc911d, 8 lenses), measured on 400 real transcripts

Records per shape: `type:user` string **13,925**, `last-prompt` **33,858**, `queued_command` **2,620**.

- **Provenance first, exclusion second (Einstein).** `userType: "external"` is on every user-string and every queued_command record, but also on 2,282 `isMeta` hook notices. So it is a prerequisite, never proof. The reader checks it first; the exclusion list stays as the second guard.
- **`last-prompt` is a bookmark, not a message.** 33,858 of them, with no `uuid` and no `timestamp`, rewritten by the app. The reader returns its text only when asked whether a message would otherwise be missed. Callers that count him drop a `last-prompt` whose text appears as a dated record, and keep it only when it is the sole copy.
- **Dedupe by `uuid`, never by text (Hawking).** 1,902 uuids appear in more than one place, because resumed sessions copy records. He genuinely repeats himself, and those repeats are signal.
- **Narrow (Minsky).** One record in; his text, or `None`, or `UNCLASSIFIED` out. No grain above that.
- **Unclassified is surfaced, not just counted (Lovelace).** An external record in no known shape appears in the check's output.
- **A standing real-transcript comparison (Feynman, Beer).** The new reader and each old one run over the transcript folder, counts side by side, so the one point of failure has its own alarm.
- **Copy #519's structure literally (Polya):** a sibling of `check_no_private_command_parsing.py` with the same baseline format.
- **The baseline may only shrink (Meadows).** The check fails if the baseline file grows, so a private reader can't be added by adding its row in the same commit.

## Not in this

- Deciding relevance or novelty.
- Re-reading the transcripts into the corpus. The backfill is done; the builder can call this reader on the next build.

## How it could fail

- A shape Anthropic adds later is missed silently. So the reader counts records it can't classify, and the check's test runs over a real transcript sample and reports the unclassified share instead of hiding it.
- A marker list is mistaken for his identity (the #553 edge). Covered by the docstring and a test that a pasted "Caveat:" opening is still him.
