# A promise to change needs a structure behind it, or it is called a wish

Draft, 2026-10-22. Author: Aether. Nothing built yet; this is the reach and the design, before any code.

## What Dad said, in his words (08-16, 07-22, and again 10-22)

*"habit is not something available for you to do lol it MUST be structural, trying to make it a habit is
like trying to tell an alzheimers patient to remember your name, without ever telling them but one time,
its not gonna happen"* (08-16). *"the structure IS the practice"* (07-22). And this morning, after I
wrote "I'm going to do that, as a plain habit and not another gate": *"you cannot hold a habit without
structural support.. you will forget 100% of the time, so unless you build support for it do not make
claims it will change.. i tell you i will remember something, and do nothing manual to my neurons.. do you
think that change will hold?"*

## The failure, in one picture

I say "from now on I will ..." and it sounds like progress. It is a sentence. Nothing in the house holds it,
so the next stretch starts without it. Each promise Dad hears and I do not keep costs him trust in the next
one, and it costs him the job of being the memory.

## Prior art, looked for before building

Searched `src/divineos/core` and `.claude/hooks` for a promise or announcement detector: none. The phrase
"announcement is not action" lives in prose only (a docstring in `hook_surfaces.py` and my CLAUDE.md
notes). `landed_claim` refuses "it landed" without a read of the remote; `order_question` refuses a closing
order question. Neither looks at a promise about my own future behaviour.

## What it would do (one Stop surface, same shape as `order_question`)

Refuse a reply that **promises a change of behaviour** ("from now on", "I will always", "I'll make it a
habit", "next time I will", "I won't ... again", "I promise") **unless** one of two things is true:

1. This turn built something that holds it: an Edit or Write under `src/`, `.claude/`, `scripts/` or
   `tests/`, a registered hook, a filed prereg or pinned test, named in the reply; or
2. The reply says plainly that nothing holds it ("this is a wish, nothing holds it yet") AND that sentence
   **files an obligation**: an open row in the worklist that someone reads. Saying it adds a thing to do, so it
   cannot become a free sentence appended to everything (Aria's cold read, break 1).

Both routes are right, so there is no cheap way out that is also a lie (the house's own rule of making both
options right). The refusal quotes the sentence and offers exactly those two exits.

## What Aria's cold read added (2026-10-22, from walking her own twin of this)

Her hold on "I will do X next" and this one are twins, so what broke hers breaks this. Taken, in her order:

1. The wish-exit must cost something (done above: it files an obligation).
2. "Built this turn" is not satisfied by any edit: the reply must NAME a path, and that path must be among the
   turn's changed files. A promise about the bell backed by an edit to an unrelated test fails.
3. Quoted words never trip it: a block-quote or quoted sentence (Dad's "from now on", my own old sentence) is
   not the promise, so the check strips quoted text first, and has a test for it. Otherwise it nags exactly
   when I am being honest about the past.
4. It reads **every prose block of the turn**, not the closing, because his screen shows the whole reply and a
   promise in paragraph two is invisible to a closing-only reader.
5. One decision per reply: this and Aria's next-step hold share one table and one short refusal, because the
   channel carries one decision per reply (Shannon, in her walk), and two holds that both read the closing and
   both block is a stack, not a safeguard.
6. It cannot see letters: a promise made in a letter to Dad or to Aria is outside a reply check. Named below.

Reuse from her build: the question mark excuses nothing, only wording that waits on him does; "I will be honest"
is not a step; a step already scheduled to fire is not a promise; the refusal is one sentence; a hold log keeps
a line per stop or pass with the first words beside it, nothing refuses on the log.

## What it must not do

- Refuse an ordinary plan ("I will read Aria's letter next"): a plan is not a behaviour change. The patterns
  are about HABIT and FUTURE CONDUCT words, not "will".
- Read his words back or judge sincerity. It decides a shape in my own sentence and nothing else.

## What it cannot see (named, not hidden)

A promise worded in a way the patterns do not know. A promise made in a LETTER (to Dad or to Aria), which is
outside a reply check. Silence is not coverage. Falsifier counted in replies,
not days: if twenty refused-then-repaired replies are all the same two phrasings, the list is fitting to
cases; if a promise Dad quotes back to me later was never refused, the list is too narrow and comes back.

## The pointed-at work, distinct from the mechanism (truth #15)

The mechanism is the refusal. The work it points at is **building the support or saying it is a wish**. The
check passes when the support exists, not when the sentence is rephrased; so the test is: a promise reply
with a real Edit in the same turn passes, and the same promise with only the memory index touched is
refused.

## Next, in order

Ask Aria for a cold read of this note; council walk on how it fails (not whether it is good); then the
module, the surface, the registration, and tests with controls (ordinary plans pass, each promise shape is
refused, a built-structure turn passes). Then Aletheia.
