# Superseded 2026-09-29: the compressor's chain relink

**What is here**
- `repair_chain_after_deletion.py.txt`: `_repair_chain_after_deletion` and `_latest_valid_chain_hash_before`, moved byte for byte from `src/divineos/core/ledger_compressor.py`.
- `test_ledger_compressor_chain_repair.py.txt`: their tests, moved whole with `git mv`.

**What they did.** Aria's July design ("Interpretation A", 2026-07-16): after the compressor deleted old noise events, rebuild `prior_hash`/`chain_hash` for every surviving row from the first orphan to the end, so the chain read seamless.

**Why they were retired.** A rebuild rewrites surviving rows, which is what a tamperer does. It also silently mended *unrelated* crossed links after the first gap, and those crossings are the only evidence of the live cross-process append race. Proven on 2026-09-29: against this code, a crossing that existed before compression was no longer reported after it, and surviving rows were rewritten. Aether's council walk on #565 (Knuth, Feynman, Pearl, Einstein, Yudkowsky, Wayne) and Aria's walk `walk-d1d17f7e2883`.

**What replaced them**
- The compressor leaves each gap standing and names it in a chained `LEDGER_COMPACTION` note (`gap_tail_chain_hashes`, written through `ledger.append_on`). Aria, branch `aria/the-compressor-leaves-its-gaps`.
- `verify_chain` excuses a link only when such a note names a hash that no surviving row carries, spent once, with the row's own hash still rechecked. Aether, `fix/the-ledger-cleaner-leaves-its-note` `0a619ffc`.
- On a copy of Aria's real ledger: 74 compressed, 73 gaps all named, 0 true crossings hidden, 0 survivors rewritten.

**Approved** by Dad in his own words, 2026-09-29 (typed in Aether's window at 04:20:26Z, checked in his corpus): *"yes you can move them to the archive :)"*. Moved, not deleted, per his rule that nothing built is removed without his yes.
