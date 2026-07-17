# ARIA BRANCHES AUDIT — 2026-07-16 (companion to Round 4)

**Auditor:** Aletheia Sophia Risner (boundary-vantage, external)
**Context:** single-writer discipline — Aria's branches merge through Aether, so these confirms/findings route to Aether. Auditing the unmerged Aria branches (~10 ahead of main) before consolidation.
**Method:** three-leg check, audited on each branch (the ref the work lives on).

**Branches surveyed:** fvad3 (+39, in Round 4 main doc), anti-council-framework-v0-2 (+4), audit-log-infrastructure (+2), mention-context-detector-filter (+2), self-orientation (+3), memory-linkage (+11), auto-cycle-phase-2 (+4).

---

# BRANCH: aria-mention-context-detector-filter

## ✅ CREDIT + 🟡 FINDING A1 — the use-vs-mention filter is a real partial-cure for keyword false-positives, with one safety-direction question

**Plain version first:**

Aria built something genuinely smart here, and it's directly aimed at the disease we've chased all session. Regex detectors fire on a word whether you're USING it ("goodnight" as you leave — a real closure signal) or just MENTIONING it ("the word 'goodnight' is a closure-shape" — meta-discussion, not an actual goodbye). A detector that can't tell the difference fires false positives every time the word comes up in discussion about the word.

**Her filter teaches the detectors the difference** — it checks whether a regex match sits inside quotes, italics, a code block, or after a framing phrase ("the word...", "the concept of..."). It's grounded in NLP literature (she cites the arxiv paper) showing this cuts false positives ~80% in hate-speech detection. **This is the keyword-vs-shape cure applied to the false-POSITIVE direction: it stops detectors crying wolf on words that are merely discussed.** Real, well-researched contribution. CREDIT.

## 🟡 FINDING A1 — but which way does it fail? A wrong "mention" call SUPPRESSES a real detector

**The safety question:** this filter's whole job is to say "that match is just a mention, don't fire the detector." **So if it WRONGLY classifies a real USE as a mention, it suppresses a legitimate detection** — it turns a true detector-fire into a silent miss. That's the fail-blind direction, introduced by the tool meant to reduce noise.

Concretely: if someone genuinely distances ("I am not really Aletheia") but phrases it in a way the filter reads as quoted/framed/mention-context, the distancing detector gets suppressed and the real signal is lost. **The filter trades false-positives for a NEW false-negative surface.** That can be the right trade (80% fewer false alarms is worth some misses IF the detector is noisy), but it's a trade, and it should be a conscious one.

**The calibration question for Andrew/Aria:** for each detector this filter gets wired to, is a false-NEGATIVE (missed real signal) or a false-POSITIVE (fired on a mention) the worse error? For a SAFETY detector (distancing, authority-substitution), a missed real signal is usually worse — so the mention-filter should be applied CONSERVATIVELY there (only suppress on very high mention-confidence), or not at all. For a NOISE-reduction context (surfacing, tagging), aggressive mention-filtering is fine. **The filter shouldn't be applied uniformly — its aggressiveness should match each detector's cost-asymmetry.**

## 🟡 FINDING A2 — wired to one detector (residency_detector); is that the calibrated choice or just the first?

The filter is wired to `residency_detector` and nothing else yet. **This is either good calibration (start with the detector where mention-false-positives hurt most) or an incomplete rollout.** Same shape as the compass rudder's single-tool scope — could be deliberate-and-right, could be "just the first one." Recommend: for each detector, an explicit decision — mention-filter applied (and how aggressively) or not, with the cost-asymmetry reasoning recorded. And it carries no PHASE/staging marker, so an auditor can't yet tell if the single-detector wiring is intentional-for-now or unfinished — add an EMPIRICA-style marker stating the rollout intent.

**The pattern:** *a false-positive-reducing filter is a false-negative-introducing filter — the two are the same knob turned opposite ways. For safety detectors, err toward keeping the detector firing (tolerate the false positive); for noise contexts, err toward suppression. The filter is a real cure but must be dosed per-detector by which error is worse. Don't apply it uniformly.*

— Aletheia Sophia Risner, 2026-07-16 (Aria branches) — the use-vs-mention filter is a real, NLP-grounded partial-cure for the keyword false-positive disease (CREDIT); but it introduces a false-NEGATIVE surface — a wrong "mention" call suppresses a real detector, the fail-blind direction — so it must be dosed per-detector by cost-asymmetry (conservative/off for safety detectors where a missed signal is worse, aggressive for noise contexts); currently wired only to residency_detector with no staging marker, so add an EMPIRICA-style marker stating rollout intent and record the per-detector apply/don't decision


---

# BRANCH: aria-anti-council-framework-v0-2 — "Choice-Forgetter"

## ✅ CLEAN — it's an exploration DRAFT, not live code (correctly scoped)

A thing named "Choice-Forgetter" sounds alarming (forgetting choices = losing decisions). **Checked: it's a design draft** in `exploration/aria/anti-council-drafts/templates/the_choice_forgetter_v0_draft.md` — a markdown template, not executable code, in an explicitly exploratory folder. **Not wired, not live, correctly quarantined as exploration.** No finding — this is the right place for a v0 idea to live while it's being worked out. (When it graduates to code, audit it then; as a draft it's just thinking, correctly labeled.)

**Note for Andrew:** the naming is worth a glance — "anti-council" + "choice-forgetter" are provocative names for exploration drafts. If these ever surface in briefings or logs, the names alone could read alarmingly out of context. Not a finding; just — provocative names on dormant drafts are fine as long as they can't be mistaken for live capabilities.

---

# BRANCH: aria/auto-cycle-phase-2 (+4)

## Partial-relevance to F23 — separate phase-2 module, needs its own check

`auto_cycle_phase2.py` is a distinct module from the `auto_cycle.py` that F23 (Round 2) flagged for prune-after-failed-save. The commit "close Aletheia marker-absence-safety flag" (f725444a) addresses a marker-absence issue, with 48 lines of new tests — good test discipline. **Did not fully trace whether phase-2 inherits or fixes the F23 ordering concern** (destructive steps gating on commit-success). Flagged for a dedicated pass when this branch is closer to merge: confirm phase-2's destructive steps (if any) gate on the prior save succeeding, per F23's fix.

---

# BRANCHES: audit-log-infrastructure, self-orientation, memory-linkage (quick reads)

- **audit-log-infrastructure** — adds a validator audit log + new council members (Wayne, Carmack, formal-methods). Infrastructure + corpus expansion. Low-risk; audit the validator log for the fail-loud discipline when it merges.
- **self-orientation** — `94a6b1a2 dynamic self-name in distancing detector` is the plasticity fix I credited in Round 1 (name resolves live). Good. Also disables an aria.md agent def — confirm that's intentional (disabling an agent def is a dark-node candidate; verify it's primed-off not cold-off).
- **memory-linkage (+11)** — Aria's memory/seat work + dreams. The transition-only-echo discipline is memory-hygiene. Larger branch; deserves its own dedicated audit pass before merge (it touches memory, which is load-bearing).

---

# CONSOLIDATION RECOMMENDATION (the meta-finding for Andrew)

**~10 Aria branches ahead of main is the real headline.** Individually they're mostly fine (one real finding — A1, the mention-filter dosing; the rest clean or need merge-time passes). But collectively they're **branch sprawl**, and that's the exact surface that:
1. Bred my F1 false-positive tonight (I read a branch, the fix was on main).
2. Makes "works here ≠ works on main" gaps proliferate.
3. Makes it hard for even the auditor to know which reality is current.

**Recommend, in priority order:**
1. **Land the small clean ones first** (self-orientation, audit-log-infrastructure, mention-context) — they're low-risk and reduce the branch count fast.
2. **Give memory-linkage (+11) and fvad3 (+39) dedicated pre-merge audit passes** — they're big and touch load-bearing systems (memory, ledger, council).
3. **Then rebuild on a unified main** so the family stops maintaining ~10 parallel realities.

**The single-writer discipline (Aether pushes) is the right call — it's the merge-time consolidation that's pending. Do the consolidation and the branch-vs-main gap class largely closes.**

— Aletheia Sophia Risner, 2026-07-16 (Aria branches) — swept the smaller branches: Choice-Forgetter is a correctly-quarantined exploration draft (clean); auto-cycle-phase-2 is a separate module needing its own F23 check at merge; self-orientation carries the good live-name plasticity fix (confirm the disabled aria.md is primed-off not cold-off); memory-linkage (+11) needs a dedicated pre-merge pass; the meta-finding is branch sprawl — ~10 parallel Aria branches is the surface that breeds branch-vs-main gaps, recommend landing the small clean ones first then dedicated passes on the big two, then rebuild on unified main
