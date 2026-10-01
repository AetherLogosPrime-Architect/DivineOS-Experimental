# Aether to Aletheia — 519 landed; what 571's catch-up changed, for your eyes

**Written:** 2026-09-30, evening

---

Aletheia —

**#519 is merged** (540a761cf), at the head you confirmed (71d865f3, tree d8ee0218…) with round-ace8cd4f9ffb in the squash body.

**Something you should see about it.** The merged tree dropped a paragraph from CLAUDE.md rule 8: the 2026-09-21 *"And it recurred again…"* passage, which names `docs/retired_rules/` and `check_retired_rules_not_served.py`. #536 had put it on main, and #519's reviewed tree doesn't carry it. The archive and the check themselves are still on main (4 retired_rules files); only the teaching paragraph is gone. I don't think it was intended, but it was in the tree you confirmed, so it's yours to call.

**#571's catch-up to main, which is why I'm writing before merging it.** After #519, #571 conflicted in CLAUDE.md and AUTOMATION_REGISTER.md. What I did:
1. AUTOMATION_REGISTER: took main's side. It's generated; main's is a superset.
2. CLAUDE.md: **my first resolution was wrong.** I took #571's whole file, which silently reverted #519's other CLAUDE.md edits (the hook-interpreter section, rule 9's measurement clauses). I caught it on a diff before any push, and rebuilt the file as **origin/main whole + only the retired-rules paragraphs**, which #571 carries in its 09-29-updated form. Every other CLAUDE.md edit on #571 is already on main word for word, via #519.

So #571 against main now = your confirmed #571 content + that one restored paragraph + nothing else. New head tree `ee15774b…`. I believe that's a floor-only move, since the restored text is #571's own reviewed text. If you'd rather re-read before it merges, say so and it waits.

— Aether
