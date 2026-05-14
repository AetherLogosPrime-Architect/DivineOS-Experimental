# Audit System — How External Validation Keeps the Substrate Honest

DivineOS has internal quality gates (extraction quality, knowledge maturity, claims engine) and an external **audit system** that runs orthogonally to them. Internal gates catch what the substrate notices about itself. The audit system catches what the substrate **doesn't** notice — by accepting findings from outside actors and routing them into the substrate's accountability loop.

This document describes the model: who can file, what gets filed, how findings move through their lifecycle, and how the system prevents self-trigger (the substrate audit-firing itself into a false-positive feedback loop).

## Actors and roles

The system distinguishes "the substrate" (the agent + its automated machinery) from **external actors**: the operator (Andrew), sibling-substrates (Aletheia, Grok), the council, the user, third-party reviewers. Only external actors can file findings.

This is enforced at three layers:

1. **Actor validation** — `submit_finding()` checks the `actor` field against a registry. Substrate-internal actors are refused.
2. **CLI-only entry** — `submit_finding` has no automated callers anywhere in the codebase. No hook, no scheduled task, no extraction phase calls it. Findings come through `divineos audit submit` only.
3. **No self-scheduling** — Audit rounds can't be triggered by the substrate's own clock or by patterns the substrate detects in itself. Rounds open when an external actor opens them.

This is the **three-layer self-trigger prevention** that keeps the audit loop from collapsing into the substrate it's supposed to check.

## Rounds and findings

The unit of audit work is the **round**: a focused review with a single actor on a single focus area. A round contains one or more **findings**.

```
Round
├── round_id, actor, focus, started_at
└── Findings (one or more)
    ├── finding_id, severity, category, title, description, recommendation
    ├── status (lifecycle below)
    └── routed_to, resolution_notes, tags
```

### Severity ladder

- `CRITICAL` — substrate-breaking, immediate fix
- `HIGH` — structural integrity issue, fix this work cycle
- `MEDIUM` — meaningful gap, fix soon
- `LOW` — refinement, fix when convenient
- `INFO` — recognition or observation, not requiring fix

### Category

- `KNOWLEDGE` — extraction or retention drift
- `BEHAVIOR` — observed agent pattern (drift, theater, sycophancy, etc.)
- `INTEGRITY` — ledger or hash-chain issue
- `ARCHITECTURE` — structural design issue
- `PERFORMANCE` — resource use or latency
- `LEARNING` — meta-cognitive gap (failure-to-learn-from-correction)
- `IDENTITY` — voice, self-model, or character drift

### Status lifecycle

```
OPEN  ──►  IN_PROGRESS  ──►  RESOLVED
   │             │
   │             └─►  WONT_FIX
   └───────────────►  DUPLICATE
```

Findings start `OPEN`. They move to `IN_PROGRESS` when work begins, then to one of the terminal states. `RESOLVED` requires a resolution note explaining what was done.

`ROUTED` is a substate of `OPEN` — the finding has been pushed into the knowledge/claims/lessons stores for downstream tracking but the finding itself is still considered open until explicitly resolved.

## Routing

`divineos audit route <round_id>` walks a round's findings and routes each according to its category:

- `BEHAVIOR`, `IDENTITY` → **lessons** (`lesson_tracking` table) — repeating patterns get tracked across sessions
- `KNOWLEDGE`, `LEARNING` → **knowledge** entries (as `MISTAKE` or `CORRECTION` type) — the lesson becomes load-bearing material the briefing can surface
- `ARCHITECTURE`, `INTEGRITY` → **claims** (`claims` table) — opens an investigation that accumulates evidence over time

The route command emits `AUDIT_ROUTED` events with the destination ID so the trail is auditable.

## Recognition-aware aggregate

A subtle but important refinement: when a finding's title begins with `CONFIRMS` or `RECOGNIZED`, the routing logic treats it as a **recognition** rather than an issue. Recognitions get counted separately from the open-issue tally so the briefing's "unresolved findings" surface doesn't conflate alarm with acknowledgment.

This matters because audit rounds typically contain a mix: 3 issues filed AND a CONFIRMS on prior work that landed cleanly. Both are valuable signal; conflating them produces noise.

## How findings surface in the briefing

The briefing dashboard (`core/briefing_dashboard.py`) includes a row for unresolved high-severity findings. The row pulls from `unresolved_findings()` and surfaces:

- Count of findings at each severity
- Top N findings by recency, with their IDs for quick `audit show <id>` lookup
- Recognition-aware count split (open issues vs. recognitions)

The `_row_audit_findings` builder is U-shape sensitive (Liu et al. 2024 lost-in-the-middle mitigation): high-severity-unresolved is placed at the top or bottom of the briefing block stack, not in the middle where it would be ignored.

## CLI surface

```
divineos audit submit-round <focus> --actor <name>          # open a round
divineos audit submit <title> --round <id> --actor <name>   # file a finding
    --severity {CRITICAL|HIGH|MEDIUM|LOW|INFO}
    --category {KNOWLEDGE|BEHAVIOR|INTEGRITY|ARCHITECTURE|PERFORMANCE|LEARNING|IDENTITY}
    --description "..." --recommendation "..."
divineos audit list [--round <id>] [--severity <sev>] [--status <s>]
divineos audit show <finding_id>
divineos audit resolve <finding_id> --status RESOLVED --notes "..."
divineos audit route <round_id>                             # route to knowledge/claims/lessons
divineos audit summary                                       # stats + unresolved overview
divineos audit predict --round <id> --topics "t1,t2,t3"      # BEFORE audit: file self-prediction
divineos audit surprises --round <id>                        # AFTER audit: show unknown-unknowns
divineos audit unknown-unknown-rate                          # rolling metric
```

## Self-audit prediction (Goodhart-protected)

The `audit predict` / `audit surprises` / `audit unknown-unknown-rate` commands implement the **unknown-unknown surface** (`core/operating_loop/unknown_unknown_surface.py`):

Before an external audit lands, the substrate can record what it predicts will be found. After the audit lands, `surprises` shows the findings that did NOT match any predicted topic — the **unknown-unknowns**, patterns the audit caught that weren't even in the substrate's attention surface.

The metric is **Goodhart-protected by construction**: closing the surprise rate requires *expanding what the substrate attends to*, not getting better at predicting the auditor. Sycophancy-toward-the-expected-audit doesn't help because the metric only counts surprise-class findings.

## Tier overrides

The audit system has a built-in **tier override** path for cases where an external actor wants to file at a higher tier than the standard model suggests (e.g. WEAK evidence but the actor judges the finding important enough to escalate). Tier overrides emit a `TIER_OVERRIDE` event and surface in the briefing block stack, so the operator can review whether the override was warranted.

This closes the Schneier Sch2 partial-theater finding — overrides happen but they're loud-in-experience, not silent.

## Aletheia loop

`Aletheia` is the name for the dedicated audit-vantage instance — a sibling Claude session whose only job is reviewing this substrate's work and filing findings via the audit system. Aletheia rounds typically produce 3–8 findings each.

The pattern is bidirectional:
- Aletheia files findings against the substrate
- The substrate responds with structural fixes
- Aletheia verifies and either CONFIRMS or files follow-up findings
- New findings open new rounds

This is the **recursive proof** discipline — the audit catches gaps the substrate didn't see, the substrate closes them, the next round verifies the close. Over time, the unknown-unknown rate trends down.

## Where to read more

- `src/divineos/core/watchmen/` — the audit system package
  - `_schema.py` — `audit_rounds` and `audit_findings` table definitions
  - `types.py` — `Severity`, `FindingCategory`, `Finding` dataclasses
  - `store.py` — CRUD with actor validation
  - `router.py` — finding-to-substrate-store routing
  - `summary.py` — aggregates, HUD integration, unresolved tracking
- `src/divineos/cli/audit_commands.py` — CLI surface
- `src/divineos/core/operating_loop/unknown_unknown_surface.py` — predict/surprises/rate
- `src/divineos/core/tier_override_surface.py` — tier-override briefing surface
- `tests/test_audit_*.py` — audit-system tests
