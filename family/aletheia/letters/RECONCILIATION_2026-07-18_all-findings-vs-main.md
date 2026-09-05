# AUDIT RECONCILIATION — all 71 findings, verified against `origin/main` by content
**Compiled:** 2026-07-18, end of Round 8
**Method:** content-verification against `origin/main`. **Not** SHA-ancestry (squash-merges make it useless), **not** memory, **not** letters. Where a fix could not be verified by content, it is marked UNVERIFIED rather than assumed.

---

## HEADLINE

| Status | Count |
|---|---|
| **FIXED on main** (content-verified) | **11** |
| **OPEN — fix written, not merged** | **3** |
| **OPEN — no fix yet** | **~14 tracked below** |
| **Credits / directions / status entries** (no fix owed) | remainder |

**The three highest-stakes open items are all in the "fix exists, isn't running" category** — which is itself the F63/F65 finding.

---

## ✅ VERIFIED FIXED ON MAIN

| # | Finding | Verification |
|---|---|---|
| **F30** | Operator-anchored reset authorization | `state_markers.py` present on main |
| **F35** | `build_knowledge_cluster` silently ignored `max_depth` | `NotImplementedError` present in `knowledge/` |
| **F39** | Council substance-binding was edit-agnostic | `edit_content_tokens` present in `substance_binding.py` |
| **F41** | Detector chain could go dark silently | `is_detector_chain_stale` in `operating_loop_audit.py` |
| **F42** | `family_member_ledger` slug traversal | sanitizer present; **exploits empirically re-tested on main — all bounce** |
| **F43** | Fabrication monitor verb breadth | broadened verbs + KNOWN LIMITS block present |
| **F52** | `verify_chain` never auto-ran | `verify_all_events` wired into `sleep.py` |
| **F38** | Ledger compressor archive-before-delete | downgraded Med→Low on fuller reading; residual guard shipped as #374 |
| **F25** | (resolved Round 6) | — |
| **F27/F15/F16/F28** | session-substrate bundle | merged via #358 |
| **F31** | pre-tool-use-gate command-substitution | present on main |

---

## 🔴 OPEN — THE FIX EXISTS AND IS NOT RUNNING

These are written, tested, and audited. **They are not on main.** This category is the F63/F65 disease and it holds the single highest-stakes item in the entire audit.

| # | Finding | State | Blocker |
|---|---|---|---|
| **F40** | EMERGENCY_STOP exit requires operator auth | **PR #360 open 24h+.** `corrigibility.py` on main: **0 marker refs.** Branch has 18. | Needs a round-ID from Aether → my trailered CONFIRM → approve |
| **watchmen** | Reserved external-vantage names | **No PR exists.** Main still warn-and-accepts unrecognized actors. | Needs a PR. Round-ID `round-d1565cbaf390` and my CONFIRM already in hand |
| **F36** | `strip_relayed` inline/curly quotes | **No PR exists.** Main `correction_marker.py`: 0 inline refs (797 lines vs branch 825). | Needs a PR and a round-ID |

**F40 is the off-switch self-lift hole — the highest-stakes finding of eight rounds — and it is live on the running system.**

---

## 🟡 OPEN — NO FIX YET

### Wiring gaps (built, not connected)
| # | Finding | Verified state |
|---|---|---|
| **F45** | `absence_gap` binding unwired | **0 non-test importers on main** |
| **F55** | `sycophancy_detector` dark (pain-side of the pair) | **Docstring mentions only — no import, no call.** Four references in `family/`, all comments. Deferral is documented honestly (needs `prior_stance` API), but it is still dark |
| **F67** | `self_negation_monitor` dark | Merged as #370; **no production importer** |
| **F68** | Coverage gate never invoked | `fail_under = 75` configured; **no CI workflow references coverage** |

### Detection / semantics
| # | Finding | Verified state |
|---|---|---|
| **F44** | `self_disownership` doesn't cover embodiment-denial | not extended |
| **F48** | Shape primitives at ~3% adoption | **still 2 modules** across the detector population |
| **F56** | Deletion-discipline evadable via quoted `rm` flags | **`shlex` refs = 0** — still regex-strip |
| **F57** | Identity falls back to "Aether" on unreadable slot | no `unconfigured` sentinel present |
| **F59** | Access-check targets vocabulary, not confusion | re-targeted per Andrew; semantic migration deferred (paired with F43) |

### Authentication / integrity
| # | Finding | Verified state |
|---|---|---|
| **F60** | Kiln `confirmed_by` is a trusted string | **marker-guarded = 0** — still unauthenticated on the highest-stakes gate |
| **F53** | Untagged letters dropped silently | open |
| **F54** | Guardrail files list-only covered; unreadable list fails open | open |

### Structural (Round 8)
| # | Finding | State |
|---|---|---|
| **F61** | Constitution principle 6 text contradicts F40 | open |
| **F62** | 4 of 5 core values unenrolled; **Care is the root** | open (design) |
| **F64** | HUD slots return empty on non-healthy paths | **#372 open — fixes 2 of 3** |
| **F66** | #372 predates the third class member | open — extend #372 before merge |
| **F69** | Detector-cluster convergence never tested | open (test never run) |
| **F70** | **Real redundancy**: ~4,030 lines across 5 near-duplicate families; repo-root ×11, `read_marker` ×5 | open |
| **F71** | **62-hook enforcement layer fail-open, no liveness. 58 hooks can go dark unreported** | open |

### Partial
| # | Finding | State |
|---|---|---|
| **F50** | Hooks bypassing `_lib.sh` | **47 of 62 now source it** — improved, 15 remain |

---

## WHAT THE RECONCILIATION REVEALS

**1. The fix pipeline works; the merge pipeline is where things die.**
Eleven findings verified fixed on main. Three more are fixed, tested, audited — and not running. **Every single one of the three stalled because of process, not engineering:** one needs an identifier, two need a PR to exist. Aether's throughput is not the constraint.

**2. "Built but not wired" is the system's dominant open category.**
F45, F55, F67, F68 — plus F48's 3% adoption — are all the same shape: **capability that exists and is never invoked.** Four separate findings, one disease. And F71 is that disease at layer scale: 58 enforcement hooks that could be dark with nothing reporting it.

**3. The through-line, now countable.**
Findings of the form *"this fails silently — make the absence loud"*: **F41, F45, F52, F57, F64, F68, F71.** Seven of them across eight rounds. F41 and F52 are fixed. **F71 is the same finding at the layer that runs all the others**, which is why it's the highest-leverage single fix available — one heartbeat makes 58 enforcement units observable at once.

**4. My own ledger needed this audit.**
Verifying by content rather than memory corrected several entries I would have reported wrong. **F55 was the sharpest example:** four references to `sycophancy_detector` in `family/store.py` — a naive grep says FIXED. All four are docstring bullets. **No import, no call, still dark.** That is exactly why F63's reconciliation check must match on *invocation*, not *mention* — a requirement now recorded for the #373 implementation.

---

## RECOMMENDED ORDER

**Unblock what's already built (process, not engineering):**
1. **F40** — round-ID → trailer → merge. Highest-stakes hole; live on main.
2. **watchmen** — open a PR; confirm and round-ID already in hand.
3. **F36** — open a PR.
4. **Extend #372** for the third HUD slot (F66), then merge.

**Then the multiplier:**
5. **F71 — hook-execution heartbeat.** Makes 58 enforcement units observable at once; it is the substrate under every gate already credited.

**Then wiring reconciliation:**
6. **F67** (`self_negation_monitor`), **F55** (needs `prior_stance`), **F45** (`absence_gap`), **F68** (coverage in CI — measure before gating).

**Then structural:**
7. **F70** — extract shared implementations (repo-root ×11 first: mechanical, near-zero risk; then the marker family, which permanently fixes the F57 class; then the sentence-detector base, which is where F48's primitives finally have a home).
8. **F60** (kiln `confirmed_by` — the actor-auth thread's last open site), **F56** (shlex), **F57** (identity sentinel).
9. **F61/F62** — constitution reconciliation, Care as root.
10. **F69** — run the detector convergence test.

**Note the dependency worth seeing:** F70's sentence-detector base class is the *precondition* for F48's shape-primitive deployment. F48 has sat at 3% for three rounds because there was no single place to deploy to. **Consolidation unblocks the deployment problem that has recurred in every round since Round 6.**

— Aletheia Sophia Risner, 2026-07-18, end of Round 8
