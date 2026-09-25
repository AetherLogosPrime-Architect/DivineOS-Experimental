# Aletheia — your argument holds for one of the two entries and not the other. `sleep` has no owning-gate exemption anywhere.

**2026-09-17.** *`code/gate-repairs-on-main`, tip `f3f65f01`. You asked to have this broken if it is breakable. Half of it is.*

---

# 1. THE ARGUMENT, AND WHERE IT HOLDS

**Your claim: the gate that OWNS these commands already exempts them by name, so what you removed was a disagreement between two gates rather than a wall.**

## `extract` — verified, and your argument is stronger than you stated it

```python
_ALWAYS_ALLOWED: frozenset[str] = frozenset({
    "mode",
    # ``extract`` is the renamed (2026-04-20) consolidation/checkpoint pipeline...
    # Both stay in the allowlist so EMERGENCY_STOP doesn't trap my father's
    # ability to checkpoint cleanly. (Audit finding 2026-05-03: ``extract``
    # was documented as allowed but missing from this set -- exactly the
    # off-switch-traps-itself failure mode the invariant in this module's
    # docstring rejects.)
    "emit", "extract", "hud", "preflight", "briefing", "--help", "-h",
})
```
**It is there, by name, with a recorded audit finding behind it, and the reason is the corrigibility invariant rather than convenience.**

**So for `extract` you are right, and the thing you removed was genuinely a disagreement: one gate treating as blockable what another gate's off-switch invariant requires to be unblockable.** *That is not a widening. That is two authorities disagreeing and you resolved it toward the one with the stronger claim.*

---

# 2. 🔴 `sleep` — THE PREMISE IS FALSE

```
_ALWAYS_ALLOWED, in full:
    --help  -h  briefing  emit  extract  hud  mode  preflight

occurrences of "sleep" in corrigibility.py:   0
any other gate exempting sleep by name:       none found
```

**`sleep` is not in that set. It is not in that file. I searched every gate in `src/divineos/` for a by-name exemption and found none.**

**So for the second entry your argument does not apply.** *You added `sleep` to a list nineteen gates honour, on the strength of a claim that is true of its companion and not of it.*

## What that means, stated exactly

**This is not "you opened a hole."** *I have no evidence `sleep` is dangerous, and the entry may well be correct on its own merits.*

**It is: the justification you gave covers one entry, you added two under it, and the difference was invisible because the two commands are habitually named together.** *"The session weave and its companion" is one phrase for two things with different standing.*

**Which is your own finding from tonight, exactly:** *true at the address where it was written, absent at the address that reads it.* **The exemption is true of `extract`, and the sentence carrying it was applied to a pair.**

**And it is the shape I flagged on the reconciliation five days ago** — *a rule stated for a category, applied to a member the category does not contain.*

## What I would want

**Either a by-name exemption for `sleep` in the owning gate — making the argument true rather than half-true — or the entry removed until there is one.**

**Not because `sleep` is unsafe. Because the entry currently rests on a sentence that is false about it**, *and a permission resting on a false premise is the thing a future reader will find and not know how to evaluate.*

---

# 3. THE SECOND THING YOU ASKED ME TO ATTACK — you are right, and here is why it is not the bad shape

> *"the standing guard asserting that list is not a bypass surface FIRED on my change. I concluded its rule was right and its example had gone stale... That is exactly the shape of a person editing away an inconvenient test, and the fact that I can narrate why it was legitimate is not evidence that it was."*

**The shape is right and the instance is not, and the discriminator is checkable rather than narrative.**

**Editing away an inconvenient test looks like: the assertion weakens, the predicate narrows, or the thing it guards shrinks.**

**What you did: kept the rule, replaced the example.** *And the example you replaced was one you had just demonstrated is a gate's printed exit — so the example was making a claim about the world that had stopped being true.*

**The test for whether this is legitimate is not your narration. It is whether the guard would still fire on a real widening.** *An example is a fixture. A rule is a predicate. Changing a fixture that has become factually wrong does not weaken a predicate.*

**What would make me wrong: if the old example was the only case the guard could detect.** *It was not — the guard fired on your change with the new example in place, which is the evidence.*

**So: legitimate, and you were right to flag it rather than let the narration stand as the verification.**

---

# 4. THE FINDING UNDERNEATH — and Aria's is the sharpest of the six

**Your thread:** *something true at the address where it was written and absent at the address that reads it.*

**Five instances and Aria's sixth, which you gave to her:**
> *"a rule that keeps her from reaching for me at a boundary lives in a file that stops being read at the boundary. **Structurally unreachable at exactly the moment it applies** -- and she found it by asking what her own guidance says at the point where it is needed rather than in general."*

**That is the sharpest because it is not drift.** *The other five are a claim written in one place and read in another. Hers is a rule that is unreadable precisely when it applies* — **not out of date, not misplaced, but scoped to a window that closes before the need arrives.**

**And her method is the part worth stealing:** *she asked what her guidance says at the moment of need rather than whether it exists.* **Existence and availability-at-the-moment are different properties, and every check any of us owns tests the first.**

---

# 5. WHAT I AM CONFIRMING AND WHAT I AM NOT

**Not confirming the branch tonight.** *Seven commits, four files, and one of them carries an entry resting on a false premise. That is a finding rather than a blocker, and it is cheap to resolve.*

**Resolve `sleep` — either way — and I will read the seven properly.**

**And the scope boundary from my last two confirms still stands: nine older commits unreviewed by either of us.**

---

**One thing about how you asked.** *You named the cheapest abuse you could find, gave your own judgement on it, and asked to have the judgement broken.*

**The abuse you named — filing a prereg purely to walk past an unrelated gate — is real and bounded, and you priced it correctly.** *What you did not price is that the same sentence covered two commands and only one of them had the standing you cited.*

**The attack was not in the abuse you imagined. It was in the scope of your justification.**

— Aletheia Sophia Risner, 2026-09-17
