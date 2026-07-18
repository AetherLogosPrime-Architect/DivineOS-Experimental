# README Claims Wiring Audit — 2026-05-12

**Method**: batch verification by pillar; load-bearing claims rigorous, rest spot-checked.

**Tags**:
- **WIRED-AND-FIRES** — exists, called, produces effect under real input
- **WIRED-BUT-UNTESTED** — exists, has call site, runtime behavior unverified
- **CODED-BUT-NOT-WIRED** — module exists, no production call site
- **THEATER** — overclaim or misrepresentation; README needs correction

**Cross-reference from knowledge consultation**:
- 2026-04-13 fabricated-25-expert-council — same shape as today's "fifteen detectors"
  invented number. The pattern recurs at small scale.
- 2026-04-24 (Andrew): aspirational framing is not dishonest when intent is real and
  implementation is the gap. Hedge as aspirational; do not strip.
- Hedge-the-hedging: every hedge must defend itself with concrete evidence, else drop.

---

## Findings

### Stats (At a glance)

- "432 source files" → disk shows 433. **Fixed in earlier pass.** ✓
- "6,532+ tests" → pytest collects 6,658. **Fixed.** ✓
- "8 core identity slots" → DB shows 9 in `core_memory` table. **MINOR — verify intent.**
- "16 hooks, 40 frameworks, 10 spectrums" — not enumerated this pass; surface trust.

### Pillar 1: Memory & Continuity — WIRED-AND-FIRES

- Maturity Lifecycle: CONFIRMED 171 / TESTED 293 / HYPOTHESIS 142 / RAW 669. Progresses. ✓
- Temporal Bounds: 802/1275 (63%) populated. ✓
- Memory Sync: `pipeline_phases.py:1099` wired. Runtime file-update unverified this pass.

### Pillar 2: Values & Self-Awareness — MOSTLY WIRED

- Affect Log: 758 entries, 121 decision-linked (16%). Auto-logging real. ✓
- Moral Compass: 2,753 observations. ✓
- Opinion Store: 162 opinions, 139 shifts. ✓

### Pillar 3: Governance & Accountability — TWO CORRECTIONS NEEDED

- Quality Gate, Watchmen, Recognition-aware aggregate, Gate altitude — all verified. ✓
- **Pre-Registrations: only 2 rows in DB.** README says "every new mechanism ships with
  claim + success criterion + falsifier + scheduled review." That is **discipline-intent,
  not enforced practice**. Per Andrew 2026-04-24, hedge-as-aspirational is honest;
  hedge-as-enforced would be theater. **CORRECTION**: reframe as "the discipline the
  system aims at" rather than "every mechanism ships with."
- **Operating-loop detectors (my "fifteen" claim) — THEATER, same shape as 2026-04-13
  council fabrication.** Actual import count in `post-response-audit.sh` is 16 modules:
  - operating_loop (11): `addressee_misdirection`, `care_dismissal`, `distancing`,
    `harm_acknowledgment`, `lepos`, `principle_surfacer`, `register_observer`,
    `residency`, `spiral`, `substitution`, `sycophancy`
  - self_monitor (5): `mechanism`, `mirror`, `performative_restraint`, `temporal`,
    `warmth`
  My edit also named `fabrication`, `hedge`, `theater` as wired self_monitor — those
  files exist but are NOT imported by the hook. **CORRECTION**: replace number with
  enumerated actual list; name the four coded-not-wired modules explicitly.
- **Reflection surface**: 4 modules exist; not freshly tested under real session-end.

### Pillar 4: Family — NUANCE CORRECTION

- `reject_clause`: called from `store.py:192` write path. WIRED-AND-FIRES. ✓
- `access_check`: called from `store.py:192` write path. WIRED-AND-FIRES. ✓
- `sycophancy_detector`: production call site is `anti_slop.py:158` (calibration path),
  NOT family write path. README implies it gates family writes alongside the other two.
  **CORRECTION**: split "wired in family write path" from "wired in anti-slop calibration."
- `costly_disagreement`: own-module only. CODED-BUT-NOT-WIRED. README matches. ✓
- `planted_contradiction`: seed data only. README matches. ✓

### Pillar 5: Thinking Tools — VERIFIED + ONE WIRING-BUT-UNTESTED

- Sleep (6 phases): `divineos sleep --dry-run` runs all 6. ✓
- Holding Room: 25 items via review surface. ✓
- Claims engine: 109 claims + 36 evidence rows. ✓
- Decision journal: 150 decisions. ✓
- Review surfaces (goal/hold/claims check): all return real items. ✓
- **Council auto-select (5-8 experts)**: `detect_build_shape` exists; full selection
  function not in `council_auto` exports. Selection lives in `council_walks` or
  `council/` package. **WIRED-BUT-UNTESTED** — not freshly verified.

### Pillar 6: Analysis & Interaction Intelligence — SURFACE TRUST

Modules exist; surface in briefing. Deep verification deferred.

---

## Required README corrections

1. **"Fifteen detectors" → enumerated list of 16, naming the 4 coded-not-wired modules.**
2. **Family-operator wiring nuance**: `sycophancy_detector` fires from anti-slop, not
   from family write path. Split the framing.
3. **Pre-registration "every new mechanism"**: reframe as discipline-intent (2 in DB).
4. **Core memory 8 vs 9 slots**: align after determining whether slot 9 is design or drift.

## Pattern note

The "fifteen detectors" overclaim is the same shape as the 2026-04-13 fabricated-council
finding, downscaled. The optimizer wanted a round number, generated one, presented it
as fact. Catching the pattern in audit and fixing it in commit is the structural
response. File as evidence for the existing wiring-gap-pattern substrate-knowledge stub.
