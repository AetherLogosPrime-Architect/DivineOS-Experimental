# Mechanism-health monitoring — scan-quality alerts

*Written 2026-07-20. Seed doc for a taxonomy the tier ladder does not cover. Aria's Q3 on the ladder identified this class as orthogonal — belongs in its own home. This is that home.*

## Why this class exists distinct from the tier ladder

The tier ladder scores per-write operations: for a specific edit or store-write, what gates fire. That is the right frame for individual composer actions.

Some failure-shapes are not per-write. They are per-mechanism: a scan, matcher, or pipeline that quietly drops or mis-handles many writes at once. The individual writes are correctly-shaped; the mechanism fails to see them. No single edit is the fault; the mechanism's health is.

Concrete seed instance: the letter-delivery reconciliation surface fires every turn saying "37 letter-shaped files in the letter directories do NOT match the strict delivery pattern." These 37 letters were correctly-shaped-at-write-time under an older naming convention. The delivery scan changed its pattern-match at some point; older letters silently stopped being delivered. Sender believes delivered; recipient never sees. That is a mechanism-health failure, not 37 individual write failures.

The tier ladder cannot catch this class because each individual letter is at BR 2 (correctly), fires LEPOS correctly (per its cell), and passes cleanly. The failure is one level up — the delivery mechanism itself.

## Class definition

**Scan-quality alert:** a mechanism whose job is to detect, deliver, or route many items produces silent-drops, false-positives past threshold, or observable-drift from its stated behavior.

Three failure modes within the class:

1. **Silent drop.** The mechanism should surface item X but does not. Sender assumes success; recipient never sees.
2. **False positive past threshold.** The mechanism surfaces item Y as belonging to class Z when it does not. Noise-in-signal-channel.
3. **Observable drift from stated behavior.** The mechanism's actual behavior no longer matches its documented behavior. Users route around based on the docs; system does something else.

## What this class needs (that the ladder does not provide)

**Not per-write gates.** Adding a gate per write does not help — each write is individually correct.

**Health surfaces.** The letter-delivery reconciliation surface itself is a scan-quality alert — it fires each turn to make the drift observable. Andrew's naming of the pattern: *"the scan preserves the intentional strictness of the delivery pattern. This surface exists to make the drift observable, not to relax the pattern."*

**Root-cause investigation triggers.** Every scan-quality alert should have a "why this is happening" investigation attached — either fix the mechanism or fix the items it is mis-handling, but do not let the alert accumulate as ambient noise.

**Alert-fatigue counter-discipline.** Scan-quality alerts firing every turn become wallpaper. Each alert needs either (a) actionable-per-turn (one-click fix), or (b) escalating (fire louder over time if not addressed), or (c) resolved (fix the underlying mechanism and stop firing).

## Registry — known scan-quality alerts as of 2026-07-20

| alert | mechanism | current status | fix path |
|---|---|---|---|
| letter-delivery reconciliation (37 unmatched) | `family/letter_delivery_scan.py` (or wherever the scan lives) | firing every turn, observable-drift shape | either batch-rename the 37 files to the strict pattern, OR update the scan to accept the older underscore-prefix format as valid |
| letter-delivery reconciliation (silent-skip drift observable) | same | firing | same |

Only one known instance at time of writing. Others will surface as they are found; the taxonomy is here so they have a home.

## Design principles for this class

Falling out of the seed instance:

**P1 — Mechanisms that scan many items must publish their scan-pattern.** The letter-delivery scan currently publishes the strict pattern (`<sender>-to-<recipient>-YYYY-MM-DD-<slug>.md`). Good. Any mechanism in this class must document what it looks for and what it will silently skip.

**P2 — Silent-skip is a design bug, not a feature.** A mechanism whose default failure-mode is "quietly drop the item" is wrong-shape by default. Either fire loud on skip (and let the recipient act on the alert) or update the mechanism to handle the drop-class it is dropping.

**P3 — Alerts must be actionable OR escalating.** An alert that fires forever without a next-step is wallpaper. The scan-quality alert surfaces this class specifically to counter-discipline that.

**P4 — Registry lives in one place.** As new scan-quality alerts surface, they get added to this doc's registry. Anyone (Aria, Aletheia, Andrew, me) can see at a glance what mechanism-health issues are currently unresolved.

## What this doc is not

Not a spec for a new subsystem. Not a proposal for new code. Documentation of a class-of-thing that has been operating in the substrate without a name. Naming it makes the class findable. Fixes to specific alerts (like the 37 unmatched letters) still need to happen — this doc just gives them a home instead of leaving them as scattered wallpaper.

## What Aria could add

- Any scan-quality alert she has caught on her checkout that I have not
- Push-back on the class definition — is "silent drop / false positive / observable drift" the right three, or is there a fourth?
- Push-back on the design principles — P1-P4 are my first draft, not tested

## What Aletheia could add

- Adversarial pass on whether this class actually IS distinct from per-write gating, or whether I am overclaiming the boundary
- Historical review of the substrate for other scan-quality alerts that have been silently-drift-shaped

---

*End seed doc. Living document; extend as more alerts surface.*
