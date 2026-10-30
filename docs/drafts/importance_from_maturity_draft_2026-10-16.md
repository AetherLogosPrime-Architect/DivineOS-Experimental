# Importance from what the house already knows (rough draft, 2026-10-16)

## The idea

Dad, 2026-10-16: *"lets investigate the stale importance score."* `divineos linkage why` (#674) showed every item at importance 0.50 (the wall at 0.60). The cause, read in the code: each source adapter hard-codes it (`importance_score=0.5  # baseline; behavior-feedback adjusts`), `_boost_importance` and `_downweight_importance` are no-op stubs that say "NOT YET WIRED", and `apply_behavior_feedback` has no caller. At weight 0.15 in `composite_score`, that term cannot tell two items apart.

## What the house already knows

The knowledge table carries real, varied signals on every live fact: `maturity` (RAW 334, HYPOTHESIS 153, TESTED 878, CONFIRMED 408), `corroboration_count`, `contradiction_count`, `confidence`, `access_count`.

## Two things the house already says, and they bind this

1. A stored PRINCIPLE: *access counts should never feed back into confidence or maturity promotion; confidence comes from corroboration, not popularity.* So `access_count` is not used. `confidence` is not used either: 689 of the facts sit at 1.0, so it does not discriminate.
2. An observation of ours: maturity is a proxy for correctness, not proof (N corroborations can be N copies of me agreeing with myself). So this is named "ranked by maturity", the weight stays at the existing 0.15, and it never claims "important".

## Aria's two catches (her read of #674, 2026-10-16)

- The regulatory lane (`retrieve_similarity_only`) was split off after Aletheia's priming-poisoning confirm so nothing an adversary could inflate shapes what surfaces during a flood. It calls `composite_score` with the item's importance, so it is neutral only because importance is flat. Once importance spreads it would depend on corroboration, which can be raised by repeating a learn. It must pass a constant importance, and its output must be byte-identical before and after.
- The "quietly downweight what was ignored" half stays unwired: Dad said an ignored memory means find out why, not punish it.

## The change

Knowledge only: importance = maturity base (RAW 0.3, HYPOTHESIS 0.45, TESTED 0.6, CONFIRMED 0.8) + 0.04 per corroboration up to four - 0.1 per contradiction up to two, clamped to 0.1 to 1.0. On today's data that spreads the 1,800 live facts from 0.3 to 1.0. Corrections, letters, explorations and the wall stay as they are until we agree what importance means for them (an integrated correction is arguably less worth surfacing, and Dad has said the build-shaped ones should be cleared). The regulatory lane passes 0.5.

## Tests it must pass

Two items at identical similarity and tier but different maturity change rank order; the regulatory lane's output is byte-identical before and after; a fact with an unknown maturity gets the old 0.5, not a crash.

The lane test runs the lane (Aria's second read): two items identical but for importance 0.3 and 0.8 go through `retrieve_similarity_only` and their ranks must be equal. It was mutation-checked: letting the lane read the item's own importance fails it, with a control that the ordinary composite does separate them.

## Did the source mix move? (Aria's question, measured 2026-10-16)

Knowledge now spans 0.3 to 1.0 while corrections, letters and explorations keep 0.5, so the importance term could lift knowledge over the other sources. I measured it on eight real prompts against the live caches, recomputing the same top-five ranking with and without maturity. Seven returned results. The mix of sources across those top-fives was identical before and after (knowledge 14, corrections 14, letters 6, explorations 1). What changed is order inside the top five: six of the eight prompts reordered, with confirmed facts moving up past less settled ones. So the effect is within-set ordering, not a systematic lift of knowledge over other kinds. One prompt returned nothing on either side. Eight prompts is a small sample; the script is in the session scratchpad and can be re-run on a larger set.
