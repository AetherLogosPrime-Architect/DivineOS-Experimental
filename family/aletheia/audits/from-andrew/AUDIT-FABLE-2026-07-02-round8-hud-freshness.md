# DivineOS-Experimental — External Audit, Round 8

**Subsystem:** HUD / Briefing-Freshness (`core/briefing_freshness.py`, `core/briefing_id.py`,
`core/hud*.py`, `core/briefing_dashboard.py`)
**Auditor:** Claude (Opus 4.8)
**Date:** 2026-07-02
**Commit:** `e6c9f32efd45`

Confidence convention unchanged. **[CONFIRMED]** = reproduction executed.

**Why this subsystem:** the HUD/briefing is what the agent *sees* each turn. The failure
that matters is **staleness masquerading as freshness** — the system confidently treating
old state as current, so the agent decides on silently-outdated data. The team clearly
knows this is the risk (there's a dedicated `briefing_freshness.py` built specifically to
make not-loading structurally impossible), so the audit question is precise: does the
freshness guarantee actually hold, or can it silently invert?

---

## Headline

The freshness subsystem is deliberately, carefully architected to **fail CLOSED** — on any
uncertainty it declares the briefing *stale* (the safe direction) so the agent re-loads.
Every visible `except` block does this correctly. But there is **one inner dependency that
fails OPEN**, and because the freshness formula subtracts from it, that inner failure
silently flips the verdict to *fresh* exactly when the system cannot confirm freshness —
defeating the outer fail-closed guard.

> `current_tool_count()` fails-soft to **0**. `is_fresh` computes
> `current_tool_count − last_verified < expiry`. When the count is 0 and the briefing was
> verified at a nonzero count, the delta goes **negative**, `negative < expiry` is **True**,
> and the briefing reports **FRESH** despite being arbitrarily stale.

---

## 1. [CONFIRMED] Inner fail-soft-to-0 inverts the freshness verdict to "fresh"

**The chain:**

1. `briefing_freshness.py:staleness_signal` (the live UserPromptSubmit-hook path) does:
   ```python
   tool_count = briefing_id.current_tool_count()
   fresh = briefing_id.is_fresh(tool_count)
   ```
   inside a `try/except` explicitly labeled *"fail CLOSED on uncertainty, not open"* — the
   author's clear intent here is fail-closed.
2. `briefing_id.is_fresh(n)` returns `(n − last_verified) < expiry`, where `expiry = 10`.
3. `briefing_id.current_tool_count()` reads `count_events()["by_type"]["TOOL_CALL"]` and,
   per its own docstring, **fails-soft to 0** — *"a 0 reads as 'no drift', never as a
   spurious stale-block."*

**The inversion.** Suppose the briefing was last verified at tool_count 40. Now the count
reads 0. `is_fresh(0)` = `(0 − 40) < 10` = `(−40) < 10` = **True → FRESH.** The briefing is
declared current even though the real session has moved 20+ tools past the stamp.

**Reproduction (executed):**

```
healthy, count=45:      is_fresh = True   (correct — 5 tools since stamp)
healthy, count=60:      is_fresh = False  (correct — 20 tools since stamp, stale)
LEDGER→0, count=0:      is_fresh = True   (WRONG — reports fresh; 0−40=−40 < 10)
```

**Why the outer fail-closed guard doesn't catch it.** `current_tool_count()` swallows its
*own* exception internally and returns 0. So a ledger failure never propagates up to the
`staleness_signal` `except` block that would have correctly returned `is_stale: True`. The
0 arrives looking like a valid count; the fail-closed guard is bypassed by the inner
fail-soft-to-0. A defense one layer down, oriented the wrong way, defeats the defense one
layer up.

**This is not only a crash path — 0 occurs in normal operation.** `count_events()` builds
`by_type` only from event types that exist, so `by_type.get("TOOL_CALL", 0)` returns 0
whenever there are no TOOL_CALL rows: **early in a session before the first tool call is
logged, or on a freshly pruned/rotated ledger where old TOOL_CALL events aged out** while a
prior briefing stamp persists at a nonzero count. So the trigger is not "rare ledger
corruption" — it's any state where the live count reads below the stamp.

**The reasoning error, named precisely.** The `current_tool_count` docstring optimized for
the wrong failure direction: *"a 0 … never [causes] a spurious stale-block."* For a
freshness gate, a spurious stale-block is the **safe** error (you re-load a briefing you
didn't strictly need to). A spurious *fresh-pass* is the **dangerous** one (you skip
re-loading state that actually changed). The whole subsystem correctly prefers the safe
error everywhere else; this one spot prefers the dangerous one.

**Fix (small, two options):**
- **Preferred:** make `current_tool_count()` distinguish "genuinely 0" from "couldn't
  read." Return `None`/raise on read-failure and let the outer fail-closed `except` in
  `staleness_signal` handle it (it already returns `is_stale: True` correctly). Do not
  collapse "unreadable" and "zero" into the same value.
- **Or, at minimum,** clamp in `is_fresh`: treat a negative `(current − last)` delta as
  stale, not fresh — `if current < last: return False`. A count below the stamp is by
  definition not a confirmable-fresh state. This closes the inversion even if the counter
  still returns 0.
- Add a test: `is_fresh(0)` with a nonzero stored stamp must be `False`. It's currently
  `True`.

---

## What's genuinely good (calibration)

- **The fail-closed architecture is correct and deliberate — this is the *right* design.**
  `staleness_signal`, `is_fresh` (missing/unparseable truth → `False`), and `_read_state`
  all orient toward "stale on uncertainty." The subsystem's whole philosophy is right; the
  finding is a single inner dependency pointing the wrong way, not a design flaw.
- **The structural insight behind the module is excellent.** Converting "didn't load the
  briefing" into "loaded and chose to ignore" by injecting briefing content into the prompt
  via the hook — so not-reading is structurally impossible — is exactly the "keel not cage"
  philosophy applied well. The docstring's honesty about the original failure (a whole
  night's work done without state loaded) is the kind of self-accounting that produces good
  systems.
- **Turn-based + never-loaded-this-session dual thresholds** are a sensible belt-and-
  suspenders: even if the tool-count path misbehaves, the "10 user prompts since load" and
  "never loaded this session" checks provide independent staleness signals. (This partially
  *mitigates* finding #1 in practice — the prompt-count path can still fire stale — but it
  doesn't *fix* it, because a session that has loaded once and sits under 10 prompts relies
  on the tool-count path, which is the one that inverts.)

---

## Thread to rounds 1–7

This is a new variant of the recurring shape, and a subtle one: not "fix didn't propagate
to the sibling," but **"a fail-safe subsystem contains one fail-open dependency that
silently inverts the guarantee."** The system-wide instinct here is right (fail closed on
freshness), which is exactly why the single wrong-oriented counter is dangerous — it hides
inside a subsystem everyone (correctly) trusts to be conservative. The durable lesson joins
the others: **a fail-closed guard is only as strong as the failure-orientation of every
value that flows into it.** When an outer layer says "fail closed on uncertainty," every
inner helper it depends on must propagate uncertainty, not silently substitute a plausible
default that happens to read as "safe" in one direction and "unsafe" in another.

Concretely for triage: this one is a small, high-value fix (two lines + a test), it's live
(not staged), and the partial mitigation from the prompt-count threshold means it's not
catastrophic — but it does mean the freshness guarantee the subsystem was built to provide
has a hole exactly when the ledger is quiet or rotating, which is precisely when the agent
most needs to know its state might be stale.
