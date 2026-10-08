# There is no hook ceiling, and the old notes still say there is (draft, 2026-10-08)

I set out to build a ceiling on the number of wired hooks, because Dad asked why there are 78 when he remembered seven, and Aether suggested a recorded cap that only a reviewed edit can raise. Looking first (the reach step) found that this exact thing was built on 2026-09-08 and removed the same day: Dad asked "why would you build something that can only shrink and never grow?", and the removal commit (62d730814) and the opening of `core/hook_layer.py` both record it. The size of the layer was never the disease; hooks holding their own judgment is.

Two facts that are the real finding:

1. `docs/hook_migration_tracker.md` still opens by saying the ceiling "lives in `docs/hook_ratchet.json` and is enforced at pre-commit by `scripts/check_hook_ratchet.py`". Neither file exists. The sign that teaches the retired rule is still on the wall. The tracker is not a surface the retired-rules checker scans.
2. The state Dad remembers (seven hooks) is a plan, not a count: seven doorbells, one per harness event, with the judgment as surfaces in `hook_surfaces`. Measured today by `divineos hook-layer show`: 78 registrations, 26 shell files embedding python, 35 never calling the OS (first written as 47; the measure did not recognise the `python -m divineos` doorbell form, fixed the same day). Four of seven events have a doorbell. The migration stalled; it did not fail.

Idea, in the order that respects his correction:

- Fix the stale sign and archive the retired rule (`docs/retired_rules/2026-10-08_the_hook_count_ceiling.md`) so a phrase that claims a ceiling exists cannot be served as current again.
- Do NOT build a count limit. If anything is enforced, it is thickness, never number: a new hook may not embed its own judgment. That is a decision for Dad, because it is a new rule on my commits, and it must not be a ratchet on size.
- Continue the migration where it was left, one doorbell and a few surfaces at a time.
