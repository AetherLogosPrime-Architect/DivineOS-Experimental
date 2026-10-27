# A draft note is neutral to the scope station (draft, 2026-10-26)

**What it fixes.** The build board's scope station (station 3) refuses a change that carries both writing and code. It counted `docs/drafts/` as code, so a letter plus the draft note the board itself requires read as MIXED. That happened on #725 (Serein's letter), and I stamped it despite the board, with the reason written down, because the board was wrong.

**The change.** Draft notes (`docs/drafts/`) are set aside before the station sorts the rest. Letters, explorations, dreams and archives still count as writing; everything else still counts as code. Only `check_scope_station` in `src/divineos/core/build_flow.py` changes.

**Why neutral and not "writing".** Every code change carries a draft note too. Counting it as writing would make every code change MIXED. Neutral keeps both cases right: a letter plus its note passes, code plus its note passes, and a note beside code AND a letter is still refused, because the code is judged on the other files. A note cannot hide code.

**Proof.** `tests/test_a_draft_note_is_neutral_to_the_scope_station.py`: four cases; the letter-plus-note case fails without the change and passes with it. The older scope tests (12) still pass.

**Not in this change.** The council gate's list of commands that only record, which charged five walks for two landings tonight, is Aria's #631 and is waiting on three more lines from her.
