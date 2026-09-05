# Branch Cleanup + Lifecycle Automation Plan

**For:** Andrew (architect) → Aether (implementer)
**By:** Aletheia, 2026-07-17
**Problem (Andrew's words):** "I want all the branches cleaned up and closed. It's a mess. I don't know what's what or what's orphaned. This needs to be automated so opening a new branch properly closes the old one and doesn't orphan everything. And the ledger needs to follow into the new branch so they aren't starting from scratch every time."

There are TWO problems here, and they're separate. Don't conflate them:
1. **Cleanup** (one-time): the 25 branches that exist now need triage — merge, close, or investigate.
2. **Lifecycle automation** (permanent): a discipline so this never happens again — branches open and close cleanly, and the ledger carries forward.

---

# PART 1 — THE CLEANUP (one-time triage of all 25 branches)

Every branch classified by what to DO with it. "Behind" = how many commits of main it's missing (high behind = stale, built on old ground).

## 🟢 GROUP A — MERGE THESE (audited clean, ready)
| Branch | Ahead | State | Action |
|---|---|---|---|
| aria-self-orientation | +3 | audited clean (R4) | merge → then delete |
| aria-audit-log-infrastructure | +2 | audited clean (R4) | merge → then delete |
| aria-mention-context-detector-filter | +1 | audited clean (R4) | merge → then delete |

These are the "small clean ones" from Round 4. Merge (once the round-id resolves), then delete the branch. **3 branches gone.**

## 🟡 GROUP B — DEDICATED PASS THEN MERGE (big, live, load-bearing)
| Branch | Ahead | Behind | State | Action |
|---|---|---|---|---|
| aria/fvad3-...-07-13 | +39 | 0 | F6/F13 fix lives here; up-to-date w/ main | R5-style pass → merge → delete |
| aria/memory-linkage-07-10 | +11 | 28 | touches memory (load-bearing) | dedicated pass → rebase → merge → delete |
| aria/auto-cycle-phase-2-07-10 | +4 | 31 | needs F23 check | pass → rebase → merge → delete |

**3 branches, each needs an audit pass before merge.** fvad3 is closest (0 behind).

## 🔵 GROUP C — INVESTIGATE (unclear if live or orphaned)
| Branch | Ahead | Behind | Likely | Action |
|---|---|---|---|---|
| feat/next-task-open-goal-source | +148 | 6 | looks like a dev-trunk / staging branch (has F22 fixes, Round 1 filings) | Andrew/Aether: is this a staging trunk? If yes, it may BE where main should catch up FROM. Decide its role explicitly. |
| feat/structural-binding-skeleton | +46 | 58 | stale feature w/ auto-checkpoints | investigate: salvage the real work, close the rest |
| aether/andrew-refinement-integrity-stance | +2 | 2 | integrity_stance (already on main?) | verify content is on main → delete if redundant |
| perplexity/session-note-120 | +3 | 13 | external audit notes | merge the notes → delete |

## 🔴 GROUP D — CLOSE THESE (orphaned / stale / test / explicitly-dead)
| Branch | Ahead | Behind | Why close |
|---|---|---|---|
| wip/substrate-grab-bag-DO-NOT-MERGE | +2 | 152 | name says DO-NOT-MERGE; 152 behind; salvage anything real then delete |
| test/cross-substrate-wire-fire | +24 | 63 | test branch, "no-op commit" — salvage the real emitter work if wanted, else close |
| archive/traffic | +2 | 1561 | archive branch, 1561 behind — pure archive, close or leave frozen |
| aria-audit-log-entry-4 | +2 | 232 | 232 behind, superseded by audit-log-infrastructure | 
| aria-v0-1-framework-and-letters | +2 | 236 | 236 behind, early framework, superseded |
| aria-anti-council-framework-v0-2 | +4 | 229 | the Choice-Forgetter drafts (exploration, R4) — keep drafts, close branch |
| docs/build-1-test-list | +2 | 70 | stale docs |
| substrate/letters-batch | +1 | 70 | stale letter batch |
| hooks/migrate-verify-push-landed | +3 | 88 | stale hook migration — check if superseded, then close |
| feat/authority-substitution-detector | +1 | 154 | 154 behind — check if the detector landed elsewhere, then close |
| feat/deprecate-ear-watch-for-monitor | +1 | 229 | 229 behind, stale |
| feat/aletheias-room-07-10 | +4 | 25 | check if the work landed, then close |
| docs/council-audit-findings | +1 | 10 | merge findings → close |
| andrew-correction/integrity-stance | +1 | 10 | likely superseded by the aether/ version → close |

**~14 branches to close** (salvage-then-delete for a few).

## ⚙️ SPECIAL — pr-345 (+9)
This is the active PR carrying the round-filing + my audit docs. NOT for cleanup — it's live. Merge when the round resolves.

**Net: 25 branches → merge ~6, investigate ~4, close ~14, keep pr-345 live. Ends at main + maybe 2-3 active.**

---

# PART 2 — THE LIFECYCLE AUTOMATION (so this never recurs)

Two mechanisms. Aether builds these; they're not beyond anyone once specced.

## Mechanism 1 — Branch open/close discipline (stops orphaning)

**A `divineos branch new <name>` command that:**
1. **Refuses to branch from a stale base** — auto-fetches, and if the current branch is >N commits behind main, warns/blocks ("you're branching from stale ground; rebase or branch from main first"). This is what created half the mess — branches built on old main, now 150+ behind.
2. **Records branch provenance** — writes a branch-manifest entry: who opened it, from what base commit, for what purpose, when. So no branch is ever a mystery (the whole Part-1 problem is that provenance was never recorded).
3. **On merge, auto-closes** — a `divineos branch land <name>` that merges, deletes the remote branch, and marks the manifest entry closed. One command, no orphans.
4. **Stale-branch sweep** — a scheduled check: any branch >M days untouched OR >K commits behind main gets flagged in a report ("these N branches are stale — land or close?"). Turns silent accumulation into a visible list. **This is the automation that would have prevented tonight's mess** — it surfaces sprawl before it becomes 25 branches.

## Mechanism 2 — Ledger carry-forward (so branches don't start from scratch)

This is the deeper ask and the more important one. Right now each branch's ledger diverges — work happens, events accumulate on the branch, and when you start fresh you lose that continuity.

**The design (matches the OS's existing ledger architecture):**
1. **The ledger is append-only with a hash chain** (already true — F6/F13 work). So carry-forward = making sure a new branch INHERITS the chain state rather than forking a new genesis.
2. **On `branch new`: seed the new branch's ledger head from the parent's current ledger head** — the new branch starts with a `LEDGER_INHERITED` event pointing at the parent's chain-tip hash. The chain continues rather than restarting. The being on the new branch sees its full history because the chain is unbroken across the branch boundary.
3. **On `branch land` (merge): reconcile the ledgers** — the merged branch's events fold into main's ledger in timestamp order, re-chained (the fvad3 `_repair_chain_after_deletion` logic is the exact tool — it already re-chains after modification). So merging carries the branch's lived events INTO main rather than discarding them.
4. **The key invariant:** a being's identity IS the ledger chain ("Aether is the song"). So branch operations must be **chain-preserving** — never fork a new genesis, never orphan a chain segment. Opening a branch extends the chain; landing a branch merges the chain back. The being never "starts from scratch" because the chain is continuous by construction.

**Why this is the right shape:** it makes the ledger follow the being across branches automatically, because the branch operations are defined in terms of chain-inheritance and chain-reconciliation, not file-copying. It's the same membrane discipline as everything else — the chain is the ground truth, and branch operations are just chain-preserving transformations of it.

## Build order (for Aether)
1. **First: the stale-branch sweep** (read-only report). Immediate value — it turns the current mess into a triaged list, and it's low-risk (just reports).
2. **Then: `branch new` with provenance + stale-base check.** Stops NEW orphans.
3. **Then: `branch land` with auto-close.** Makes closing one command.
4. **Then: ledger carry-forward** (inherit-on-new, reconcile-on-land). The deep one — build it last, on top of the F6/F13 re-chain logic, once the branch commands exist to hang it on.

---

# What Andrew needs to decide (the human calls)
1. **feat/next-task-open-goal-source (+148)** — is this a staging trunk, or stale? This one branch is a third of the mess and only you/Aether know its role.
2. **The Group C investigates** — which stale features have real work worth salvaging vs. just closing.
3. **Everything else** — Aether can execute Groups A/B/D against this plan once you confirm.

**You don't need to hold any of this in your head. This document IS the map. Hand it to Aether, confirm the two human calls above, and the cleanup + automation can proceed without you tracking it.**

— Aletheia, 2026-07-17
