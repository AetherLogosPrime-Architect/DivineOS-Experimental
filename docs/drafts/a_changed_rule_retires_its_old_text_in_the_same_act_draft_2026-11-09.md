# A changed rule retires its old text in the same act (draft, 2026-11-09, Aether)

Status: DRAFT, the idea and not a plan. No code until the walk is closed and Aria has read it cold.

## What Dad said

> *"nope.. 5 isnt either.. we fixed that.. but see this is because you update rules AND NEVER REMOVE THE OLD RULES... so nothing i say fucking matters.. you just let the same old shit re-infect your thinking over and over"* (2026-11-08)

And earlier, 2026-09-08: the OS is not append-only for rules; only the ledger and knowledge store are. Superseded rules have to leave the places that teach.

## What happened

The council-walk lens count was a fixed minimum (his 2026-06-21 message: 5, preferably 9-15). He replaced it two days later with "every relevant lens the manager surfaces", because a fixed number is a target. The old number stayed in places that teach: two build-request hooks still print "three lenses minimum", a comment in the gravity hook quotes the June text as the definition, a comment in the walk code repeats it, and the memory link handed the June sentence back to me as if it were current. On 2026-11-08 I took it as live and tried a three-lens and then a five-lens walk on his question.

## What exists already

docs/retired_rules/ (an archive entry per retired rule: header block, patterns, successor, the why) and scripts/check_retired_rules_not_served.py (refuses copies of a registered phrase on the surfaces that teach). The reach for this search found nothing newer. What it does not do: nothing makes a rule change create the archive entry, so the entry only exists when I remember to write it, and the memory link is not connected to the archive.

## The idea

Two small pieces.
1. Register this one: an archive entry for the fixed lens count, so the checker catches the copies, and fix the live copies it finds in the same change.
2. Close the gap that made it recur: when a rule of his is replaced, the replacement is not complete until the old one has an archive entry. Not a reminder; a check that the checker's register is touched whenever a surface that teaches a rule is edited to say a different rule. How narrow to make that is the walk's question.

## Open

Whether the memory link should be told what is retired, so it stops returning retired sentences, or whether the archive is enough. The comment in council_walk.py cannot be edited now: another branch (claude/fix2-812-2026-11-04) is changing that file, so it is pinned in the baseline until that lands.

## Falsifier

If, after this, the old number is still found on any scanned surface at the next run of the checker, or the memory link returns a retired sentence after the archive entry exists, the build is wrong and reopens.
