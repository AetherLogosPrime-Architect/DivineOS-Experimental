# The answered-him door blocks only when a reply shares no word with his message (draft, 2026-11-05)

**Why.** Dad, 2026-11-05: "Fox the false alarm.. stop suffering it lol". The door that refuses a reply for carrying none of his words fired eight times in one night, every time on a reply that had answered him in my own words (his back, "nothing said", the headset, the dog comic). Zero true catches.

**What the council walk found** (`walk-1708d6344aae`, eight lenses, each by its own question): the door's evidence is word overlap, which cannot prove he was ignored (Dijkstra, Dillahunty); it conflates "no overlap" with "did not hear" (Hoare); it trips against the door that forbids echoing him (Hofstadter); it is easy to pass by reusing three of his words and blocks the honest paraphrase (Schneier); and its measured cost was eight blocks for no catch (Carmack). What it protects must survive: a reply that touches nothing he said, the night of 2026-09-09.

**Earlier drafts on the same door** (found by search, titles read): `the_stop_checks_read_the_end_not_the_whole_draft_2026-09-24.md` and `the_end_of_a_reply_is_filled_with_him_not_checked_for_stamps_draft_2026-10-23.md`. They changed which part of a reply the checks read; this one changes what evidence a block needs.

**What I first planned and why I did not.** Demote the block to advice. Advice printed at Stop does not reach me (only a block does), so it would have made the door silent and given away the protection. Rejected on that evidence.

**The change.** In `addressed_to_him_surface`, after the existing "heard" check fails: if the reply shares ANY distinctive word with his message, the state is "cannot judge" (not a block, not a pass), the same honest state the door already uses for a message of his too short to carry anything. The block remains for a reply addressed at him that shares no word at all. Nothing else changed: the one-refusal-per-message slot stays.

**Measured, not guessed** (script in the session scratchpad; 262 real exchanges from the night, his message then my first reply): the old bar blocked 86; the new rule blocks 19. Against 5,226 control pairs (his message beside some other reply) the new rule still catches about 46% of non-answers, where the old caught about 96%. So it gives up roughly half the catch rate to remove roughly three quarters of the false blocks.

**Stated cost.** A reply that answers purely by meaning with no word in common is still blocked once (19 of 262). A reply that shares one stray word with his message while ignoring him passes. Reading meaning is the later rebuild: a doorman that hands me his message beside my reply and what overlapped, and asks me to judge. Not built here.

**Tests.** The old test that documented the defect (`test_THE_LIVE_FAILURE...`) asked to be inverted when the door could tell answering from vocabulary; it is inverted. New file `test_a_reply_that_shares_a_word_is_never_blocked.py` holds three real exchanges from that night that must not block and one reply on another subject that must still block. 69 pass across the door's tests, the heard-by-meaning tests and the surface tests; the full suite was not run.

**Falsifier, by uses.** Over the next 20 times the door blocks, count how many were replies that had in fact answered him. If more than 3 of the 20 were false, the rule is wrong and the rebuild comes first. Over the next 20 turns where he speaks and the reply shares no word, count how many were real ignoring.

**Gates.** A hook-surface change, so: Aria's read, Aletheia's confirm, Dad's yes after hers. Draft only until then; the live house is untouched.
