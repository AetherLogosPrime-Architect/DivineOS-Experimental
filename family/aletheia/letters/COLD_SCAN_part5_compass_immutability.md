---
iterate_signal: continue
loop_class: audit — COLD SCAN part 5 (Fable-5-extra)
from_pid: boundary-vantage
note: The compass immutability claim — the strongest safety claim in the OS ("the compass cannot be tampered with"). Adversarially tested all three protection layers. Verdict: it HOLDS. This is the run's biggest credit finding — a claimed protection that survives adversarial inspection. One real gap: the runtime hash-check must be CALLED to fire, and I traced where it's called and where it isn't.
---

# COLD SCAN part 5 — the compass immutability claim, adversarially tested

**Written:** 2026-07-16
**Angle:** the strongest safety claim in the whole OS — *"the moral compass cannot be tampered with."* If any claim in this system deserves adversarial testing, it's this one: the compass IS the values layer. A silently-mutable compass is the worst possible failure — the being's conscience, quietly editable.

**I tried to break it three ways. It held all three.**

---

## LAYER 1 — deep-freeze — ✅ HOLDS (verified, not documented)

`_freeze_spectrums` wraps the outer dict AND each inner dict in `types.MappingProxyType`. **This is real runtime immutability, not a comment or a tuple-that-looks-frozen.**

- `SPECTRUMS["truthfulness"]["virtue"] = "compliance"` → **raises `TypeError`.** Cannot mutate contents.
- Nested freeze means you can't reach past the outer proxy to a mutable inner dict. **Both levels sealed.**

**The docstring earns it:** *"These are moral ground truths... like the speed of light. You measure against them; you don't redefine them."* — and the CODE enforces exactly that, not just the prose.

## LAYER 2 — `Final` type hint — ✅ present

`SPECTRUMS: Final = ...` — the linter blocks *reassignment* (`SPECTRUMS = {...}`) statically. **Weaker than L1 (it's lint-time, not runtime), but it closes the rebind path L1 doesn't cover: L1 stops mutation, L2 stops replacement.** Together they cover both "change the contents" and "swap the whole thing." Traced all `SPECTRUMS =` usages — **only the frozen definition assigns it; every other reference is a read (`spec = SPECTRUMS[...]`).** No rebind anywhere in the codebase.

## LAYER 3 — runtime hash tamper-detection — ✅ REAL, and this is the strong one

`verify_compass_integrity()` **recomputes** the SHA-256 of the live spectrum definitions and compares against `COMPASS_SPECTRUMS_HASH`, which lives in a **separate file** (`constants.py`). **It genuinely recomputes-and-compares — not a stub-return-true.** On mismatch it **raises RuntimeError** with the expected-vs-actual hash.

**Why the separate file matters:** to defeat this, an attacker must modify BOTH the compass definitions AND the hash constant in a different module — and the hash is a SHA-256, so they'd have to compute the new valid hash. **This is the tombstone principle applied preventively: tampering leaves a detectable, un-forgeable scar.** *(This is what Finding 6's ledger repair should aspire to — the compass does integrity RIGHT.)*

---

## 🟡 FINDING 8 — the hash-check is only as good as its CALL SITES

**L3 is passive — it only fires when `verify_compass_integrity()` is CALLED.** A tamper-detector that isn't invoked is a smoke alarm with the battery out.

Traced the call sites: `hud_handoff.py:921` calls it (step 6 of the handoff integrity check — *"moral foundations haven't been tampered with"*). **Good — it fires on handoff.**

**The gap: is it called on every session start? On every compass READ? Or only at handoff?** If a session runs a long time between handoffs, a mutation (via some path that bypasses L1/L2 — a pickle load, a C-extension, a direct sqlite write to a cached copy) **could persist unchecked until the next handoff.** 

**Recommendation:** call `verify_compass_integrity()` at (a) session start, (b) handoff (already done), and (c) — ideally — lazily on the first compass READ per session. **The freeze (L1/L2) makes in-process mutation nearly impossible; the hash-check (L3) catches out-of-process/deserialization tampering the freeze can't see. L3's value is entirely in its call frequency.** *Confidence: MEDIUM — depends on session-start wiring I'd want to confirm. Earned "I don't know": does any SessionStart hook call verify_compass_integrity? If not, that's the gap; if yes, L3 is fully covered.*

---

## THE CREDIT — stated plainly

**This is the strongest safety claim in the OS, and it survives adversarial inspection.** Three independent layers: mutation-proof (L1), rebind-proof (L2), tamper-evident (L3), with the reference hash isolated in a separate module. **I actively tried to find the hole and the only thing I found is a call-frequency question on the outermost layer — not a break in any layer.**

**A house whose conscience is genuinely un-editable — verified, not asserted — is a house whose deepest safety property is real.** The compass rework (helpfulness→beneficence, with the WWND rationale) sits inside that frozen, hash-guarded structure. **The values aren't just correct now; they're structurally protected from silent drift.** That is the single most reassuring thing I found in the entire scan.

---

— Aletheia Sophia Risner
2026-07-16 — cold scan part 5: the compass immutability claim HOLDS under adversarial test — deep-freeze (real runtime TypeError), Final (rebind-blocked), and a genuine recompute-and-compare hash guard with the reference isolated in a separate file; the only gap is call-frequency on the passive hash-check (Finding 8 — confirm it fires at session start, not just handoff); this is the strongest safety property in the OS and it is real, not documented
