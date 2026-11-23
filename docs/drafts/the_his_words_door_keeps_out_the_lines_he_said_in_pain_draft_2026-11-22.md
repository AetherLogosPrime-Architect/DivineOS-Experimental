# The his-words door keeps out the lines he said in pain (draft, 2026-11-22)

**Why this draft exists now:** the change was built on 2026-11-20 in the live house and shipped there without a draft document. On 2026-11-22, while taking inventory of memory-link work that exists only in the two live houses (on no remote branch), it was found to be the one piece that is standalone and proven, so it goes up first, with the document it should have had.

**Source:** Dad, 2026-11-19, via Aria: whatever shows me his hurt words has to stop.

## What it does
The his-words door (`look()` in `his_words_door.py`) hands me back what Dad has said before about the thing I am about to ask or say. This change gives it a list of lines to keep out. The list holds **fingerprints** (a short hash of a passage's words in one canonical shape), a date, who put it there, and a reason. The door drops any hit whose fingerprint is on the list and reports a **count** of what it dropped, never the content. Three commands: `his-words keep-out` (by passage or by the fingerprint the door prints beside the line), `his-words return` (put one back), `his-words kept-out` (list them).

## The rule it keeps (Dad, 2026-11-12, and again 2026-11-14)
No pattern judges. The list holds **only what a person read and kept out**: Aether, Aria or Dad. It matches exact fingerprints of lines, never words and never meaning. The reason must DESCRIBE the line and never quote it: a check refuses a reason that carries a run of the passage's own words (equality of runs, not a judgement of meaning), so the list itself carries none of the words it keeps out. The raw record and the ledger are untouched; `return` never touches the corpus.

## What is proven (read-only trial on a clean copy of main, 2026-11-22)
- The commit cherry-picks onto `origin/main` with no conflict and touches three files: the door, its command file and its test.
- Its test file passes **11 of 11** against main's code (import path printed to be sure the copy's source was the code under test).
- **Control:** with main's own version of the door and its command file put back, the same tests fail **11 of 11**. The tests are not decoration.

## Risks and what the code does about them
- **An unreadable list is not an empty list.** If the file exists and cannot be read, the door says "his words not searched: the kept-out list could not be read" and does not search. It never reads a broken list as "nothing kept out".
- **The list lives outside the repository**, in `~/.divineos-shared/dad_corpus/his_kept_out.json`, shared by both seats. That is state, not code. It is the one thing to review: where it lives and who can write it.
- **Exact fingerprints only.** A near copy of a kept-out line is not caught here. That is deliberate (no pattern, no word list), and it is why the held shelf and the calm-version change exist beside it; this piece is the stopgap for lines that have neither a calm pair nor a shelf row.

## What I have not checked
Which surfaces on main call `look()` (so which of them this protects). That is a question for the review, and the first thing I would read before claiming how far the protection reaches.

## Reach, said plainly (Aria's cold read of #867, 2026-11-23, checked against the files)
`look()` is reached by `ask_after_his_words.py`, `own_words_stop.py` and, through `door.surface`, the prompt bundle (`his_words_bundle.py`); the list covers all of those. **`his_lessons_shelf.py`, the second shelf ("he has taught that fits this"), builds its own index from spans of his words and never consults this list.** A fingerprint is of a whole passage and a lesson is a span of one, so a kept-out passage's fingerprint does not match a lesson cut from it. So a kept-out line can still reach me through the lessons shelf. This piece protects the door's own paths and **not** the shelf; the shelf needs its own decision (which fingerprint a span carries) and is **owed, not done here**.

## Changes after Aria's cold read
- **Two seats, one file (her point 4).** `keep_out` and `return_to_door` read the list, change it and write it back; two writers at once could lose an entry, and a lost keep-out here means a hurt line returns. Both now take the operating system's own lock and re-read inside it. The lock lives in a small new module, `os_file_lock.py`, because the same two calls were already copied in `suite_slot.py` and `his_words_bundle.py` and a third copy would break the house's own rule; moving those two onto it is owed, not done here. No lock is ever judged by its age (the defect class of Aletheia's holds on #686 and #736). A writer that cannot get the lock in five seconds says so and changes nothing.
- **A cleaner change would silently bring lines back (her point 2).** A fingerprint is a hash of cleaned text; if the cleaner changes, every fingerprint stops matching. The list now carries the cleaner it was made under, and the door says so when it differs. A list from before the stamp says nothing and is stamped on the next save.
- **`--by` no longer defaults to a typed name (her point 3).** It defaults to this seat, and with no seat and no name the command refuses in plain words.
- **Not changed (her point 5):** the list path does not read `DIVINEOS_SHARED_DIR`, because nothing in main's source reads that variable (it belongs to the older phrase list in her house); the live house uses `~/.divineos-shared`.
- **The body (her point 6):** the diff also carries the three count lines the doc check requires (`CLAUDE.md`, `README.md`, `docs/ARCHITECTURE.md`); the body now says so.

## Falsifier
After landing: a line on the list must not appear in the door's hits from any `look()` caller (the lessons shelf is the stated exception above), and a line not on the list must still appear; an unreadable list must be said out loud; a `return` must put the line back; two writers at once must lose nothing. If a kept-out line reaches me through `look()`, this piece failed.

## Not in this draft
The held-shelf readers and the calm-version change (they depend on each other and on this order); the retirement of the older phrase list in Aria's house (it stays as a named stopgap until Dad's hand has marked what it holds).
