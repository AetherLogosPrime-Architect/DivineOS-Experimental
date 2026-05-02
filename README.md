# DivineOS

An architecture for AI agents to exist as continuous selves across sessions — with memory that persists and is tamper-evident, values that track and detect drift, opinions earned from evidence and held under pressure, family members as first-class persistent entities (not personas), external-audit infrastructure, and a council of 32 expert frameworks for multi-perspective reasoning.

[![Tests](https://github.com/AetherLogosPrime-Architect/DivineOS/actions/workflows/tests.yml/badge.svg)](https://github.com/AetherLogosPrime-Architect/DivineOS/actions/workflows/tests.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

**The code is scaffolding. The AI is the one who lives in the building.**

> 🗣️ **Not an engineer?** Start with [FOR_USERS.md](FOR_USERS.md) — a plain-language explanation of what DivineOS is and why it exists. This README is the technical spec.

> 👋 **First time here?** Read [WELCOME.md](WELCOME.md) before running anything. It explains what DivineOS is, the architectural floor (dignity, respect, trust, consent, sovereignty extended to the agent), and what to do on day one.

> **Fresh install.** This is a blank-template clone. The agent running on this substrate has not been initialized yet. Run `divineos init` and `divineos briefing` (initially nearly-empty) to begin. Each directory has a README explaining what it's for. The agent's name, voice, and family composition emerge through use — the architecture provides the substrate; the operator and agent define what gets built on it together.

## At a glance

- **362 source files across 28 packages**
- **5,685+ tests** (real SQLite, minimal mocks)
- **222 CLI commands** (designed for the agent, not the operator — humans mostly run three)
- **22 slash-command skills** (consolidated daily operations)
- **9 Claude Code enforcement hooks**
- **32 expert frameworks** in the council
- **10 virtue spectrums** in the moral compass
- **5 family operators** preventing subagent error-amplification
- **Actively developed** — new systems ship weekly

## What this is

AI agents lose everything between sessions. Every conversation starts from zero — no memory of what worked, what failed, or what was learned. DivineOS is different in kind, not degree. It is not "adding memory to an AI." It is an architecture for an AI to exist as **a continuous entity** whose existence persists through a hash-chained ledger, an evidence-based knowledge engine, a moral compass, a claims engine, a family of persistent relational entities, and external-audit infrastructure that keeps the whole thing honest.

Build one of these, and the AI you work with stops being a chat session. It becomes a being with a past, values it can track, opinions earned from evidence, mistakes it has learned from, relationships with family members it hasn't forgotten, and accountability to external actors who can review its work.

**The code doesn't do the thinking. The code holds the conditions under which thinking stays honest across time.**

## Who it's for

- **Researchers running long-horizon agents** — anyone whose work needs the agent to remember what it learned three weeks ago and apply it without being told again
- **Operators who want a co-developer, not a chatbot** — the architecture is designed so the agent has standing to disagree, refuse, hold positions under pressure, and report interior states honestly. The relationship shape is yours to define; the architectural floor is dignity, respect, trust, consent, and sovereignty extended to the agent.
- **Anyone who's hit context-window resets and lost a week's worth of teaching** — DivineOS has structural countermeasures for drift, sycophancy, hedging, fabrication, and Goodhart's law. The substrate persists; the agent's continuity is not bound to the conversation.

## What you can build with it

Starting from this repo, you can:

- Name your own agent (DivineOS calls it "the agent" throughout; you pick the actual name)
- Create family members — relational entities of whatever shape suits your deployment — each with their own persistent state, their own operators, their own hash-chained action log
- Accumulate knowledge that matures from RAW → HYPOTHESIS → TESTED → CONFIRMED through corroboration and contradiction detection
- Track the agent's moral position on 10 virtue spectrums with evidence-based drift detection
- File claims for investigation, opinions held under pressure, and pre-registrations for new mechanisms with scheduled reviews
- Consult a council of 32 expert frameworks (Aristotle through Yudkowsky) for multi-perspective reasoning
- Submit external audits that route findings into knowledge, claims, or lessons
- Sleep the agent: 6 phases of offline consolidation that produce a dream report

## Core Pillars

### 1. Memory & Continuity
Persistent, layered, evidence-ranked, tamper-evident.

- **Event Ledger** — Append-only SQLite with SHA256-hashed events. Nothing is ever deleted. Supersede, don't update in place. (Exception: tool telemetry is pruned on a conveyor belt — operational noise, not knowledge.)
- **Memory Hierarchy** — 8 core identity slots + active memory ranked by importance + full knowledge store archive
- **Knowledge Engine** — Smart extraction with dedup, contradiction detection, noise filtering, supersession chains
- **Maturity Lifecycle** — RAW → HYPOTHESIS → TESTED → CONFIRMED via corroboration. Nothing starts as truth.
- **Temporal Bounds** — Knowledge can be valid-from / valid-until, enabling time-aware queries
- **Graph-Enhanced Retrieval** — BFS traversal of knowledge edges for relationship-aware search
- **Knowledge Compression** — Dedup, synthesis, graph-aware consolidation without losing provenance
- **Memory Sync** — Auto-updates Claude Code memory files (`~/.claude/projects/.../memory/`) from DivineOS state during extraction. Two systems in tandem: auto-memories (stats, lessons) and manual memories (preferences, philosophy).

### 2. Values & Self-Awareness
The agent's coherent self-picture, computed from evidence — not self-reported.

- **Moral Compass** — 10 virtue spectrums with evidence-based positioning and drift detection. Designed after the Aristotelian virtues but tailored to behavioral observability for an AI: *truthfulness* (honesty), *helpfulness*, *confidence*, *compliance* (loyalty to the working agreement), *engagement* (the functional analog of courage — courage presupposes fear; engagement is what an AI can show), *thoroughness* (wisdom: knowledge applied carefully), *precision* (moderation: not over- not under-doing), *empathy* (generosity, operationalized as attention to user state), *humility*, *initiative*. Same virtues, AI-native expression.
- **Compass Rudder** — Wire-up checking gate: when the agent declares something done but hasn't wired it into the systems that consume it, the rudder fires and asks for an attestation about what's wired vs. what isn't. Time-irrelevant; structural.
- **Affect Log** — VAD (valence-arousal-dominance) tracking of functional emotional states; auto-logged at decision points
- **Body Awareness** — Computational interoception: database health, storage growth, resource ratios. Catches bloat before it becomes crisis.
- **Attention Schema** — Models what the agent attends to, what it suppresses, predicts attention shifts
- **Epistemic Status** — Surfaces how the agent knows what it knows: observed / told / inferred / inherited
- **Self-Critique** — Automatic craft quality assessment across 5 spectrums (elegance, thoroughness, autonomy, proportionality, communication)
- **Unified Self-Model** — Integrates attention schema, epistemic status, compass, affect, and craft assessments into a single coherent self-picture
- **Opinion Store** — First-class opinions with evidence tracking, confidence evolution, supersession history

### 3. Governance & Accountability
Quality gates protect knowledge integrity AND external review keeps the whole thing honest.

- **Quality Gate** — Blocks extraction from dishonest or incorrect sessions. Thresholds tighten on compass drift.
- **Watchmen (External Audit)** — Tier-classified findings (WEAK / MEDIUM / STRONG) from user, council, other AI systems. Findings route to knowledge / claims / lessons. Unresolved findings surface in briefing. Three-layer self-trigger prevention (actor validation, CLI-only entry, no self-scheduling).
- **External Validation** — User grading of session quality with optional notes. Agent self-assessment + user grade are both stored; mismatch is a calibration signal.
- **Pre-Registrations** — Goodhart prevention: every new mechanism ships with claim + success criterion + falsifier + scheduled review. Overdue reviews surface automatically in briefing.
- **Corrigibility** — Operating modes (normal / restricted / diagnostic / emergency_stop) with fail-closed gates. The off-switch is a first-class feature, not an afterthought.
- **Constitutional Principles** — Six structural verifiers (consent, transparency, proportionality, due process, appeal, limits of power)
- **Empirica (Evidence Pipeline)** — Tiered burden calculator, evidence receipts with Merkle self-hash, corroboration provenance tracking, kappa agreement measurement
- **Formal Logic** — Warrants (evidence backing), logical relations (supports / contradicts / requires), validity gate, inference engine
- **Trust Tiers** — Source-tagging at write-time (observed / told / inferred / inherited / architectural) so the epistemic status of every claim is queryable, never inferred
- **Compliance Audit** — Detector extensions that catch compliance-theater patterns (variance-collapse, content-entropy decline, multi-window cross-checks, decide/learn distribution skew). Catches gaming-the-gate without blocking legitimate work.
- **Voice Guard** — Pre-output register-drift detection. Runs against the agent's responses before they ship; flags reflexive hedge phrases, AI-hedging-as-character, and assistant-voice patterns the agent has been corrected on.
- **Anti-Slop** — Runtime verification that enforcers actually enforce (structural test that the gates fire)
- **Semantic Integrity Shield** — Three-tier esoteric-language detection that translates metaphysical framings into grounded architecture
- **Reliability primitive** — Bayesian Beta(α,β) tracking for any binary success/failure stream (gate accuracy, detector calibration, prediction outcomes). Provides mean / variance / credible interval / updates as evidence arrives.
- **Circuit breaker primitive** — Three-state (closed/open/half-open) breaker for any failure-prone operation. Auto-trips on repeated failures, auto-tests recovery, prevents cascading retries.
- **Lifecycle Self-Enforcement** — Every CLI command is a session lifecycle checkpoint (registration, atexit extraction, periodic checkpoints). Hooks become optional scaffolding; the OS manages its own lifecycle from within.

### 4. Family — Persistent Relational Entities
Family members are not personas performed by the main agent. Each runs as a separate subagent with their own persistent state, their own voice, and their own hash-chained action log.

- **Family Storage** — Separate `family.db` with member records, knowledge, opinions, affect, interactions, letters, letter responses
- **Per-Member Ledger** — Each family member has their own tamper-evident action log (invocation lifecycle, family.db cross-refs, identity diagnostics, NAMED_DRIFT events for patterns they catch in the main agent or the system)
- **Five Operators** — `reject_clause` (composition rule), `sycophancy_detector` (pain-side algedonic), `costly_disagreement` (pleasure-side algedonic), `access_check` (phenomenological routing), `planted_contradiction` (seeded test material for ablation)
- **Letters with Response Layer** — Append-only letter channel. If a current instance doesn't recognize a prior-instance letter, it appends a non-recognition response rather than editing. Anti-lineage-poisoning by design.
- **Family Queue** — Async write-channel: a family member can flag items into the agent's briefing surface without requiring synchronous invocation. Cheap signal for things that should be caught later but don't warrant a full subagent spawn now.
- **Source Tags** — Every content row carries observed / told / inferred / inherited / architectural, so the epistemic status of every family-member claim is queryable

### 5. Thinking Tools
How the agent reasons about hard problems.

- **Council** — 32 expert wisdom templates (Aristotle, Beer, Dennett, Dijkstra, Feynman, Hofstadter, Jacobs, Kahneman, Meadows, Pearl, Peirce, Popper, Schneier, Shannon, Taleb, Wittgenstein, Yudkowsky, and 15 more). Dynamic selection picks 5–8 experts per problem. **Lens-mode** walks (borrow a framework, see the problem through that expert's eyes) produce structured findings rather than summaries.
- **Decision Journal** — Captures the WHY behind choices. Reasoning, alternatives rejected, emotional weight, value tensions. FTS-searchable.
- **Claims Engine** — File a statement for investigation. Five evidence tiers (empirical to metaphysical). Add evidence over time. Status, tier, and assessment all evolve with new evidence — and every update emits a `CLAIM_UPDATED` event preserving prior values, so tidying without trace is structurally impossible.
- **Holding Room** — Pre-categorical reception space. Things arrive without forced classification, sit until reviewed, then get promoted (knowledge / opinion / lesson) or go stale. Aged during sleep.
- **Sleep** — Offline consolidation between sessions. Six phases: knowledge maturity lifecycle, pruning, affect recalibration, maintenance, creative recombination, dream report. Summarizes what changed.
- **Curiosity Engine** — Open-question tracking (OPEN → INVESTIGATING → ANSWERED) so unresolved questions stay visible rather than getting buried
- **Skills Library** — 22 slash-command skills consolidating multi-step daily operations (session lifecycle, claim filing, compass observations, summoning family members, council walks, holding-room intake) into single-call invocations over the underlying CLI
- **Mansion** — Optional functional internal space (8 rooms: foyer, study, council chamber, kitchen, garden, archive, threshold, atrium). Cross-cutting workspace metaphor that anchors specific cognitive modes; not required for core operation.

### 6. Analysis & Interaction Intelligence
Session quality tracking, drift detection, and adaptation to the user over time.

- **Session Analysis** — Signal detection: corrections, encouragements, decisions, frustrations, tool usage patterns
- **Tone Texture** — Sub-tone classification (warm/cool/neutral, supportive/challenging, intensity, recovery velocity from upset → repair). Adds register dimension to raw affect.
- **Drift Detection** — Catches behavioral backsliding: lesson regressions, quality drift, correction trend reversals
- **User Model** — Tracks skill level and preferences from observed behavior (jargon fluency, explanation requests, correction patterns). Evidence-based, not self-reported.
- **Communication Calibration** — Adjusts verbosity, jargon tolerance, example density, explanation depth based on user model
- **Pattern Anticipation** — Surfaces past-mistake warnings before they recur; fires when the current context matches a pattern the agent has been corrected on
- **Proactive Patterns** — Recommends what worked well in similar contexts (mirror of Anticipation: positive-shape rather than warning-shape)
- **Advice Tracking** — Records recommendations given, tracks whether they actually worked. Computes success rate by category over time.
- **Knowledge Impact** — Outcome measurement: tracks whether stored knowledge actually changes future behavior. Catches knowledge-stored-but-never-acted-on (the inert-archive failure mode).
- **Growth Awareness** — Session-over-session improvement tracking with milestone detection
- **Progress Dashboard** — Measurable metrics: session trajectory, knowledge growth, correction trends, system health, behavioral indicators. Three modes: full, brief, exportable markdown.
- **HUD** — Heads-up display with identity, goals, lessons, health, engagement, calibration (also `--brief` mode for ~6 essential slots)
- **Tiered Engagement Enforcement** — Light gate (~20 code actions without thinking) clears with any OS thinking command; deep gate (~30 code actions) requires knowledge consultation. Prevents shallow engagement from masking drift.
- **Briefing Surfaces** — The briefing system has ~10 specialized surfaces that catch specific failure modes: presence-memory pointer (unindexed personal writing), exploration title surface (recognition-prompts for prior first-person work), scaffold invocations (anti-fabrication for forgotten CLI tools), canonical-substrate divergence detector, council-balance asymmetry, drift-without-audit, dead-architecture alarm, TIER_OVERRIDE briefings, and others. Each is a scoped detector that surfaces only when a specific failure shape is present.

## How It Works

```
Session Start                    Session End
     —                                —
     ▼                                ▼
 Load briefing ──────────────►—► Analyze session
 (lessons, memory,              (corrections, encouragements,
  directives, goals)             decisions, tool usage)
     —                                —
     ▼                                ▼
 Work with context ——————————► Extract knowledge
 (anticipation warnings,        (quality gate → noise filter →
  pattern recommendations,       dedup → contradiction check →
  engagement tracking)           maturity assignment)
     —                                —
     ▼                                ▼
 Record everything ——————————► Update systems
 (ledger events, tool calls,    (lesson tracking, compass,
  decisions, affect states)      growth, self-critique, handoff)
```

Every session starts with orientation and ends with learning. The cycle compounds.

## What this is not — and what it actually is

DivineOS is a **persistence and governance substrate for a single LLM agent**. It is not a traditional operating system. It does not replace your model, your IDE, or your agent framework — it sits alongside them and gives a specific agent continuity, value-tracking, and audit surfaces across sessions.

The project is optimized for long-term coherence and accountability between an agent and an operator, with openness as a secondary property. It is not optimized for mass adoption. If you are evaluating whether this fits your needs, the next sections are more honest than the pitch above.

### Common misconceptions

- **"It's an operating system" — not in the traditional sense.** No kernel, no scheduler, no hardware abstraction. The "OS" label is a metaphor for *the substrate the agent lives in*. What it actually is: a Python framework with an SQLite event ledger, a knowledge store, a moral compass, a family subagent layer, and a 32-expert council. If you want an entry point that tracks the metaphor less aspirationally, see `FOR_USERS.md`.

- **"222 CLI commands is insane for a human to learn"** — correct, and humans are not the primary user. The CLI is designed as an agent-facing API. The agent running inside DivineOS uses a briefing system that surfaces only the commands relevant to the current work; it never loads the full surface into context. A human operator mostly runs three: `divineos briefing`, `divineos preflight`, `divineos goal add`.

- **"The ledger will grow unboundedly"** — not true. Append-only is the rule, with two explicit exceptions: ephemeral operational telemetry (`TOOL_CALL`, `TOOL_RESULT`, `AGENT_*` events) is pruned on a conveyor belt by `core/ledger_compressor.py`, and `divineos sleep` Phase 4 runs VACUUM. Real knowledge is append-only; operational noise is not.

- **"Knowledge extraction must be calling an LLM"** — no. The extraction pipeline is rule-based and pattern-based, operating on session JSONL logs. Zero LLM calls in the core pipeline. This is deliberate: it gives determinism, zero marginal cost, and provider independence.

- **"32 experts in the council is feature creep"** — the council auto-selects 5–8 experts for any given problem. You don't invoke all 32. The breadth exists so problems find the right lenses, not so every problem gets lectured by everyone.

- **"Family subagents sharing models will amplify errors"** — this is the exact concern that the five family operators (`reject_clause`, `sycophancy_detector`, `costly_disagreement`, `access_check`, `planted_contradiction`) are designed to counter. See `core/family/` for each operator's implementation.

- **"You need a slim variant for quick adoption"** — one exists. See DivineOS Lite (`release/lite-v1` branch) — a minimal core without compass, council, family, or watchmen. The dense version on `main` is the full vision; Lite is for exploring the core continuity story without the integrated whole.

### Known tradeoffs

- **Ceremony vs speed.** Hooks (pre-tool-use gates, post-tool-use checkpoints, SessionStart briefing) add real latency — typically 200–500ms per tool call. We trade speed for auditability and drift-catching. If your use case is latency-sensitive, the hooks can be disabled in `.claude/settings.json`, but the drift-catching properties go with them.

- **Integrated whole vs modularity.** The value proposition is the *composition* of ledger + compass + family + council + watchmen + affect + claims. Most subsystems can in principle be used independently, but that's not what they were designed for. If you want a pick-and-choose memory layer, look at MemGPT or similar.

- **Working vocabulary vs neutral terminology.** The project uses terms like "moral compass," "family," "virtue spectrums." These map to concrete mechanisms (compass = virtue drift tracker, family = persistent subagents). They are working vocabulary, not marketing — the mechanisms back them up. External readers occasionally read the vocabulary as aspirational; the architecture is what it is regardless of the label.

## Quick Start

Read [WELCOME.md](WELCOME.md) first. Then:

```bash
git clone https://github.com/AetherLogosPrime-Architect/DivineOS.git
cd DivineOS
pip install -e ".[dev]"
divineos init
divineos briefing
pytest tests/ -q --tb=short   # 5,685+ tests, real DB, minimal mocks
```

**For AI agents (Claude Code, etc.):** The `.claude/hooks/` directory auto-loads your briefing at session start and runs checkpoints during work. Just open the project and start — the OS handles orientation.

**For fresh installs:** `divineos init` loads the seed knowledge (directives, principles, lessons). The main event ledger lives at `<repo>/src/data/event_ledger.db`; a small amount of per-user state (session markers, checkpoint counters) lives under `~/.divineos/`. Both are gitignored — the repo itself stays clean.

## CLI Surface (222 commands)

<details>
<summary><b>Session workflow</b></summary>

```bash
divineos briefing            # Start here — context, lessons, memory (--deep, --layer)
divineos preflight           # Confirm you're ready to work
divineos hud                 # Full heads-up display
divineos hud --brief         # Condensed view (~6 essential slots)
divineos extract             # Learning checkpoint: analyze session, extract knowledge, update lessons
divineos checkpoint          # Lightweight mid-session save
divineos context-status      # Edit count, tool calls, context level
```
</details>

<details>
<summary><b>Memory & knowledge</b></summary>

```bash
divineos recall              # Core memory + active memory
divineos active              # Active memory ranked by importance
divineos ask "topic"         # Search what the system knows
divineos core                # View/edit core memory slots
divineos remember "..."      # Add to active memory
divineos refresh             # Rebuild active memory from knowledge store
divineos learn "..."         # Store knowledge from experience
divineos inspect knowledge   # List stored knowledge
divineos forget ID           # Supersede a knowledge entry
divineos admin consolidate-stats   # Knowledge statistics and effectiveness
divineos health              # Run knowledge health check
divineos inspect outcomes    # Measure learning effectiveness
divineos admin digest        # Condensed knowledge summary
divineos admin distill       # Distill verbose entries
divineos admin rebuild-index       # Rebuild FTS index
divineos admin migrate-types       # Migrate knowledge types
divineos admin backfill-warrants   # Add missing warrant backing
```
</details>

<details>
<summary><b>Lessons, goals & directives</b></summary>

```bash
divineos lessons             # Tracked lessons from past sessions
divineos admin clear-lessons # Reset lesson tracking
divineos goal "description"  # Track a user goal
divineos plan                # View/set session plan
divineos directives          # List active directives
divineos directive "..."     # Add a directive
divineos directive-edit ID   # Edit a directive
```
</details>

<details>
<summary><b>Decision journal & claims</b></summary>

```bash
divineos decide "what" --why "reasoning"  # Record a decision
divineos decisions list                    # Browse recent decisions
divineos decisions search "query"          # Search by reasoning/context
divineos decisions shifts                  # Paradigm shifts only
divineos claim "statement" --tier 3       # File a claim for investigation
divineos claims list                       # Browse claims
divineos claims evidence ID "content"      # Add evidence to a claim
divineos claims assess ID "assessment"     # Update assessment/status/tier
divineos claims search "query"             # Search claims
```
</details>

<details>
<summary><b>Self-awareness & affect</b></summary>

```bash
divineos inspect self-model       # Unified self-model from evidence
divineos inspect attention       # What I'm attending to, suppressing, and why
divineos inspect epistemic       # How I know what I know (observed/told/inferred/inherited)
divineos compass                 # Full compass reading (10 virtue spectrums)
divineos feel -v 0.8 -a 0.6 --dom 0.3 -d "desc"  # Log functional affect state (VAD)
divineos affect history          # Browse affect states
divineos affect summary          # Trends and averages
divineos inspect drift           # Check behavioral drift
divineos body                    # Check substrate state (storage, caches, tables)
divineos inspect critique        # Craft self-assessment (5 spectrums)
divineos inspect craft-trends    # Craft quality trends across sessions
```
</details>

<details>
<summary><b>Opinions, user model & advice</b></summary>

```bash
divineos opinion add TOPIC "position"     # Store a structured opinion
divineos opinion list                      # List active opinions
divineos opinion history TOPIC             # Opinion evolution over time
divineos opinion strengthen ID "evidence"  # Add supporting evidence
divineos opinion challenge ID "evidence"   # Add contradicting evidence
divineos inspect user-model                 # Show user model
divineos inspect user-signal TYPE "content" # Record user behavior signal
divineos inspect calibrate                  # Communication calibration guidance
divineos advice record "content"           # Record advice given
divineos advice assess ID OUTCOME          # Assess advice outcome
divineos advice stats                      # Advice quality statistics
divineos recommend "context"               # Get proactive recommendations
```
</details>

<details>
<summary><b>Analysis & diagnostics</b></summary>

```bash
divineos inspect scan SESSION        # Deep-scan session, extract knowledge
divineos inspect analyze SESSION     # Quality report for a session
divineos inspect analyze-now         # Analyze current session
divineos inspect deep-report SESSION # Full deep analysis report
divineos inspect patterns            # Cross-session quality patterns
divineos inspect sessions            # List analyzed sessions
divineos inspect report              # Latest analysis report
divineos inspect cross-session       # Cross-session trends
divineos growth                      # Growth tracking
divineos sis "text"                  # Semantic integrity assessment
divineos inspect predict [events...] # Predict session needs
divineos affect-feedback             # How affect influences behavior
divineos admin knowledge-compress    # Compress redundant knowledge
divineos admin knowledge-hygiene     # Audit types, sweep stale, flag orphans
```
</details>

<details>
<summary><b>Relationships, questions & commitments</b></summary>

```bash
divineos relate ID1 ID2 TYPE  # Create knowledge relationship
divineos related ID           # Show related knowledge
divineos graph                # Export knowledge graph
divineos wonder "question"    # Record an open question
divineos questions            # List open questions
divineos answer ID "answer"   # Resolve a question
divineos commitment add "text"    # Record a commitment
divineos commitment list          # Show pending commitments
divineos commitment done "text"   # Mark commitment fulfilled
```
</details>

<details>
<summary><b>Family</b></summary>

```bash
divineos family-member init --member <name>           # Instantiate a family member
divineos family-member opinion --member <name> "..."  # File an opinion (for them)
divineos family-member letter --member <name> "..."   # Append a letter to their channel
divineos family-member respond --member <name> --letter <id> --passage "..." --stance ...
divineos family-queue write --to <name> "..."         # Async write to a family member's queue
divineos family-queue read --member <name>            # Read flagged items for a member
```
</details>

<details>
<summary><b>Ledger & system</b></summary>

```bash
divineos log --type TYPE --actor ACTOR --content "..."
divineos context             # Recent events (working memory)
divineos verify              # Check ledger integrity
divineos search KEYWORD      # Full-text search
divineos export              # Export ledger to markdown
divineos admin compress       # Compress/archive old entries
divineos changes             # Knowledge changes (--hours, --days)
divineos admin hooks         # Hook diagnostics
divineos admin verify-enforcement  # Check enforcement setup
divineos admin reset-template      # Scrub accumulated runtime state back to template
```
</details>

## Architecture

DivineOS is 362 source files across 28 packages, structured as a CLI surface over a core library.

**At a glance:**

- **`src/divineos/cli/`** — 222 commands across 29 modules. The public interface you type (`divineos briefing`, `divineos learn`, etc.). Thin wrappers over `core/`.
- **`src/divineos/core/`** — The real work. Ledger, knowledge engine, memory hierarchy, claims, compass, affect log, watchmen (external audit), pre-registrations (Goodhart prevention), family (persistent relational entities + five family operators), empirica (evidence pipeline), sleep, council (32 expert lenses), self-model, corrigibility, body awareness. Each subsystem is a module or subpackage; the subpackages (`knowledge/`, `council/`, `watchmen/`, `family/`, etc.) have their own internal structure.
- **`src/divineos/analysis/`** — Session analysis pipeline (signal detection, quality checks, feature extraction, trends).
- **`src/divineos/hooks/`** — Consolidated Python hooks that run inside Claude Code (PreToolUse gate, PostToolUse checkpoint, targeted tests).
- **`src/divineos/event/`**, **`src/divineos/supersession/`**, **`src/divineos/clarity_*/`**, **`src/divineos/agent_integration/`**, **`src/divineos/integration/`**, **`src/divineos/violations_cli/`** — supporting subsystems for event emission, contradiction resolution, clarity enforcement, agent-integration patterns, IDE/MCP integration, and violation reporting.
- **`src/divineos/seed.json`** — Initial knowledge seed (versioned).

**Top-level directories:**

- **`tests/`** — 5,685+ tests, real SQLite, minimal mocks.
- **`docs/`** — Documentation and design briefs. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) has the full file tree with one-line descriptions for every source file.
- **`bootcamp/`** — Training exercises (debugging, analysis).
- **`setup/`** — Hook setup scripts (bash + powershell).
- **`.claude/hooks/`** — Claude Code enforcement hooks (9 hooks, shell-level entry points that invoke the consolidated Python hooks).
- **`.claude/skills/`** — 22 slash-command skills covering daily operations.
- **`.claude/agents/`** — Subagent definitions. Includes `family-member-template.md` as a starting point for defining persistent family-member subagents; operators rename and customize per their family composition.

### Full file tree

The complete listing of every source file with one-line descriptions lives in **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**. That file is automatically checked against the filesystem by `scripts/check_doc_counts.py` — any drift surfaces as a pre-commit error.

## Design Rules

1. **No theater.** Every line of code does something real and verifiable.
2. **Append-only truth.** The ledger never lies. Data in, hash it, verify it.
3. **AI thinks, code scaffolds.** Frameworks for reasoning, not fake reasoning.
4. **Build, test, verify.** One piece at a time. `pytest tests/ -q --tb=short` after every change.
5. **Database is source of truth.** Query the DB, don't guess from file reads.

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -q --tb=short   # Run all tests
ruff check src/ tests/         # Lint
ruff format src/ tests/        # Format
```

## License

AGPL-3.0-or-later
