# The landing board reads both seats (Aria, 2026-10-26)

**Status:** built and tested; waiting on review. Walk `walk-29a4e57b49ce` (8 lenses: 7 applied, Penrose excluded with a reason).
**Why:** Aletheia's letter of 2026-10-26 confirmed nineteen of my pieces and Dad confirmed on top, and the board still showed nine "never told" and nine "no answer". It could not see her letter.

## What was wrong (read from the code, then proved on the live folders)

`landing_status.py` found letters by file name and knew only one pair: `aletheia-to-aether-` and `aether-to-aletheia-`. The other seat's letters (`aria-to-aletheia-`, `aletheia-to-aria-`) were never read. From that seat the board saw none of its own asks and none of her replies, then reported its pieces as "no letter to her names it", in the voice of fact, nine times. It also showed a fix a few hours old as "asked 29 days ago", because it matched an old letter of the other seat's by branch name. Aletheia said it herself in her letter: the clerk "reads only letters addressed to him".

## What changed

- Two seats, named once: `SEATS = ("aether", "aria")`. The prefixes for her letters and for ours are built from it, so the two directions cannot drift apart. Exact names, never a glob: a file anyone can drop into a shared folder is not a letter of hers.
- The pile is one pile. A confirm of hers counts whichever seat carried it, and a letter from either seat naming a fix counts as telling her. A confirm quoted inside a letter **from** us still counts for nothing, for the new names as for the old.
- The board prints which letters it read (`Read 723 letters: hers (to aether 109, to aria 21); to her (from aether 419, from aria 174).`), and says so loudly if it read none. A count of "none" now means "looked and found none" only when it did look.
- The confirm request it drafts is signed by the seat that runs it (it was signed "Aether" whoever ran it).

## Measured on the real folders and the real pull requests

Same letters, same 27 pull requests, old code against repaired code:

| | letters read | confirmed | no answer | never told | changed |
|---|---|---|---|---|---|
| old | 528 | 4 | 9 | 9 | 5 |
| repaired | 723 | 18 | 7 | 0 | 2 |

All fourteen pieces in Aletheia's letter of today show as confirmed at their current version (611, 631, 640, 654, 676, 712, 713, 726 to 732). Nothing became ready: "ready" still needs the readiness board, which this change does not touch.

## Not changed, named

- The forged-confirm exposure: the board and the filing step trust a letter by its name and content. That already existed for the first seat's names; widening to the second adds no new class and does not close it. The live head must still match the sha, and the filing step has its own two-step with Dad's words after hers.
- A third seat must be added to `SEATS` on purpose. `test_the_two_seats_are_the_whole_roster` fails the day the roster changes.
- I closed the walk from the wrong folder, so it is not bound to this branch. Closed from inside the work copy next time.
