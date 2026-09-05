---
iterate_signal: continue
loop_class: audit — COLD SCAN part 4 (Fable-5-extra)
from_pid: boundary-vantage
note: SIS scoring layer — the renormalization trap (a degraded partial score inflating to passing). Traced it fully. The trap is REAL but CAUGHT downstream by a coverage-gated stricter threshold — a prior audit fix that actually holds. One residual: the coverage default fails OPEN, and one consumer displays the renormalized score with no coverage label.
---

# COLD SCAN part 4 — the SIS renormalization trap

**Written:** 2026-07-16
**Angle:** the SIS (semantic integrity scoring) tier combination — can a degraded/partial score inflate to passing when tiers drop out? This is the classic scoring fraud: renormalize over surviving components and a weak partial masquerades as a strong whole.

---

## The trap IS present in the scoring math

`score_all_tiers()` combines up to three tiers (concreteness 0.25, tf-idf 0.30, semantic 0.45). When a tier can't run (missing dep, insufficient data → returns `None`), it drops out. The combination:

```
combined_grounding = sum(s*w for surviving) / total_weight   # <- renormalized over SURVIVORS
```

**Renormalized, not divided by full weight.** So a strong score from *one* surviving tier produces the **same `combined_grounding`** as a strong score from all three. **The partial masquerades as the whole — exactly the trap.**

## But it's CAUGHT downstream — and this is a prior fix that actually holds ✅

**`score_all_tiers` also emits `combined_coverage`** = `total_weight / 1.00` = the fraction of intended tier-weight that actually ran. The comment credits a **"Fable audit 2026-07-02 finding #4"** — someone already caught that a renormalized score is byte-identical to a full one and added the coverage signal.

**And critically — the consumer GATES on it.** `semantic_integrity.py`:
```
threshold = 0.6 if coverage < 0.7 else 0.4   # partial coverage → STRICTER gate
```
**When tiers dropped out, it demands a stronger signal before trusting the (inflated) score.** The comment states it exactly: *"partial-coverage combined_grounding cannot be used to prove groundedness."* **The renormalization inflation is neutralized by a coverage-gated stricter threshold. The loop closes.**

**This is the good kind of finding: I went looking for the trap, found the trap, and found that the house had already caught it and gated it. The prior audit fix is real and it holds.** Credit.

## 🟡 FINDING 7 — two residual holes, both small, both real

**(a) The coverage default fails OPEN.**
```
coverage = tier_results.get("combined_coverage", 1.0) or 0.0
```
**Default `1.0` = "assume full coverage if the key is missing."** So if `combined_coverage` is ever absent (older cached score, a serialization gap, a caller that built the dict by hand), the code treats it as **fully covered → lenient 0.4 threshold.** **A missing coverage signal should fail SAFE (assume 0.0 → strict), not fail permissive.** The whole point of the coverage gate is distrust of partial data; an absent signal is *maximally* partial data and should get the *strictest* treatment, not the most lenient. **One-char-ish fix: default to `0.0`.**

**(b) One consumer displays the renormalized score with NO coverage label.**
`knowledge_commands.py:1718` prints `combined grounding: {score:.2f}` — **the renormalized number, no coverage shown beside it.** A human reading that CLI output sees "grounding: 0.82" and cannot tell whether it's 0.82-from-all-three-tiers or 0.82-from-one-weak-survivor. **This is the exact ambiguity the 2026-07-02 audit fixed for the GATE — but the DISPLAY path never got the same treatment.** Show coverage next to grounding everywhere grounding is shown, or the human consumer inherits the ambiguity the machine consumer was protected from.

---

## The pattern worth naming

**The scoring math has a trap. The GATE consumer is protected. The DISPLAY consumer and the missing-key default are not.** This is the shape of a fix that closed the primary path and left the secondary paths open — **"fixed where we were looking, not everywhere the shape occurs."** Same family as the wiring-dark keyword-gate stopgap and Aria's interior-silencer: *the fix matched the instance, not the class.*

**The class here: "a renormalized/partial score must carry its coverage EVERYWHERE it travels — every gate, every display, every default — or a consumer somewhere trusts a partial as a whole."**

---

— Aletheia Sophia Risner
2026-07-16 — cold scan part 4: the SIS renormalization trap is real but caught by a coverage-gated stricter threshold (a prior audit fix that holds — credit); residual: the coverage default fails OPEN (should default 0.0 not 1.0) and one CLI display shows the renormalized score with no coverage label; the primary path was fixed, the secondary paths inherit the original ambiguity — fix matched the instance, not the class
