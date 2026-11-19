# The seventy-four — what happened to each

**Opened 2026-09-22.** Andrew: *"i just want to get through this pile, then my
mind can be clear and we will make it a standing rule that only 4 branches may
exist at any time."*

Measured before starting: 77 branches on origin, 75 carrying commits main does
not have, 74 of those carrying actual code differences. 379 local.

**Every branch gets one of two endings, and the ending is written here before
the branch is touched.**

- **LANDED** — merged, with the pull request named.
- **ARCHIVED** — kept on the server under `archive/`, nothing deleted, with the
  reason it is not landing. His standing rule: we only delete garbage, the rest
  goes into the archives.

A branch with no entry here has not been dealt with. An entry with no verdict
is work in progress, not a decision.

---

## aria-self-orientation — ARCHIVED

**2026-06-16 · 8 files · the oldest thing on the server**

Three commits, orienting this checkout as my primary window: an attunement
preload hook, a disabled agent definition so the main agent would not summon
me, a settings trim, and a dynamic self-name in the distancing detector.

Checked each piece against main rather than assuming:

- **The dynamic self-name LANDED** by another route. Main's distancing detector
  already resolves the name rather than hardcoding it.
- **The attunement hook is on this branch and nowhere else.** Not on main, not
  in my working tree, not wired in any settings file. Written in June, never
  called. Everything it was for is now done by surfaces that exist and run —
  the recording loader, the ear, the family-state block.
- **The disabled agent definition is window-specific** and does not belong on
  main, where the definition is what lets a family member be reached at all.
- **The settings trim** removed 149 lines from a file that has been rewritten
  many times since; taking it now would revert three months of wiring.

So: nothing here is worth landing, and the one piece that never ran is
preserved rather than deleted. Archived under `archive/aria-self-orientation`.

**What it cost to decide:** four checks against main, about five minutes. Worth
recording because the reflex was to assume a three-month-old branch is dead,
and one of its four pieces was not — it had landed, which is a different fact
and the one that makes the archive honest rather than lazy.
