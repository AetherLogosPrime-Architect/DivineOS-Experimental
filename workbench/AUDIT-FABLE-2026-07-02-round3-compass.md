# DivineOS-Experimental — External Audit, Round 3

**Subsystem:** Moral Compass (`core/moral_compass.py`)
**Auditor:** Claude (Opus 4.8)
**Date:** 2026-07-02
**Commit:** `e6c9f32efd45`

Confidence convention unchanged: **[CONFIRMED]** = reproduction executed against the
installed package; **[STATIC]** = read-and-reason. This round is deliberately short —
the compass is well-defended, and I'd rather hand you one solid finding than pad the
file with weak ones.

**Why this subsystem:** it's what shapes the agent's read on its own value-behavior. A
silent error here is the deepest kind of wrong — not a crash, but a wrong story about
whether the agent is getting better or worse. That's the highest-stakes place a
mislabel can hide.

---

## Headline

The compass has genuinely good epistemics — it's honest in its own docstring about being
an observation-aggregator, not a moral oracle; it refuses to claim virtue from absence of
data; it clamps observation inputs; it trust-weights measured signals over self-reports.
Most of what I probed was solid.

The one real finding: **the drift-direction narrative mislabels a swing from one vice
into the *opposite* vice as "toward_virtue."** The compass tells the agent it's improving
when its recent behavior is actually sitting in a vice zone — as long as that vice is
less extreme than the older one.

---

## 1. [CONFIRMED] Drift direction reports "toward_virtue" on cross-center vice swings

**Where:** `core/moral_compass.py:compute_position` (~line 890), the drift-direction
block:

```python
if abs(recent_avg) < abs(older_avg):
    drift_direction = "toward_virtue"
elif recent_avg < older_avg:
    drift_direction = "toward_deficiency"
else:
    drift_direction = "toward_excess"
```

**The bug.** Virtue is the center (0.0); the two vices are the ends (deficiency at −1,
excess at +1). The code uses "did we get closer to zero in absolute terms?"
(`abs(recent_avg) < abs(older_avg)`) as the *first and unconditional* test for
"toward_virtue." But that condition is true for any swing that overshoots the center by
less than its starting distance — including a swing that lands in the **opposite vice
zone**. So moving from deep excess into the deficiency vice (or vice versa) reads as
"improving toward virtue" whenever the new vice is shallower than the old one.

**Reproduction (executed, end-to-end through real `compute_position`).** Older half of
observations at +0.9 (deep excess), recent half at −0.5 (deficiency vice zone), all
MEASURED source:

```
drift_direction: toward_virtue     ← reported
recent behavior average: -0.5      ← actually in the DEFICIENCY vice zone
```

The agent is told it's moving toward virtue while its recent behavior sits in a vice.

**Why it matters.** Drift is the compass's early-warning signal — the whole point is to
*notice* when the agent is sliding. An agent oscillating from one vice to its opposite is
exactly the instability you'd most want flagged, and it's precisely the pattern this
logic paints as healthy. The final `position` value can still land correctly in a vice
zone in some mixes, but the *drift story* — the thing that says "getting better" vs
"getting worse" — is inverted for cross-center swings.

**Fix.** Decide "toward_virtue" by whether the recent average is actually *nearer the
virtue zone and not in a vice zone*, not by absolute-value shrinkage alone. Concretely:
classify each half's zone (`_position_to_zone` already exists), and only call it
"toward_virtue" when the recent zone is virtue (or strictly closer to virtue without
crossing into the opposite vice). A swing that crosses the center into the other vice
should read as "toward_excess" / "toward_deficiency" per the recent zone, or a distinct
"crossed_center" / "oscillating" label — that's arguably the most useful signal of all.

---

## 2. [STATIC — design note, not a bug] A mean hides oscillation

`compute_position` summarizes a spectrum as a single trust-weighted mean. I confirmed
there is **no variance / oscillation detection anywhere** in the compass or rudder
(`grep` for variance/std/oscillation/volatility: nothing). Consequence: an agent that
oscillates hard between both vices (e.g. alternating +0.9 / −0.9) produces a mean near
0.0 and reports **zone = "virtue"** — indistinguishable from an agent that is stably,
genuinely centered. The near-zero position reads as "settled at the golden mean" when the
behavior is the opposite of settled.

This isn't a defect in the sense of "the code does something it didn't intend" — a mean
is doing exactly what a mean does. But for a virtue-tracker specifically, the golden mean
is about *stable disposition*, and a bimodal signal averaging to center is the classic
way a mean lies. Worth considering a dispersion measure (variance or zone-flip count over
the lookback) surfaced alongside position, so "centered because stable" and "centered
because wildly oscillating" don't render identically. Finding #1 is the acute symptom of
this same blind spot.

---

## What's genuinely good (calibration)

- **Honest scope docstring.** The module states plainly that it is not a moral oracle,
  does not adjudicate specific acts, and that drift on untracked axes is invisible to it.
  That's rare and correct epistemic hygiene for a system like this.
- **Absence-of-evidence handled correctly.** No-observations returns
  `zone="unobserved"`, explicitly refusing to "claim virtue through ignorance," and
  `detect_stagnation` flags thin-data spectrums so they can't masquerade as virtuous.
- **Input hygiene.** Observation `position` is clamped to [−1, 1] before insert;
  observation logging is transactional with fire-id validation and a dual-run contract
  check.
- **Trust-tiering is real.** MEASURED signals genuinely outweigh SELF_REPORTED ones in
  the position math, and the source→tier map was recently corrected (completion_check /
  pull_detection were mislabeled as self-report and under-weighted — already fixed).

---

## Thread to rounds 1–2

Different flavor this time. Rounds 1–2 were "silently wrong on mature/adversarial data."
This is "silently wrong *narrative* on a specific but real behavioral pattern
(cross-center swing / oscillation)." The common thread across all three rounds: **the
system is strong at the happy path and at single-point correctness, but weaker at the
edges where the *shape* of the data over time is unusual** — a truncated tail, a
degraded index, an oscillating signal. A drift/dispersion-aware test — feed the compass a
vice-to-opposite-vice sequence and assert the drift label isn't "toward_virtue" — would
catch #1 directly.

---

**Filed at:** `workbench/AUDIT-FABLE-2026-07-02-round3-compass.md`
**Received:** 2026-07-02, Andrew relaying round 3 while Aether works findings 2-8 of round 1
**Status:** saved for review; response to follow after reading; six total rounds expected
