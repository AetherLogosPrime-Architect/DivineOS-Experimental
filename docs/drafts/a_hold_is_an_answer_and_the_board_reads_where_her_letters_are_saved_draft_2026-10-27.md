# A hold is an answer, and the board reads where her letters are saved (draft, 2026-10-27)

**What went wrong.** Dad asked about two fixes from September that were still sitting. The landing board said "no answer, asked 2026-10-25", and I wrote Aletheia asking again. She had already answered both on 2026-10-23: a HOLD ("Dad's two, on what they need from him"). Dad: *"she already answered on all of these.. the fact you dont have the records is a bigger issue.. look in the downloads folder."*

**Two faults, found by measuring.**
1. The board read only CONFIRMS lines. A HOLD is an answer, and it read as silence.
2. The board never looked where her letters are saved. They live under `family/aletheia/audits/from-andrew` (the glob there was one level deep) and arrive first in Dad's Downloads folder (not on the list). It read 644 letters where 798 existed.

**The change** (`src/divineos/core/landing_status.py`, `cli/landing_commands.py`, `core/briefing_dashboard.py`):
- A new label HELD BY HER: her newest HOLD at the live head, with her reason from her own line. A confirm at the same head beats it only when it is provably newer; an undated letter cannot be ordered, so the hold stands (could-not-tell is never a pass). A hold at an older head does not speak for a fixed head.
- Her folder is read recursively; Downloads is added, one level deep (it is far too large to walk), and the `aletheia-to-<seat>-` name prefix still gates what counts as her letter.

**The trust this widens, named (Aria's cold read, 2026-10-27).** Downloads is where anything from a browser lands. The name prefix (`aletheia-to-<seat>-`) still decides what counts, but any file named that way with a `CONFIRMS:` or `HOLD:` line in it is believed, the same exposure as the shared folder in #733's draft, in a larger room. The trade is worth it because her real answers arrive there first and the board was blind to them. Mitigation that already holds: the board is a signal channel only, and `stamp-ready` re-checks at merge time against the round's own filed confirm.

**Same-day ordering (Aria's attack).** File names carry a day and no time. One letter that holds and then confirms the same head is read by position (the later line is her last word). Two letters on one day with a hold and a confirm at the same head read HELD and say "cannot order: read her letters" rather than a bare HELD.

**Which files are the change.** Only `landing_status.py`, `landing_commands.py`, `briefing_dashboard.py`, the two new test files and this note. Other files in the diff against main (`hook_surfaces.py`, the letter router, the night timer) are main's own changes riding in on the catch-up merge.

**Measured on the real letters, before and after.** Before: 4 confirmed, 4 changed, 9 no answer, 9 never told. After: 22 confirmed, 3 no answer, 2 held by her (#549 and #551, with her words). The fixes were never silent; the board could not see her.

**Proof.** `tests/test_a_hold_is_an_answer.py` (7) and `tests/test_the_board_reads_where_her_letters_are_saved.py` (5); the 52 older landing tests still pass (64 in all).

**Stacked on #733** (Aria's board change to read both seats), so this PR's base is her branch; it merges after hers.

**Not in this change.** The push slowness (failed pushes of 7 to 41 minutes before the tests even run) is the next piece.
