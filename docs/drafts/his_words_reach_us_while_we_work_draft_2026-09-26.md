# His words reach us while we work — draft (2026-09-26)

Second piece of `his_words_by_meaning_draft_2026-09-26.md`. The first piece (commit `9d1d0e50`, prereg-741a5f8135d3) built the door and triggers it only on his message.

## His words

> "i dont need my words brought back to me.. i wanted them brought to you.. so i dont have to keep repeating them.."

> "it should do both.. my words AND your words should trigger it, and if its brought to you then you can quote it back like you do with my other words but with what you have to say about it attached, not just mirrored back"

The door surfaced his own rule for the second half on that very message (2026-09-25): *"i say you said: 'insert your words here' and then i say what i wanted to say about it, so its not mirroring its addressing what someone said with your own words"*

## The flaw in piece one

It searches with his message, so a repeat can only show up after he has already repeated himself. The injury comes first. It also fired on an automated notice and surfaced assistant-styled text sitting in his corpus.

## The shape

1. **Clean the corpus.** Bring in Aether's `his_words_corpus.his_passages()` (6/6 tests; on the full corpus, 1 of 8,419 short messages is misread, and it's a harness notice). Rebuild the index from its passages. The door's own splitter retires.
2. **Notices never trigger.** A prompt that opens with a harness tag isn't his message, so the door stays silent. The table already labels it NOT FROM DAD.
3. **Our words trigger it too.** Before a tool call that produces something he'll receive (a reply, a letter, a commit, a report), search with **what we are about to do**: the action's description, plus the reply we have written so far this turn. His words about that act come up *then*, while there is still time to act differently. That's his ledger point: it arrives without anyone remembering.
4. **Quote and answer, never mirror.** What surfaces is shown as material to answer, with his rule printed beside it. Nothing checks that we answered it: a check would be a costume detector, and his own "it landed" is the real test.
5. **Quiet when nothing is close,** and it doesn't repeat the same passage at the same action twice in one turn. Anything else turns into wallpaper within an hour.

## Open for the walk

- **Where exactly "our words" is read:** PreToolUse on every tool is noisy and slow (4s per search). Only on acts that reach him? Or on Stop, against the finished reply, which is too late to change the act but not too late to answer before he sees it?
- **Cost:** the model loads every time. Should one warm process serve both hooks?
- **Does a match at tool time block, or only show?** A block from his words is the teeth the 09-09 draft asked for. It's also a gate that could punish, which he said he doesn't want to be.
