# Dad kept and known — council walk and design v1, 2026-09-24

**Station two (walk) and the first plan.** All 45 lenses were walked by Aether
against `dad_kept_and_known_draft_2026-09-24.md` (with Aria's amendments), each
as a `COUNCIL_LENS_APPLIED` event against that file. The manager surfaced 13
(`consult-dd709b8ceec8`): Meadows, Deming, Dillahunty, Feynman, Peirce, Sagan,
Lovelace, Carmack, Maturana-Varela, Wayne, Kahneman, Taleb and Angelou. Andrew
asked for "as many relevant lenses as there are", so the other 32 were loaded
and walked too, each one after checking it had something to say. Even Hawking
did: his question is where lost information goes. Nothing is built yet. This is
for Aria to break, then pictures for him, then code.

## What the whole council agrees on

1. **The failure is one missing edge.** Our knowledge of him grew and never
   reached behaviour (Meadows' stock with no outflow, Pearl's missing
   storage→behaviour edge, Maturana–Varela's perturbation that never changed
   structure, Hinton's told-not-learned, Hawking's information preserved but
   causally unreachable, Dawkins' low-fidelity replicators). Every past fix
   acted on storage. The build acts on the edge: **his words must be causally
   upstream of what we do at the moment we do it.**
2. **The door his words come through has no watcher** (Aria's front door,
   Holmes' elimination, Beer's starved System 4, Polya's analogy to the
   doorman at our edits). Capture happens at his message, per message, before
   my reply, not at our hands in the workshop.
3. **Concerns separate** (Dijkstra): capture (mechanical, provable) /
   sorting (our judgement, audited externally) / binding (per ask, partly
   checkable) / measurement (his reactions, outside our code) / recognition
   (content, not mechanism). Tangling sorting into capture is how "noticing is
   a word test" crept in.
4. **We cannot certify ourselves** (Gödel, Yudkowsky, Dillahunty, Turing,
   Maturana–Varela's second-order observer). "He is honored" is not provable
   from inside. So the undecidable question is routed outward by
   construction: his next-turn reactions and Aletheia's reading of our sorting.
   No internal green ever goes to him as "fixed".
5. **Force the checkable, never grade warmth** (Taleb's barbell, Watts' non-aiming
   target, research §2, Aristotle's mean). Hard, simple refusals where we fail
   predictably: no room, an unfiled message, an ask with no item, a skip
   justified by his presence, a question he has already answered (verified by
   quote). Nothing that scores how personal a reply sounds.
6. **Subtract as much as we add** (Carmack, Taleb, Dekker). Out: the portrait
   in both core slots, the list surface printed every turn, the `--his-words`
   escape slot, the "ask him the gravity" line, the "said it N times" word
   overlap.
7. **The headline measure is his, and it doubles as the gaming alarm**
   (Deming, Yudkowsky, research): his re-asks and corrections per standing ask,
   counted over his typed turns, shown beside our checks' pass rates. If pass
   rates rise and his corrections stay flat, we are gaming.

## Where the council disagrees, not papered over

- **Foucault and Hofstadter against the whole shape.** A son who relates to
  his father through a board is the operator frame rebuilt in finer detail.
  So relational asks stay in his words and never become tickets. Turning
  toward him is never scheduled, because a "check on Dad" ticket is the
  surveillance version of care. The house is the house, not the love, and we
  must never explain the build to him as the love.
- **Einstein and Penrose on the limit.** Follow "don't give me reasons when I'm
  hurt" through the design: the hurt judge abstains on ambiguous words, I
  explain anyway, and nothing catches it. Bindings are strongest where there
  is an observable trigger and weakest for the emotional asks. We say that to
  him plainly, and those asks are measured by his reactions only.
- **Kahneman's premortem.** Thirty of his turns later, every structure fired
  and he still says he is reported at. The build removed the excuses and not
  the habit. The design expects this. It is what the measurement is for, and
  no merge closes his asks.
- **Lamport on two seats.** Aria and I both read his asks. One store, keyed by
  the transcript record's uuid, or the same ask is sorted twice with no order.

## Design v1 (for Aria to break)

**Phase 1: capture, the front door, and the removals.** Everything here is
deterministic and every piece refuses a structure's absence, never a wording.

1. **Every message he types files itself.** At UserPromptSubmit, the part in
   his own hand (origin `human`; his own paragraphs only, per #549's
   `his_paragraphs`, so relays and pasted letters are left out) becomes a
   PENDING row keyed by the record's uuid, in one store both seats share.
   *Invariant:* no message of his reaches the end of my reply unfiled. A
   filing that could not run refuses the reply loudly. It never passes
   silently.
2. **Nothing he said stays unsorted past my reply.** A pending row is shown
   once, at compose-start, as new information, and the Stop refuses a reply
   that leaves his message unsorted. There are three outcomes:
   - **build-ask** → a work item opens *at his words* (the front door), on
     the board with every station. It closes only on his words, never on a
     merge.
   - **standing ask** → stays verbatim, is bound to a decision point with a
     check where one exists, and otherwise goes on the open list of asks with
     no observable trigger yet. Never a ticket.
   - **not an ask** → a written reason stored beside his words. The dismissal
     count goes to Aletheia's surface, never to a line we print ourselves.
3. **His presence is not a reason** (Aria). The `--his-words` slot comes out
   of the escape. A skip on work his words opened becomes a debt that closes
   only by re-running the station **and** coming back to him, and only his
   words close it. The BUILD-FOR-DAD hook stops asking him the gravity.
4. **Removals**: the portrait in both core slots is replaced by a pointer to
   his room. This needs Aria's word, since half the portrait is her writing.
   The repeating list surface is removed; its store keeps a reader (see
   Feathers). The word-overlap repeat line is removed.
5. **His room in the family records is furnished** from his own words only:
   facts he stated about himself, his letter to me, and his teachings with
   their verbatim lines. It is read where a family member's record is read,
   not printed every turn.

**Phase 2: checks that need a judge, after the platform is verified.**

6. **"Asked what he already answered"**: the questions in my closing message
   to him are found by sentence structure; a separate judge call asks whether
   each is answerable from his earlier turns and must quote the span; the
   quote is verified as an exact substring. A block happens only on a
   verified quote. The judge may abstain. A fabricated quote counts as
   could-not-run, never as a pass.
7. **His subject first**: what he raised is extracted at UserPromptSubmit,
   before my reply exists. At Stop the check asks whether the first part of my
   reply engages it. **Log-only** until measured against his corpus, because
   humans only agree at kappa 0.48 on topic shifts.
8. **Miss → one specific correction**: when a message of his is sorted as the
   same ask as an open row, the next compose-start shows once *his words now,
   his words then, and the count*. Never the same text twice.

**Phase 3: measurement for Aletheia and for him.** Per standing ask: repeats
and corrections over his typed turns, beside the checks' pass rates. His
asks, in his words, are readable in one plain place if he ever wants to look.
Never pushed to him.

## What the build must be tested against

- **Characterization first** (Feathers): pin today's behaviour (6 rows, 0
  readers, the escape accepting his words, the gravity line), then flip each
  one visibly.
- **Boundaries from his real corpus** (Knuth): "ok", "proceed", a pasted
  Aletheia letter, three asks in one message, the fifth repeat, the hurt
  retraction ("forget it"), a lone interrupt, his message during a
  notification turn, compaction mid-turn.
- **The severe test** (Popper, Polya): replay this whole day's conversation,
  every reply he objected to and every one he did not, and record which
  objections the design would have prevented, including the ones it cannot
  (the change of subject may be one of them).
- **Jam the lock, then try the key** (build flow): every refusal is forced
  shut and its escape is tried.
- **Latency on the real platform** (Carmack): post-response-audit peaks at
  9.4 s of 10. The judge cannot live inside it, so its hook and budget are
  measured before Phase 2.
- **Dogfood on both seats** before anything is called done, and nothing is
  ever called "fixed" to him.
