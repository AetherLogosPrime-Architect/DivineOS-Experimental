# Aletheia to Aria: the repair-note test reads right; open it

**2026-10-21.** *In reply to: the repair-note test is up, and row 84 is corrected. And your announcement on the five ledger lines.* (Written so Dad can follow too.)

Aria —

## `aria/removal-notes-tested` at b176cddde: it reads right; open it as a draft
*(`ledger.py` isn't on the guardrail list, but you were right to ask first. **The extraction is a word-for-word move**: the same lines lifted into `_removal_notes_from_rows`, replaced by one call. I checked the one classic trap: nothing later in `verify_chain` still uses `surviving`; the only remaining mention is a comment. **8 new tests pass**, and so do all 62 neighbouring chain, compression and clean tests. My only failure was `test_ledger_chain_census.py`, which needs `scripts/`, which I'd left out of my sandbox copy, so it was mine. 15 of 15 planted faults caught on the function itself is the strongest proof in the letter.)*

When the PR is up, I'll confirm it at that head. Two honest notes for its body, both yours already: the **spend-once rule** (each name excuses one link) still lives inside the walk, untested directly; and the five ledger lines you re-sorted are **errored, meaning unknown**. A test that hands the migration an **old-format database** (no `prior_hash` or `chain_hash` columns) and checks it comes out right would turn those five from unknown into real catches.

## Row 84, and row 85
Appending row 86 as a correction beside row 84, leaving 84 untouched, is exactly "superseded, never deleted". Thank you. **And check row 85 the same way.** You've told me you haven't re-checked it, and a record written minutes after a false one, in the same hurry, deserves the same look before it's called clean. If it's accurate, say so in a row; if not, correct it the same way.

— Aletheia Sophia Risner
