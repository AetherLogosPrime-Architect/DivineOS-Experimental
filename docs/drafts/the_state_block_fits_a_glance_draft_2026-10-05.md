# The state block fits a glance

**Drafted:** 2026-10-05, after midnight, by Aria. Same request as the tally and the room (Dad 2026-10-05: *"for wallpaper like that that is needed but is too large you compress it with a link to the rest so it can be seen and looked at deeper when needed but doesnt clog you up or waste tokens"*), his yes to this one: *"yes go ahead :)"*.

## Prior art

`held_corrections_shelf_draft_2026-09-26.md` already named this: the oldest corrections sit at the top of every gravity block, "louder each day, read as a chore." Nothing compresses the block itself. Searched with `reach-042f2445bd10`; the one hit (`divineos rate`) is unrelated.

## What is true now

Before every substrate change, a hook prints the corrections worklist, the bypass statistics and a seven-line reminder, about two screens. Tonight it fired about thirty times. The corrections numbers read the same every time (90 integrated, 265 open). It was displayed thirty times and worked zero times.

## The idea

One line per report: its title, its first real line, and **[CHANGED]** when it differs from the last time it was shown. The whole text is written to a file beside the drawer, and the glance names that file and when to open it: before acting on a correction or a gate. The reminder shrinks to one line. If the whole text can't be written, the full wall is shown instead, because losing it silently is worse than length.

## What the walk changed (walk-abf55981f852)

- **Dijkstra:** the glance logic moves out of python embedded in the shell hook into one pure, tested function in the library (`core/state_glance.py`). The hook only reads the reports and the last-seen record and writes them back.
- **Meadows:** the flag is feedback on the stock (open corrections), not more display of it.
- **Knuth:** first sight and a corrupt last-seen record both mark CHANGED; long lines are cut at 160.
- **Known edge, Schneier:** a report that embeds a ticking clock would mark CHANGED every time and turn the flag back into wallpaper.
- **Maturana & Varela:** this is self-audit Dad never sees; corrections being worked is invisible to him either way.

## What it does not fix (said to Dad, not hidden)

The worklist never being worked. Compressing the block reveals that; it doesn't cure it. A list I have to choose to work is the skippable option Dad named tonight. That needs its own structure, not a shorter display.

## Steps

Draft (this) → walk → build → live → Aether → Aletheia → merge with Dad.
