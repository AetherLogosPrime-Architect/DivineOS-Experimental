# A crossing onto a compacted tail (draft, 2026-09-29)

Follows `the_compressor_leaves_its_gaps_draft_2026-09-29.md`.

Aletheia's attack on `aria/the-compressor-leaves-its-gaps`: a race row B crosses
onto row A; A is routine and gets compacted as the tail of a removed run, so a
LEDGER_COMPACTION note now names A's hash and no survivor carries it. Does
verify excuse B as a gap and launder the race?

Reading verify: a name is spent once, in rowid order. The honest survivor right
after A's run spends it first; B comes later and finds it spent, so B is still
reported at B. The worry that the *wrong* anomaly shows would need B to precede
the honest successor, and the honest successor is by construction the first
survivor after A.

The idea: don't trust the reading. Pin it with a test that builds the race the
way it really happens (B's own chain hash honest for the wrong prior, so only
the link is wrong), compacts A as a tail, and asserts the break is still B.
If it fails, the fallback is hers: the compressor refuses to compact any row
that more than one survivor links to.
