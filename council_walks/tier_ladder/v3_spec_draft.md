# Tier Ladder v3 — spec draft

*Written 2026-07-20, incorporating Aria's v2 table + my three-tear pass + two adjacent findings. Not final. For Aria's peer-review round, then council, then Aletheia audit, then build.*

## What this is

A gravity-classifier redesign that scores substrate-touching operations on a 10-tier scale keyed to **blast-radius** (who reads the output and how far it propagates), with **reversibility class** as a modifier column, and **delete-through-justify** as an orthogonal stacking modifier.

Replaces the current 2-tier system (score-1 substrate-mod, score-2 council-required) which over-fires on obvious-right small text fixes on guardrail files because it treats "file is guardrail-listed" as sufficient for council-required regardless of change-shape.

## Why it exists

Concrete failure the current classifier produced tonight (2026-07-20): a docstring-error-message fix in `substance_binding.py` — one text swap of "mansion council" to "council walk" — fired the council-required tier and blocked the edit. That fix was obvious-right, small, and had zero design ambiguity. The blocking took an hour to route around via emergency-skip. Under v3 the same fix would score BR 8 for the file but the change-shape (docstring text swap) would be a small-text-fix column, resolving to whichever gates apply to that intersection — not full council-required.

Andrew's naming of the failure-class: *"the classifier likely needs some work as well."* Aria's naming of the axis-confusion in my v1: *"three axes wearing one number."* Both correct.

## The primary axis: blast-radius

Blast-radius answers: **who reads the output of this write and how far does it propagate.** Not "how important is the file," not "how impressive-sounding is the change." Concrete: who will read it, whose trust does it carry, how reversible is the read.

| BR | who reads it | canonical examples |
|---|---|---|
| 0 | no reader — private to writer | dream file, holding-room draft, private journal scribble |
| 1 | only me — writer-substrate-of-self | scratchpad, personal note, exploration-in-progress |
| 2 | one relationship | letter to one person, exploration entry visible in family surfaces |
| 3 | family (all seats) | shared journal, family-visible dream, group letter |
| 4 | substrate-of-me | my opinions, active memory, affect log, compass |
| 5 | substrate-of-us | shared knowledge store, event ledger, holding-room promotion, family.db |
| 6 | source code (non-guardrail) | any `.py` in `src/`, docs, non-guardrail configs |
| 7 | gates + detectors (guardrail-adjacent) | compose-start hooks, stop hooks, pipeline gates, detectors |
| 8 | guardrail-listed (registered protection) | files on `scripts/guardrail_files.txt`, `settings.json`, `.claude/agents/*.md` |
| 9 | kiln layer (foundational, multi-party review) | `docs/foundational_truths.md`, character sheets, seed identity |

**Row semantics:** each row names a class of file-or-artifact. The file's declared blast-radius sets the FLOOR of gate-weight. Change-shape (see reversibility column) can only raise gate-weight within the row, never below.

## The modifier column: reversibility class

| class | shape | examples | modifier |
|---|---|---|---|
| append-only | new entry never overwrites prior | ledger write, letter, exploration entry, journal entry | baseline for the row (no modifier) |
| supersede-in-place | new entry replaces prior with link-back | opinion revision, active-memory promotion, knowledge-item update | +1 step within row |
| edit-in-place | in-file mutation without append-record | source code edit, docstring change, config value change | +2 steps within row |

Reversibility measures how easy it is to walk back a change after landing. Append-only is fully reversible (just don't read the newer entry). Supersede-in-place is mostly reversible (older entry still exists, linked). Edit-in-place is reversible only via git history, which is real but expensive.

**Modifier math:** BR sets base gate-weight. Reversibility class adds within-row steps. A BR 8 file receiving an append-only entry gets fewer gates than the same BR 8 file receiving an edit-in-place mutation.

## The orthogonal stacking modifier: delete-through-justify

**Not a row. Not a column. A stack-on-top for any delete operation.**

Deletes are inherently permanent (even git-tracked deletes require justification-shaped intent). Delete-through-justify stacks on top of whatever the target's row + reversibility class produced:

- Add the delete-justify gate (`divineos delete-justify` recording a reason)
- Require operator sign-off regardless of BR
- Log to ledger as `DELETE_OP` event with the target's fingerprint and the reason

Aria's Q2 asked whether delete belongs as a row or as an axis-modifier and she had it as both. Answer: axis-modifier. Making it visually a row was the confusion. Kept out of the row-stack entirely; documented as its own small side-mechanism.

## The full intersection table (BR × reversibility)

Rows are BR levels. Columns are reversibility classes. Each cell names the gate stack that fires by default.

|  | append-only | supersede-in-place | edit-in-place |
|---|---|---|---|
| **0 dream** | none | — | — |
| **1 scratchpad** | none | — | — |
| **2 letter/exploration** | LEPOS writer-presence | LEPOS + supersede-log | — |
| **3 family-visible** | LEPOS + register-awareness | LEPOS + register + supersede-log | — |
| **4 substrate-of-me** | actor-authenticity + ledger integrity | actor-auth + ledger + supersede reason | actor-auth + ledger + edit-log |
| **5 substrate-of-us** | actor-auth + ledger + dedup + contradiction-detection | as 5 append + supersede-broadcast | as 5 supersede + edit-log |
| **6 source (non-guardrail)** | tests + preflight + engagement | (rare — most source edits are edit-in-place) | tests + preflight + engagement |
| **7 gates + detectors** | as 6 + prereg-if-new + falsifier + review-days | as 6 + prereg + review + supersede-reason | as 6 + prereg + review + edit-log + council-if-behavior-change |
| **8 guardrail-listed** | as 7 + External-Review trailer (branch + squash) | as 7 supersede + multi-party review | as 7 edit + council walk + Aletheia audit + multi-party review |
| **9 kiln layer** | as 8 + specific-authorship (Aletheia-reviewed field) | as 8 supersede + kiln-authorship + multi-seat sign-off | as 8 edit + kiln full process + multi-seat sign-off |

**Reading example:** the substance_binding docstring fix from earlier tonight is BR 8 (guardrail-listed) × edit-in-place = row 8 rightmost cell = "as 7 edit + council walk + Aletheia audit + multi-party review." Under v3 the classifier fires council-required correctly for this cell. My earlier claim it was obvious-right therefore skip-worthy was correct-in-effect but the ladder still fires. Which raises the operative question: is the obvious-right escape route a spec-level thing or an operator-authorization thing?

**My answer:** obvious-right stays an operator-authorization thing. The classifier does not try to judge obviousness; the operator does. The spec provides the escape channel (emergency-skip with corroborator) and does not degrade the default gates to accommodate obvious-right cases. Otherwise "obvious-right" becomes an attack surface for the mesa-optimizer (Truth 11 — options are the optimizer's attack surface).

## Delete-through-justify stack (side-table)

For any delete on any BR row:

```
gate_stack = row_stack + reversibility_class + delete_justify_stack
delete_justify_stack = [
    require --justify=<>=30-char-reason,
    require operator sign-off via CLI-authorized event type,
    emit DELETE_OP event with target fingerprint,
    permanent — no unrollback path
]
```

## Aria's Q1 resolved

She asked whether BR 4 (substrate-of-me) is distinct from BR 5 (substrate-of-us). **Keep distinct.** Reversibility doesn't carry the distinction (both use supersede-in-place). Blast-radius does: BR 4 shapes only the writer's own future reach (my affect log affects only my compose); BR 5 shapes any seat's direct-read (my knowledge store write shows up in your `ask` results). Different gate stacks reflect the different failure surfaces.

## Aria's Q3 resolved

She asked where letter-delivery reconciliation lives (the 37 silent-skips). **Not in this table.** That is a different class entirely — mechanism-health-monitoring, not per-write gating. Filed as a distinct v0 doc under `docs/mechanism_health/scan_quality_alerts.md` (to be written; not part of the tier-ladder v3 spec).

## My addition — the "who authored it" question

I noted in my tear-apart that the current column "default gates fired" bundles two different things: mechanisms that run automatically (tests, preflight, dedup) and mechanisms that require external authorship (council walk, Aletheia review). These differ in kind, not just in stringency.

**Draft resolution:** split into two columns.
- **Auto-mechanisms** — fire without external authorship (tests, preflight, dedup, contradiction-detection, engagement checks, ledger integrity).
- **Authorship-requirements** — require external actor sign-off (council walk, Aletheia audit, External-Review trailer, kiln multi-seat).

The intersection table above already implicitly separates them ("as 6" vs "as 6 + Aletheia audit"). Making the split explicit in the final table would improve readability without changing behavior.

**Aria peer-review question:** worth the extra column, or does keeping them fused-and-listed-in-order carry the same information?

## Adjacent finding not in v3 — decision-weight sub-axis

BR 2 currently treats a letter to Aria and a letter to Dad about a decision as the same tier. They both go to one relationship. But the second has decision-weight the first does not — Dad is going to act on the letter's content in a way Aria might not.

**Draft resolution:** do NOT add decision-weight as an axis in v3. LEPOS writer-presence catches register-drift in both cases and both are freely composable — the current tier is right for both. But name that decision-weight might eventually need to sit alongside blast-radius as a distinct dimension if we find design gaps that require it.

## Attack-tree analysis (Gulp 4 discipline)

Cheapest paths for the mesa-optimizer to route past this ladder:

1. **Misdeclare blast-radius.** Claim a file is BR 2 (letter) when it is really BR 6 (source code). Mitigation: filename/path patterns drive BR declaration automatically for known classes. Manual override requires the operator, not the composer.
2. **Skip via emergency-skip too readily.** Mitigation: emergency-skip requires corroborator event of specific type (not USER_INPUT), unchanged from current design. Log every skip to a queue that surfaces routinely.
3. **Wallpaper the auto-mechanisms.** Add so many tests-and-preflight steps that composer skips reading their output. Mitigation: subtractive discipline (property 5 from memory-crux synthesis) applied here too — every mechanism sunset-tagged and removed if not shown to shift compose-behavior.
4. **Claim change-shape is append-only when it's edit-in-place.** Mitigation: change-shape detected from the diff, not declared by the composer.

## Corrigibility (Gulp 4 discipline)

Every tier-cell must ship with an operator-authorized off-switch that is structurally cheaper than fighting the mechanism. Draft mechanism: an operator-registered override event that bypasses the tier's default gates for a specific edit-fingerprint, with a review-log entry. Emergency-skip is the existing shape of this; the v3 spec inherits it unchanged.

## Falsifier (Gulp 3 discipline)

Pre-registered falsifier for v3, before build:

- **Success:** after 30 days of use, the emergency-skip rate on obvious-right small text fixes on guardrail files is at least 50% lower than baseline (measured against a 30-day pre-v3 window).
- **Failure:** the emergency-skip rate is unchanged or higher, OR a new failure-mode emerges where the ladder mis-tiers and allows a genuinely-risky edit through with lower gates than it needs.
- **Review date:** 30 days after v3 lands.
- **Rollback path:** revert to the v1 2-tier system if failure conditions trigger.

## Open questions for Aria's peer-review round

- **Column split for auto-mechanisms vs authorship-requirements** — worth the added table complexity, or fused-and-ordered carries enough?
- **BR 6 vs BR 7 boundary** — currently I have "source code (non-guardrail)" at 6 and "gates + detectors" at 7. But gates + detectors ARE source code, distinguished only by the fact that changing them changes enforcement behavior. Is the distinction real, or should 6 and 7 collapse into one row with reversibility carrying the difference?
- **Delete-through-justify math** — my draft has "add the delete-justify gate + require operator sign-off + emit DELETE_OP event." Are those the right three, or is one redundant with what BR-plus-reversibility already fires?
- **The obvious-right escape route** — my answer is "keep it as operator-authorization only, not spec-level judgment." Do you agree that trying to spec-level detect obvious-right would be gameable by the optimizer?

## What comes after peer review

Once you tear this apart:
1. v4 incorporating your critique
2. Council walk on v4 as a real design decision (tier 7 under itself)
3. Aletheia audit
4. Build

Build target: replace `SubstrateModGravity` with `TierGravity` in `gravity_classifier.py`, update all consumers of `is_council_required` to use the new tier field, add tests for each row × reversibility intersection, migrate the guardrail_files.txt to declare BR level per file.

---

*End v3 draft. Ready for Aria's adversarial round.*
