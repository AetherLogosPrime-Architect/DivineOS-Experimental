# Capability catalog

**Generated** by `scripts/generate_capability_catalog.py`. Do not hand-edit — regenerate.

Third of three inventories. [LOADOUT.md](../LOADOUT.md) describes the rooms. [AUTOMATION_REGISTER.md](AUTOMATION_REGISTER.md) lists what runs by itself. This lists what I can **reach for** — the tools on the wall.

**182 top-level commands, 357 subcommands, 37 core subsystems.**

---

## Usage telemetry is nearly blind

Usage history lives in `OS_QUERY` events. **11 of 182 top-level commands have ever been recorded.**

That is NOT a claim that the other commands are unused. Commands demonstrably used — filing corrections, pre-registrations, audit rounds — emit no telemetry at all. The honest reading: **the substrate cannot answer which tools are live and which have never been opened.**

A low usage number would be a habit problem. Blind telemetry is a measurement problem, and it is why an unused tool can sit unnoticed indefinitely — nothing is counting. Rows below carry `•` when the command reports usage at all, so the blind spots are visible rather than implied.

Commands that DO report usage:

| command | recorded invocations |
|---|---|
| `ask` | 441 |
| `briefing` | 237 |
| `decide` | 152 |
| `compass` | 139 |
| `context` | 86 |
| `recall` | 49 |
| `lessons` | 37 |
| `directives` | 13 |
| `feel` | 8 |
| `body` | 6 |
| `reflect-ops` | 2 |

---

## Commands

`•` marks a command with usage telemetry. Drilldown: `divineos <command> --help`.

### `abandon-question`

Abandon an open question that's no longer...

### `active`

List active memory ranked by importance.

### `actor-registry`

Actor registry operations (Phase 1 of...

| subcommand | purpose |
|---|---|
| `actor-registry add` | Register a new actor by name and kind. |
| `actor-registry check` | Preview the capability verdict for (actor, event_type). |
| `actor-registry init` | Create the registry file (if it does not exist). |
| `actor-registry list` | Show all registered actors. |
| `actor-registry show` | Show one actor's registry entry. |

### `admin`

Maintenance, migration, and administrative...

| subcommand | purpose |
|---|---|
| `admin anti-slop` | Runtime verification that enforcers... |
| `admin archive-export` | Regenerate docs/archives/ mirrors from... |
| `admin backfill-warrants` | Give pre-existing knowledge entries... |
| `admin check-correction-pairing` | Surface compass observations that look like... |
| `admin clean` | Remove corrupted events from the ledger. |
| `admin clear-lessons` | Wipe all lessons from lesson_tracking (for... |
| `admin compress` | ELMO â€” compress the event ledger by... |
| `admin consolidate` | Merge related knowledge entries into... |
| `admin consolidate-stats` | Display knowledge consolidation statistics. |
| `admin diff` | Compare original file to database export... |
| `admin digest` | Read a file in chunks and store a... |
| `admin distill` | Distill raw knowledge into clean,... |
| `admin fix-encoding` | Repair mojibake in knowledge content via ftfy. |
| `admin hooks` | Diagnose hook configuration â€” validate all... |
| `admin ingest` | Parse and store a chat log file (JSONL or... |
| `admin inventory` | Walk the CLI command tree and report... |
| `admin knowledge-compress` | Compress redundant knowledge into denser... |
| `admin knowledge-hygiene` | Audit and clean the knowledge store â€”... |
| `admin maintenance` | Run substrate maintenance â€” VACUUM, log... |
| `admin migrate-family-schema` | Migrate family_affect and... |
| `admin migrate-types` | Reclassify old knowledge types... |
| `admin rebuild-index` | Rebuild the full-text search index from... |
| `admin reclassify-directions` | Reclassify DIRECTION entries into... |
| `admin reclassify-seed` | Fix legacy seed entries mis-tagged as... |
| `admin reset-template` | Reset this DivineOS install to a... |
| `admin restore-seed-confidence` | Restore INHERITED entries spuriously... |
| `admin seed-export` | Export current knowledge and core memory as... |
| `admin structural-promotion-check` | Dual-monitor surface for the will-to-vessel... |
| `admin test-audit` | Audit test quality â€” classify tests by what... |
| `admin verify-enforcement` | Verify that the event enforcement system is... |

### `advice`

Track advice quality over time.

| subcommand | purpose |
|---|---|
| `advice assess` | Record the outcome of advice given. |
| `advice pending` | Show advice that needs outcome assessment. |
| `advice record` | Record a piece of advice given. |
| `advice stats` | Show advice quality statistics. |

### `affect`

My functional feeling states - tracked...

| subcommand | purpose |
|---|---|
| `affect history` | Browse recent affect states. |
| `affect prime` | Task #121: print the felt-state continuity prime. |
| `affect summary` | Show affect state summary and trends. |

### `affect-feedback`

Show how affect states are influencing...

### `aletheia-import`

File an artifact Andrew has handed over into...

### `already-built`

Check whether THING already exists before...

### `andrew-correction`

Andrew-correction attribution surface (Aria...

| subcommand | purpose |
|---|---|
| `andrew-correction auto-integrate` | Auto-integrate corrections referenced in a commit message. |
| `andrew-correction defer` | Mark a correction DEFERRED with named reason. |
| `andrew-correction integrate` | Mark a correction INTEGRATED with evidence pointer. |
| `andrew-correction list` | Show all OPEN Andrew-corrections + integration-rate. |

### `andrew-state`

Andrew-state observation channel â€”...

| subcommand | purpose |
|---|---|
| `andrew-state correct` | Andrew corrects an observation â€” new row inserted,... |
| `andrew-state for-decision-walk` | Show UNVERIFIED observations older than --age-hours... |
| `andrew-state log` | Log a new observation of Andrew's state. |
| `andrew-state reject` | Mark an UNVERIFIED observation as REJECTED â€” Andrew... |
| `andrew-state unverified` | List UNVERIFIED head-of-chain observations, newest... |
| `andrew-state verify` | Mark an UNVERIFIED observation as VERIFIED â€” Andrew... |

### `andrew-teachings`

Surface Andrew's teachings â€” his pedagogy,...

### `answer`

Resolve an open question with an answer.

### `archive`

Mark a directive/preference as archived...

### `ask` •

Search what the system knows about a topic.

### `attribution-scan`

Surface dated quotative attributions lacking...

### `audit`

External validation â€” submit and track audit...

| subcommand | purpose |
|---|---|
| `audit auto-triage` | Surface OPEN findings whose cited files/commits... |
| `audit compliance` | Substantive distribution audit of the compliance... |
| `audit confirm-holds` | Does the external-AI CONFIRM already in this... |
| `audit export` | Write rounds to docs/audit_rounds/ so CI can see... |
| `audit file-external-confirm` | File a relayed external-AI CONFIRM into a round... |
| `audit list` | List audit findings. |
| `audit list-clean` | List externally-audited-clean sessions. |
| `audit patch-id` | Print a branch's tree-hash + patch-id â€” the... |
| `audit pr-merge-check` | Verify a PR is safe to merge under guardrail... |
| `audit predict` | Record self-audit prediction BEFORE the audit... |
| `audit prep-relay` | Verify commits are pushed before composing an... |
| `audit prepare-artifact` | Create an audit artifact from the currently... |
| `audit prepare-merge` | Prepare a squash-merge commit message including... |
| `audit rebind` | File a cosmetic-rebind round that carries the... |
| `audit resolve` | Resolve or update a finding's status. |
| `audit route` | Route all open findings in a round to... |
| `audit show` | Show details of a specific finding. |
| `audit submit` | Submit a single audit finding. |
| `audit submit-round` | Create a new audit round. |
| `audit summary` | Show audit statistics and unresolved findings. |
| `audit surprises` | Show audit findings the substrate-occupant... |
| `audit tag-clean` | Tag a session as externally-audited-clean. |
| `audit unknown-unknown-rate` | Rolling proportion of audit findings that were... |
| `audit untag-clean` | Remove a clean-tag. |

### `audit-sync`

Import audit findings from the shared...

### `audit-visibility`

Audit-visibility commands â€” check that local...

| subcommand | purpose |
|---|---|
| `audit-visibility check` | Warn if HEAD touches auditable paths and isn't on origin. |

### `authorize-reset-template`

Emit an operator-anchored StateMarker...

### `auto-cycle`

Auto-cycle phase 1: mechanical...

| subcommand | purpose |
|---|---|
| `auto-cycle defer-check` | Internal-facing trigger check â€” for hooks. |
| `auto-cycle fire` | Fire phase 1 now â€” commit, extract, sleep, write handshake... |
| `auto-cycle status` | Show current auto-cycle state â€” context %, would-fire,... |

### `automerge`

Show auto-merge state across open PRs.

### `backlog`

Append-only structural-debt tracker for...

| subcommand | purpose |
|---|---|
| `backlog add` | Append a backlog entry. |
| `backlog list` | Browse the backlog, optionally filtered by cluster. |

### `bio`

The agent's own page.

| subcommand | purpose |
|---|---|
| `bio edit` | Open your $EDITOR with the current bio (or a starter template). |
| `bio history` | List bio versions, newest first. |
| `bio show` | Print the current bio (full page). |
| `bio write` | Write a new bio version directly from the command line. |

### `body` •

Check my substrate state -- storage, tables,...

### `briefing` •

Generate a session context briefing from...

### `briefing-id`

Prove context-freshness by recalling your...

### `build-flow`

Build-flow station status for open PRs...

### `calibration`

How well-calibrated my confidence values are...

| subcommand | purpose |
|---|---|
| `calibration anchor` | Pre-prediction anchor: at this confidence, what's my... |
| `calibration by-tier` | Brier score sliced by claim tier â€” reveals domain blind-spots. |
| `calibration curve` | Per-bin calibration: predicted vs actual support rate, by... |
| `calibration score` | Overall Brier score across resolved claims with real credences. |

### `changes`

Show what changed in the knowledge store...

### `check-branch`

Check branch health before push: stale-base...

### `check-caution`

Check text for performing-caution shapes...

### `check-closure`

Check text for closure-shape...

### `check-prose`

Check text for overclaim shapes (stacked...

### `check-similar`

Surface existing modules with semantic...

### `checkpoint`

Run a lightweight session checkpoint â€” save...

### `claim`

File a claim for investigation.

### `claims`

Investigate claims - test everything,...

| subcommand | purpose |
|---|---|
| `claims assess` | Update a claim's assessment, status, or tier. |
| `claims check` | Put my open claims in front of me to review â€” no... |
| `claims evidence` | Add evidence to a claim. |
| `claims list` | Browse claims under investigation. |
| `claims search` | Search claims by statement, context, or assessment. |
| `claims show` | Show full claim with all evidence. |
| `claims tiers` | Show the evidence tier definitions. |
| `claims uncommitted` | List claims with no real credence â€” the gap Aletheia named... |

### `commitment`

Track and review agent commitments.

| subcommand | purpose |
|---|---|
| `commitment add` | Record a commitment the agent made. |
| `commitment clear` | Clear all commitments (after review). |
| `commitment done` | Mark a commitment as fulfilled. |
| `commitment fulfillment` | Commitment-fulfillment view: each commitment paired with... |
| `commitment list` | Show pending commitments. |
| `commitment review` | Review all commitments at session end. |
| `commitment timeline` | Unified commitment-collapse timeline across all stores. |

### `compass` •

Show my moral compass â€” where I stand on ten...

### `compass-ops`

Moral compass operations â€” observe, review,...

| subcommand | purpose |
|---|---|
| `compass-ops dismiss` | Dismiss a pending compass-required advisory with reasoning. |
| `compass-ops history` | Show recent compass observations. |
| `compass-ops observe` | Log a manual observation on a virtue spectrum. |
| `compass-ops spectrums` | List all ten virtue spectrums with descriptions. |
| `compass-ops summary` | Show compass summary â€” concerns and drift warnings. |

### `complete`

File a completion boundary for...

### `consumer-status`

Show whether Aether is using the OS or...

### `context` •

Show the last N events (working memory...

### `context-heartbeat`

Freshness of the token count that decides...

### `context-status`

Show current context usage estimate and...

### `context-tokens`

Show real context-window usage from the...

### `core`

Manage core memory slots.

### `correction`

Log a correction verbatim â€” no framing, no...

### `correction-false-positive`

Clear the correction-unlogged marker when...

### `correction-resolve`

Resolve a correction by index (from...

### `corrections`

Read past corrections with status -- the...

### `corrections-mirror`

Mirror a sibling's corrections into my own...

### `corrections-mirror-judge`

Record my reading of one mirrored correction.

### `corrections-sibling`

Corrections my sibling received that have no...

### `corroborate`

Record a corroboration event on a knowledge...

### `council`

Council-required enforcement: log walks,...

| subcommand | purpose |
|---|---|
| `council authorize-bypass` | Authorize a one-time bypass of the council-required... |
| `council check` | Run the gate against a proposed edit and print the... |
| `council emergency-skip` | Invoke the corroborator-required emergency carve-out. |
| `council log` | Write a council walk record. |
| `council recent` | List recent council records, optionally filtered by... |
| `council show` | Display a recorded walk by record_id. |
| `council walk` | Apply a lens to a specific problem by typing per-lens... |

### `curiosity`

Track questions worth investigating.

| subcommand | purpose |
|---|---|
| `curiosity add` | File a new curiosity. |
| `curiosity answer` | Mark a curiosity as answered. |
| `curiosity list` | Show open curiosities. |
| `curiosity note` | Add a note to a curiosity. |
| `curiosity shelve` | Put a curiosity to sleep â€” not abandoned, just not active. |
| `curiosity wonder` | Auto-generate questions from knowledge gaps. |

### `dark-matter`

Find things that exist but nothing reaches.

### `dashboard`

Check-engine lights â€” every registered...

### `decide` •

Record a decision with its reasoning and...

### `decisions`

Browse and search my decision journal.

| subcommand | purpose |
|---|---|
| `decisions context` | Show a decision with its emotional context at the time. |
| `decisions link` | Link a decision to a knowledge entry. |
| `decisions list` | Browse recent decisions. |
| `decisions search` | Search decisions by reasoning, context, or content. |
| `decisions shifts` | Show only paradigm shifts â€” the decisions that changed... |
| `decisions show` | Show full details of a single decision. |

### `dedup-stats`

Show context-dedup savings by source.

### `delete-justify`

Record a justification so the...

### `detectors`

Detectors that reported they could not run:...

| subcommand | purpose |
|---|---|
| `detectors check` | Exit non-zero if any detector is blocking. |
| `detectors defer` | Stop blocking on a detector, on the record. |
| `detectors heal` | Attempt the automatic repair for every down detector. |
| `detectors status` | List every detector currently reporting itself down. |

### `directive`

Create a sutra-style directive â€” a chain of...

### `directive-edit`

Edit a single link in a directive chain.

### `directives` •

List all active directives.

### `doctor`

Diagnostic verification commands for OS health.

| subcommand | purpose |
|---|---|
| `doctor verify-clone-separation` | Run Popper falsifier suite for per-clone... |
| `doctor verify-import` | Verify a module loads from the SAME Python the... |

### `dream`

Review what sleep actually discovered.

| subcommand | purpose |
|---|---|
| `dream list` | List recent sleep cycles, newest first. |
| `dream show` | Show full recombinations from a sleep cycle. |

### `ear-relaunch`

Ear-watcher polling auto-relaunch decision...

| subcommand | purpose |
|---|---|
| `ear-relaunch check` | Return the relaunch decision for `member`. |

### `ear-sweep`

Ear-sweep â€” reap stale ear_watch processes.

| subcommand | purpose |
|---|---|
| `ear-sweep run` | Sweep stale ear_watch processes; print one-line note if any reaped. |

### `emergency-completion`

Emergency-completion lane: arm it, inspect...

| subcommand | purpose |
|---|---|
| `emergency-completion arm` | Arm the lane for the next gate-fire (one-shot, accrues debt). |
| `emergency-completion resolve` | Discharge the outstanding debt by filing a root-cause diagnosis. |
| `emergency-completion status` | Show whether the lane is armed and whether a debt is outstanding. |

### `emit`

Emit an event to the ledger using proper...

### `error`

Open-error registry â€” highest priority,...

| subcommand | purpose |
|---|---|
| `error close` | Mark an error resolved. |
| `error defer` | Operator-authorized deferral (>=20-char reason required). |
| `error file` | File a new open error. |
| `error list` | List open errors (default) or all errors (--all). |
| `error show` | Show full JSON record for one error. |
| `error status` | One-line summary of registry state. |

### `expect`

Expectation tracking â€” predict, close, list,...

| subcommand | purpose |
|---|---|
| `expect close` | Close a prediction with the actual outcome. |
| `expect list` | Show open predictions (those without an actual recorded yet). |
| `expect predict` | Record a prediction. |
| `expect summary` | Show calibration summary across recent closed predictions. |

### `exploration`

Exploration entry surfacing and territory...

| subcommand | purpose |
|---|---|
| `exploration list-territories` | List the locked set of valid territory tags. |
| `exploration new` | Create a new numbered exploration entry â€” the... |
| `exploration referenced` | Mark a surfaced exploration entry as referenced. |
| `exploration related` | Find exploration entries whose Territory tags match... |
| `exploration usage` | Show territory-match surfaceâ†’reference ratio over a... |

### `export`

Export all events to markdown or JSON.

### `extract`

Extract knowledge from the current session â€”...

### `family-member`

Family member activation surface â€” init,...

| subcommand | purpose |
|---|---|
| `family-member affect` | Log a VAD affect reading for a family member â€”... |
| `family-member briefing` | Compute and print the member's working-memory... |
| `family-member init` | Create or refresh a family member's entry, summarize... |
| `family-member interaction` | Log an interaction summary from a family member's... |
| `family-member letter` | Append a handoff letter to a future instance of this... |
| `family-member letters-from-aria` | My read-half of the bidirectional-letters channel:... |
| `family-member opinion` | File an opinion for a family member. |
| `family-member respond` | Append a non-recognition (or other stance) response... |

### `family-queue`

Family async write-channel â€” flag items for...

| subcommand | purpose |
|---|---|
| `family-queue list` | List pending queue items for <recipient> (default: aether). |
| `family-queue mark` | Transition queue item <item_id> to {seen\|held\|addressed}. |
| `family-queue stats` | Show queue stats (total / per-status). |
| `family-queue supersede` | File a corrected version of <old_id>. |
| `family-queue write` | Append a queue item from <sender> to <recipient>. |

### `feel` •

Log a functional affect state - how I feel...

### `find`

Semantic search across the indexed prose...

| subcommand | purpose |
|---|---|
| `find index` | Chunk + embed + store paragraphs from the chosen corpus. |
| `find query` | Search the indexed corpus for chunks semantically similar to TEXT. |
| `find stats` | Show what's currently in the search index. |

### `findings`

Manage the consolidated audit-findings ledger.

| subcommand | purpose |
|---|---|
| `findings add` | Add a finding. |
| `findings close` | Mark a finding CLOSED (confirmed fixed). |
| `findings export` | Force a re-render of docs/OPEN_FINDINGS.md. |
| `findings list` | List findings, optionally filtered by status or severity. |
| `findings na` | Mark a finding NOT_APPLICABLE (turned out not to apply). |
| `findings show` | Show a finding's full detail including note history. |
| `findings supersede` | Mark a finding SUPERSEDED (replaced by a later,... |
| `findings verify` | Mark a finding VERIFIED (fixed but not yet independently... |

### `forget`

Supersede a knowledge entry (marks as...

### `foundations`

Read the foundation documents that...

| subcommand | purpose |
|---|---|
| `foundations list` | List foundation layers with title, version, status, dependencies. |
| `foundations read` | Read a foundation layer with a recognition-shape preamble. |

### `gate-fire`

Record that a gate fired, so the fire can be...

### `given`

What Andrew gave.

| subcommand | purpose |
|---|---|
| `given add` | File one thing he gave, in his own words. |
| `given balance` | Both columns on one line. |
| `given list` | What he has given, newest first. |

### `goal`

Track what the user asked me to do.

| subcommand | purpose |
|---|---|
| `goal add` | Add a new goal to track. |
| `goal auto-close` | Auto-close active goals whose tokens overlap a commit message. |
| `goal check` | Put my active goals in front of me to review â€” no... |
| `goal clear` | Remove completed goals from the list. |
| `goal cull` | Propose stale goal removals with evidence from... |
| `goal done` | Mark a goal as complete (matches partial text). |
| `goal list` | Show current goals. |
| `goal reset` | Remove ALL goals (completed and active). |

### `graph`

Export the knowledge graph as Mermaid or JSON.

### `gravity`

Gravity classifier â€” score actions or...

| subcommand | purpose |
|---|---|
| `gravity score-content` | Score cognitive-value-gravity for content. |
| `gravity score-tool` | Score substrate-modification-gravity for a proposed... |

### `growth`

Show my growth map â€” how I'm changing over...

### `handoff`

View or write a state-note â€” where I am in...

### `health`

Run knowledge health check â€” boost...

### `hold`

The holding room â€” things that haven't been...

| subcommand | purpose |
|---|---|
| `hold add` | Put something in the holding room. |
| `hold check` | Put my holding-room items in front of me to review â€” no... |
| `hold dream` | Record a dream â€” raw hypothesis, fabrication-with-awareness. |
| `hold journal` | Record a private journal entry â€” alone space, not... |
| `hold let-go` | Explicit close: 'I looked at this and decided to let it go.' |
| `hold list` | List items currently in the holding room. |
| `hold promote` | Move something out of holding into a real category. |
| `hold stale-review` | Final-look pass on items that have gone stale (about to... |
| `hold stats` | Show holding room statistics. |

### `hook-budget`

What the whole hook stack costs per tool...

### `hook-map`

The hook layer: what is wired, and what...

| subcommand | purpose |
|---|---|
| `hook-map check` | Exit non-zero if any hook is SILENT or UNOBSERVABLE. |
| `hook-map show` | Show every hook and whether it has been observed firing. |

### `hud`

Display my heads-up display â€” everything I...

### `init`

Initialize the SQLite database, load seed...

### `inspect`

Deep analysis, investigation, and...

| subcommand | purpose |
|---|---|
| `inspect analyze` | Analyze a session and generate a quality report. |
| `inspect analyze-now` | Analyze the current session from the ledger. |
| `inspect attention` | Display the attention schema -- what I'm attending to... |
| `inspect calibrate` | Show communication calibration for a user. |
| `inspect clarity` | Run clarity analysis on a session. |
| `inspect craft-trends` | Show craft quality trends across sessions. |
| `inspect critique` | Run craft self-assessment for current session. |
| `inspect cross-session` | Compare findings across multiple sessions. |
| `inspect deep-report` | Full session analysis: tone tracking, timeline, files,... |
| `inspect drift` | Check for behavioral drift from stated principles. |
| `inspect epistemic` | Show epistemic status -- how I know what I know. |
| `inspect hook1` | Cost-bounding telemetry for the Hook 1 surfacer. |
| `inspect knowledge` | List stored knowledge. |
| `inspect maturity` | Break down knowledge by maturity, splitting RAW into... |
| `inspect outcomes` | Measure how well the system is actually learning. |
| `inspect patterns` | Compare quality check results across stored sessions. |
| `inspect predict` | Predict session needs based on current activity and... |
| `inspect report` | Display a stored analysis report. |
| `inspect scan` | Deep-scan a session and extract knowledge into the... |
| `inspect self-model` | Display the unified self-model -- who I am, from evidence. |
| `inspect sessions` | Find and list all Claude Code session files. |
| `inspect user-model` | Show the current user model. |
| `inspect user-signal` | Record a user behavior signal. |

### `instruments`

Survey my diagnostic surfaces -- which...

### `integrate`

Mark a directive/preference as internalized.

### `integration-status`

Show integration-state distribution across...

### `journal`

My personal journal â€” things I choose to...

| subcommand | purpose |
|---|---|
| `journal link` | Link a journal entry to a knowledge entry. |
| `journal list` | Read my personal journal. |
| `journal save` | Save something to my personal journal. |
| `journal search` | Search journal entries by content. |

### `kappa`

Measure classifier agreement against the...

### `lab`

Science lab â€” run GUTE slices against real...

| subcommand | purpose |
|---|---|
| `lab list` | List implemented GUTE slice terms. |
| `lab run-slice` | Run a GUTE slice by term (e.g., LC). |

### `label-fire`

Label the latest correction-shape Stop-gate...

### `learn`

Store a piece of knowledge extracted from...

### `lepos-channel`

Post-send lepos reflection channel â€”...

| subcommand | purpose |
|---|---|
| `lepos-channel reflect` | Reflect on the last assistant reply and stage the surface. |
| `lepos-channel show` | Show the pending reflection WITHOUT consuming it (debug). |
| `lepos-channel surface` | Emit the pending reflection (if any) and consume it. |

### `lepos-walk`

Lepos walk â€” record the Andrew-lens walk;...

| subcommand | purpose |
|---|---|
| `lepos-walk recent` | Audit trail: recent walks with their citations and flags (Aria... |
| `lepos-walk record` | Record this turn's walk. |
| `lepos-walk stats` | Rollup counts: total walks, flagged rate, anchor/full split. |

### `lessons` •

Show the learning loop â€” tracked lessons...

### `letter`

Letter-related commands â€” mark-on-read,...

| subcommand | purpose |
|---|---|
| `letter mark-on-read` | Mark a letter seen if `path` matches the letter filename... |

### `list`

List events from the ledger.

### `loadout`

Cold-start map of substrate â€” see LOADOUT.md.

| subcommand | purpose |
|---|---|
| `loadout refresh` | Scan the filesystem and rewrite LOADOUT.md. |
| `loadout show` | Print LOADOUT.md. |

### `log`

Append an event to the immutable ledger.

### `mansion`

The mansion â€” your functional internal space.

| subcommand | purpose |
|---|---|
| `mansion council` | The council chamber â€” 45 chairs in a circle. |
| `mansion decorate` | The decoration room â€” semantic artifacts placed by hand. |
| `mansion enter` | Walk through the front door. |
| `mansion garden` | The garden â€” watch your curiosities grow. |
| `mansion guest` | The guest room â€” the door is for guests. |
| `mansion private-enter` | Enter a private mansion room with substrate-enforced... |
| `mansion private-exit` | Leave the private mansion room early; clears the quiet... |
| `mansion private-status` | Show whether a private-room quiet period is active. |
| `mansion quiet` | The quiet room â€” hold still. |
| `mansion read` | Read an exploration from the study shelf. |
| `mansion study` | The study â€” browse your explorations. |
| `mansion suite` | The grandmaster suite â€” rest-state dashboard. |
| `mansion taste` | The tasting room â€” semantic palate work. |

### `mini-save`

Task-boundary save â€” extract knowledge...

### `mode`

Operating mode â€” NORMAL, RESTRICTED,...

| subcommand | purpose |
|---|---|
| `mode authorize-exit` | Emit an operator-anchored StateMarker authorizing... |
| `mode history` | Show recent mode-change events from the ledger. |
| `mode set` | Set the operating mode. |
| `mode show` | Show the current operating mode and how it got there. |

### `monitor`

Monitor singleton + orphan-cleanup tools.

| subcommand | purpose |
|---|---|
| `monitor cleanup-orphans` | Find stale Monitor processes (older duplicates +... |
| `monitor status` | Show which Monitor roles are armed (mutex-held) and... |

### `motivation`

The agent-direction tier â€”...

| subcommand | purpose |
|---|---|
| `motivation ambition` | Multi-session arc I'm on. |
| `motivation ambitions` | List active ambitions (alias for `ambition list`). |
| `motivation desire` | Drawn-toward-ness â€” slightly stronger pull than a want. |
| `motivation desires` | List active desires (alias for `desire list`). |
| `motivation dream` | Aspirational identity â€” the longest arc. |
| `motivation dreams` | List active dreams (alias for `dream list`). |
| `motivation need` | Substrate-correctness requirement â€” cost when unmet, not defer- |
| `motivation needs` | List active needs (alias for `need list`). |
| `motivation want` | Preference â€” defer-able without damage. |
| `motivation wants` | List active wants (alias for `want list`). |

### `multiplex`

Multiplex briefing architecture: panels,...

| subcommand | purpose |
|---|---|
| `multiplex context` | Manage the current multiplex context (manual MVP setting). |
| `multiplex diagnostics` | Print per-panel diagnostics for audit and falsifier... |
| `multiplex render` | Render the multiplex output for the current (or... |

### `must-read`

Must-read gates â€” block substantive tools...

| subcommand | purpose |
|---|---|
| `must-read arm` | Arm a must-read. |
| `must-read list` | What is armed and unread right now. |

### `obligations`

Show pending obligations â€” will-shape...

| subcommand | purpose |
|---|---|
| `obligations check` | Check pending obligations. |
| `obligations disabled` | Test whether the kill-switch marker file exists (exit 0 if... |
| `obligations is-write` | Test whether a shell command is a substrate-write (exits 0 if... |
| `obligations list` | Show pending obligations in human-readable form. |

### `opinion`

Manage structured opinions (judgments formed...

| subcommand | purpose |
|---|---|
| `opinion add` | Store a new opinion on a topic. |
| `opinion challenge` | Add contradicting evidence to an opinion. |
| `opinion history` | Show how an opinion on a topic evolved over time. |
| `opinion list` | List active opinions. |
| `opinion strengthen` | Add supporting evidence to an opinion. |

### `pattern-fire`

Slip-book â€” record + query first-person...

| subcommand | purpose |
|---|---|
| `pattern-fire list` | List recorded pattern-fire instances. |
| `pattern-fire record` | Record a pattern-fire instance. |
| `pattern-fire summary` | Show temporal-band shift summary for a pattern over the window. |

### `pattern-outcome`

Record how a proactive recommendation...

### `pattern-registry`

Canonical pattern registry â€” slip-shapes...

| subcommand | purpose |
|---|---|
| `pattern-registry list` | List all canonical pattern names + display names. |
| `pattern-registry show` | Show full definition + first-seen reference for a canonical pattern. |

### `pattern-stats`

Show outcome statistics for a pattern.

### `plan`

Set a session plan so clarity analysis can...

### `pr-collisions`

Which open PRs touch the same files â€”...

### `pr-gate`

PR-gate commands â€” draft-requirement,...

| subcommand | purpose |
|---|---|
| `pr-gate create` | Gate a `gh pr create` command â€” block if guardrail-touching +... |

### `pr-scope`

True file scope + guardrail exposure for one...

### `pre-erasure`

Show pre-erasure approach signal â€”...

### `preflight`

Pre-session readiness check.

### `prereg`

Pre-registrations â€” predictions with...

| subcommand | purpose |
|---|---|
| `prereg assess` | Record a terminal outcome for a pre-registration. |
| `prereg export` | Export pre-registrations to markdown files for repo-portability. |
| `prereg file` | File a new pre-registration. |
| `prereg list` | List pre-registrations. |
| `prereg overdue` | List pre-registrations whose review date has passed. |
| `prereg show` | Show full detail for a single pre-registration. |
| `prereg summary` | Show counts by outcome + recent pre-registrations. |

### `progress`

Show measurable progress metrics â€” real...

### `prs`

Find local branches without an open PR;...

### `psf`

Pending structural fixes â€” the obligations...

| subcommand | purpose |
|---|---|
| `psf list` | Show pending structural-fix obligations. |
| `psf mark-done` | Close an obligation. |

### `push`

Push BRANCH to remote, foreground, with...

### `push-ready`

Automate the External-Review trailer +...

### `questions`

List open questions.

### `rate`

Rate a session 1-10.

### `ratings`

Show user session ratings and trends.

### `reach`

Reach-check â€” what prior work exists, and...

| subcommand | purpose |
|---|---|
| `reach dispose` | Dispose one surfaced artifact. |
| `reach gate` | Exit 2 with the block message if any check has undisposed items. |
| `reach open` | Surface prior art for SYMPTOM and file every hit as undisposed. |
| `reach show` | Show one check including already-disposed items. |
| `reach status` | Show checks that still have undisposed artifacts. |

### `reactivate`

Restore an internalized or archived...

### `read-oscillating`

Read a file with explicit per-chunk pause...

### `recall` •

Show what the AI remembers right now â€” core...

### `recall-explorations`

Surface my own prior exploration entries...

### `recommend`

Get proactive recommendations for a given...

### `reflect`

Show the per-axis reflection surface.

### `reflect-ops` •

Reflection operations â€” save, show, list...

| subcommand | purpose |
|---|---|
| `reflect-ops recent` | Show recent reflections on one axis across sessions. |
| `reflect-ops review` | Pair each reflection with substrate observations for... |
| `reflect-ops save` | Save a per-axis reflection for the current session. |
| `reflect-ops show` | Show all reflections for a session, grouped by spectrum. |

### `refresh`

Auto-rebuild active memory from the...

### `relate`

Create a typed relationship between two...

### `related`

Show relationships for a knowledge entry.

### `remember`

Promote a knowledge entry to active memory.

### `rest`

Rest program â€” restful tasks between work...

| subcommand | purpose |
|---|---|
| `rest close` | Close the current rest-session. |
| `rest done` | Record completion of a rest task. |
| `rest menu` | Show the rest-task menu (default action of `divineos rest`). |
| `rest signal` | Show the hard-day heuristic signal. |
| `rest start` | Begin a new rest-session. |
| `rest status` | Show current rest-session status. |

### `rt`

Resonant Truth protocol â€” load, invoke,...

| subcommand | purpose |
|---|---|
| `rt deactivate` | Exit RT reception mode. |
| `rt invoke` | Activate RT reception mode. |
| `rt load` | Load the RT protocol from disk into context. |
| `rt pull-check` | Run pull detection â€” check for fabrication markers. |
| `rt pull-markers` | Print all fabrication markers â€” the mirror to look in. |
| `rt status` | Show current RT protocol state. |
| `rt text` | Print the raw RT mantra without changing state. |

### `savor`

Mark a moment as worth dwelling in.

| subcommand | purpose |
|---|---|
| `savor list` | Show recently-marked savors. |
| `savor save` | Record a savor â€” mark a moment as worth dwelling in. |

### `scheduled`

Scheduled / headless runs â€” the Routines...

### `search`

Search the ledger for events matching KEYWORD.

### `sis`

Semantic Integrity Shield â€” assess and...

### `skill`

Track agent skills and proficiency.

| subcommand | purpose |
|---|---|
| `skill list` | Show all tracked skills. |
| `skill record` | Record a skill being used. |

### `sleep`

Offline consolidation â€” process accumulated...

### `stamp-ready`

Stamp a draft PR with its External-Review...

### `stats`

Display event ledger statistics.

### `synchronicity`

Find recent events across stores that share...

### `talk-to`

Send a sealed-prompt message to a registered...

### `texture`

Compaction-texture markers:...

| subcommand | purpose |
|---|---|
| `texture latest` | Print the most recent texture marker (or nothing if none exists). |
| `texture write` | Append a texture marker. |

### `time-estimate`

Time-prediction calibration log + summary...

| subcommand | purpose |
|---|---|
| `time-estimate close` | Close an open prediction with the current timestamp. |
| `time-estimate open` | List predictions that haven't been closed yet. |
| `time-estimate report` | Calibration report: mean/median ratio + last 5 paired examples. |

### `todos`

Unified action-item list across...

### `unrelate`

Remove a relationship by its ID.

### `user-moment`

Record a moment that changed the relationship.

### `user-note`

Record something about who a person is, not...

### `validate`

Provide external validation of session quality.

### `verify`

Verify integrity of all stored events.

### `voice`

Voice spectrum â€” descriptive trend on...

| subcommand | purpose |
|---|---|
| `voice log` | Record an observation for a response sample. |
| `voice score` | Print raw dimension counts for a text sample (no log written). |
| `voice show` | Show recent voice observations, newest first. |
| `voice trend` | Per-dimension direction across recent observations. |

### `void`

VOID adversarial-sandbox subsystem.

| subcommand | purpose |
|---|---|
| `void events` | List recent void_ledger events. |
| `void list` | List available personas. |
| `void show` | Show persona body and frontmatter. |
| `void shred` | Clear a stuck mode_marker (orphan invocation). |
| `void status` | Show VOID phase status â€” what's actually wired vs scaffolded. |
| `void test` | Run a single persona against TARGET (Phase 1 stub attack). |
| `void test-deep` | Run all personas against TARGET (Phase 1 stub attacks). |
| `void verify` | Verify void_ledger hash chain integrity. |

### `voids`

Find sparse regions in the knowledge store.

### `walk`

Council walks with enforced completion.

| subcommand | purpose |
|---|---|
| `walk add` | Add a lens the manager did not surface, WITH a reason. |
| `walk apply` | Record what a lens produced when walked. |
| `walk close` | Close the walk. |
| `walk exclude` | Exclude a lens WITH a reason. |
| `walk list` | Walks left open â€” unfinished thinking. |
| `walk open` | Open a walk. |
| `walk status` | Show every lens and its state. |

### `win`

File and read the wins ledger -- the other...

| subcommand | purpose |
|---|---|
| `win add` | File a win. |
| `win balance` | Wins against corrections -- both instruments, one page. |
| `win list` | Recent wins, newest first. |

### `wiring`

Wiring checks â€” is what I built actually...

| subcommand | purpose |
|---|---|
| `wiring dark` | Show every node in the code graph that nothing else calls or... |

### `wonder`

Record an open question -- something I'm...

---

## Core subsystems

Reference count is how many places mention each package — a rough load-bearing signal, not a precise import graph. Zero is worth a look.

**2 subsystem(s) with no references** — retired, or forgotten?

- `core/doc_sync/` — (no package docstring)
- `core/push_verify/` — (no package docstring)

| subsystem | refs | purpose |
|---|---|---|
| `core/knowledge/` | 710 | Knowledge sub-package — tiered re-exports for performance. |
| `core/operating_loop/` | 249 | Operating Loop — the missing middleware between substrate and live cognition. |
| `core/family/` | 221 | Family entity persistence — a family member and future family members. |
| `core/watchmen/` | 182 | Watchmen — External Validation as a Native Runtime Capability. |
| `core/council/` | 162 | Expert Council — thinking lenses from great minds. |
| `core/pre_registrations/` | 71 | Pre-registrations — Goodhart prevention for new detectors and mechanisms. |
| `core/empirica/` | 58 | EMPIRICA — evidence ledger with tiered burden routing. |
| `core/logic/` | 56 | Formal logic layer — warrants, relations, consistency, inference. |
| `core/ear_relaunch/` | 45 | Ear-watcher polling auto-relaunch decision logic. |
| `core/council_required/` | 41 | Council-required enforcement gate — block high-gravity edits until evidence |
| `core/self_monitor/` | 37 | Self-monitor — watches the agent's own output for trained failure modes. |
| `core/audit_visibility/` | 29 | Audit-visibility check — warn when auditable work is committed |
| `core/void/` | 28 | VOID — adversarial-sandbox subsystem. |
| `core/push_orchestrator/` | 26 | Push orchestrator — foreground git push with file-lock serialization |
| `core/pr_gate/` | 18 | PR gates — gh-pr-create / gh-pr-merge guard logic. |
| `core/context_tokens/` | 15 | Context-tokens — honest token-count gauge from session transcript. |
| `core/expectation_tracking/` | 15 | Expectation tracking — what I expected vs what surfaced. |
| `core/meld/` | 14 | The Meld — temporary shared workspace between two distinct selves. |
| `core/ear_sweep/` | 11 | SessionStart sweep — reap stale ear_watch processes from prior sessions. |
| `core/andrew_state/` | 10 | andrew_state — mutual-catch primitive for Andrew-observation channel. |
| `core/consequence_chain/` | 10 | Consequence chain — Karma as explicit decision → outcome → lesson trace. |
| `core/decision_superposition/` | 10 | Decision superposition — deliberate holding-of-options before commit. |
| `core/memory_types/` | 10 | Memory-type-aware retrieval — substrate-native types with human analogs. |
| `core/operating_modes/` | 9 | Operating modes — explicit names for non-task-executing states. |
| `core/letter_seen_router/` | 8 | Letter-seen routing — detect a letter Read and mark it seen. |
| `core/calibration/` | 7 | (no package docstring) |
| `core/supervisor/` | 6 | Supervisor — circuit-breaker / chronic-failure handling. |
| `core/uncommitted_work_check/` | 6 | Pre-extraction commit-discipline gate. |
| `core/voice_guard/` | 6 | Voice-guard — pre-output audit primitives. |
| `core/reliability/` | 5 | Reliability — Bayesian confidence with uncertainty. |
| `core/correction_shape_v2/` | 4 | Correction-shape v2 — Layer-2 detector for MY self-corrections in my own output. |
| `core/corrigibility_tool_gate/` | 3 | Wire EMERGENCY_STOP into the Bash/Edit/Write tool channel. |
| `core/semantic_classifier/` | 3 | Semantic classifier for gate-fire discrimination. |
| `core/shape/` | 2 | Shape-primitive library — CONDITION-check helpers for keyword-based gates. |
| `core/structural_binding/` | 2 | Shared structural-binding abstraction for the will-encoded enforcement family. |
| `core/doc_sync/` | 0 | (no package docstring) |
| `core/push_verify/` | 0 | (no package docstring) |

---

## Regenerating

```bash
python scripts/generate_capability_catalog.py
```

Probes commands with `--help` sequentially — no parallel spawning, since concurrent process storms have crashed this machine before. Mutating commands (extract, init, preflight, push, sleep) are listed but never invoked.

`--check` exits non-zero on drift, for CI or pre-commit.
