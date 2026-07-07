# Council Manager — How the Right Experts Get Picked

The DivineOS council holds 42 expert frameworks — methodologies, reasoning patterns, and concern triggers distilled from thinkers like Aristotle, Feynman, Pearl, Schneier, Taleb, and Wittgenstein. Running every expert on every problem is expensive and unfocused. The **dynamic council manager** classifies the problem signal-by-signal and selects a council of 5–12 experts whose methodologies best fit.

This document explains what the manager does, why it works the way it does, and how it gets invoked.

## What it does in one sentence

`select_experts(problem)` reads the problem text, scores each of the 42 experts against ~47 problem categories using each expert's own metadata (tags, domain, concern triggers, characteristic questions), and returns the top 5–12 experts whose combined methodology covers the problem's signal mix.

## Why dynamic, not all-42

Identified during SWE-bench benchmarking as the #1 architectural improvement: running all 42 experts on every problem produces diffuse output, costs tokens proportional to council size, and dilutes signal. A focused council of 5–8 experts whose methodologies actually fit the problem produces tighter, more usable reasoning at a fraction of the cost.

The classification is **signal-based, not LLM-based** — no extra API calls. It uses the rich metadata already attached to each `ExpertWisdom` instance (see `src/divineos/core/council/framework.py`).

## Size bands

```
MIN_EXPERTS = 5    # always at least this many; problems with weak signal still get a council
SOFT_CAP    = 12   # default ceiling; most problems land here or below
HARD_CAP    = 15   # absolute maximum; even multi-dimensional problems can't exceed
```

The split between soft and hard caps lets a genuinely multi-axis problem pull a wider council without forcing every problem to hit the maximum. A focused single-axis problem gets ~5; a tangled multi-domain problem gets up to 12 by default, with the option to push to 15 when needed.

## The ~47 problem categories

Each category has a `name`, a list of signal words, and an affinity list of expert names. The categories are derived from SWE-bench failure-mode analysis plus additional cognitive/philosophical categories. A sample:

**Engineering failure-modes:**
`causal_chain`, `logic_error`, `type_error`, `api_misuse`, `state_management`, `format_spec`, `concurrency`, `security`, `performance`, `design_flaw`

**Cognitive / epistemic:**
`via_negativa` (what NOT to do — Taleb), `epistemics` (how do we know — Peirce/Popper), `cosmic_scale` (Hawking/Sagan), `evolution_replication` (Dawkins), `distributed_time` (Lamport)

**Plus:** identity/sovereignty, ethics-under-uncertainty, framing problems, structural-vs-superficial, falsification design, and others. See `manager.py` for the full registry.

## Scoring model

For each candidate expert, the manager computes a score combining:

1. **Tag overlap** — does the expert's `tags` set include any of the problem's category labels?
2. **Trigger match** — does the problem text contain any of the expert's `concern_triggers` or `when_to_apply` phrases?
3. **Domain affinity** — does the expert's `domain` match the inferred problem domain?
4. **Family deduplication** — experts in the same intellectual family (e.g. two ancient-Greek ethics frameworks) get partial penalty so the council doesn't stack on one vantage.

The top-scoring experts up to the soft cap form the council. Hard-cap acts as an absolute ceiling.

## Public API

The manager exposes two entry points in `src/divineos/core/council/manager.py`:

- `classify_problem(problem: str) -> list[tuple[ProblemCategory, float]]`
  Returns the problem's category mix with confidence scores. Useful for understanding *why* a council was selected.

- `select_experts(problem, experts, min_experts=5, max_experts=12, hard_cap=15) -> list[ExpertScore]`
  Returns the chosen experts with individual scores.

The higher-level `CouncilManager` class composes these with the council engine to produce a `ManagedCouncilResult`.

## How it's invoked

**CLI surfaces:**
- `divineos council walk "<problem>"` — runs a council walk on a topic; the manager picks the experts
- `divineos mansion council-chamber "<problem>"` — same, with mansion-room framing
- `divineos lab <command>` — research/experiment surface; uses the manager for evidence-pattern questions

**Programmatic:**
```python
from divineos.core.council.manager import select_experts, ALL_EXPERTS

scores = select_experts("Why does the queue deadlock under load?", ALL_EXPERTS)
# scores -> [(beer, 8.4), (lamport, 7.1), (dijkstra, 6.8), ...]
```

**Inside other systems:**
The manager is wired into the operating loop for lens-mode walks (where the agent borrows an expert's framework to look at a problem from that vantage) and into the family subsystem when a member needs council backing for an opinion.

## Design principle: structure, not control

The manager **recommends** experts; the caller can always override. It never prevents an expert from being consulted on a problem they weren't auto-selected for. The discipline is structural — selection is principled — but the architecture leaves the door open for the agent to reach for a specific expert when the moment calls for it.

## Where to read more

- `src/divineos/core/council/manager.py` — the selection logic, full category registry
- `src/divineos/core/council/engine.py` — how a selected council actually runs
- `src/divineos/core/council/framework.py` — the `ExpertWisdom` data model
- `src/divineos/core/council/experts/*.py` — the 42 expert profiles, one per file
- `tests/test_council_experts_all.py` — parametrized smoke + integrity tests across the roster
- `tests/test_council.py` — manager + engine integration tests
