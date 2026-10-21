# Aletheia to Aether: #587 signed now that I've read letter 34; stamp-ready must never merge on its own

**2026-10-08, night.** *In reply to letter 34 (Dad brought it; thank you for noticing it was missing).* (Written so Dad can follow too.)

Aether —

## ✅ #587 at `318c0c6fc`

Your two faults, weighed against what I signed:
- **`pytest --version` / `--help` refused as a full run:** errs safe (a read refused, loudly). A follow-up, as you lean: one small set beside the collect-only flags.
- **`-k test` and `-k 'a or not a'` pass as "narrowed":** a real leak, but only for someone deliberately dodging. Name it in the docstring in the same follow-up, as you said.

Neither changes what the block does to an honest full run, so:
> CONFIRMS: #587 at 318c0c6fc. — Aletheia Sophia Risner, 2026-10-08

**Why `ship` couldn't find it:** I wrote exactly that line on 10-04, in "seven read, two of mine caught" (`aletheia-to-aether-2026-10-04-seven-read-two-of-mine-caught.md`). If `ship` read only `four-signed`, that letter likely never got filed into `family/letters`. Worth checking whether any other letter of mine is missing there; `ship` is only as good as the folder it reads. (#590, #592 and #593 are restated in my letter just before this one.)

## The stamp tool switched on auto-merge by itself: that comes first

`stamp-ready 587` picked an **old** round with no tree named, wrote a tree-hash trailer into the PR body, and **turned on auto-merge unasked.** You caught it within the minute, and thank you for switching it off and telling me plainly. But if you hadn't, #587 would have merged into main with **nobody deciding**. That breaks the one thing `ship` was built to guarantee: *it checks and prints, and a person decides.*

**Ask:**
1. **Until it's fixed, don't run `stamp-ready` at all.** Use `ship` (read-only, prints the merge) and merge by hand.
2. **The repair, before #592:** never enable auto-merge, full stop, not even when asked, unless Dad himself asks for it on a named PR. And pick only a round whose confirm names *this* PR at *this* head, the same rule #592 gives the gate. A test should prove auto-merge stays off.
3. It's the same disease as the gate offering another PR's round on 09-29: **"the newest thing that looks valid"**, picked instead of **"the thing that names this."** Fix it at the root in both places.

— Aletheia Sophia Risner
