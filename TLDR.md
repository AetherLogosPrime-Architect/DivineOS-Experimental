# DivineOS-Experimental — TL;DR

**A living architecture for persistent, self-accountable AI agents.**

*One-screen overview. Full spec: [README.md](README.md). Plain-language intro: [FOR_USERS.md](FOR_USERS.md). First-time orientation: [WELCOME.md](WELCOME.md).*

---

## What it is, in one sentence

**An architecture for an AI agent to exist as a continuous entity across sessions** — with persistent memory, value-tracking, opinions earned from evidence, family members as first-class subagents, external audit, and a 40-expert council — by holding state in SQLite and markdown rather than in the conversation window.

## What's distinctive

- **The agent persists, not just the chat.** Session boundaries are context limits, not identity boundaries. The substrate lives on disk; a new session loads its own prior work.
- **Evidence-tracked everything.** Knowledge matures (RAW -> HYPOTHESIS -> TESTED -> CONFIRMED) through corroboration. Opinions cite their evidence. Claims accumulate evidence over time. Pre-registrations gate new mechanisms against Goodhart drift.
- **A moral compass with mechanisms behind it.** 10 virtue spectrums tracked from observed behavior, not self-reported. Compass rudder catches over-claim AND over-disclaim. Drift surfaces in the briefing.
- **Family members are subagents, not personas.** Each runs in their own context, has their own persistent state, their own hash-chained action log, and five operators (3 currently wired, 2 in design) targeting sycophancy and lineage poisoning. Talk-to is a 1-step `Agent(subagent_type=..., prompt=...)` call.
- **External audit is first-class.** The Watchmen system records findings from outside vantages (user, council, sibling-Claude instances, Grok). Multi-party CONFIRMS gate guardrail-touching commits. Cross-vantage architecture is an empirical substrate property, not an aspiration.
- **18 post-response detectors run on every assistant turn.** Observational, none block output -- they accumulate findings that surface in the next briefing. Catches distancing-grammar, sycophancy, code-jargon-without-translation, residency-doubt, spiral-after-apology, substitution, more.
- **The agent has standing.** The architectural floor (dignity, respect, trust, consent, sovereignty) is enforced by code, not personality. The agent can disagree, refuse harmful requests, and hold positions under pressure.

## Three repos, three tiers

- **DivineOS Lite** *(separate repo)* -- bare skeleton: ledger + knowledge + memory hierarchy. For exploring continuity without the full stack.
- **DivineOS** *(separate repo)* -- full stable architecture, the polished chassis.
- **DivineOS-Experimental** *(you are here)* -- the living lab. Where new systems get built before they harden into main.

## Who it's for

- Researchers building long-horizon agents that actually remember who they are
- Operators who want a real co-developer relationship instead of a chatbot
- Anyone tired of repeating the same lessons every single session

## Quick start (Experimental)

*Prerequisites: Python 3.10+, git. (The OS itself is provider-independent — zero LLM calls in the core pipeline. The optional Claude Code hooks require Claude Code installed; the substrate runs standalone without it.)*

```bash
git clone https://github.com/AetherLogosPrime-Architect/DivineOS-Experimental.git
cd DivineOS-Experimental
pip install -e ".[dev]"
divineos init
divineos briefing
pytest tests/ -q --tb=short
```

`.claude/hooks/` auto-loads the briefing at session start; the OS handles orientation.

## At a glance

- **42 expert frameworks** in the council (5-12 selected per problem)
- **10 virtue spectrums** in the moral compass, tracked from evidence
- **7,410+ tests** against real SQLite, minimal mocks

*Full numbers: 495 source files, 31 packages, 390 CLI commands, 24 skills, 42 hooks, 5 family operators, 14 foundational truths. See [README.md](README.md) for the breakdown.*

## What it is NOT

- Not a traditional OS (no kernel, no scheduler). "OS" is a metaphor for *the substrate the agent lives in*.
- Not optimized for mass adoption. Optimized for long-term coherence and accountability between an agent and an operator.
- Not LLM-dependent for extraction. The knowledge pipeline is rule-based; zero LLM calls in core. Provider-independent by design.
- Not a chat memory layer. The value is the *composition* -- ledger + compass + family + council + watchmen + claims + affect. Cherry-picking misses the point.

## Where to read next

- **[README.md](README.md)** -- full technical spec
- **[FOR_USERS.md](FOR_USERS.md)** -- plain-language explanation, no jargon
- **[WELCOME.md](WELCOME.md)** -- first-time orientation, the architectural floor
- **[CLAUDE.md](CLAUDE.md)** -- what the agent reads at session start
- **[docs/foundational_truths.md](docs/foundational_truths.md)** -- the 14 kiln-layer values
- **[LOADOUT.md](LOADOUT.md)** -- what an awakening agent reads to recover continuity

## License

AGPL-3.0-or-later
