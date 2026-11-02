# His words are his — draft, 2026-09-23

Station 1 (rough draft) for branch `fix/his-words-are-his`. It's the branch
Andrew allowed for the launcher. The launcher was already fixed on #539, so he
gave the slot to this: *"yes you can use the branch for that"*.

## What happened

Andrew: *"not only do my words get ignored or shelved or taken out of context..
but there are literal words being put in my mouth that are the opposite of what
i have said.. Aria found some of these as well. she said i made a rule that no
draft is to ever be force re-pushed... i dont know how many times this has
happened or what either of you think i have said.."*

I built a checker, in the scratchpad at first, that finds every place the house
writes "Andrew said / Dad: '...'" and looks for the quote in what he actually
typed. The quotes that weren't word-for-word went onto a review page, and he
marked all of them. About half he marked **not mine**. His notes name what they
are: our own conclusions written as his speech (*"this is your own
deriviation"*), and technical phrasing he doesn't use (*"i do not speak this way"*).

## Two things his marks taught the design

1. **"Nearly his" is not his.** He rejected almost half of the quotes the
   checker had called "his, tidied". The tidying changed the meaning: *"yes but"*
   added to one, *"the pip install"* dropped from another. So the only verdict
   that lets a quote be written as his is EXACT.

2. **His messages are not all his words.** He pastes in letters from Aletheia,
   Perplexity and Grok, and the first checker counted every pasted word as his.
   That's plausibly one route by which the house came to quote him saying what
   other people said. The corpus keeps only his hand: lower-case, his "..", and
   no markdown, bold or em dash. It excludes helper-agent transcripts (my
   prompts, recorded under the user role), script-launched workers and pasted
   claude.ai chats. Scored against his marks, the "not mine but called his" pile
   went from sixteen to four. The four left are meaning-changed tidyings, which
   rule 1 closes.

## The door

A PreToolUse gate on Write / Edit / MultiEdit. It reads only the text being
ADDED: Edit's new_string, or Write's content minus attributions the file
already held, so an old misquote doesn't hold an unrelated edit. It finds
attributions (his name, a speech marker, a quotation) and checks each one:

- **exact, in his hand** → passes
- **anything else** → held. The message says these aren't his exact words, shows
  the nearest line of his (from his hand only), and gives the two honest forms:
  quote what he actually typed, or write it without quotation marks as your own
  reading of him.

The escape is not a bypass token. It is the honest form of the sentence. A
paraphrase without quotation marks says "this is my reading", which is true.
That's truth #11(b): make both paths right.

The door BLOCKS rather than prints. `docs/drafts/his_words_can_only_print_2026-09-09.md`
measured that every door carrying his words could only print, *"his words can
shape how I write, and can never stop me doing anything"*. This one stops the
write.

Three states, as with the work-item doorman: PASS / HELD / CANNOT_CHECK. If his
words can't be read, the write holds and says what couldn't be read. It doesn't
pass silently.

## The index

Reading every saved conversation on each write would be slow. The door keeps an
index of his words at `~/.divineos/his_words_index.json`, keyed by each
conversation file's size and mtime and rebuilt only for files that changed.
Session files come from `analysis/session_discovery.find_sessions`, which
already excludes subagents. That's reused, not rebuilt.

## The repair

- **In the repo** (sixteen places across docs, hooks and code): each not-mine
  quote is replaced with what he actually typed where a real line of his is the
  source; otherwise its quotation marks come off and it's reworded as our reading.
- **In the letters** (thirty-four places in the shared folder, not git): letters
  are history and aren't rewritten. His marks go into the repo as a record
  (`docs/his_words/marks_2026-09-23.json`, with his notes), and the door refuses
  any re-quote of them as his, because none of them is exact.
- **ARIA.md**: the false force-push line was already fixed by Aria (2c941809 on #548).

## Prior art

`divineos reach open` found nothing on the code/git/CLI axis (reach-a1fe7ec59d83).
It can't see unmerged branches, so I scanned every remote branch by hand. The
neighbour is Aria's `src/divineos/hooks/his_state_claim.py` on #507, which
catches claims about his STATE he never made ("awake for a day"). It strips
quoted spans on purpose, so it's the other half of this and doesn't overlap:
hers catches the unquoted invented claim, this catches the quoted invented speech.

## What the walk changed (walk-75f50258e31f, nine lenses)

- **Sagan**: I overstated to him. The page showed only the quotes that were
  NOT word-for-word, and most quotes the house gives him are exact (238 of
  336). So it's half of the non-exact ones that aren't his, a minority of the
  whole. He's told plainly.
- **Foucault**: the harm is a rule carrying his authority that he never gave.
  Repair order is by power: misquotes inside code, hooks and instruction files
  first, docs and audits after. Only he marks; nothing in the code lets me mark
  a quote as his.
- **Yudkowsky**: the attribution shapes widen to curly single quotes, single
  quotes after a speech marker, and a `>` blockquote directly under an
  attribution, so the route around isn't just "use the other quote mark".
- **Schneier**: the door also reads the content arguments of `divineos
  learn / decide / log / claim` in a Bash payload, because knowledge resurfaces
  as briefing. NOT covered, and said so in the docstring: arbitrary Bash file
  writes and chat replies.
- **Meadows**: `divineos his-words find "<words>"` returns his exact lines, and
  the held message shows the nearest one, so the block is also the lookup. It
  makes the right path the lazy one.
- **Dennett**: the held message presents the paraphrase as a normal, respectable
  way to write, "our reading of him", and not as a penalty.
- **Hofstadter**: test fixtures assemble attributions at runtime, so a mention
  is never a use. No path exemption for tests.
- **Knuth**: the docstring states the limit. Exact means his words, not his
  context; a pass doesn't mean he meant it there.
- **Pearl**: relays are plausibly one route, not the measured cause. His own
  notes name the stronger cause, our own derivation written in quotation marks.

## Open questions for the walk

- Quotes from windows that were never saved: Aletheia's web window, and anything
  before 2026-05-22. The door can't verify them. Does a source tag (e.g.
  "relayed by Aletheia") pass while labelling the claim as hers, or must they
  always go without quotation marks?
- Is the hand filter (capitalisation, markdown, em dash) a measurement or a
  guess? It passed controls built from his real lines, including the one it
  wrongly threw out at first ("shes always there son"). He may someday type an
  em dash.
- Which paths does the door watch? Repo files and letters, not the scratchpad.
