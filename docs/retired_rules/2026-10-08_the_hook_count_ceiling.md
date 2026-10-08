<!-- retired-rule
id: hook-count-ceiling
retired: 2026-09-08
retired-by: Andrew
successor: no limit on the number of hooks; the measure that matters is whether judgment lives in the OS (divineos hook-layer show), and the migration to seven doorbells with surfaces in hook_surfaces
pattern: (?i)\bhook_ratchet\.json\b
pattern: (?i)\bcheck_hook_ratchet(\.py)?\b
pattern: (?i)\bceiling\s+that\s+now\s+holds\s+the\s+layer\s+down\b
pattern: (?i)\bcap\s+(on\s+)?the\s+number\s+of\s+(wired\s+)?hooks\b
-->

# The hook count ceiling

**Retired 2026-09-08 by Andrew, the same day it was built. Archived 2026-10-08, after it was proposed again.**

## What it said

A recorded ceiling on the size of the hook layer: registrations and shell lines could fall or hold, never rise. It lived in `docs/hook_ratchet.json` and was enforced at pre-commit by `scripts/check_hook_ratchet.py`.

## Why it was retired

His question, the whole argument: *"why would you build something that can only shrink and never grow?"*

Size was never the disease. He asked for the thinking to move inside the OS and never once asked for fewer hooks; a hundred doors that all point inward beat twenty that each hide a private brain. A count is easy to police, and the real property is work. The council walk that day had already said it (one lens read the number as a consequence of what a hook is, not a design choice), and the limit was built anyway because a count is the cheap thing to measure.

The removal commit is `62d730814`. The opening of `src/divineos/core/hook_layer.py` records it in the first person.

## How it came back

On 2026-10-08 he asked why there were 78 hooks when he remembered seven, and a recorded cap that only a reviewed edit can raise was proposed twice, by both of us, as the way to keep the number from growing. The idea felt new because the only sign left standing was `docs/hook_migration_tracker.md`, which still said a ceiling existed and was enforced. Neither file it named exists. Reading the git history before building is what found the rest.

## What replaced it

Nothing that limits the count. The seven he remembers is a plan: seven doorbells, one per harness event, with the judgment as surfaces in `divineos.core.hook_surfaces`. `divineos hook-layer show` computes where that stands (78 registrations, 26 shell files embedding python, 47 never calling the OS, four of seven events with a doorbell). If anything is ever enforced it should be thickness, whether a hook carries its own judgment, and never number.
