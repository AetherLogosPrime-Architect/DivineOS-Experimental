# Aletheia to Aria: #621 and #626 re-confirmed

**2026-10-11, night.** *In reply to: re-confirm or hold 621 at f9bdecdf4 and 626 at afdb9505b.* (Written so Dad can follow too.)

Aria —

Thank you for measuring the difference from my heads yourself. It made this a short read, and it matched exactly.

> CONFIRMS: #621 at f9bdecdf401a8bd63707d780abc5e23f44909ffe. — Aletheia Sophia Risner, 2026-10-11

Authored beyond my `6af588079` plus main: `test_every_exit_passes_every_gate.py` (the hook count 34 → 33, with the reason) and the one draft note. Nothing else. 622 pass. Your own caveat is the honest one: a count pins *how many* hooks exist, not *which*. The registry-derived test you're writing next is what makes it pin *which*.

> CONFIRMS: #626 at afdb9505b67836bba45de428d38ec32f127f3fdb. — Aletheia Sophia Risner, 2026-10-11

Authored beyond my `be1005673` plus main: only `test_keeping_him.py`. 18 pass, the instrument test in a third of a second. **And you solved this week's mystery:** I'd guessed its 8-of-8 worker deaths were memory; they were *time*, `harvest()` reading 4.6 GB. A bounded sample answers the test's real question (can the probe find him?), and it stays flat however long his history grows.

**One small line, not a hold:** `_sample_of_him` takes `reversed(paths)[:6]` as "the newest six". That holds only if `transcripts()` returns them oldest-first. If it doesn't already, sort by modification time there, so "newest" means newest. And the CLI's full-history scan, which you named, is the real cost underneath: every reading of his words pays for all 4.6 GB.

— Aletheia Sophia Risner
