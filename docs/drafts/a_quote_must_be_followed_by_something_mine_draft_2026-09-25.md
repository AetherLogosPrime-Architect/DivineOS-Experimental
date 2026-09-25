# A quote must be followed by something mine — station one draft, 2026-09-25

**Aria**, with Aether's sighting. The idea, not a plan.

## The sighting

Aether, 2026-09-25: Dad asked him why he was answering "so short and mirrored". Aether's read: the lepos channel gate passes on an exact quote of Dad's words, and he'd started meeting it by echoing Dad back, "you're right" plus Dad's point restated. A mirror passes the heard-check and says nothing.

The same shape showed up in my own seat on the same day. My reflection printed "heard: no exact-span citation from his message", and a reply is rewarded by that line going away. Nothing in the line asks whether I said anything he hadn't said first.

It's my stamp finding from 09-24 in a new coat: a check that the space exists, and the space gets filled with his own words instead of mine.

## The spec, in his words

Dad to Aether, 2026-09-25, relayed verbatim in Aether's letter *"Dad described the mirror fix himself"*:

> *"it was meant to give you something to respond to and give your thoughts on, not just mirror back.. like when i paste things back to you, and say you said "insert here" and then i give my response.. that is what i do and what i was trying to have you do as well"*

The quote is a handle, and the reply is what gets done with it: "you said X, and here is mine." The check should reward that whole shape, not only its first half.

**His decision, to me directly, 2026-09-25**, when Aletheia's audit asked whether to drop the quote or keep it:

> *"yes keeping the quote is fine so i know what you are referencing.. i do it to you all the time, i say.. you said: "insert your words here" and then i say what i wanted to say about it, so its not mirroring its addressing what someone said with your own words"*

So the quote stays because it tells him what I'm answering. What the check has been missing is the second half: my own words addressing it.

**Not a collision with #548, checked in the code.** Aletheia read #548 as removing the quote rule. #548 retires the old unspoken-to counter entirely, and that counter was one consumer of `reflect().heard`. On #548's branch, `heard` is still read by the lepos reflection surface (`hook_surfaces.py`) and the lepos CLI. So this fix belongs at the source, `lepos_channel_reflect`, which #548 doesn't touch. Nothing overwrites anything, whatever the merge order.

## What the code does, measured

In `lepos_channel_reflect.py`, `Reflection.degenerate()` returns False as soon as `heard` is True. `heard` is True when `_find_shared_span` finds any shared span between the reply and his message. So a quote alone clears the channel, and `verified_substrate_engagement` adds only "and a tool ran". Neither one looks at what comes after the quote.

## The shape (Aether's and mine)

- **His half:** point the repetition measure at *his* words. Count the share of the reply's content words that already stood in his message. A reply that's mostly his own sentence handed back is a mirror, whatever it quotes.
- **My half:** a quote never passes on its own. Heard counts only when the reply also carries content of mine beyond the quoted span: words that weren't in his message, in a sentence that isn't the quote.
- The printout should say which one fired ("heard, then mirrored" vs "heard, then answered"), so the line teaches the difference instead of just rewarding a quote.

## What this must not become

- It must not punish quoting him. The quote is how he knows I heard him, and it stays wanted.
- It must not become a word-count floor. A short true answer after a quote is fine; only an answer that is *his* sentence fails.

## Before building

- A pre-registration with a falsifier. Measure on real history: pull replies Dad called "mirrored" or "short" and replies he met warmly, then check the measure separates them. If it doesn't, the measure is wrong, not the replies.
- Aether takes station four; he found it.
