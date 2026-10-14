# A round opened in Dad's name is a voiced filing too (draft, 2026-10-11)

**Found by Aether** reading 621 at `16753f8bb`: `divineos audit submit-round "x" --actor user` is a remedy, because the voiced-filing list names `submit` and `file-external-confirm` and not `submit-round`. A round is not a CONFIRMS, but a round names the real reviewer, and a user-named round is what a later user confirm leans on, so it should pause like the others.

**Change.** Add `("divineos", "audit", "submit-round")` to the voiced list in `remedy_allowlist.py` and to the generated family in `tests/test_every_exit_passes_every_gate.py`, both directions: no spelling naming `user` is a remedy, the same spellings naming a closed-list actor still are. `--actor` is a required option of `submit-round`, so no legitimate round is paused.

**Order of work.** Test first (the family gains the round command and goes red on the user cases), then the one-line entry in the source list, then the neighbouring test files.

**Not in this change.** Loose shell prefix; `ask-resolve` and `extract` on the python list; the printed-exit survey as a repo test.
