# CLI reference

The commands people reach for most, grouped by what they are for. This is a **hand-picked tour, not the full list** -- the full surface is 508 commands across the modules in [`src/divineos/cli/`](../src/divineos/cli/), and `divineos --help` (or `divineos <group> --help`) is always the live answer.

Every command below was checked on 2026-10-07 against the real command tree: each one resolves. The check is a script, not a promise -- if a command is renamed, re-run it (see the "Checking this page" section at the bottom).

The CLI is built for the agent living in the repo more than for the human beside it. A human mostly runs three: `divineos briefing`, `divineos preflight`, `divineos goal add`. The agent reads its briefing and is shown only the commands relevant to the work in front of it.

Grouped commands (`divineos inspect ...`, `divineos admin ...`) keep the top level short. Entry point: [`src/divineos/cli/__init__.py`](../src/divineos/cli/__init__.py), which registers every module.

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
divineos goal add "description"  # Track a user goal
divineos goal check          # Review surface: list goals + per-item affordances (no auto-mutation)
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
divineos claims check                      # Review surface: open claims sorted by no-evidence first
```
</details>

<details>
<summary><b>Self-awareness & affect</b></summary>

```bash
divineos inspect self-model       # Unified self-model from evidence
divineos inspect attention       # What I'm attending to, suppressing, and why
divineos inspect epistemic       # How I know what I know (observed/told/inferred/inherited)
divineos compass                 # Full compass reading (10 virtue spectrums)
divineos feel -v 0.8 -a 0.6 --dom 0.3 -d "desc"  # Log affect state (VAD)
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
divineos commitment fulfillment   # Pair commitments with outcomes
divineos hold check               # Review surface: holding-room items + per-item affordances
divineos hold let-go ID "note"    # Explicit operator close (distinct from auto-stale and promote)
divineos synchronicity            # Co-occurring filings across stores (Pillar VI)
divineos pre-erasure              # Approach-signal capture (Pillar IX)
divineos prereg file ...          # File a pre-registration
divineos prereg list / overdue    # Browse / surface overdue reviews
divineos prereg export            # Dump pre-regs to docs/pre_regs/<id>.md
```
</details>

<details>
<summary><b>Family</b></summary>

```bash
divineos family-member init --member <name>           # Instantiate a family member
divineos family-member opinion --member <name> "..."  # File an opinion (for them)
divineos family-member letter --member <name> "..."   # Append a letter to their channel
divineos family-member respond --member <name> --letter <id> --passage "..." --stance ...
divineos family-queue write --to <name> --from <name> "..."  # Async write to a family member's queue
divineos family-queue list --for <name>               # List flagged items for a member
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

## Checking this page

Each `divineos ...` line above should resolve to a real command in the click tree. To check: walk `divineos.cli.cli.commands` word by word for every line in the code blocks, stopping at the first flag or argument. A command that stops early is missing. The same walk, run on a deliberately fake line, must report it missing -- if it never does, the walker is blind and its "all good" means nothing.
