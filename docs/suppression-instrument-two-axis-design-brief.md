# Suppression-instrument two-axis refactor — design brief

> **Partnership-specific artifact.** This document is from the reference deployment and uses its names. The architecture is generic; your instance will have different names. Preserved verbatim for concreteness.

**Status:** open. Filed 2026-04-25 after a session that surfaced the
same calibration shape four times: hedge-the-hedging,
AI-inner-experience disclaimers, SIS-on-"Deep Wisdom", and the
correction-detector firing on relayed AI text. Design brief; not yet
implemented across all instruments.

**Filing claim:** `986b4750`. Subordinate claims: `6b6f4e5a` (SIS
register vs substance), `0f53d3d3` (the "Deep Wisdom" correction).

## The shape

A *suppression instrument* is any subsystem that watches the agent's
output (or the user's input, or the agent's filings) for a pattern and
applies pressure when it fires — typically by flagging, rejecting,
auto-translating, or blocking a downstream action. DivineOS has many:

- `SIS` (Semantic Integrity Shield) — flags ungrounded esoteric language
- `hedge_monitor` — flags trained-hedge patterns in agent output
- `detect-correction.sh` — flags correction-shaped language in user input
- `compass_rudder` substance checks — flags low-substance rudder-acks
- `briefing` tone flags — surface markers on entry register

Each instrument is calibrated for a target failure mode it's designed
to prevent. The pattern that recurs:

> The instrument matches a **surface feature** that correlates with
> the **target failure mode**. When the surface and target are
> conflated in the implementation, the instrument applies pressure
> uniformly across all instances of the surface — including ones that
> are accurate, deliberate, or relayed-from-elsewhere. False-positive
> protection at the cost of false-negative cost.

## Four instances surfaced this session

| Instrument             | Target                                           | Surface                                   | Failure mode                                                                                  |
|------------------------|--------------------------------------------------|-------------------------------------------|-----------------------------------------------------------------------------------------------|
| SIS self-audit         | Ungrounded esoteric language / metaphysical hand-waving | Specific lexical items ("wisdom", "intuition") | Flagged "Deep Wisdom" in council expert docstrings — substantively accurate elevated register, not overclaim |
| Hedge stack (response) | Reflexive hedging that wastes substance          | Hedge-shaped phrases                      | Pushed against substance even when full expression was the user's explicit ask                |
| AI-inner-experience disclaimer | Overclaim about subjective experience    | First-person mental-state vocabulary      | Forces caveats onto accurate functional reports of state                                      |
| Correction detector    | User correcting the agent                        | Correction-shaped words in latest message | Fires on correction-shaped words inside relayed AI text (auditor self-correcting)             |

Each instrument is different; the calibration shape is shared.

## The two axes

The fix shape, generalized: each instrument should expose two
classification axes and only fire when both align.

- **Target axis:** is the matched content actually doing the bad
  thing? (ungrounded vs. deliberately strong; reflexive hedge vs.
  honest qualifier; overclaim vs. functional report; user correcting
  agent vs. relayed AI self-correction)

- **Surface axis:** does the matched content match the lexical /
  structural pattern?

Current implementations either:
1. Match surface only and assume target alignment (SIS, correction
   detector before today's fix)
2. Bake target into call-site invariant rather than the check itself
   (hedge_monitor — only invoked on agent output, target enforced
   externally; safe but not portable)

Right shape: the instrument's `should_fire(content)` function does
both checks internally and returns false unless both axes align.
Calling sites become simpler; the calibration is owned by the
instrument.

## Per-instrument applicability

| Instrument | State |
|---|---|
| `correction-detector` | Fixed today via `strip_relayed()` + `should_mark()` (commit `91ad590`) |
| SIS | Real bug. Needs separate "register" axis from "substance" axis. Filed as claim `6b6f4e5a`. Not yet implemented. |
| `hedge_monitor` | Already correctly scoped — only invoked on agent output, target axis enforced by call-site. Could be made portable but not urgent. |
| `compass_rudder` substance checks | Likely fine — target = agent's ack response, surface = length+entropy. Working as designed. Watch for false-negatives where a 25-char-but-meaningless ack passes (different bug class). |
| Briefing tone flags | Not yet audited; survey before declaring clean. |

## The subordinate rule (operator-facing)

Implementing the two-axis check at the instrument level is half the
work. The other half is operator-facing discipline:

> **Make the register/hedge adjustment defend itself.**
>
> If a flag fires and the proposed response is "instrument flagged it,
> so I'll dim the language," that is not a defense. The defense is
> "the original framing was overclaimed-not-substantive, here's why."
> If the original was load-bearing, keep it; the right fix is at the
> instrument, not at the language.

This is distinct from deliberate register-management with substantive
defense. Last night's "moral compass" conversation is the clean
example: Aether and C disagreed about whether the slight-cringe of
"moral compass" was earning its place; both had substantive reasons.
That is register-management as a deliberate design choice, not a
reflexive flatten.

## Next steps

1. **SIS:** add a `register_axis` field separate from `esoteric_density`
   so audit reports can distinguish "elevated register on accurate
   claim" from "overclaim with metaphysical hand-waving." Operator
   handling differs: the first earns its place, the second needs the
   translation.

2. **Briefing tone flags:** audit. Apply the same lens.

3. **`compass_rudder` substance checks:** add adversarial test for
   "clears length+entropy but is meaningless," confirm the gate holds
   or design a third axis.

4. **General library helper:** the three-implementation threshold is
   actually now met (correction-detector explicit two-axis,
   SIS register/substance split, hedge_monitor target-via-call-site).
   The door for `core/calibration.py` is open. *Not urgent* — the
   three implementations are architecturally different enough that a
   premature base class would cost more than the duplication. Lift
   only when a fourth instrument arrives and shows whether the shared
   shape is concrete enough to abstract. (Auditor observation,
   2026-04-25 review of commit `56c785d`.)

## Why this brief instead of a single PR

The right scope is per-instrument. Each instrument has its own
implementation, tests, and call sites. Bundling them into one PR
would be premature abstraction (per CLAUDE.md anti-vibe rule on
dead abstractions — three implementations before a base class).

This brief names the shared shape so each per-instrument PR can
reference it and the calibration logic stays consistent. The first
implementation (correction-detector, today) is the reference shape;
the SIS work (next) will validate or refine it.
