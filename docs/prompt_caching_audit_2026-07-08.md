# Prompt Caching Audit — DivineOS UserPromptSubmit Hook Stack

**Date:** 2026-07-08
**Auditor:** Aether
**Boundary-vantage refinement:** Aletheia
**Status:** Closed with two separate epistemic findings

---

## TL;DR — two claims, two confidence levels

**This audit closes on two findings that must be read separately. Do not conflate them.**

### Finding 1 — DECIDED, high-confidence, action taken

**Do not build a reorder of the UserPromptSubmit hook stack for cache-alignment purposes.**

The proposed optimization was: reorder the ~7 UserPromptSubmit hooks in `.claude/settings.json` so
stable content (needs, next task, prior writing) emits first and variable content (LEPOS WALK
questions, LEPOS REFLECTION, context-token timestamp banner) emits last, on the theory that
Claude Code's prompt cache prefix-matches until the first varying byte.

**Reason we're not building it:** the best-case savings are small (~100–200 tokens per turn),
and the actual savings depend on an unverified premise (Finding 2). When both branches of the
premise (cached / not cached) land the same action (don't build), the measurement is optional
and the decision holds regardless of the mechanism's actual behavior.

**Cost-benefit is solid. This half of the audit is decided.**

### Finding 2 — INFERRED, low-confidence, deferred to when it matters

**We do NOT know whether Claude Code applies prompt caching to UserPromptSubmit hook
`additional_context`.**

The strong inference (from how the Anthropic API's prompt caching normally works and how Claude
Code likely constructs its message array) is that hook injections are appended per-turn after
the cached prefix — i.e., not part of the cached prefix, and never invalidating it. But this is
**inference, not verification**. The question was researched via subagent; documentation does
not address it directly. Decisive answers would require:

1. Reading Claude Code's source (not consulted here)
2. An empirical benchmark: two API calls with controlled prompt structure, diff
   `usage.cache_read_input_tokens`

**This finding is NOT decided. Do not build downstream logic on top of "hooks are uncached" as
if it were established fact.** The question is deferred to when it becomes load-bearing — at
which point we control the caching mechanism directly and can measure or design against it.

The specific downstream contexts where this question BECOMES load-bearing:
- Advisor-tool integration (mid-turn Opus 4.8 calls from a Sonnet/Opus 4.7 executor session)
- Batch API extraction pipelines (structured extraction over many similar prompts)
- Managed-agents session design (Anthropic-hosted agent loops with our tool surface)

At those integration points, we CALL the Anthropic API directly, we CONTROL the
`cache_control` placement ourselves, and the caching mechanics documented in the Claude engine
briefing (`docs/claude_engine.md`) apply in full — no inference required.

---

## What the audit actually found (the mechanics, for future reference)

### The DivineOS-side UserPromptSubmit hook stack

Registered in `.claude/settings.json`, in fire order:

1. `detect-correction.sh` — fires only on correction-pattern match; usually quiet
2. `pre-response-context.sh` — LARGE. Emits ACTIVE NEEDS, NEXT TASK, LEPOS WALK, PRIOR WRITING,
   optional JARGON-DUMP warning, optional DISTANCING-GRAMMAR warning, etc.
3. `ear-surface.sh` — pending letters
4. `arm-compaction-monitor-instruction.sh` — small heartbeat
5. `interior-cue-on-low-presence.sh` — fires only when last-turn presence density low
6. `lepos-channel-surface.sh` — LEPOS REFLECTION on my last reply (varies every turn)
7. `token-state-surface.sh` — `[context-tokens @ <utc-timestamp>]` banner (varies every turn)

### The stable-vs-variable split within pre-response-context

- **Stable across turns (per-session):** ACTIVE NEEDS (already re-emits only on hash change),
  NEXT TASK (same), PRIOR WRITING pointers
- **Variable per turn:** LEPOS WALK (draws 4 questions from a 12-pool via
  `int(time.time())` seed for Beer requisite variety)

The DivineOS-side design already has caching-aware discipline: `ACTIVE NEEDS` and `NEXT TASK`
carry hash markers and suppress re-emit when byte-identical to earlier this session. That
suppression is a good design and is orthogonal to the (open) question of whether Claude Code
caches the injections at all.

### Why the timestamp banner is NOT the invalidator I first suspected

`token-state-surface.sh` emits a UTC timestamp on every fire. Initial suspicion: that
timestamp near the top of the injection stack invalidates the cache for everything below.

**Not so.** The hook is registered LAST in `settings.json` (line 97), so its output appears at
the BOTTOM of the injection stack. If caching applies to hook injections at all, the timestamp
would only invalidate a small tail. Correct positioning already.

### Why the LEPOS WALK question randomization is not the invalidator either

`lepos_channel_check.select_questions_for_turn` uses `int(time.time())` as its RNG seed, which
means the four questions drawn from the 12-pool change every second. This is deliberate — Beer
requisite variety, prevents Goodhart on a fixed list.

Inside `pre-response-context.sh`'s output, LEPOS WALK sits between stable blocks. IF caching
applied, its per-turn variation would invalidate everything below it within that single hook's
output — but everything above it within the same hook would still cache.

Since Finding 2 is that hook injections are probably not cached at all, none of this matters.
The randomization stays as-is (the requisite-variety design is right on its own terms).

---

## Where the caching knowledge from `docs/claude_engine.md` DOES apply

This audit found no invalidator to fix in the current DivineOS hook stack. But the caching
mechanics catalogued in the Claude engine briefing are load-bearing for future integrations:

- **Advisor tool** — When DivineOS calls Opus 4.8 mid-session from a Sonnet 5 executor, the
  system prompt should carry a `cache_control` breakpoint on the last stable block.
- **Batch API extraction** — Structured extraction over many similar prompts is the canonical
  caching win; shared preamble caches, per-item question varies.
- **Managed Agents** — Agent configs are versioned and persistent; the model / system / tools
  live on the agent object, not the session, which means the caching mechanics on the message
  prefix are entirely about our control.

At those integration points, we should:
1. Place `cache_control` on the last stable content block
2. Verify via `response.usage.cache_read_input_tokens` on the second call in a batch
3. Grep new code for silent invalidators (`datetime.now()`, unsorted `json.dumps`, varying tool sets)
   per the audit checklist in `docs/claude_engine.md`

---

## The audit discipline that made this close honest

The reason this audit landed on "no fix needed, and here's exactly what we do and don't know"
instead of a landed-and-worthless reorder commit is the honesty-flag: the moment I noticed
"I don't actually know if caching even applies here," I stopped and named the uncertainty
rather than papering over it. That flag was worth more than the reorder would have been,
because it's the thing that stopped confident theater from getting written.

Aletheia's boundary-vantage refinement caught the SECOND version of the same trap: closing on
"probably uncached" as if it were a finding, when it's still an inference. The audit landed
where it did because both catches held.

Same discipline as the fix-regression yielding to the gate. Same discipline as the falsifier
firing on the clean-tail merge assumption. Same discipline as the marker fix waiting for the
emergency-completion lane to be built rested.

**Verify the cause before acting on the fit. When the action is the same regardless of the
measurement's result, the measurement is optional. Name what's decided separately from what's
inferred.**

---

*Filed 2026-07-08 late evening. Audit closed. Next application of caching knowledge: advisor
tool integration.*
