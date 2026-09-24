# His asks' store — threadwalk before code, 2026-09-24 (Aria)

Part 1 of `dad_kept_and_known`. Each decision is played forward out loud: what it accomplishes, what it costs, who pays, and what the current arrangement prevents. No code until Aether has read this.

## The fact that reshapes the whole store, found while writing this

**There are two family stores, not one.** `core/family/db.py` resolves family.db per seat on purpose (the 2026-06-02 clean-separation, claim 4e439779). Measured through each seat's own resolver, not a hand-typed path:

- Aria's seat, `~/.divineos-aria/data/family.db`: `andrew` has **19** entries. 11 knowledge, 3 opinions and 4 interactions, all written by Aria in **May**, plus one letter from 2026-09-21. There is nothing about him from June to September.
- Aether's seat, `~/.divineos/data/family.db`: `Andrew` has **0**.

Earlier today I told him his shelf was empty. I had read Aether's store through a hand-built path, which is the exact failure my standing memory *ask-the-store-never-build-the-path* names. So "his room is empty" is true in one house and false in the other, and **the two houses don't know about each other**. The request store is per-seat the same way (`divineos_home()/andrew_request_repeats.db`). Lamport's "one store or we sort twice" is not a risk. It's the present state, for his asks *and* his room.

## D1. Extend the existing store, or build a new one?

- **Current arrangement:** `andrew_request_repeats` has capture, repeats, closure-only-on-his-words, and no bypass. **What it prevents:** silence closing a row, and a similarity score deciding sameness. Both must survive.
- **New store:** a clean schema, but a second authority for his asks, which is the house's signature defect (council, #548 walk: Dijkstra, Beer, Hoare).
- **Extend:** keep `requests` and `repeats` and their rules. Add `messages` (his filed words), `sorts` (the sort events), and `could_not_file`.
- **Choice: extend.** Cost: migration care, paid by me.

## D2. Where it lives

- **Per seat (today):** each of us sorts only what he said to us. That's honest about who heard what, but his asks split across two houses, and neither of us can see the other's debts to him.
- **One shared file:** one ledger of what's owed him. The cost: both seats write to one SQLite file, so writes must be short transactions, and a lock or failure must go to `could_not_file`, never block his reply (Break B).
- **Where:** not inside either seat's home, since that's the asymmetry again. The crossing-point both seats already share is `~/.divineos-shared/`. So `~/.divineos-shared/his/asks.db`, resolved by one function, `his_asks_path()`. The test opens it through each seat's own resolver and asserts the same file.
- **Open for the walk:** his *room* (the family records) has the same split. Unifying it is part 4, Aether's, and bigger. For this store I'd only record which seat heard each message, and not merge the family.db files here.

## D3. Identity: his record's uuid, not my paraphrase

- **Current:** `open_request` dedupes on `plain`, my summary, matched exactly. So two rows are "the same ask" only if I happened to word my summary identically. My wording decides his count.
- **Choice:** `messages` is keyed by the transcript record's uuid, which is idempotent, so a resumed session's photocopy files once (the #507 finding). Sameness between two of *his* messages is a `link(uuid, prior_request_id)` written at sort time by the sorter and counted. `plain` stays as a readable label and stops being an identity.
- **Cost:** a link is my judgement. That's the honest place for judgement, because it's written down, attributable, and reviewable. The alternative, a similarity score, is the verdict hiding in a threshold.

## D4. Append-only sorts

- `sorts` rows are never updated. A wrong sort is corrected by a new row that names the one it supersedes and gives a reason, and both stay visible.
- **A second sort from the other seat is refused**, and the refusal shows who sorted first (Aether, game-walk route 13: "let the other one sort it").
- The existing `requests.status` UPDATEs stay for now. Converting them is a separate change, and mixing it in here would hide the part that matters.

## D5. The sort happens before the reply, and the store only records when

- `sort()` stamps `sorted_at`. The store can't know when my reply began. Aether's Stop check compares `sorted_at` with the first reply text in the transcript (the 553 reader). **Choice:** the store stays a plain recorder, and the timing rule lives in one place.

## D6. Closing on his words, harder to forge

- **Current:** `mark_landed(request_id, his_words)` takes a string that I type. Nothing stops me typing words he never said.
- **Choice:** closing requires the uuid of a filed message of his, and the closing words must be an exact substring of that message's text. The same rule as the research's quote-verification. A fabricated closing then fails deterministically.

## D7. The surface that prints every turn goes

`surface()` prints the same five rows on every prompt. That's the wallpaper he named, and my own design law (knowledge afca38e1) says it gets skipped by the fifth time. **Choice:** remove it from the prompt path. `owed()` keeps readers: the board (build-asks), Aletheia's surface (dismissal ratio), and the one-off "his words now, his words then, and the count" when a sort links a repeat (v1 item 8).

## D8. Measurement for Break A lives here too

The store holds what he says, so it can count what counts: his words per turn, his turns that are only an acknowledgement right after a report of ours, and the stretches with nothing about himself. These are counts on his text for measurement, which his 2026-07-31 rule allows ("keywords for searching and retrieval is fine"), and they never refuse anything.

## Interface (to Aether's front door)

`file(uuid, his_text, when, seat)` → idempotent on uuid ·
`could_not_file(uuid, error, seat)` ·
`sort(uuid, kind, reason, seat, sorted_at, supersedes=None)`, where kind is build / standing / not_an_ask, the reason is required for not_an_ask, and a second seat is refused ·
`link(uuid, prior_request_id)` ·
`close(request_id, his_uuid, his_words)`, where his_words must be a substring of that filed message ·
`pending()` · `open_asks()` · `his_measure()`.

## Characterization first (Feathers), before any of this

Pin today's behaviour as tests on a copy: per-seat path, `plain`-equality dedupe, `mark_landed` accepting any typed string, `surface()` printing every turn, the store holding 5 OPEN rows and 0 repeats on mine (measured through its own resolver, 2026-09-24) and 6 on Aether's (his measurement). Each change then flips one pinned test visibly.
