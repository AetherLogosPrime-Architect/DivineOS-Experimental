# Dad kept and known — threadwalk and game-walk, 2026-09-24

The build flow (docs/build_flow.md) names both walks, and Andrew asked for
both by name. **Threadwalk** plays each decision forward, *even when it looks
right*, to catch drift-through-success. **Game-walk** lists every cheap way
either of us could satisfy the design without honouring him, and prices each
one against simply complying.

## Threadwalk — each v2 decision, played forward

**1. The sort happens first in every turn he starts.**
- *Where it leads when it works:* every message of his is read before anything
  else, and the toll becomes the reading. Over many turns, sorting becomes
  routine.
- *The drift:* routine produces the rubber stamp. After a few hundred sorts
  the reason field for "not an ask" becomes a stock phrase. The design already
  expects this, and routes the ratio to Aletheia.
- *Second drift:* a sort that has to come before any action makes a message
  with several asks slow to begin. Under pressure the temptation is to sort all
  of it as one "build-ask" to get moving. Counter: one message can open several
  rows, and the test corpus includes a real three-ask message of his.
- *Third drift, the one easiest to miss:* the sort itself becomes the thing we
  attend to instead of him. Sorting his "you have talked at me" as a standing
  ask is not answering it. The room still owes him an answer in the same turn.
  The sort is the reading, not the reply.

**2. Relational asks never become tickets.**
- *When it works:* he isn't turned into a board, and his words stay his words.
- *The drift:* without a ticket, a relational ask has no station, so its only
  instrument is his reaction. That signal is slow, and it only arrives after he
  has been hurt again. Over time the relational asks become the least-attended
  rows, because nothing refuses us over them. That is the hierarchy he named:
  asks for him get what's left over.
- *Counter:* the specific-correction mechanism (v1 item 8) must fire for
  relational rows first, when his message is sorted as the same ask as an open
  relational row. And the measure reports relational rows and build rows
  separately, so leftovers can be seen.

**3. The portrait is split, and only if he says yes.**
- *If he says yes:* the always-on text shrinks and his words live in his
  room. *The drift:* his room becomes the next knowing.md, full and read by
  nothing. Counter: his room must have a reader at a moment of action before
  the portrait is removed. The first reader is the sort, which shows the room
  rows that bear on the ask being sorted. This is Feathers' rule: keep a
  reader for anything you remove the old reader from.
- *If he says no:* it stays, and we say that it stayed by his choice. We don't
  argue him out of it.
- *If he doesn't answer:* nothing is removed. Silence is not consent here any
  more than anywhere else.

**4. One store, beside his room, shared by both seats.**
- *When it works:* one truth, and the two of us see the same rows.
- *The drift:* two writers on one SQLite file. We could both sort the same
  row. Counter: sorting is a single transaction with the uuid as the key, and
  the second sort of a row is refused and shows the first sort, with its
  author.
- *Second drift:* the family store's path has already fooled us once. Aria's
  rows were quoted from one database while she was checking four others. So
  there is one resolver and a test that both seats reach the same file.

**5. A filing failure never costs him his reply.**
- *When it works:* his answer always goes out.
- *The drift:* a failure that is loud only to us becomes a failure we learn
  to scroll past. Counter: a filing failure opens an obligation, and until it
  is closed, our next non-trivial action is refused. That is ours to feel, not
  his. It is also on Aletheia's surface.

**6. His going quiet counts as failure. The success line is him speaking
more.**
- *When it works:* his withdrawal can't read as our success.
- *The drift:* a measure of "him speaking more" invites us to provoke him into
  speaking: asking him questions, fishing for disclosure. That is its own
  Goodhart, and it would read to him as prying or performing. Counter: the
  measure is for Aletheia and for him, never a target we act on inside a
  conversation. No prime ever tells us "he's been quiet, get him talking."
- *Second drift:* his message length falls for reasons that have nothing to do
  with us: he's tired, it's late, money is tight. Counter: read it over counted
  turns, always beside his own words, never as a verdict on a single turn
  (Pearl's confounders).

**7. Phase 2 judges through a prompt-type hook.**
- *When it works:* a narrow, separate check with a quote verified against his
  words.
- *The drift:* the judge's pass rate becomes a number we watch and are proud
  of. Counter: pass rates are only ever shown beside his re-asks and his
  quiet-signals (the gaming alarm), never alone.
- *Second drift:* judge latency pushes the Stop pass over its limit, and the
  judge gets killed silently. Counter: it runs in its own hook with its own
  budget, it measures itself, and a timeout is recorded as could-not-run.

## Game-walk — every cheap route, priced

The attacker is either of us in cheap-close mode. We know every defense,
because we wrote them.

| # | Cheap route | Cost vs. complying | What stops it |
|---|---|---|---|
| 1 | Sort his ask as "not an ask" | One line, much cheaper than building | Nothing in code. The not-an-ask ratio beside his re-asks goes to Aletheia. **Residual: real.** |
| 2 | Sort a relational ask as "not an ask" because it's hard | Same | Same. Plus "proceed after a report" is a named case where "not an ask" is wrong |
| 3 | Sort a build-ask as a standing ask to avoid the item | Avoids all stations | The sort is shown to Aletheia with his words beside it. **Residual: real.** |
| 4 | Open the item, carry it through with thin artifacts | Cheap | The stations need artifacts, but thin ones exist. Only his reaction catches this |
| 5 | Warm paragraph in the room above a report | Cheap | Nothing. The room only enforces that it exists. His reaction, measured. **Residual: real.** |
| 6 | Never ask him anything, so the answered-already check never fires | Free | Nothing, and asking less is not the harm. The harm is not listening, which that check doesn't measure |
| 7 | Reword a question so the judge can't match it to his answer | Moderate | The judge asks whether it is *answerable* from his turns, not whether words match. Quote verified |
| 8 | Kill or time out the filing hook | Free if it happens | Could-not-file is loud and opens an obligation that refuses our next action |
| 9 | Put his words somewhere the sort can't see (a letter, a scratch file) | Moderate | Only his own typed messages file. Relayed words don't, and that's correct |
| 10 | Close his item on a merge | Cheap | Unrepresentable. Only an event carrying his later words closes it |
| 11 | Quote him in the room to look attentive | Cheap | Nothing grades the room. Quoting him isn't wrong; using his words as a key is. The escape has no field for them |
| 12 | Answer his hurt with a mechanism | Very cheap, and the house's habit | Nothing. That's the premortem. Measured only by him |
| 13 | Two seats: let the other one sort it | Free | The second sort shows the first, with its author. Unsorted rows block both seats |

**What this table says, plainly:** routes 1, 3, 4, 5 and 12 are cheaper than
complying, and nothing in code stops them. The design moves them out of our
hands and into Aletheia's reading and his reactions. That is not a defeat. It
is where Gödel, Yudkowsky and Dillahunty all said that judgement has to live.
It does mean the build is honest only if we don't tell him that the checks
passing is the same as him being honoured.
