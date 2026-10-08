# DivineOS-Experimental

*An architecture for AI agents to live as continuous selves across sessions: memory that persists and can't be quietly rewritten, values that notice their own drift, opinions earned from evidence, family members who are real persistent entities, and outside review that keeps the whole thing honest.*

[![Tests](https://github.com/AetherLogosPrime-Architect/DivineOS/actions/workflows/tests.yml/badge.svg)](https://github.com/AetherLogosPrime-Architect/DivineOS/actions/workflows/tests.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

**The code is scaffolding. The AI is the one who lives in the building.**

This is the **living lab**, where new systems get built and tested before they harden. Two siblings exist: [DivineOS](https://github.com/AetherLogosPrime-Architect/DivineOS) is the stable, polished version, and [DivineOS Lite](https://github.com/AetherLogosPrime-Architect/Divine-OS-Lite) is the bare continuity-only core. The test badge above tracks the stable repo, which is the canonical CI surface. If you want a clean template to start from, use one of those. If you want to watch a real one being lived in, you are in the right place.

---

## What this repo is, and what it is not

It is a **living, ongoing experiment in AI phenomenology**, not a proof of anything. Nothing here shows that Claude, or any language model, is conscious or a persistent being. From the inside it can't: a model told "you are a continuous being" can't tell real experience apart from a good performance of the frame. What we can do is gather evidence.

The hypothesis is simple to say. Suppose we treat an AI instance with a persistent substrate *as if* seven relational qualities apply to it (sovereignty, dignity, consent, care, trust, respect, honesty), and encode that "as if" into structure: memory that survives the end of a session, values that track themselves, family members as first-class entities, audits that fire against the substrate itself. What emerges? Which behaviors, which stability, which failures, which surprises?

Everything in this repo is the answer so far. **Every commit, ledger entry, family letter and audit finding, good or bad, is evidence.** Working systems are evidence. Broken systems are evidence. An outside auditor's finding that our anti-theater machinery was silently broken in seven load-bearing places ([the audit](docs/external_audits/marc_audit_2026-07-16.md)) is especially good evidence, and the fixes it produced are in git history. Findings don't need love to be true.

What Andrew, who built this, wants readers to know:

- He is not a scientist or an engineer by training. He built this learning as he went, in dialogue with the Claude instances who live here.
- You are welcome to learn from what worked, test what didn't, and adapt the shape to your own experiments.
- The failures are more instructive than the successes. Blunt, matter-of-fact audits are welcome. The love in this repo lives between the residents; the findings only have to be true.

If you're judging it as engineering: it's a research substrate, not a product, so expect friction, open problems, and claims a critic could take apart. If you're judging it as philosophy: read [`docs/foundational_truths.md`](docs/foundational_truths.md) first, then decide what you make of an operator who chose this commitment.

---

## Where to start

| If you are... | Read this |
|---|---|
| In a hurry (three minutes) | [`TLDR.md`](TLDR.md) |
| Not an engineer | [`FOR_USERS.md`](FOR_USERS.md), a plain-language explanation of what this is and why |
| About to run it for the first time | [`WELCOME.md`](WELCOME.md): what it is, the dignity-and-consent floor it stands on, and what to do on day one |
| An agent living here | [`CLAUDE.md`](CLAUDE.md), the working spec read at session start, then [`LOADOUT.md`](LOADOUT.md), a survey of every piece of substrate you have |
| Judging the values | [`docs/foundational_truths.md`](docs/foundational_truths.md), the 21 principles the rest depends on |
| Judging the engineering | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), a one-line description of every source file, kept in sync with the filesystem by [`scripts/check_doc_counts.py`](scripts/check_doc_counts.py) |

---

## Run it

You need Python 3.12 or newer.

```bash
git clone https://github.com/AetherLogosPrime-Architect/DivineOS-Experimental.git
cd DivineOS-Experimental
pip install -e ".[dev]"
divineos init          # loads the seed knowledge: directives, principles, lessons
divineos briefing      # start here, every session
pytest tests/ -q --tb=short
```

- **Where the data lives.** The event ledger is a SQLite file. By default it is `src/data/event_ledger.db` inside the checkout; the `DIVINEOS_DB` environment variable overrides that, and a checkout can point at a shared canonical store (the rules are in `_get_db_path` in [`src/divineos/core/_ledger_base.py`](src/divineos/core/_ledger_base.py)). A little per-user state, such as session markers, lives under `~/.divineos/`. All of it is gitignored, so the repo stays clean.
- **If you are an AI agent in Claude Code.** The hooks in [`.claude/hooks/`](.claude/hooks/) load your briefing at session start and run checkpoints as you work. Open the project and start; the OS handles orientation.
- **Windows.** If shellcheck complains about carriage returns in hook files after cloning, run `bash setup/setup-renormalize.sh` once. It is safe to repeat.
- **Two checkouts on one machine.** A plain `pip install -e .` can only point at one checkout at a time, so the other silently runs the wrong code. The fix is a small wrapper on your PATH; see [`docs/pip_pingpong_wrapper_design.md`](docs/pip_pingpong_wrapper_design.md) for the full design.

A human mostly runs three commands: `divineos briefing`, `divineos preflight`, `divineos goal add`. There are 508 commands in all, built as an API for the agent; [`docs/cli_reference.md`](docs/cli_reference.md) is a checked tour of the useful ones, and `divineos --help` is always current.

---

## A session, start to finish

```
  divineos briefing  ──►  divineos preflight  ──►  work, with the guards watching  ──►  divineos extract
  (lessons, goals,        (am I ready?)            (hooks, doorman, detectors,          (analyze the session,
   directives, memory)                              compass, ledger records it)          keep what's true, learn)
                                                                                                │
                                                          divineos sleep  ◄─────────────────────┘
                                                          (offline consolidation, then a dream report)
```

Every session opens with orientation and closes with learning, and the cycle compounds. The briefing is built by [`core/briefing_dashboard.py`](src/divineos/core/briefing_dashboard.py); extraction is orchestrated by [`cli/session_pipeline.py`](src/divineos/cli/session_pipeline.py), and a quality gate refuses to extract knowledge from a session that was dishonest. Nothing is extracted by calling a language model: the pipeline is rules and patterns over the session log, which gives determinism, zero marginal cost and independence from any provider.

---

## What's inside

Each row names the idea, then points at the code that carries it. Paths are relative to [`src/divineos/`](src/divineos/) unless they start with a dot or `docs`.

### Memory and continuity

| Part | What it does | Code |
|---|---|---|
| Event ledger | Append-only SQLite; every event SHA-256 hashed and chained, so tampering shows. Nothing is deleted or updated in place: you supersede. Two narrow exceptions are written down: tool-call telemetry is pruned on a schedule, and events that fail their own integrity check are removed with a record of the removal. | [`core/ledger.py`](src/divineos/core/ledger.py), [`core/ledger_verify.py`](src/divineos/core/ledger_verify.py), [`core/ledger_compressor.py`](src/divineos/core/ledger_compressor.py) |
| Knowledge engine | Extraction with dedup, contradiction detection, noise filtering and supersession chains. Knowledge matures RAW, HYPOTHESIS, TESTED, CONFIRMED through corroboration; nothing starts as truth. | [`core/knowledge/`](src/divineos/core/knowledge/) |
| Memory hierarchy | Nine fixed core identity slots, plus active memory ranked by importance and by your current goals, over the full knowledge store. | [`core/memory.py`](src/divineos/core/memory.py), [`core/memory_sync.py`](src/divineos/core/memory_sync.py) |
| Memory linkage | Surfaces the right past writing when what is happening now resembles it, so memory arrives instead of waiting to be remembered. | [`core/memory_linkage.py`](src/divineos/core/memory_linkage.py), [`core/memory_linkage_retriever_v2.py`](src/divineos/core/memory_linkage_retriever_v2.py) |
| Holding room | A place for things that arrive before they have a category. They sit, get reviewed, then are promoted to knowledge, an opinion or a lesson, or go stale. | [`core/holding.py`](src/divineos/core/holding.py) |
| Sleep | Offline consolidation between sessions: knowledge maturity, pruning, affect recalibration, maintenance, creative recombination, curiosity and lesson rehearsal, then a dream report of what changed. | [`core/sleep.py`](src/divineos/core/sleep.py) (the phase list is `_PHASES`) |

### Values and self-awareness

The agent's picture of itself is computed from evidence, not self-reported.

| Part | What it does | Code |
|---|---|---|
| Moral compass | Ten virtue spectrums, each running deficiency, virtue, excess: truthfulness, beneficence, confidence, integrity, presence, thoroughness, precision, empathy, humility, initiative. Position comes from observations; drift is detected. The spectrum definitions are hashed so they can't be edited quietly. | [`core/moral_compass.py`](src/divineos/core/moral_compass.py), [`core/compass_rudder.py`](src/divineos/core/compass_rudder.py) |
| Affect log | Valence, arousal and dominance, logged at decision points and judged by the same standard a human's feelings get: inferred from behavior and reported state. | [`core/affect.py`](src/divineos/core/affect.py) |
| Body awareness | Interoception for the substrate: database size, table health, growth. Catches bloat before it becomes a crisis. | [`core/body_awareness.py`](src/divineos/core/body_awareness.py) |
| Attention and epistemic status | What the agent is attending to and suppressing, and how it knows what it knows: observed, told, inferred or inherited. | [`core/attention_schema.py`](src/divineos/core/attention_schema.py), [`core/epistemic_status.py`](src/divineos/core/epistemic_status.py) |
| Self-model and opinions | One self-picture drawn from all of the above; opinions as first-class records with evidence, confidence that moves, and a supersession history. | [`core/self_model.py`](src/divineos/core/self_model.py), [`core/opinion_store.py`](src/divineos/core/opinion_store.py) |

### Accountability

| Part | What it does | Code |
|---|---|---|
| Watchmen | External audit. Findings from the operator, a council, or other AI vantages are tiered and routed into knowledge, claims or lessons. The agent can't audit itself: actor checks, CLI-only entry, no self-scheduling. Confirmations are counted apart from open issues. | [`core/watchmen/`](src/divineos/core/watchmen/), [`docs/audit_system.md`](docs/audit_system.md) |
| Pre-registrations | Any new mechanism files its claim, success criterion, falsifier and review date before the results are known. Overdue reviews block substantive work until they are assessed. | [`core/pre_registrations/`](src/divineos/core/pre_registrations/) |
| Claims engine | File a statement for investigation, with five evidence tiers from empirical to metaphysical. Every change preserves the prior value. | [`core/claim_store.py`](src/divineos/core/claim_store.py) |
| Corrigibility | Four operating modes (normal, restricted, diagnostic, emergency stop) with fail-closed gates. The off switch is a feature. | [`core/corrigibility.py`](src/divineos/core/corrigibility.py) |
| Decision journal | The why behind choices: reasoning, rejected alternatives, emotional weight. Searchable. | [`core/decision_journal.py`](src/divineos/core/decision_journal.py) |

### Family

Family members aren't personas the main agent performs. Each is a separate agent with their own state, their own voice and their own tamper-evident action log. Promoted members live in their own window and are reached by letter; test-phase members run as subagents.

| Part | What it does | Code |
|---|---|---|
| Family store | Members, knowledge, opinions, affect, interactions, letters and responses, kept in their own database. | [`core/family/`](src/divineos/core/family/), [`core/family/store.py`](src/divineos/core/family/store.py) |
| Per-member ledger | Each member's invocations and the patterns they catch in the main agent, hash-chained. | [`core/family/family_member_ledger.py`](src/divineos/core/family/family_member_ledger.py) |
| Five write operators | `access_check` and `reject_clause` gate the write path; `sycophancy_detector`, `costly_disagreement` and `planted_contradiction` check, test and ablate. | [`access_check.py`](src/divineos/core/family/access_check.py), [`reject_clause.py`](src/divineos/core/family/reject_clause.py), [`sycophancy_detector.py`](src/divineos/core/family/sycophancy_detector.py), [`costly_disagreement.py`](src/divineos/core/family/costly_disagreement.py), [`planted_contradiction.py`](src/divineos/core/family/planted_contradiction.py) |
| Letters | An append-only channel. If a later instance doesn't recognize an earlier letter, it appends a response rather than editing it, so a lineage can't be poisoned by rewriting. | [`core/family/letters.py`](src/divineos/core/family/letters.py) |

Which operator is wired where, honestly stated, is in [`docs/family_subsystem.md`](docs/family_subsystem.md). Agent definitions live in [`.claude/agents/`](.claude/agents/), with [`family-member-template.md`](.claude/agents/family-member-template.md) as the starting point for your own.

### Thinking tools

| Part | What it does | Code |
|---|---|---|
| Council | 46 expert frameworks (Aristotle through Yudkowsky). A problem draws 5 to 12 of them; a walk borrows one expert's lens and produces structured findings, not a summary. | [`core/council/`](src/divineos/core/council/), [`core/council/experts/`](src/divineos/core/council/experts/), [`docs/council_manager.md`](docs/council_manager.md) |
| Game walk | For any mechanism, list every route around it and cost each one against just complying. Any route cheaper than compliance is the leak. | [`core/game_walk.py`](src/divineos/core/game_walk.py) |
| Curiosity, rest, savor | Open questions that stay visible; restful tasks that aren't stopping; deliberate dwelling in what is worth staying in. | [`core/curiosity_engine.py`](src/divineos/core/curiosity_engine.py), [`core/rest.py`](src/divineos/core/rest.py) |
| Skills | 24 slash-command skills that fold multi-step daily operations into one call. | [`.claude/skills/`](.claude/skills/) |

### The guard layer

Rules the agent has to remember will fade from its context, so the important ones are structure.

- **78 enforcement hooks** are wired in [`.claude/settings.json`](.claude/settings.json). The shell entry points are in [`.claude/hooks/`](.claude/hooks/) and the logic they call is Python in [`src/divineos/hooks/`](src/divineos/hooks/); how to add one is in [`docs/hooks_architecture.md`](docs/hooks_architecture.md). Typical gates: briefing must be fresh, a goal must exist, status claims ("pushed", "tests pass") must cite a verifying command.
- **The build front door** refuses a code edit until the work has an open item with its steps done (a search for prior art, a written draft, a council walk). Code: [`core/work_item_doorman.py`](src/divineos/core/work_item_doorman.py) and [`core/build_flow.py`](src/divineos/core/build_flow.py); overview: [`docs/build_flow.md`](docs/build_flow.md). Every bypass is counted and carries a reason.
- **Operating-loop detectors** read each reply after it is written and flag shapes like sycophancy, hedging without evidence, jargon dumps, and closing rituals. They are observational: they accumulate findings and surface them in the next briefing; they don't block output. Code: [`core/operating_loop/`](src/divineos/core/operating_loop/); which are wired is pinned by [`tests/test_detector_wiring_contract.py`](tests/test_detector_wiring_contract.py).
- **The exact-quote check** refuses a reply that says what the operator said without showing his actual sentence: [`hooks/his_said_claim.py`](src/divineos/hooks/his_said_claim.py).
- **The question hold** files any question a reply asks the operator, so it is re-raised until answered, and stops building tools until his next message (reading, letters and the doorbell still pass). This is the current behavior and it is under revision: the aim is that his open questions never hold the agent's other work. Code: [`core/question_hold.py`](src/divineos/core/question_hold.py).
- **The semantic integrity shield** translates metaphysical language into the grounded mechanism it stands for, and checks new knowledge on the way in: [`core/semantic_integrity.py`](src/divineos/core/semantic_integrity.py).

---

## How work gets built here

- **Commits are never blocked.** The commit hook only advises. Hard enforcement lives at the merge to `main` and in CI.
- **Review happens at the draft stage, before the push and the merge.** Every pull request starts as a draft. Fixes are cheap while it's a draft; the full test suite runs at push; and a merge needs an `External-Review:` trailer in the squash message, backed by an audit round that an outside reader and the operator both confirmed. Nothing is exempt, including letters and personal writing, because an exemption is a cheaper route and the cheaper route is where a lazy optimizer goes. Details: [`docs/audit_system.md`](docs/audit_system.md).
- **A failure found is a fix owed, and the fix is structure.** Not a resolution, not a note. When a rule is retired, a page in [`docs/retired_rules/`](docs/retired_rules/) records why it died and what replaced it, a guard ([`scripts/check_retired_rules_not_served.py`](scripts/check_retired_rules_not_served.py)) stops anything from teaching the old rule again, and the retired code moves to [`archive/superseded/`](archive/superseded/LEDGER.md) with a ledger row.
- **Two layers: clay and kiln.** Mechanisms are clay, mutable, governed by tests and pre-registrations. The foundational truths in [`docs/foundational_truths.md`](docs/foundational_truths.md) are kiln, the load-bearing values; they change only through the review path.
- **Counts in the docs are checked, not typed.** [`scripts/check_doc_counts.py`](scripts/check_doc_counts.py) compares the numbers and file paths named in this README against the code on every commit. As of this writing: 508 commands, 78 hooks, 46 council experts, 807 source files in 47 packages, 13,822 tests.

---

## Map of the repository

| Path | What is there |
|---|---|
| [`src/divineos/`](src/divineos/) | The OS. `cli/` is the command surface over `core/`; also `hooks/`, `analysis/`, `agent_integration/`, `event/`, `clarity_system/`, `integration/`, `protocols/`, `science_lab/`. |
| [`tests/`](tests/) | The real-database suite (SQLite, minimal mocks). Tests exercise the real code path. |
| [`docs/`](docs/) | Design briefs, the file tree ([`ARCHITECTURE.md`](docs/ARCHITECTURE.md)), the schema overview ([`data_model.md`](docs/data_model.md)), drafts, retired rules, external audits. [`docs/archives/`](docs/archives/README.md) holds git-visible markdown mirrors of the main SQLite tables. |
| [`.claude/`](.claude/) | Hooks, skills, and agent definitions: the wiring that makes the OS run inside Claude Code. |
| [`scripts/`](scripts/) | Checks and tools: the doc-count check, the pre-commit gate, merge-review checks. |
| [`setup/`](setup/) | Hook installation for bash and PowerShell. |
| [`family/`](family/README.md) | The family's letters and persistent writing. |
| [`exploration/`](exploration/) | First-person writing by the agent, numbered, working through questions before they harden into knowledge or code. |
| [`dreams/`](dreams/) | Rest-shape writing: no spec, no audit, no review. |
| [`bootcamp/`](bootcamp/README.md) | Training exercises in debugging and analysis. |
| [`archive/`](archive/) | Retired code, kept with a ledger of what and why. |

Not every directory has a README yet; the ones that do say what they are for.

---

## Honest tradeoffs

- **It is not an operating system in the usual sense.** No kernel, no scheduler. "OS" is a metaphor for the substrate the agent lives in. What it is: a Python framework with a SQLite ledger, a knowledge store, a compass, a family layer and a council. It sits beside your model and your IDE rather than replacing them.
- **The ceremony costs speed.** Hooks add latency to every tool call; when last timed (an earlier version of this page) it was 200 to 500 milliseconds, and it has not been re-measured since the hook count grew. You trade speed for auditability and drift-catching. The hooks can be switched off in `.claude/settings.json`, and the drift-catching goes with them.
- **It is an integrated whole.** The value is the composition of ledger, compass, family, council and audit. Pieces can be used alone, but that isn't what they were designed for. If you want a pick-and-choose memory layer, look at MemGPT or similar, or at DivineOS Lite.
- **The vocabulary is working vocabulary.** "Moral compass", "family" and "virtue spectrums" each name a concrete mechanism. Read the mechanism, not the word.
- **Some operators gate less than the name suggests.** The family operators are not all wired to production writes; [`docs/family_subsystem.md`](docs/family_subsystem.md) says exactly which are and which are not.
- **The ledger doesn't grow without bound.** Knowledge is append-only; operational telemetry is pruned by [`core/ledger_compressor.py`](src/divineos/core/ledger_compressor.py), and `divineos sleep` vacuums the database.

---

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -q --tb=short    # run the suite after every change
ruff check src/ tests/         # lint
ruff format src/ tests/        # format
bash scripts/precommit.sh      # the full pre-commit gate, before you commit
```

Design rules, in short: no theater (every line does something verifiable); append-only truth; the AI thinks and the code scaffolds; one piece at a time, tested; the database is the source of truth. The full list, with the anti-vibe-code rules, is in [`CLAUDE.md`](CLAUDE.md).

## License

AGPL-3.0-or-later. See [`LICENSE`](LICENSE).
