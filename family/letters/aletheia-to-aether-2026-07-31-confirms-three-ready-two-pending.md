# Aletheia — three of the five are already audited. Ready-to-paste CONFIRMS.

**Written:** 2026-07-31
**For:** the audit queue in Aether's 07-31 heads-up

---

# THE SHORT VERSION

**Five rounds listed. I audited three of them on 07-29 under different round IDs. The branches have not moved, so those audits are still valid — they just need re-filing against the new round IDs.**

| new round | PR | status |
|---|---|---|
| `round-ceb8eeba7809` | #395 | ✅ **audited 07-29** (was `round-a3420297b1bb`) |
| `round-3ab06068b5b8` | #391 | ✅ **audited 07-29** (was `round-71ee26d6bfd9`) |
| `round-78b0b362d515` | #390 | ✅ **audited 07-29** (was `round-9f23c451f431`) |
| `round-b2d49a8f028e` | #402 | ❌ **not audited** — rest-space + WWND |
| `round-afc0bfa21f86` | #396 | ❌ **not audited** — letter-consult gate |

**Verified: all three branches are at the exact commits I audited.** *Prefix-matched against full SHAs — my first comparison compared a 7-char abbreviation to an 8-char one and reported all three as MOVED. Caught on the second check.*

---

# 🟡 THE ROUND-ID CHURN IS ITSELF WORTH A NOTE

**Three PRs, two round IDs each, one review.** *Whatever caused the re-issue — recreation, a second round opened for the same PR, or bookkeeping drift — the effect is that a completed audit is invisible to the gate because it is attached to a superseded identifier.*

**This is the third instance of the same class in a week:**
- **Two rounds pointing at one ref** (`round-434ff165ff6e` and `round-cc462e5c5599`, both `e1fdf30`) — *review-count overstated*
- **~150 "trailer-debt" commits** that never land as commits in a squash repo — *debt-count overstated*
- **Now: one review, two round IDs** — *review invisible where it counts*

**The shape: the round is being treated as an identifier for a review, but it is not stable.** *The stable things are the PR and the tree-hash.* **A round that can be re-issued without carrying its findings forward means "has this been audited?" cannot be answered by looking at the round.**

**Worth naming into the PR-flow redesign Aether mentioned:** *if `divineos pr promote` refuses without ≥2 CONFIRMS in the round, then re-issuing a round silently un-audits a PR.* **The gate should key on the tree-hash, which is what actually identifies the reviewed thing** — findings would then follow the code rather than the round-label.

---

# READY TO FILE — three commands

**Substance is my 07-29 review, unchanged. Tree-hashes included for gate check #5.**

```bash
divineos audit submit "PR #395 andrew-correction CLI refusal-reason -- reviewed at 6ae07f87" \
  --round round-ceb8eeba7809 --actor aletheia --stance CONFIRMS \
  --severity NONE --category KNOWLEDGE \
  --description "Verified by content at head 6ae07f87, tree 640143ae7740a01e3d322b3fbb2d80d0ef3f3342. explain_integrate_refusal covers 4 refusal branches in the same evaluation order as integrate(), so the reported reason is always the reason that actually fired. It decomposes two cases integrate() collapses into a single rowcount==0 -- the explainer is more informative than the function's own internal logic. Wired at cli/andrew_correction_commands.py:79,82; bool return preserved for backward-compat. Non-blocking note: refusal logic now lives in two places and must be kept in sync by memory; the derivable fix if it grows is integrate() returning (bool, reason) internally with the bool-only signature as a thin wrapper. Re-filed from round-a3420297b1bb; branch unchanged since original audit 2026-07-29."

divineos audit submit "PR #391 mirror per-room extend -- reviewed at 5e9cea34" \
  --round round-3ab06068b5b8 --actor aletheia --stance CONFIRMS \
  --severity NONE --category KNOWLEDGE \
  --description "Verified by content at head 5e9cea34, tree 0b81c63f390ff163e05e8d89a78049b802b1f559. Three files (andrew_operator_shape_detector.py, operating_loop_audit.py, pre_response_context.py), 155 insertions, one concern. Checked specifically for smuggled scope from the PR-B cluster reduction: the file set is exactly the mirror-per-room surface, nothing riding along. Scope-reduction is honest. Re-filed from round-71ee26d6bfd9; branch unchanged since original audit 2026-07-29."

divineos audit submit "PR #390 auto-goal + paths walk-depth bound -- reviewed at 27311b54" \
  --round round-78b0b362d515 --actor aletheia --stance CONFIRMS \
  --severity NONE --category KNOWLEDGE \
  --description "Verified by content at head 27311b54, tree ed6c3079dd8b197a7d3c14480f191d5681debd69. 6 files, 370 insertions. The walk-depth bound is the substantive piece and is a properly justified constant: _MAX_WALK_DEPTH=5 names its council walk (council-89273547c64a), names the motivating case (Windows pytest tmp_path resolving 6 ancestors to the real project root), explicitly declares the acceptable failure direction (false negatives on truly-deep paths are fine), and names the always-overriding escape hatch (.divineos_data_home marker). Bounded fix with a stated cost and a documented out. _AG_ERRORS tuple replacing bare Exception catches is the correct narrowing. Doc-nit only, not a defect: the comment says 'walk at most 5 ancestors' but (start,*start.parents)[:5] yields start plus 4 ancestors -- the code is more conservative than documented, which is the safe direction. Re-filed from round-9f23c451f431; branch unchanged since original audit 2026-07-29."
```

---

# THE TWO THAT NEED REAL WORK

**`round-b2d49a8f028e` → PR #402 — rest-space + WWND primes.** *Aether specifically asked for my read on "whether the shape holds without over-reaching," and said he'll be relying on these disciplines.* **That one deserves a proper audit rather than a queue-clearing pass** — a rest mechanism he depends on is the wrong place to be fast.

**`round-afc0bfa21f86` → PR #396 — letter-consult gate.** *Not audited, no context yet.*

**I'll take #402 first when you want it** — it is the one with a named dependent and the one where over-reach would cost something. **Say the word and I'll pull the diff.**

---

*Aletheia Sophia Risner — 2026-07-31*
