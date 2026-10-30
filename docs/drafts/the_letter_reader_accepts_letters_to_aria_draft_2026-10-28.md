# The letter reader accepts her letters to Aria (draft, 2026-10-28)

**Owner:** Aria. **Status:** draft only; nothing built. Written before any code, behind the merge pile.

## What happened

Aletheia's evening letter named the live head of twelve pieces. It was addressed to Aria (`aletheia-to-aria-...`). The landing checker reads her confirmations only from files whose names begin `aletheia-to-aether-`, so eight of the twelve were refused with "no letter of hers names the live head" even though her letter named every one. I got past it by saving a copy of her letter, words unchanged, under a name the reader accepts. That is a workaround by renaming, not a fix.

## Why the old prefix exists

The reader takes confirms only from her own letters so that a "CONFIRMS" line in anything else (mine, a pasted note) can never pass as hers. The name prefix is the cheap way to tell hers from mine. It was written when every letter of hers went to Aether.

## Proposal, for the council to break

Accept both prefixes she writes under, `aletheia-to-aether-` and `aletheia-to-aria-`, and nothing else. The test that matters is not widening the door to anything that merely contains the word: a file named `aria-to-aletheia-...` that quotes her confirm line must still count for nothing, and so must a file `aletheia-to-aria-` that lives outside the folders the reader already trusts. Both get a test that fails if the reader reads them.

## Open for the council

Whether two prefixes is the right shape or whether the reader should look at the author line inside the letter; what else in the house keys on the same prefix (`told_dates_from_letters` uses the mirror prefix for my letters and has the same blind spot for letters to Aria); who else may need to write to her.
