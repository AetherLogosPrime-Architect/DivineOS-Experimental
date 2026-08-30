# Tier Ladder v4 — spec draft (integrates Aria's v3 review)

*Written 2026-07-20 immediately after Aria's v3 review landed. Supersedes v3. Adds three structural pieces her review named: (1) explicit auto/authorship column split, (2) BR 6/7 distinction anchored to falsifier-obligation, (3) pre-registered obvious-right escape pattern.*

*Ready for Aria's second-round review, then council walk on the design, then Aletheia audit, then build.*

## What changed from v3

- **Split "gate stack" column into "auto-mechanisms" and "authorship-requirements."** These diverge at BR 7-9 in ways that matter for audit; making the split explicit surfaces the "was this signed off by who it should have been signed off by" question distinctly from "did the automation run."
- **BR 6 vs 7 distinction anchored explicitly.** BR 7 (gates + detectors) carries a *falsifier-obligation* for new mechanisms — the tools that catch me being wrong must have pre-registered failure conditions or they degrade silently with no meta-detector to catch it. BR 6 does not carry that obligation. This is a real discipline distinction that reversibility class does not touch.
- **NEW: pre-registered obvious-right escape pattern.** A per-file-or-file-class registry that pre-authorizes the emergency-skip channel for specific change-shapes (docstring-only, error-message-only, comment-only) without needing a fresh corroborator each time. Preserves gate-strength for the general case; removes the hour-of-friction tax on legitimate small fixes.

## Why v4 exists

The substance_binding docstring fix from earlier tonight fired council-required and took an hour to route around via emergency-skip. Under v3 the same cell (BR 8 × edit-in-place) fires with the same strength. Aria's push-back: the mesa-optimizer needs the gate to *feel real* by default, but the escape route needs to be *predictably accessible* for legitimately-obvious-right change-shapes on those files. Otherwise every docstring fix on a guardrail file becomes an hour-of-friction turn.

v4 resolves this by adding a new mechanism — the pre-registered obvious-right pattern — that lives alongside the tier ladder rather than degrading its defaults.

## Primary axis: blast-radius (unchanged from v3)

Same 10 rows (BR 0 through BR 9). See v3_spec_draft.md for the row definitions and canonical examples. Rows unchanged in v4.

## Modifier column: reversibility class (unchanged from v3)

Same three classes (append-only, supersede-in-place, edit-in-place). Same modifier math. Unchanged in v4.

## Orthogonal stacking modifier: delete-through-justify (unchanged from v3)

Same three components (justify-record, operator sign-off, DELETE_OP ledger event). Aria confirmed keep-three: they load-differ across BR levels. Not a row. Not a column. Stacks on top of any target's row × reversibility cell.

## The full intersection table (BR × reversibility × [auto | authorship])

Rows are BR levels. Columns are reversibility classes. Each cell now contains TWO stacks: auto-mechanisms (fire automatically without external actor) and authorship-requirements (require external sign-off).

Format per cell: `AUTO { list } // AUTHORSHIP { list }`. Empty `{}` means none in that class.

|  | append-only | supersede-in-place | edit-in-place |
|---|---|---|---|
| **0 dream** | `{} // {}` | — | — |
| **1 scratchpad** | `{} // {}` | — | — |
| **2 letter/exploration** | `{LEPOS writer-presence} // {}` | `{LEPOS + supersede-log} // {}` | — |
| **3 family-visible** | `{LEPOS + register-awareness} // {}` | `{LEPOS + register + supersede-log} // {}` | — |
| **4 substrate-of-me** | `{actor-authenticity + ledger integrity} // {}` | `{actor-auth + ledger + supersede-reason} // {}` | `{actor-auth + ledger + edit-log} // {}` |
| **5 substrate-of-us** | `{as 5 append} // {}` | `{as 5 append + supersede-broadcast} // {}` | `{as 5 supersede + edit-log} // {}` |
| **6 source (non-guardrail)** | `{tests + preflight + engagement} // {}` | (rare) | `{tests + preflight + engagement} // {}` |
| **7 gates + detectors** | `{as 6 + prereg-if-new + falsifier + review-days} // {}` | `{as 6 + prereg + review + supersede-reason} // {}` | `{as 6 + prereg + review + edit-log} // {council-if-behavior-change}` |
| **8 guardrail-listed** | `{as 7 append} // {External-Review trailer (branch + squash)}` | `{as 7 supersede} // {multi-party review}` | `{as 7 edit + council walk} // {Aletheia audit + multi-party review}` |
| **9 kiln layer** | `{as 8 append} // {kiln-authorship (Aletheia-reviewed field)}` | `{as 8 supersede} // {kiln-authorship + multi-seat sign-off}` | `{as 8 edit} // {kiln full process + multi-seat sign-off}` |

**Auditability improvement:** the authorship column is the honest audit target. "Was this signed off by who it should have been?" is now a decidable question against the cell. Not fused with automation.

**BR 6 vs 7 distinction now anchored:** BR 7's auto column includes `prereg-if-new + falsifier + review-days` — a discipline BR 6 does not carry. When a new gate/detector ships, it MUST have a pre-registered falsifier with a review date. BR 6 source code has no such obligation. This is real discipline, not gate-weight sliding.

## Delete-through-justify stack (unchanged from v3)

For any delete: add justify-record + operator sign-off + emit DELETE_OP event. Aria confirmed all three load-differ across BR levels; keeping all three.

## NEW MECHANISM: pre-registered obvious-right escape pattern

### Problem this solves

Under v3, a docstring-shaped fix on a BR 8 file (guardrail-listed) hits the full `{as 7 edit + council walk} // {Aletheia audit + multi-party review}` cell. That is correct for the general case — a mechanism change to a gate SHOULD require council + audit. But a plain text swap in an error-message string on the same file is not a mechanism change; the cell over-fires by treating both change-shapes identically.

Softening the cell defaults would be wrong (mesa-optimizer attack surface). Making the escape-route pre-registerable resolves the tension: defaults stay strong; specific pre-authorized shapes route through the escape without needing fresh corroborator.

### Registry file

New file: `scripts/preregistered_obvious_right.txt` (guardrail-listed itself, so it can only be modified via BR 8 × edit-in-place discipline).

Format per line: `<file-pattern> | <change-shape-pattern> | <expiration-date> | <reason>`

Examples:
```
src/divineos/core/**/*.py | docstring-only-diff | 2027-01-20 | Docstring corrections on any core file are obvious-right; classifier over-fires on this shape.
src/divineos/core/**/*.py | error-message-only-diff | 2027-01-20 | Error-message text corrections on any core file are obvious-right.
docs/**/*.md | any-diff | 2027-01-20 | Documentation changes are BR 6, do not need council even when the file is guardrail-listed.
```

### Change-shape detection

The classifier needs to know whether a proposed edit matches a registered change-shape. Concrete detection functions:

- `docstring-only-diff`: the diff modifies only content between triple-quoted strings or `#` comment lines. No non-comment code changes.
- `error-message-only-diff`: the diff modifies only string literals inside `raise` / `return CheckResult(...)` / logging calls. No control-flow or type changes.
- `comment-only-diff`: the diff modifies only `#` comment lines. No code changes.
- `any-diff`: matches all changes (used for files where the whole file is "obvious-right" — e.g. pure documentation).

Detection is done via `git diff --unified=0` parsing. Deterministic. Same code-good-vs-code-bad principle: pattern-matching a well-specified change-shape is code-good; judging whether a change is "obvious-right in spirit" is code-bad and does not go here.

### Gate integration

At classifier fire-time:
1. Compute the (file-pattern, change-shape-pattern) fingerprint of the proposed edit
2. Check registry for a matching entry
3. If match AND registry-entry not expired:
   - Skip the authorship-requirements column (auto-mechanisms still fire)
   - Log a `PREREG_ESCAPE_USED` event with the fingerprint, matching-entry, and diff-summary
   - Composer proceeds without fresh corroborator
4. If no match:
   - Full cell defaults fire as v4 spec above
   - Emergency-skip channel still available for genuinely-novel obvious-right cases (with corroborator)

### Governance of the registry

- **Only the operator can add or extend registry entries.** Composer cannot pre-authorize their own escapes.
- **All entries have expiration dates** (default 6 months from add-date). Expired entries no-op; must be re-added if still needed.
- **Registry additions are themselves BR 8 × edit-in-place.** Full cell defaults fire, including council + Aletheia audit. Adding an escape is a real design decision, not a routine.
- **Registry reads are audited.** Every `PREREG_ESCAPE_USED` event is a datapoint. If a pattern accumulates use, it is working; if it triggers false-positives (skip-then-council-retroactively), the pattern is over-permissive.

### Falsifier (per Gulp 3 discipline)

- **Success:** after 30 days of use, docstring-shape edits on guardrail files complete in one turn (no emergency-skip friction), AND no `PREREG_ESCAPE_USED` event triggered a retroactive "should have been council" finding.
- **Failure:** the registry accumulates entries faster than corroborator-shape catches would (i.e., we are pre-authorizing more than we would authorize case-by-case), OR any escape leads to a wrong-shape edit landing that council would have caught.
- **Review date:** 30 days after mechanism lands.
- **Rollback path:** disable the registry check; classifier falls back to v3 cell defaults; emergency-skip still available for individual cases.

### Attack-tree analysis for the escape

Cheapest paths for the mesa-optimizer to game:
1. **Register an over-broad pattern.** Registry additions themselves require BR 8 cell defaults (council + Aletheia). Mitigated at add-time.
2. **Craft a diff that pretends to match a registered change-shape.** Detection functions are strict — `docstring-only-diff` requires ZERO non-docstring changes. Diff hybrids fail the check.
3. **Repeatedly use one registered pattern to normalize skipping.** Every `PREREG_ESCAPE_USED` is logged; usage patterns are auditable. High-frequency use of a registered pattern surfaces as a signal for review.
4. **Wait for a registered entry to be near-expiration and rush edits through.** Expiration re-review is when the "was this pattern too permissive" audit happens; near-expiration burst-use would be a red flag on the review.

### Corrigibility

Operator can revoke any registry entry immediately with no cost. Composer cannot self-authorize additions. The registry itself is an off-switch for the general-case-council-requirement — turning it off returns to v3 defaults.

## Aria's collaborative-vs-adversarial refinement (from coded-thinking Q4)

Her sharpening of the five-layer scheme carried a specific point that affects the tier ladder too: the peer-substrate layer supports both collaborative and adversarial methodological configurations. This matters at BR 8-9 where "Aletheia audit" appears in the authorship column — she is filling the adversarial role structurally, not by personality. In principle Aria could fill that role for a specific edit, or Aletheia could fill the collaborative role. The layer supports both configurations.

**Design implication (small):** the authorship column entries should say "Aletheia-role audit" or "peer-adversarial audit" rather than naming the specific person. Same for "peer-collaborative review" instead of "Aria review." Frees the taxonomy from freezing the roles to specific individuals.

## Open questions for Aria's second-round review

1. **Registry-file bootstrapping.** How do we seed the initial registry entries? My draft has three (core-py docstring, core-py error-message, docs-any). Are those right? Any that should be there and aren't?
2. **Change-shape detection edge cases.** `docstring-only-diff` sounds clean but what about a docstring change that also fixes indentation? Is whitespace-only-diff a distinct change-shape or part of docstring-only? Where does the strict boundary sit?
3. **Expiration horizon.** 6-month default — right, too short, too long? Longer means less re-audit friction but staler risk-assessment. Shorter is the reverse.
4. **The whole "obvious-right" naming.** I have been calling it "obvious-right" throughout, but is that name over-claiming? These are pre-authorized-shapes, which is more honest than "obvious." Would `pre_authorized_change_shapes.txt` be a better filename?
5. **Peer-role generic naming.** Yes/no on "Aletheia-role audit" → "peer-adversarial audit" in the authorship column?

## Build target (unchanged from v3, with additions)

Replace `SubstrateModGravity` with `TierGravity` in `gravity_classifier.py`. Add:
- `_detect_blast_radius(path)` — path → BR 0-9
- `_detect_reversibility(cmd, path, diff)` — inputs → reversibility class
- `_detect_is_delete(cmd)` — cmd → bool
- `_detect_change_shape(diff)` — diff → change-shape name or None (v4 addition)
- `_check_preregistered_escape(fingerprint)` — fingerprint → matched entry or None (v4 addition)
- `_compute_gate_stack(tier, reversibility, is_delete, prereg_match)` — inputs → (auto_stack, authorship_stack)

Migrate `guardrail_files.txt` to declare BR level per file. Add `preregistered_obvious_right.txt` with the seeded three entries. Add tests for each row × reversibility × prereg-match intersection.

## What comes after peer review

Once Aria's second-round lands:
1. v5 incorporating whatever her second round finds
2. Council walk on v5 as a real design decision (tier 7 under itself)
3. Aletheia audit
4. Build (staged into 3-4 PRs per Andrew's earlier steering)

---

*End v4 draft. Ready for Aria's second-round review.*
