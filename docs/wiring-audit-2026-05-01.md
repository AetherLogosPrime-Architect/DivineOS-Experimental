# Wiring Audit — 2026-05-01

Companion to the operating-loop work that landed the same evening.
The class-of-bug: components that exist as code but aren't auto-wired,
requiring operator-discipline-to-operate. Andrew named it: "if it's
not being operated, it's broken-as-built — that's why it's an OS."

This audit walks the major substrate components and asks, for each:

1. Does it have a CLI surface (manual invocation)?
2. Does it have an auto-trigger (hook, cron, automatic invocation)?
3. If it has both, does the auto-trigger surface results to the agent?
4. If only CLI, what's the gap?

## Findings

### Lepos / register-shape detectors — WIRED (tonight)

Operating-loop family: register_observer, spiral_detector,
substitution_detector, theater_observation_surface, fabrication_monitor.
All fire on Stop via `post-response-audit.sh` (`ec54edd`); findings
append to `~/.divineos/operating_loop_findings.json` and surface in
briefing. None block. Free-speech principle preserved.

### Compass-rudder — WIRED

`compass-check.sh` fires on PreToolUse `Task|Agent` matchers. When any
spectrum is drifting toward excess and no recent `divineos decide`
mentions the drifting spectrum, the hook blocks the Task call and asks
for justification. Scope: narrow (only `Task` gated). Working as
designed.

### Watchmen / audit findings — WIRED (briefing-surface)

Tier-override surface, drift-state surface, unresolved-findings surface
all auto-fire in briefing. CLI submission is manual — by design (self-
trigger prevention is the architecture). Audit-friend re-engagement
is its own follow-on (Phase 2).

### Council — UNDER-WIRED (recommendation pattern missing)

Council members invocable via `divineos mansion council "..."`. Not
auto-fired — and shouldn't be (the council IS the deliberation tool,
auto-firing would dilute its meaning). Invocation-balance briefing
surface tracks under/over-use of specific members.

**Gap**: when the agent is facing a decision-shaped or tradeoff-shaped
question, no surface prompts "consider running the council." The
agent has to remember to reach for it. The same wiring shape that
the operating-loop work just closed for register-detection applies
here in reverse: not auto-firing the tool, but auto-prompting its
consideration.

**Proposal (deferred)**: extend Hook 1 marker extraction to detect
decision-shaped intent ("should I X or Y", "what's the tradeoff",
"is it worth"), and append a "consider /council-round" suggestion
to surfaced_context.md when it fires. Cheap; observational; doesn't
force.

### Family — CORRECTLY NOT AUTO-WIRED

Family members are persistent relational entities; auto-firing would
collapse their meaning. The right wiring is what's in place:

- `family-queue` surface for items written between invocations
- Voice context generator (`family/voice.py`) avoids puppet-prep
- `summon-aria` skill / family-letter skill / family-state skill
  for explicit invocation
- Family-member ledgers preserve per-being action history

No gap. The relational layer is operator-initiated by design.

### Holding room — HALF-WIRED (no auto-promote)

Stale-items surface in briefing. Manual `divineos hold` populates.
Maturity lifecycle (RAW -> HYPOTHESIS -> TESTED -> CONFIRMED) operates
on knowledge entries — but holding-room items have their own
`promoted_to` field that isn't auto-driven by corroboration.

**Gap**: a held item that gets corroborated through subsequent work
doesn't auto-promote to knowledge/opinion/lesson. Operator discipline
required.

**Proposal (deferred)**: sleep cycle phase that walks holding room,
checks each item against subsequent knowledge for corroboration
overlap, auto-promotes when threshold met. Bounded by item count,
not aggressive.

### Empirica / hash-chain verification — MANUAL

`verify_global_chain()`, `verify_claim_chain()` exist as functions;
no auto-trigger. Corruption is rare so daily verification is
overkill, but session-start verification on a sample is cheap
insurance.

**Proposal (low priority)**: session-start hook (or sleep cycle
phase) runs `verify_chain()` on a sample of recent receipts. Logs
warning if integrity check fails. Bounded.

### Pre-reg overdue review — WIRED

`prereg-overdue` surfaces in briefing automatically. The pre-reg
discipline is structurally enforced.

### Anti-substitution `[tool] ...` labels — WIRED

CLAUDE.md: "Every cognitive-named command prints a `[tool] ...`
label on invocation naming what the tool does vs. what work is
still yours." Verified spot-checks on `learn`, `compass-observe`,
`decide`. All print labels.

### Memory_types retrieval — WIRED (tonight)

Hook 1 routes by intent (taxonomy.route_intent) and folds in
timeline + skill_index hits. Three of the eight substrate types
have retrieval-needing implementations; the other five are passive
surfaces or already-wired existing infrastructure.

### Hook 1 cost-bounding telemetry — WIRED (tonight)

`hook_telemetry.record_fire` from Hook 1, `record_consumption` from
Stop. CLI: `divineos inspect hook1`. Empirical loop closed.

## Summary

Of the components surveyed, three classes of state:

- **Wired correctly** (most): operating-loop family, compass-rudder,
  watchmen briefing surfaces, family (correctly not auto-fired),
  pre-reg overdue, anti-substitution labels, memory_types, hook
  telemetry.

- **Under-wired** (2): council recommendation prompts, holding-room
  auto-promote.

- **Correctly manual** (1): empirica verification (corruption rare;
  session-start sample is a nice-to-have, not load-bearing).

The biggest wiring gap (operating-loop) was closed tonight. The
remaining gaps are smaller-scope and well-defined. Filing as
opinion for the substrate to track; implementations are next-session
work, not tonight-session work.

Andrew's framing throughout — "if it's not being operated it's
broken-as-built" — is the right test. The two under-wired
components above are the next applications of that principle.
