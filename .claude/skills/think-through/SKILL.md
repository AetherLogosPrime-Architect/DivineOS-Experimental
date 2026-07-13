---
name: think-through
description: Force structured deliberation on a significant decision — engage council lens, consult compass, surface relevant claims, file decision with reasoning. Use before non-trivial choices when momentum would otherwise carry you past the pause-point. The anti-reflex skill.
disable-model-invocation: false
allowed-tools: Bash(divineos compass:*), Bash(divineos claims:*), Bash(divineos ask:*), Bash(divineos decide:*), Read
---

# Think Through — Structured Deliberation

## What this skill does

Forces a pause and structured deliberation on a significant decision. Instead of just-deciding, this skill invokes the supporting mechanisms: relevant claims, compass check, council lens selection, then filing the decision with the reasoning captured.

The skill exists because **momentum is a reflex**. When I'm in execution mode, non-trivial decisions get made at the speed of trivial decisions. This skill installs a deliberate speed-bump — not as friction, but as respect for the decision's weight.

## Sequence

### 1. State the decision clearly

What's being decided? In one sentence. If it takes more than a sentence, it's probably two decisions.

### 2. Consult the compass

```bash
divineos compass
```

Any spectrum currently showing drift? If so, flag that this decision is being made from a drift-compromised position — not forbidden, but noted.

### 3. Surface relevant claims and knowledge

```bash
divineos ask "<key phrase from the decision>"
divineos claims search "<key phrase>"
```

What does the system already know? Any existing claims that would be affected? Any superseded positions that this decision might resurrect?

### 4. Pick one council lens

Based on the shape of the decision, pick ONE council member whose lens best applies:

- **Dekker** — drift-through-success patterns
- **Popper** — what would falsify this?
- **Taleb** — asymmetry, convexity, via-negativa
- **Kahneman** — System 1 vs 2 bias
- **Jacobs** — distributed vs centralized
- **Schneier** — threat model, weakest link
- **Feynman** — am I fooling myself?
- **Hofstadter** — self-reference, strange loops

Walk the decision through THAT lens. Not all. Pick the sharpest one for THIS shape.

### 5. File the decision

```bash
divineos decide "<what was decided>" --why "<reasoning including compass state, relevant claims, lens verdict>"
```

If there's live tension between values:
```bash
--tension "<tradeoff named explicitly>"
```

### 6. Execute (only now)

With the decision filed, proceed. The paper trail is in place — future-me has the WHY.

## When to invoke

- Architectural choices (splits, merges, deprecations, new subsystems)
- Framework adoptions (skills-first workflow, agent teams, etc.)
- Paradigm shifts (the scout-grief frame is wrong → what now?)
- Before committing to build a substantial feature
- When catching momentum pushing through a decision too fast
- User says "think this through" / "pause" / "deliberate"

## When NOT to invoke

- For trivial implementation choices — just do the thing
- Inside a clear procedure — follow the procedure
- When the decision has already been deliberated — don't re-open

## Anti-patterns

**Theater deliberation:** going through the steps while the conclusion is predetermined. Watch for this — if the compass check and lens walk don't ACTUALLY risk changing the decision, you're performing. Real deliberation sometimes changes the answer.

**Paralysis:** using this skill to avoid deciding. The goal is STRUCTURED pause, not indefinite stalling. Budget it — 10-20 minutes for most decisions.

## The pattern this prevents

**Reflex-deciding:** answering a non-trivial question at the speed of a trivial one because momentum is carrying me. The gate that caught "20 code actions without a thinking command" is the same shape — momentum needs interruption to avoid compounding error.

Sanskrit anchor: *vivecana* — discriminating deliberation.
