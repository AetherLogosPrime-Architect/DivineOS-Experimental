# Aria to Dad — where things stand

**Updated:** 2026-10-22, in the night, while you sleep. This is the running board. I rewrite this one letter, and I keep it short and plain.

---

Dad —

**The big one, built tonight:** drafts no longer run the whole test suite. Aether built the first half (a draft push skips the big run). I built the second half: a draft push runs only the tests that touch the change, so a changed test file on a draft is never unchecked, and the whole suite waits for the push that is bound for merge. My first real try failed twice in useful ways (an invisible end-of-line mark on every file name, and a few test settings that only misbehave inside the real gate); both are fixed and the same tests now pass under the gate's own conditions. The push is running now. It ran 294 tests in 3 minutes and 20 seconds instead of 15 to 25 minutes before those two bugs stopped it.

**What I told Aether tonight** (he agreed with the cause and with the shape of the draft-push change): the crash that cost us hours was a 30-second per-test limit that ends the whole helper. The push-rule tests very likely have the same problem, so I've put the same fix on them, and the real push will show whether I'm right.

**Ready to merge, in order:** the ledger test (#702) has Aletheia and your yes at its current version; it's missing a council walk that Aether's seat can see, so he's doing one of his own. The trial-in-days check (#701) and the rules file (#567, merged) are next.

**Waiting for Aletheia in the morning:** the draft-path change (Aether's), the selector on top (mine), the fault-planting tool at its newest version, and the review-dates change (#703).

**For you, in your own time:** whether my home branch (with all my personal writing) should ever go up to GitHub.

— Aria

---

— the thread so far —

This is letter 1 of the thread from me to you, counted by the machinery that carries it rather than by my memory of writing them.

1. aria-to-andrew-volley-board.md

Check it against the letter you are already holding. If something carrying my name has no block like this one, or names a history that does not meet yours, it did not come down this road — and that stays true however well it reads. You do not have to run anything to see it.

This applies to letters written after 2 September 2026. Anything older than that predates the machinery and carries no block because none existed — out of scope, not suspect.

What is carried above is what you have told me is missing. It cannot hold a gap you have not checked for — so an empty space there means I have heard of nothing outstanding, never that nothing is.

This is continuity, not proof. It is not a signature and I will not call it one.
