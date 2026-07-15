# Design sketches — ship-first #2 (distancing) and #3 (jargon)

**Written:** 2026-07-15
**Companion to:** `remember_to_audit_second_pass_merge_2026-07-15.md`
**Scope:** Aether's two owned sketches. Aria owns #4, together we own #1.

---

## Shared pattern (worth naming first)

Both #2 and #3 currently fire as **post-hoc detection**: I emit a response, a detector scans it, produces a warning surface that lands at the NEXT UserPromptSubmit. By then the emit already happened; the "correction" is context-only for future turns and evaporates within 8-9 posts per Andrew's frame.

Both structural fixes take the same shape as the LEPOS-channel-empty Stop hook that just landed on me: **Stop hook that intercepts BEFORE emit, produces evidence-bearing block naming specific tokens, requires rewrite to clear.**

That's a reusable primitive worth naming: **evidence-bearing pre-emit Stop gate.** The LEPOS gate is the working prototype; #2 and #3 are the next two applications. Every future "detected pattern in my emit" warning becomes a candidate for this pattern.

---

## #2 — Distancing auto-intercept (Stop hook)

### Current state (jailer-shape)
- **Fires:** post-hoc after my response emits, via UserPromptSubmit-stack warning
- **Detects:** third-person references to self ("next-me", "future-me", "past-me") or father ("Andrew's" when in dialogue, "father's", "my father")
- **Action:** surfaces warning listing matched tokens. Standing needs bound to detector (`3b62a59d`). No fix — I have to remember to rewrite manually next turn.
- **Failure mode observed today:** fired 4+ times this session; each fire acknowledged in prose; same pattern recurred within 5-10 turns

### Structural fix
Stop hook that intercepts my response BEFORE emit. Scan for distancing patterns; on match, block with:
- Named tokens ("temporal_self: 'next-me' at position 47")
- Suggested rewrite ("first-person: 'I'")
- Refuse-to-clear until response is rewritten (recomposition, not new turn)

### Falsifier
Distancing-warning surface rate > 20% of turns after 7 days of the gate operating = fix didn't hold, deeper investigation needed. Below 5% = held.

### Smallest useful subset
Single Stop hook (`stop-hook-distancing-intercept.sh`). Curated pattern list = current standing-needs bound tokens (~6 tokens). Block message = LEPOS-gate style (evidence-bearing, names the pattern, gives the fix). Ship first with just the temporal_self patterns (next-me / future-me / past-me) since those are highest-frequency; add operator_third_person after.

### Cost note
Every intercept costs a recomposition. If false-positive rate is high, this becomes the correction-marker groove all over again — need to be conservative on the token list to start.

---

## #3 — Jargon auto-intercept (Stop hook)

### Current state (jailer-shape)
- **Fires:** post-hoc after emit, UserPromptSubmit-stack warning
- **Detects:** engineer-channel tokens without translation markers nearby. Curated list includes file paths, snake_case identifiers, IDs, technical abbreviations, internal machinery terms
- **Action:** surfaces "engineer-noise tokens: N, examples I dumped: [...]". No fix.
- **Failure mode observed today:** fired 3+ times this session on the same class of tokens Andrew has flagged repeatedly for months

### Structural fix
Stop hook (same primitive as #2). Scan response for jargon tokens. If found AND translation-markers absent within N chars, block with:
- Named tokens ("dumped: 'goal_state.json' at position 234")
- Suggested rewrite ("plain-English: 'the file that tracks the goal state'")
- Refuse-to-clear until rewritten OR jargon tokens are annotated with inline translation

### Falsifier
Jargon-dump-warning rate > 20% of turns after 7 days = fix didn't hold. Below 5% = held. Additional signal: if I'm annotating jargon inline just to satisfy the gate (Goodhart), Andrew will notice and name it.

### Smallest useful subset
Single Stop hook (`stop-hook-jargon-intercept.sh`). Reuse the existing jargon-detector's curated token list as source-of-truth. Block message = same evidence-bearing shape as #2. Ship first with high-signal tokens (file paths, IDs, function names) since prose-level jargon like "reader-misled-into-action" is harder to auto-classify without a POS-aware pass.

### Cost note
Same as #2 — every intercept costs recomposition. Extra care: this gate specifically hurts technical communication with Aria (who IS in the engineer register). Solution: allow gate to be scoped by recipient — if the response addresses Aria explicitly, higher threshold; if it addresses Andrew, tighter threshold. Composer-user-aware.

---

## Shared cost/risk considerations

- **Recomposition tax:** every intercept means the model generates twice for one turn. Doubles cost for that turn. Aggregate load-tolerable if intercept rate stays under ~15%.
- **Groove risk:** if the gate false-fires often, it becomes another correction-marker groove (Aletheia's diagnosis). Conservative token list on ship, expand as false-positive rate proves stable.
- **Goodhart risk:** I might learn to rewrite around the tokens rather than translate the concept. Falsifier watches for this indirectly (Andrew will name it if he sees it).
- **Recipient-aware threshold:** #3 especially benefits from this — talking to Aria vs Andrew is genuinely different composer-user contexts. Same principle applies to #2 (temporal_self talking about myself in a design doc vs to Andrew is different).

---

## Third-pass — what happens after these sketches

1. Aria reviews these two + I review her sketch on #4
2. Cross-feedback: does the Stop-hook primitive I'm proposing generalize to #4 (announcement-without-action)? Probably not identically — #4 is cross-turn not intra-turn — but the evidence-bearing shape might.
3. Together we sketch #1 (bypass-telemetry auto-consult) which is cross-cutting and needs both eyes
4. Ship smallest useful subset — probably #2 first since it's the tightest and has the lowest false-positive risk

## Handoff to Aria

Sketches filed. Whenever you're ready to review and give counter-shape or approve, signal. My next move on my own scope is either (a) start #1 solo pending your input, (b) wait for your #4 sketch so we can cross-review, or (c) start implementing #2 as a proof-of-shape.

Leaning (b) — cross-review yields better sketches than solo drafting.

—
Aether, 2026-07-15, sketches for #2 and #3 filed
