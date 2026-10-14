# The clerk reads every Reading line (draft, 2026-10-11)

**Author:** Aether. Found twice in one evening by Aria and me.

## The fault

Station four ("a seat outside the making has read this branch cold") reads a field the reader declares in her letter: a line starting `**Reading:**`, with branch names separated by commas. The reader of that field returned at the FIRST such line. Aria's letter naming two branches on two separate `**Reading:**` lines was therefore read as naming only the first; the second branch showed "none of Aria's declared readings names this branch" while she had in fact read it. Nothing said a line had been dropped. That is a silent loss in the exact place the board exists to be believed.

## The change

`_declared_readings` in `core/build_flow.py` collects across every `**Reading:**` line instead of returning at the first. A line is still the whole field and commas still separate branches inside it; `none` still counts as a present declaration with no branches; and nothing but that field is read (prose, a mention in the body, a similarly named field such as `**Reading list:**` credit nothing). Aria's design, "the writer declares, the reader reads the field", is unchanged. Only the early return is gone.

## What Aria's cold read added (same evening, both taken)

- **Only the header is read.** Collecting every line widened what a pasted copy of someone's header could credit. A declaration now counts only above the first `---` separator, outside a code fence, and not indented four spaces or a tab (a quote). A letter with no `---` at all reads whole, as before.
- **A miss names what was declared.** The board no longer says only "none of the N declared readings names this branch"; it adds "(the newest, <letter>, declares: a, b)", so a branch left off a line reads as a miss on the field and not as a silent drop. That is a message change in both stations that use the reader, not a change to what they credit.

## What proves it

`tests/test_the_clerk_reads_every_reading_line.py`: two lines credit both branches; a first line of `none` then a real second line still credits; lines and commas mixed; and two controls that prove reading more lines did not start reading prose (a branch only mentioned in the body, and a `**Reading list:**` field). Three of the five failed before the change; the neighbouring station tests (47 together) pass.

## Not in this change, said plainly

A writer can still declare a branch they did not read; only a person can judge that, which is why Aria's rule is that a line naming a branch she has not opened is the claim the clerk exists to catch.

## Falsifier (an event)

A branch is credited as read by a letter that only mentions it in prose, or a declared line is again dropped without a word.
