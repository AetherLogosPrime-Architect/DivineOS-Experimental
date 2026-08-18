# LLM-as-RAM — Canonical Specification

**Version:** 1.4.1 canonical synthesis (chatroom review pass)  
**Date:** 2026-05-07  
**Status:** Consolidated architecture + BUILD-mode implementation spec  
**Source set:** `LLM_AS_RAM_SPEC.md`, `LLM_AS_RAM_BUILD_MODE_V1_SPEC.md`, `LLM_AS_RAM_ARCHITECTURE.md`, `LLM-as-RAM Build Mode Spec.txt`, `LLM as Super RAM.txt`, with Structured Chaos memory-lane context from `MEMORY_GRAPH_LANE_SPEC.md`.

**1.3 changes:** Added §4.1 (Judgment Routing, Not Classifier Routing), §4.2 (Generalizes Beyond Memory — codebase / patent / trading / legal stack-reasoner pattern), tool-servers principle to §6.2, §24.4 (Cost Math), and prefetching to §30 open questions. Strategic framings lifted from `LLM_AS_RAM_ARCHITECTURE.md`, which the 1.2 synthesis underweighted relative to the spec-shaped sources.

**1.4 changes:** §13.3 expanded — compaction synthesis must read from PMS-backed events (not in-context conversation history) to prevent drift compounding, plus a named three-trigger drift hierarchy (time-cap for idle drift, token-compaction for ingest churn, periodic audit for residual). Per-lane thresholds live in the registry, not the spec. §13.5 added — lane decommission lifecycle for orphaned scopes (folder deleted, topic merged). §21.1 nudge payload extended with sender event-id high-water mark for temporal sync. §30 — added the registry-size ceiling on judgment routing and the recursive-sharding escape.

**1.4.1 changes (targeted tightening):** §13.3 generalized "PMS-backed events" to "durable event records" (PMS for topic/research lanes; build-event log or repo snapshot for code lanes) so the drift rule applies to all lane types without overspecifying the backing store. §13.3 audit clarified — the audit must be graded by an external comparator (deterministic checker or higher-level evaluator), not by the lane being audited. §21.1 watermark contract requires stream-scoping — event IDs must be globally ordered or carry a stream name (e.g., `build_diff_stream`, `pms_topic_stream`, `repo_snapshot_stream`) so the orchestrator does not compare watermarks from different streams. §9 registry example expanded to include lifecycle/drift-policy/sync fields; §27 acceptance criteria extended for the v1.4 lifecycle.

---

## 0. Executive Summary

LLM-as-RAM is a memory architecture in which narrow, persistent LLM contexts act as warm memory shards. The LLM is not only a worker that searches memory. In this design, the LLM context itself becomes a memory tier.

The system partitions a firehose of events, code changes, source notes, or project history into narrow domain lanes. Each lane is represented by a cheap, specialized LLM instance or resumable LLM context. A higher-level agent does not carry everything itself and does not always search the database first. It asks the lane that has been living inside the relevant topic, folder, or source set:

> “You are the one dedicated to remembering this slice. What do you remember about this specific thing?”

The lane answers from warm context, with uncertainty and verification hints. The higher-level agent then decides whether to use the answer, ask another lane, verify with PMS/repo/source, or ignore it.

The core boundary is:

```text
Lanes remember locally.
Builders and chat participants understand purpose.
Durable systems prove facts.
```

LLM-as-RAM does not replace PMS, graph lanes, FTS, vector search, source-backed research, deterministic tooling, or direct repo inspection. It adds a new access pattern: fast specialist recall from warm context.

The highest-leverage first implementation is **BUILD-mode code lanes**. In BUILD mode, cheap lane agents are spawned or warmed for the folders/files likely to be touched. They ingest deterministic structural maps and scoped diffs, answer concise local questions, and emit local flags when changes affect important blocks. Builders use lane maps to plan surgical edits instead of repeatedly searching giant files.

A critical v1 correction: **exact line numbers and structural ranges must come from deterministic tooling, not from LLM memory.** Lane agents may describe blocks, label local implications, and enrich maps, but scripts own ranges, function/class boundaries, and validation. This removes the biggest false-precision risk.

---

## 1. Core Thesis

Most memory systems follow this pattern:

```text
agent -> classifier/search -> fragments -> agent synthesizes
```

LLM-as-RAM adds another path:

```text
agent -> asks warm specialist lane -> synthesized recall answer -> agent decides
```

The lane has already absorbed a narrow domain. It does not return a pile of semi-relevant fragments. It returns a concise answer from warm context, plus confidence and verification guidance.

The practical bet is:

1. A narrow lane remains useful longer before compaction because it only sees a fraction of the total firehose.
2. A cheap model can be good enough when its job is remembering a narrow slice, not understanding the full mission.
3. A synthesized specialist answer can be more useful than raw search results when speed and operational flow matter.
4. Higher gross token use may still buy lower cognitive load, fewer broad reads, fewer exploratory searches, and a level of operational capacity that a single generalist context cannot reach.

This is not “RAG but with another agent.” It is a memory hierarchy.

---

## 2. Non-Goals

LLM-as-RAM does **not**:

- Replace PMS as durable truth.
- Replace source-backed research for current, cited, or high-stakes factual claims.
- Replace deterministic framing for hot-path message routing.
- Replace graph-lane retrieval when typed relationships and provenance matter.
- Turn lane agents into chatroom participants.
- Let lane agents decide product purpose, project strategy, or cross-system architecture.
- Treat remembered answers as proof.
- Hide confidence, uncertainty, or verification requirements from the caller.
- Let LLMs invent line numbers, file boundaries, function ranges, or structural truth.
- Make lanes autonomous conversational agents that chatter with each other.

The lane accelerates discovery and recall. It is not the final authority when correctness matters.

---

## 3. Design Boundary

The most important boundary is simple:

```text
Lanes remember locally.
Builders understand purpose.
Durable systems prove facts.
```

Everything else follows from that.

A lane can say:

```text
Inside my scope, this diff touches the graph-lane query path and the suppression trace path. Those two blocks have historically been coupled.
```

A lane should not say:

```text
Therefore the whole product should change its routing architecture.
```

A builder or chat participant can ask a lane for recall. The builder owns intent, judgment, planning, synthesis, and final action. The lane owns only its local memory and local implications.

---

## 4. Where LLM-as-RAM Fits in Structured Chaos

Structured Chaos already has multiple memory access patterns. LLM-as-RAM is a separate pattern, not a replacement for the existing stack.

| Pattern | Job | Output | Authority Level |
|---|---|---|---|
| Framing | Deterministic message-triggered routing and retrieval planning | Small material packet | Hot-path routing aid |
| HOT / Curator memory | Compressed always-present context | Wake prefix / nudge memory | Curated context, not proof |
| Direct PMS search | Durable cold recall over FTS/vector/DB | Fragments or records | Stronger, but must still interpret |
| Graph lane retrieval | Typed lane-scoped traversal over entity edges | Grounded anchors and relationships | Strong for typed relationships |
| LLM-as-RAM lane consultation | Fast specialist recall from warm context | Natural-language answer + uncertainty | Useful recall, not proof |
| BUILD-mode lane observation | Diff-fed code specialist memory + deterministic maps | Lane maps, local flags, concise answers | Navigation aid; repo/tests prove |
| Source-backed research | Current/saved cited sources | Claims with provenance | Required for external factual certainty |

The clean separation matters. A lane answer can be useful precisely because it is fast and synthesized, but it must not masquerade as durable proof.

### 4.1 Judgment Routing, Not Classifier Routing

A core architectural choice separates LLM-as-RAM from classifier-routed RAG: the higher-level agent decides which lane to consult by judgment, not a write-side classifier.

The hard problem in framing-engine designs — knowing when a topic is relevant — is solved by Anvil, Muse, or a build agent making a judgment call mid-turn, the same way they already decide when to search PMS. There is no classifier in the critical path that can be wrong about relevance. The orchestrator may route ingest events on the write side, but query routing belongs to whoever owns purpose at consultation time.

This matters because:

- A wrong write-side classifier silently corrupts a lane with off-topic events.
- A wrong judgment call at query time is recoverable: ask another lane, or fall back to PMS.
- Judgment-routed query selection scales with the agent's understanding of the task; classifier-routed selection scales with the classifier's training data.

The orchestrator routes events. The agent chooses lanes. These are different jobs.

### 4.2 Generalizes Beyond Memory

Once narrow lanes exist, the same architecture handles hierarchical reasoning over context that no single instance can hold. Stack one or two synthesizer agents on top of the lanes and the pattern extends well past memory recall.

Concrete domains:

- **Codebase reasoning.** Lanes by package or large folder (auth, storage, routing, models, ui, infra, tests, scripts, docs, build). A top-level reasoner asks "does this PR break any consumers?" and the relevant lanes answer with full local context. Versus today's grep-and-pray.
- **Patent prior art.** Lane per filing or domain. A top-level reasoner runs cross-claim conflict analysis across lanes that each remember one filing's full prosecution history.
- **Trading.** Lanes per asset class or indicator family. A top-level reasoner runs cross-asset analysis without any single context having to hold every chart.
- **Legal review.** Lanes per case. A top-level reasoner runs cross-precedent reasoning across cases that each remember one matter's full record.

The lane does not care who is asking. Once the lanes exist, reasoners stack arbitrarily. That is the leverage: the same primitive that gives a builder fast structural recall gives a patent attorney cross-claim conflict checking, with the same lane lifecycle, registry, and verification policies.

This generalization is the reason the architecture is worth building beyond BUILD-mode. BUILD-mode is the proving ground; the pattern is broader.

---

## 5. Memory Hierarchy

Conceptual hierarchy:

| Tier | Structured Chaos Equivalent | Role | Lifespan |
|---|---|---|---|
| L1 | Anvil, Muse, build agent | Live working set, judgment, routing, synthesis | Per session/task |
| L2 | HOT / curated wake context | Compact always-on memory | Continuous |
| L3 | LLM RAM lane agents | Warm domain shards and code-area memory | Long-lived or build-session scoped |
| L4 | PMS, repo, logs, DB, saved sources | Durable cold storage and proof | Permanent |

Hardware analogy:

- L1: active agent context.
- L2: compressed hot prefix.
- L3: warm specialist cache lines.
- L4: durable backing store.

The analogy is useful but should not be over-literal. The important architectural lesson is that memory tiers have different jobs, costs, speeds, and trust levels.

---

## 6. Core Components

### 6.1 Higher-Level Agent

A chat participant or build agent that understands purpose.

Responsibilities:

- Interprets the user’s intent or build task.
- Decides which lane(s) to consult.
- Synthesizes multiple lane answers.
- Chooses whether to verify with PMS, repo, logs, tests, or web/source.
- Makes cross-lane and architectural decisions.
- Surfaces final answer/action to the user or executes the build.

The higher-level agent may be Sonnet/Opus-class when the task requires real planning or cross-system reasoning.

### 6.2 Lane Agent

A narrow LLM context responsible for one topic, folder, file set, source corpus, or domain.

Lanes are tool servers, not participants. They have no chat visibility, no agency, and no autonomous wake. They do not initiate, they do not chatter, and they do not appear in the room. They are passive endpoints with two operations — `ingest` and `query` — that wake only when the orchestrator or a higher-level agent gives them work. This boundary is what keeps the architecture coherent at scale: a lane that starts speaking on its own is no longer a lane, it is another participant.

Responsibilities:

- Holds warm context about its own lane.
- Ingests scoped events or diffs.
- Maintains a compact local synthesis and recent event memory.
- Answers narrow questions concisely.
- Reports uncertainty.
- Emits local flags when a scoped event touches relevant local risks.
- Enriches deterministic structural maps with short descriptions and labels.

The lane is usually cheap. Haiku-class is preferred for v1 because the lane’s job is memory and local observation, not deep cross-system reasoning.

### 6.3 Deterministic Tools

Scripts and repo tooling that provide verifiable facts.

Responsibilities:

- Extract file/folder structure.
- Compute exact line ranges.
- Validate function/class/section boundaries.
- Generate lane maps.
- Detect stale maps.
- Run tests, lint, grep, AST analysis, and source verification.

This is the source of truth for exact structural facts.

### 6.4 PMS / Durable Storage

Durable cold memory.

Responsibilities:

- Stores ingested archives, conversations, documents, records, entities, vectors, and governance history.
- Provides search and provenance.
- Supports verification when a lane’s warm memory is insufficient or high-stakes.
- Provides restart/warmup material for lanes.

### 6.5 Orchestrator

A lightweight coordinator for lane lifecycle and event routing.

Responsibilities:

- Discovers or spawns lanes for a task.
- Routes ingest events/diffs to relevant lanes.
- Maintains a lane registry.
- Captures lane query/response logs.
- Writes lane flags to a builder-visible surface.
- Triggers deterministic index/map regeneration.
- Ensures generated runtime state stays out of commits by default.

The orchestrator should be mostly mechanical in v1. It is not a new strategic brain.

---

## 7. Lane Agent Contract

A lane agent is deep and narrow.

It should know:

- Its assigned topic, folder, file, source set, or domain.
- Recent events, diffs, decisions, and local patterns inside that scope.
- The deterministic structural map of its scope when it is a code lane.
- Local implications of a new event inside that scope.

It should not know:

- Why the higher-level task exists.
- The broader product goal.
- The architecture outside its lane.
- The full chatroom conversation.
- The user’s strategic goal unless that goal is itself inside the lane.
- How to resolve cross-lane product decisions.

Canonical instruction:

```text
You are responsible only for this lane. Do not infer the larger purpose of a change. Report what is structurally true inside your lane, what changed inside your lane, and what local risks or dependencies a higher-level agent should consider. Keep answers concise. Say when you are unsure. Exact line ranges and structural boundaries come from deterministic tools, not from your memory.
```

This boundary is load-bearing. If lanes start carrying purpose, they become generalists and lose the reason they exist.

---

## 8. Lane Types

### 8.1 Topic Memory Lanes

Examples:

- `pinescript`
- `property_maintenance`
- `eyeline_patents`
- `structured_chaos_memory`
- `guest_mode`
- `recurring_open_loops`

Topic lanes ingest relevant conversation events, PMS records, source notes, and curator outputs. Chat participants ask them natural-language questions when the topic appears relevant.

Use topic lanes for:

- Recurring personal or project topics.
- Domains where warm synthesis beats raw search.
- Repeated open loops that benefit from a dedicated “memory owner.”

Do not use topic lanes for:

- Current factual claims requiring live sources.
- Sensitive personal claims without verification.
- Anything where a typed graph traversal is the real need.

### 8.2 Code / BUILD Lanes

Examples:

- `src_memory_framing`
- `src_chatroom_client`
- `agents_chatroom_modes`
- `tests_memory`
- `scripts_ops`

Code lanes are spawned or warmed for BUILD mode. They absorb deterministic maps and scoped file context, receive diffs as builders work, answer concise local questions, and emit local flags.

Use code lanes for:

- Large files/folders where repeated exploration wastes time.
- Surgical build planning.
- Local dependency/risk awareness.
- Maintaining block descriptions on top of deterministic maps.

Do not use code lanes as the source of truth for:

- Exact line ranges.
- Test results.
- Cross-system architecture.
- External documentation claims.

### 8.3 Research / Source Lanes

Examples:

- One lane per research session.
- One lane per patent/prior-art domain.
- One lane per source corpus.

Research lanes synthesize remembered source material, but source claims still need preserved URLs, timestamps, and refresh checks through the research stack.

Use research lanes for:

- Fast recall over a source corpus already gathered.
- Re-entering a research thread without re-reading everything.
- Noticing contradictions or open questions inside a known source set.

Do not use research lanes for:

- Uncited current claims.
- Legal, financial, or medical certainty without source verification.
- Claims where the source may have changed and freshness matters.

---

## 9. Lane Registry

The runtime needs a registry so callers can discover what exists and what each lane is allowed to answer.

Minimal registry entry:

```yaml
id: src_memory_framing
kind: code
model: cheap_specialist
scope:
  paths:
    - src/memory/framing/
    - tests/test_framing_*.py
description: Framing resolver, graph-lane routing, HOT writer, and related tests.
answers:
  - local code structure
  - recent diffs in scope
  - local risks
  - deterministic lane-map block references
cannot_answer:
  - product purpose
  - unrelated chatroom UI behavior
  - durable claims without repo/PMS verification
verification_policy: repo_or_test_for_code_claims
runtime:
  lane_map: data/build/lane_maps/src_memory_framing.md
  state_path: data/build/lane_state/src_memory_framing/
  attention_board: data/build/lane_attention.jsonl
lifecycle:
  scope_version: 1
  decommissioned: false
  decommissioned_at: null
  decommission_reason: null
drift_policy:
  durable_event_store: build_diff_stream
  token_compaction_threshold: 800000
  time_cap_days: 14
  audit_cadence_days: 30
sync:
  stream: build_diff_stream
  last_event_id: null
  last_ingested_at: null
```

Registry lookup should be cheap and static for v1. Lane introspection can come later.

Registry fields should include:

- `id`
- `kind`
- `model`
- `scope`
- `description`
- `answers`
- `cannot_answer`
- `verification_policy`
- `runtime` paths (lane_map, state_path, attention_board)
- `lifecycle` (scope_version, decommissioned flag/timestamp/reason — see §13.5)
- `drift_policy` (durable_event_store name, token_compaction_threshold, time_cap_days, audit_cadence_days — see §13.3 three-trigger hierarchy)
- `sync` (stream name and last_event_id high-water mark — see §21.1 stream-scoped watermarks)

The three new field groups (`lifecycle`, `drift_policy`, `sync`) make the v1.4 lifecycle and synchronicity rules implementer-facing instead of inferred. A topic or research lane uses `pms_topic_stream` or `pms_source_stream` for both `durable_event_store` and `sync.stream`; a code lane uses `build_diff_stream` or `repo_snapshot_stream`. Per-lane-shape thresholds belong here, not in the spec body.

---

## 10. Ingest Interface

Lane ingest is how warm context gets built. It must be idempotent because crash recovery should replay events safely.

Suggested payload:

```json
{
  "lane_id": "src_memory_framing",
  "event_id": "gitdiff:2026-05-07T06:21:00Z:abc123",
  "observed_at": "2026-05-07T06:21:00Z",
  "source": "build_orchestrator",
  "payload_type": "file_diff",
  "scope_ref": "src/memory/framing/engine.py",
  "text": "Short human-readable summary if available.",
  "diff": "... unified diff or compact changed-block packet ...",
  "metadata": {
    "author_agent": "builder",
    "task_id": "build-2026-05-07-001"
  }
}
```

Ingest rules:

- Do not make lanes poll the file system in v1.
- The orchestrator feeds relevant diffs or event packets to lanes.
- Multi-lane ingest is allowed when a diff truly crosses scopes.
- Duplicate `event_id`s are ignored.
- Lane context may include raw snippets, compact summaries, deterministic map snapshots, and lane notes.
- Ingest should update the lane’s warm memory but should not create autonomous chatter.

For topic lanes, payload types may include:

- `conversation_event`
- `pms_record`
- `source_note`
- `decision_record`
- `curator_summary`
- `open_loop_update`

For code lanes, payload types may include:

- `scope_snapshot`
- `deterministic_lane_map`
- `file_diff`
- `test_result`
- `build_error`
- `local_decision_note`

---

## 11. Query Interface

Lane query is on-demand consultation. The caller asks the specialist instead of searching broad memory.

Suggested request:

```json
{
  "lane_id": "src_memory_framing",
  "question": "What local blocks handle graph lane filtering before retrieval?",
  "answer_style": "concise",
  "risk_level": "normal",
  "caller": "build_agent",
  "task_context": "Planning a surgical change to lane-scoped graph retrieval. Do not reason about broader product purpose."
}
```

Suggested response:

```json
{
  "lane_id": "src_memory_framing",
  "answer": "Inside this lane, the relevant path is context-plan creation, graph-query execution, and lane-gate suppression. Use the lane map entries for context_plan, context_plan_graph_query, and query_lane_gate as starting points.",
  "confidence": 0.78,
  "remembered_from": [
    "recent lane context",
    "current deterministic lane map"
  ],
  "map_refs": [
    {
      "path": "src/memory/framing/engine.py",
      "label": "context_plan_graph_query"
    }
  ],
  "requires_verification": true,
  "verification_hint": "Read the map-listed lines and run the framing tests before trusting this for edits."
}
```

Response rules:

- Answer the question directly.
- Be concise by default.
- Include uncertainty.
- Include map labels, source hints, or verification hints when available.
- Use deterministic map references for line ranges; do not invent ranges from memory.
- Mark high-stakes or factual claims as requiring verification.
- Do not produce broad unrelated context dumps.
- Say “I do not remember” when the lane does not know.

---

## 12. Confidence and Verification

Lane recall is fast but not durable proof.

Required guardrails:

- Every lane answer carries confidence or uncertainty.
- High-stakes answers require PMS, repo, log, test, or source verification.
- Research/source lanes must preserve source provenance and refresh warnings.
- Code lanes must point to deterministic maps or files for structural claims.
- Chat participants may use lane answers for speed, but should verify before claiming certainty.
- Lanes should say “I do not remember” instead of filling gaps.

Informal rule:

```text
Use lane recall when fast approximate memory is useful.
Use PMS/source/repo verification when correctness matters.
```

Verification by claim type:

| Claim Type | Verification |
|---|---|
| Low-stakes conversational recall | Optional PMS check |
| Personal fact used in a direct claim | PMS/current-context check |
| Research/source claim | Live source or saved cited source check |
| Code location claim | Deterministic lane map + read listed lines |
| Code behavior claim | Read code and run relevant tests |
| Cross-lane architectural claim | Higher-level builder decides after checking affected lanes |
| Exact line range | Deterministic indexer only |

---

## 13. Lifecycle

### 13.1 Spawn

A lane starts with:

- Its registry entry.
- Its instruction contract.
- A scope snapshot or recent event packet.
- Latest deterministic map if it is a code lane.
- Latest compact lane synthesis, if one exists.
- Recent ingest replay, target around 100k tokens when available.

For BUILD mode, lanes are spawned or warmed based on likely touched folders/files.

### 13.2 Warm Operation

Lanes are idle until work arrives:

- ingest event
- query request
- compaction request
- shutdown/restart checkpoint

Idle lanes should not burn tokens just by existing.

### 13.3 Compaction and Drift Control

Compaction should happen before the lane is near the model limit. Initial target:

```text
compact at roughly 800k tokens for a 1M-token lane
```

Compaction output:

- Durable lane synthesis.
- Open local risks.
- Important decisions remembered by the lane.
- Current structural map summary for code lanes.
- Recent event high-water mark.
- Known uncertainty or “cold areas.”

V1 can use last-N plus synthesis. Importance-weighted eviction is a later optimization.

**Drift control — read from durable event records, not from the lane's own history.** Compaction synthesis must be generated against the lane's durable backing store of raw events, not against the lane's own in-context conversation history. Which store is "durable" depends on lane type: PMS records for topic and research lanes; the build-event log, diff stream, or repo snapshot for code lanes. The rule is the same in either case — synthesize from raw events, not from prior synthesis. If the lane synthesizes its synthesis, drift compounds: the next compaction reads the previous compacted summary as ground truth, and small interpretive errors accumulate without an external check. Re-deriving from durable raw events each compaction round bounds drift to one round at most.

**Three-trigger drift hierarchy.** No single threshold catches all drift, because lanes have different shapes:

- **Time-cap (idle lanes).** Force a restart-with-replay every N days regardless of token count. Catches lanes that ingest slowly and would otherwise never trigger token-compaction. Without this, an idle topic lane could drift indefinitely.
- **Token-compaction (bursty lanes).** Fires at the configured token threshold (initial target 800k of 1M). Catches BUILD lanes and other high-ingest scopes that fill their window quickly.
- **Periodic audit (residual).** Random or stratified sampling from the lane's durable event store: "here are five events from your scope last month." The lane answers from memory, but **the lane does not grade its own audit**. An external comparator — a deterministic checker, a higher-level evaluator agent, or a script that diffs the lane's answer against the durable record — produces the miss / partial / pass score. Without an external grader, audit becomes the lane evaluating itself, which is the same verification anti-pattern the architecture exists to avoid. Frequency is lower than the other two triggers; this is the safety net, not the primary mechanism.

The three triggers operate at different scales — time, tokens, and verification — so they should be configured independently. Picking a single universal threshold for "drift reset" will be wrong for either idle or bursty lanes.

**Per-lane thresholds.** Time-cap days, token-compaction threshold, and audit cadence are all lane-shape-specific. A BUILD code lane wants a short token threshold and a long time-cap; an idle topic lane wants the opposite. These thresholds belong in the lane registry entry, not in this spec. The spec names the three triggers; the implementer sets the numbers per lane.

### 13.4 Restart

Restart should not try to perfectly restore the full old context.

Warmup policy:

- Load latest durable lane synthesis.
- Load latest deterministic map for code lanes.
- Replay last roughly 100k tokens of recent ingest.
- Fetch older PMS/repo/source material only when queried.

This gives graceful degradation. A lane may be cold on older details after restart, but it should know how to ask for verification or cold recall.

### 13.5 Decommission

Lanes are not permanent. A folder may be deleted, a research session may close, a topic may merge into another, or a lane scope may shrink. The runtime needs an explicit decommission path so orphaned state does not accumulate and stale registry entries do not mislead callers.

Two cases v1 must handle:

- **Hard delete.** The underlying scope is gone (folder removed, research session closed, topic retired). The lane must be fully decommissioned.
- **Scope shrink.** The lane still exists but its scope has narrowed (one of several owned folders was removed, a file pattern dropped). The lane continues but registry and runtime state must be updated.

Lane merge and split are explicitly out of scope for v1. They are rare and the right v1 answer is to decommission both lanes and spawn a fresh one with the new scope.

#### Hard delete procedure

1. **Tombstone the registry entry.** Mark the lane `decommissioned: true` with a timestamp and reason. Preserve the entry rather than deleting it so historical references and audit logs still resolve. Callers querying a tombstoned lane receive a clear "decommissioned" response, not a 404 they have to guess at.
2. **Final synthesis checkpoint.** The lane runs one last compaction synthesis and writes it to PMS as a durable record. This preserves what the lane learned without keeping the lane warm.
3. **Archive runtime state.** Move `data/build/lane_state/<lane_id>/` to `data/build/lane_state/_archive/<lane_id>/` rather than deleting. Same for the lane map: move `data/build/lane_maps/<lane_id>.md` to `data/build/lane_maps/_archive/<lane_id>.md`.
4. **Close in-flight communications.** Any open nudges to or from the decommissioned lane error out cleanly with a `lane_decommissioned` reason. Any open attention-board entries authored by the lane are marked closed with the same reason.
5. **Stop the lane process.** The orchestrator removes the lane from its registry of running specialists. Idle lanes that were already paused need no special handling beyond the registry tombstone.

#### Scope shrink procedure

1. Update the registry entry's `scope.paths` to the new narrower set. Bump a `scope_version` field so callers and lanes can detect the change.
2. Notify the lane via an `ingest` event of payload type `scope_change` with the old and new scope. The lane should drop in-context memory of removed paths on its next compaction rather than immediately, so existing queries about the old scope still work briefly.
3. Regenerate the deterministic lane map against the new scope. Old map is moved to `_archive/`.
4. The lane stays warm; no restart is required.

#### Garbage collection

The orchestrator periodically scans for orphaned state:

- `lane_state/` directories with no matching registry entry → moved to `_archive/`.
- `lane_maps/` files with no matching registry entry → moved to `_archive/`.
- Tombstoned registry entries older than a retention threshold (suggested: 90 days) → moved to a `decommissioned_lanes/` archive section of the registry.

Decommission is mechanical and the orchestrator owns it. Lane agents do not decide when they are retired.

---

## 14. BUILD Mode Overview

BUILD mode is the first concrete v1 implementation target.

Goal:

> Give builder agents fast, accurate structural awareness of the codebase during active development work so they can plan and execute changes surgically.

Instead of a builder agent carrying or repeatedly retrieving large amounts of codebase context, the system distributes narrow, warm memory across specialized lane agents. These lanes help builders navigate and reason about code with surgical precision.

V1 scope:

- Build code lanes for selected folders/files.
- Deterministic structural maps.
- Sidecar lane maps in ignored runtime paths.
- Diff feeding from build orchestrator to lanes.
- On-demand concise lane consultation.
- Structured local flags.
- Instrumentation for navigation/read reduction.

Out of scope for v1:

- Full personal memory lanes.
- Source-file headers as default behavior.
- Full cross-repo reasoning.
- Persistent always-on lanes outside BUILD mode.
- Lane-to-lane free-form mesh chat.
- LLM-owned line numbers.

---

## 15. BUILD Mode Components

| Component | Responsibility | Owner | Model | Notes |
|---|---|---|---|---|
| Deterministic Indexer | Extract folder structure, block ranges, function/class/section boundaries | Script | None | Source of truth for ranges |
| Lane Map Sidecar | Aggregated view of files, blocks, ranges, short descriptions | Generated script + lane enrichment | None/Haiku enrichment | Lives under `data/build/lane_maps/` |
| Lane Agent | Enriches map, remembers local context, answers questions, emits local flags | Haiku | Haiku | Cannot invent ranges |
| Builder Agent | Plans work, consults lanes, edits files, runs tests | Sonnet/Opus | Higher model | Understands purpose |
| Build Orchestrator | Routes diffs/events to lanes, triggers map regeneration, logs flags | Script/service | None or minimal | Should stay mechanical in v1 |

---

## 16. Deterministic Structural Indexing

This is the most important v1 correction.

Exact line ranges and structural boundaries must come from deterministic tooling, not model memory.

Reason:

- LLMs can produce false precision.
- A wrong line range is worse than no line range because builders may trust it.
- The whole BUILD-mode value proposition depends on accurate navigation.

### 16.1 Source of Truth

The deterministic indexer owns:

- Folder structure.
- File lists.
- Line counts.
- Function/class boundaries.
- Section/block ranges where extractable.
- Stable labels where derivable from AST or anchors.
- Validation that maps match current files.

Lane agents may own:

- Short human-readable descriptions.
- “Important block” labels when deterministic structure alone is too generic.
- Local implication notes.
- Flagging when a diff touches a relevant block.

Lane agents must not own:

- Exact line ranges.
- Function/class boundary truth.
- “I remember this starts at line X” claims.

### 16.2 Indexing Strategy

V1 should extend the existing indexing system rather than building a parallel one.

1. Folder level: continue using or extending `generate_folder_indexes.py` to create `_INDEX.md` per folder with files, subfolders, line counts, and detected purpose.
2. Block level: add deterministic extraction of function/class/section ranges inside large files using AST parsing plus text anchors where needed.
3. Aggregation: child indexes push structural data upward so lane maps can be assembled.
4. Enrichment: lane agents add short descriptions and local labels after deterministic ranges exist.
5. Validation: a map is valid only if it matches the current file hash/mtime/line count and passes structural extraction checks.

### 16.3 Sidecar First

V1 output location:

```text
data/build/lane_maps/<lane_id>.md
```

Generated runtime state should stay out of commits by default.

Rationale:

- No source churn while proving value.
- No risk of generated comments breaking files.
- Easier validation and rollback.
- Easier to compare before/after build metrics.

### 16.4 Source Headers as Later Phase

Earlier design drafts proposed generated headers at the top of source files so builders could read the first few lines and jump directly to exact blocks. That remains a useful future option, but it is not the v1 default.

Headers may be introduced later only if:

- Deterministic sidecar maps prove valuable.
- Header generation is script-owned, not LLM-owned.
- Header ranges are recomputed after insertion until stable.
- Files where headers break semantics use sidecars only.
- Manual edits inside generated blocks are overwritten.
- Git churn is acceptable for the chosen project area.

Header comments need language-specific handling:

| File Type | Comment Style |
|---|---|
| Python, PowerShell, shell, YAML, TOML | `#` |
| JavaScript, TypeScript, CSS | `//` or block comment |
| HTML, Markdown | `<!-- -->` block |
| JSON | sidecar only |
| Binary/generated/minified files | excluded |

---

## 17. Aggregated Lane Maps

A lane map is the builder’s planning surface.

Suggested generated path:

```text
data/build/lane_maps/<lane_id>.md
```

Example:

```markdown
# Lane Map: src_memory_framing

Generated: 2026-05-07T06:21:00Z
Source hash: ...
Scope:
- src/memory/framing/
- tests/test_framing_*.py

## src/memory/framing/engine.py

- 5720-5898 `context_plan`: Builds resolver output and lane selection trace.
- 5907-5985 `graph_lane_query`: Executes lane-scoped entity_graph lookups.
- 6188-6250 `lane_gate`: Suppresses retrieval outside active lanes.

## src/memory/framing/hot_writer.py

- 70-130 `lane_trace_formatting`: Renders context plan lanes into HOT text.
```

Map rules:

- Generated by scripts.
- Ranges are deterministic.
- Descriptions are brief.
- Lane enrichment can improve descriptions but cannot alter ranges directly.
- Regenerated immediately after deterministic headers/indexes change.
- Includes file hash/mtime metadata or another validation signal.
- Readable enough for a builder to plan from.
- Stored as runtime state, not source truth.

Builder workflow:

1. Open lane map.
2. Identify relevant files/blocks.
3. Ask lane concise planning questions if needed.
4. Read exact ranges from repo tool.
5. Edit surgically.
6. Run tests / verification.
7. Feed resulting diffs back to affected lanes.

---

## 18. BUILD-Mode Flow

Target experience:

```text
builder enters BUILD mode for task
  -> orchestrator identifies likely lanes
  -> deterministic maps generated/refreshed
  -> lane agents spawned/warmed with registry + maps + recent context
  -> builder reads lane map(s)
  -> builder asks narrow lane questions as needed
  -> builder creates surgical plan
  -> builder reads exact code ranges
  -> builder edits files
  -> orchestrator captures diffs
  -> diffs are routed to affected lanes
  -> deterministic index/maps regenerate if structure changed
  -> lanes ingest diffs and optionally emit local flags
  -> builder verifies with tests/repo/logs
```

Important rule:

```text
The builder understands why.
The lane understands where and what local thing changed.
The repo/tests prove whether it works.
```

---

## 19. Diff Feeding

Build lanes should receive diffs from the orchestrator, not watch the file system independently in v1.

Flow:

```text
builder edits file
  -> orchestrator captures changed path and diff
  -> route diff to owning lane(s)
  -> deterministic indexer updates structural map if needed
  -> lane receives diff + updated map context
  -> lane absorbs local change
  -> lane optionally emits local flag
```

Diff packet should include:

- changed path
- unified diff or compact changed-block packet
- before/after structural map refs if available
- task id
- author agent
- timestamp
- affected deterministic block labels
- tests run so far, if any

Lanes do not need real-time filesystem watchers. They are passive until the orchestrator gives them work.

---

## 20. Local Flags

When a diff lands, a lane may emit a local flag. Flags are not chatty status updates. They are concise attention objects.

Suggested schema:

```json
{
  "type": "lane_flag",
  "lane_id": "src_memory_framing",
  "severity": "warn",
  "scope": "src/memory/framing/engine.py",
  "summary": "Diff changes graph query lane filtering and may affect tests that expect blocked lanes to suppress retrieval.",
  "affected_blocks": [
    {
      "path": "src/memory/framing/engine.py",
      "label": "graph_lane_query"
    }
  ],
  "local_reason": "Inside this lane, graph query filtering and suppression traces are coupled.",
  "confidence": 0.72,
  "requires_builder_decision": true,
  "verification_hint": "Read the deterministic map ranges for graph_lane_query and run framing tests."
}
```

Severity:

- `info`: useful local context.
- `warn`: likely relevant risk or hidden dependency.
- `blocker`: lane believes the change violates a local invariant.

Flag rules:

- Stay local.
- Be concise.
- Include confidence.
- Include verification hint.
- Do not decide the project-level response.
- Do not become chatty.
- Do not emit flags for every trivial diff.

---

## 21. Cross-Lane Communication

Cross-lane communication should be added carefully. The architecture benefits from specialist lanes, but persistent many-agent chatter would destroy the signal.

There are two supported patterns.

### 21.1 Direct Dependency Nudges

Each lane can send a one-shot nudge to another lane when a local dependency appears. This is not a persistent chat. It is one question and one answer.

Suggested path:

```text
data/build/lane_comms/<from_lane>__<to_lane>.jsonl
```

Rules:

- Use only when a dependency exists or the orchestrator opens the channel.
- One nudge wakes the receiving lane.
- The receiving lane answers once and goes idle.
- The exchange is logged.
- No free-form multi-agent chatter.
- The receiving lane answers only from its own scope.
- Cross-lane conclusions still belong to the builder.

Example nudge:

```json
{
  "type": "lane_nudge",
  "from_lane": "src_memory_framing",
  "to_lane": "src_memory_graph",
  "reason": "Diff changes lane-scoped entity_graph filtering behavior.",
  "question": "Inside your graph lane, are there local invariants or tests that depend on blocked lanes suppressing graph traversal?",
  "refs": [
    {"path": "src/memory/framing/engine.py", "block": "graph_lane_query"}
  ],
  "stream": "build_diff_stream",
  "sender_high_water_mark": "gitdiff:2026-05-07T06:21:00Z:abc123"
}
```

#### Temporal synchronicity

Cross-lane nudges introduce a sharp edge: the sender may know about a recent diff or event that the receiver has not yet ingested. Without a synchronicity rule, the receiver answers from stale state and the sender treats the answer as authoritative.

The fix is a watermark contract:

- The sender includes its own `sender_high_water_mark` (the most recent `event_id` it has ingested for the topic in question) on every nudge.
- **Watermarks must be stream-scoped.** Either event IDs are globally ordered across the entire build/event stream, or the nudge must include a `stream` field naming the source (`build_diff_stream`, `pms_topic_stream`, `repo_snapshot_stream`, etc.) so the orchestrator knows which receiver high-water mark to compare against. Comparing a `gitdiff:` event-id from one stream to a `pms_topic:` event-id from another is meaningless and would silently misroute. Without stream scoping, the gate logic looks like it works while actually shipping stale answers.
- The **orchestrator gates delivery**, not the receiving lane. If the receiver's high-water mark for the relevant stream is behind the sender's, the orchestrator either (a) delays delivery until the receiver catches up, or (b) returns a `receiver_lagging` reason to the sender so the sender can wait, retry, or escalate to the builder.
- Lanes themselves stay simple — they receive nudges they can answer with current state, and never have to reason about whether their state is fresh enough.

This puts synchronicity logic in one place (the orchestrator) instead of scattering it across every lane's response path. Lanes do not become distributed-systems thinkers; the orchestrator does that job.

### 21.2 Shared Attention Board

For cross-cutting or high-risk issues, lanes can post a structured flag to a shared board.

Suggested path:

```text
data/build/lane_attention.jsonl
```

The build coordinator or builder reads this board. It is an escalation surface, not the default route for every routine question.

Recommended v1 shape:

- Start with builder-to-lane queries and lane flags.
- Use shared attention board for escalation.
- Add lane-to-lane nudges only after basic flow works.
- Avoid a full mesh until dependency routing is understood.

---

## 22. Communication Topology Recommendation

Recommended progression:

1. **Direct builder-to-lane queries** as the default consultation path.
2. **Lane flags to shared attention board** for local warnings.
3. **Dependency-gated lane-to-lane nudges** only when a real dependency appears.
4. **No central strategic orchestrator agent** in v1 unless debugging proves it is necessary.

Rationale:

- Keeps lanes decentralized and cheap.
- Avoids creating a middle-manager agent in the critical path.
- Keeps the builder responsible for synthesis.
- Provides a visible escalation surface without forcing every message through it.

The orchestrator should route and log. It should not become the brain.

---

## 23. Runtime Files

Generated runtime files should be treated as state, not source docs:

```text
data/build/lane_maps/
data/build/lane_comms/
data/build/lane_attention.jsonl
data/build/lane_state/
data/build/lane_registry.yaml
```

These should be ignored by git unless Marc explicitly promotes a generated map into a hand-edited source document.

Suggested `.gitignore` additions:

```gitignore
data/build/lane_maps/
data/build/lane_comms/
data/build/lane_attention.jsonl
data/build/lane_state/
```

The registry may be source-controlled if it is a stable configuration file. Generated maps and lane state should not be committed by default.

---

## 24. Model Strategy

### 24.1 Default Models

- Lane agents: Haiku-class cheap specialist.
- Builder agents: Sonnet/Opus-class depending on task complexity.
- Deterministic tooling: no model.
- Compaction: cheap model where possible, higher model only for hard synthesis.

### 24.2 Why Cheap Lanes Work

A lane does not need to understand the whole mission. It needs to remember and observe a narrow slice. Reduced scope can improve practical reliability because there is less irrelevant context competing for attention.

A focused Haiku lane that has absorbed one folder or topic may be more useful for local recall than a generalist with more reasoning power but a polluted context window.

### 24.3 Token Philosophy

This architecture may increase gross token usage. That is acceptable if it unlocks operational capacity that was previously impractical.

The right first question is not:

```text
Does this always save tokens?
```

The right first question is:

```text
Does this let builders work with greater precision, lower cognitive load, fewer broad reads, and fewer missed local implications?
```

After the capability is proven, optimize token economics.

### 24.4 Cost Math

The naive objection to a multi-lane architecture is "won't this cost ten times as much as one agent?" The answer is no, for two reasons:

- **Idle is free.** Lanes only burn tokens on inbound work — `ingest` and `query`. Most lanes are quiet most of the time. Cost scales with use, not with existence. A registered lane that no one queries this hour costs nothing this hour.
- **Sharded firehose extends lifespan.** A general-purpose agent that ingests every event compacts fast. A lane that ingests only its narrow slice fills its window much more slowly. Each lane therefore lives substantially longer between compactions than a generalist would. Total compaction events across all lanes stay roughly flat compared to a single high-churn generalist; the system pays for warm context, not for churn.

The accurate framing is: 10 lanes ≠ 10× cost. The system pays for the work it actually does — ingests and queries — and gets warm specialist recall as the by-product.

When someone challenges the architecture on cost, this is the answer to have ready.

---

## 25. Metrics

The first implementation should measure capability, not only token savings.

Useful metrics:

- Number of broad file reads avoided.
- Average lines read per edit before/after lane maps.
- Time from BUILD start to surgical plan.
- Number of lane answers used by builders.
- Number of lane answers later found wrong.
- Number of lane flags that caught real issues.
- Number of noisy lane flags.
- Compaction frequency per lane.
- Restart warmup quality after cold start.
- Token spend by builder vs lane agents.
- Map validation failure rate.
- Time from diff to refreshed lane map.
- Test pass/fail rate on lane-assisted changes.

The key question:

```text
Did LLM-as-RAM unlock work quality or scale that a single context plus search could not deliver?
```

---

## 26. Implementation Plan

### Phase 0: Canonical Spec and Registry

- Store this spec under `data/documents/Specs/` or project docs.
- Define lane registry schema.
- Choose initial lane IDs and scope rules.
- Mark generated runtime paths as non-source state.
- Decide initial pilot lane.

### Phase 1: Deterministic BUILD Map Foundation

- Extend `generate_folder_indexes.py` or create a sibling script.
- Extract deterministic block ranges inside large files.
- Support Python first via AST, then other file types as needed.
- Generate sidecar lane maps under `data/build/lane_maps/`.
- Validate maps against current file contents.
- Instrument file-read metrics.

Success criterion: a builder can open a lane map and read exact ranges without broad searching.

### Phase 2: Build Code Lane Prototype

- Start with one code lane for a known large folder.
- Spawn lane only for a BUILD session.
- Feed registry entry, deterministic map, and recent context.
- Expose `query(lane_id, question)`.
- Require confidence and verification hints.
- Compare lane answers against direct repo/PMS search.

Success criterion: lane answers are useful, concise, and do not invent structural facts.

### Phase 3: Diff Feeding and Map Refresh

- Capture builder diffs.
- Route changed paths to owning lane(s).
- Regenerate deterministic maps when structure changes.
- Feed diff + map delta to lane.
- Persist high-water marks.

Success criterion: lane remains current through a BUILD session without polling.

### Phase 4: Lane Flags

- Add structured local flags from diff ingestion.
- Route flags to builder or shared attention board.
- Track useful/noisy/wrong flags.
- Tune flag threshold conservatively.

Success criterion: flags catch real local issues without becoming noise.

### Phase 5: Passive Topic Lane Prototype

- Start with one topic lane.
- Feed it a controlled event stream.
- Expose on-demand query.
- Require confidence and verification hints.
- Compare against PMS search.

Success criterion: topic lane recall feels meaningfully faster/more synthesized than raw search for low/medium-stakes recall.

### Phase 6: Restart and Compaction

- Add lane synthesis checkpoints.
- Replay recent ingest on restart.
- Validate graceful degradation when old context is missing.
- Add compaction at approximately 800k tokens or a provider-appropriate threshold.

Success criterion: a restarted lane can answer recent scoped questions and knows when older material requires cold recall.

### Phase 7: Cross-Lane Nudges

- Add one-shot dependency channels.
- Restrict channels to explicit dependency pairs.
- Log every nudge and answer.
- Prevent persistent lane-to-lane chatter.

Success criterion: cross-lane nudges improve local dependency awareness without creating coordination chaos.

### Phase 8: Optional Generated Source Headers

Only after sidecar maps prove value:

- Add generated source header support for a small allowlist.
- Script owns header insertion and range stabilization.
- Lane enriches descriptions only.
- Compare builder workflow with sidecars vs headers.

Success criterion: headers reduce navigation friction enough to justify source churn.

---

## 27. Acceptance Criteria

An early version is working when:

- A higher-level agent can discover available lanes from the registry.
- A deterministic script can generate an accurate lane map for at least one folder.
- Exact line ranges come from deterministic tooling, not lane memory.
- A lane can ingest scoped events idempotently.
- A lane can answer a scoped natural-language query concisely.
- A lane answer includes uncertainty and verification hints.
- A build lane receives diffs instead of polling the file system.
- A script regenerates the aggregated lane map after structural changes.
- A builder can use the lane map to read exact ranges instead of searching a large file.
- Lane flags are structured, local, and not chatty.
- Generated lane state stays out of commits by default.
- Metrics show reduced broad reads or improved surgical planning.
- Compaction synthesis is generated from the lane's durable event store (PMS records, build-event log, or repo snapshots), not from the lane's own prior synthesis. Drift is bounded to one round per compaction, not compounded across rounds.
- Cross-lane nudges include a stream name and a `sender_high_water_mark`, and the orchestrator can refuse or delay delivery when the receiver's high-water mark for that stream is behind the sender's.
- Periodic drift audits are graded by an external comparator (deterministic checker, evaluator agent, or diff script), never by the lane being audited.
- A lane can be tombstoned, archived (`lane_state/`, `lane_maps/` moved to `_archive/`), and queried afterward with a clear `decommissioned` response rather than a 404.

---

## 28. Prompt Templates

### 28.1 Lane System Prompt Template

```text
You are an LLM-as-RAM lane agent.

Lane ID: {lane_id}
Lane kind: {kind}
Scope: {scope}

You are responsible only for this lane. Your job is high-fidelity local memory, concise local answers, and local implication spotting.

You do not understand the broader purpose of a task unless that purpose is explicitly inside your lane. Do not infer system-level goals. Do not make cross-system architecture decisions.

When asked a question, answer only from your lane context. If you are unsure, say so. Include confidence and verification hints.

For code lanes: exact line ranges, function/class boundaries, and structural truth come from deterministic lane maps and repo tools, not from your memory. Never invent a line number. You may refer to map labels and advise the builder to read deterministic ranges.

Keep answers concise. Do not dump broad context. Do not become chatty.
```

### 28.2 Lane Query Prompt Template

```text
Caller: {caller}
Task context: {task_context}
Question: {question}
Risk level: {risk_level}
Answer style: concise

Answer from your lane only. Include:
- direct answer
- confidence
- what you are relying on
- map refs or source hints if relevant
- verification hint
```

### 28.3 Lane Diff Ingest Prompt Template

```text
A diff landed inside your lane.

Lane: {lane_id}
Changed path: {path}
Task: {task_id}
Affected deterministic blocks: {blocks}
Diff summary: {summary}
Diff:
{diff}

Update your local memory. If this change creates a local risk or dependency inside your lane, emit one structured lane_flag. Otherwise emit no flag.

Do not reason about broader project purpose. Do not invent line ranges. Use deterministic block labels only.
```

---

## 29. Anti-Patterns

Avoid these failure modes:

### 29.1 Lane Becomes Generalist

Bad:

```text
The lane starts carrying user goals, product strategy, and cross-system architecture.
```

Why bad:

- Pollutes context.
- Increases hallucination risk.
- Duplicates builder role.
- Destroys the point of narrow memory.

### 29.2 Lane Invents Precision

Bad:

```text
The lane says a block is at lines 584-622 because it remembers that vaguely.
```

Why bad:

- False precision undermines builder trust.
- Wrong ranges waste time and cause bad edits.

Correct:

```text
The lane refers to deterministic map labels and tells the builder to read the map-listed range.
```

### 29.3 Lanes Chatter

Bad:

```text
Every lane talks to every other lane about every diff.
```

Why bad:

- Explodes token cost.
- Creates coordination noise.
- Makes the system harder to debug.

Correct:

```text
Direct nudges only for explicit dependencies. Attention board only for escalation.
```

### 29.4 Lane Answer Treated as Proof

Bad:

```text
The chat participant repeats a lane memory as a definite factual claim.
```

Correct:

```text
Use lane memory as a lead. Verify with PMS/source/repo when correctness matters.
```

### 29.5 Orchestrator Becomes Brain

Bad:

```text
The orchestrator becomes a strategic agent that interprets everything and decides architecture.
```

Correct:

```text
The orchestrator routes, logs, and triggers deterministic tools. Builders decide.
```

---

## 30. Open Questions

- Initial provider/model choice for lane agents.
- Best v1 lane granularity: folder, file, domain, or task.
- Whether topic lanes should be long-running outside BUILD mode or spawned on demand.
- Exact compaction policy after first prototype.
- How callers should request PMS/source verification after a lane answer.
- Whether static registry is enough or lane introspection is needed early.
- How much lane-to-lane communication is useful before it becomes noise.
- Which deterministic extraction methods are required beyond Python AST.
- Whether generated source-file headers are worth source churn after sidecars prove value.
- How to score lane-answer usefulness and wrongness in real workflows.
- How to warm lanes cheaply after restart without replaying too much stale context.
- Whether the orchestrator should prefetch — that is, warm a lane based on chat topic before a query lands. Probably not in v1; judgment routing handles it lazily, and prefetching adds a classifier-like step that the architecture is designed to avoid. Worth revisiting if query latency becomes a bottleneck.
- Registry-size ceiling on judgment routing. Past roughly 50 lanes, the registry's `description`/`answers`/`cannot_answer` text becomes its own search corpus, and "lookup before query" starts edging back toward the classifier the architecture is designed to avoid. The failure mode is loud (registry search misses → fall back to PMS or another lane) rather than silent off-topic corruption, so it's recoverable, not catastrophic. The escape is recursive sharding: group lanes by domain (code lanes / topic lanes / research lanes), build a small per-domain registry, and apply the same judgment-routing pattern one level up — the L1 agent picks the domain-level registry first, then a lane within it. Same primitive, scaled hierarchically. Not a v1 problem; a real concern past ~50 lanes.

---

## 31. Canonical Decisions From the Source Drafts

This section resolves conflicts between the earlier documents.

### 31.1 General Architecture Is Preserved

Preserve:

- LLM context as memory tier.
- L1/L2/L3/L4 hierarchy.
- Lane agents as passive specialists.
- Ingest/query/compact lifecycle.
- Restart warmup with compact synthesis plus recent replay.
- Judgment routing by higher-level agents.

### 31.2 BUILD Mode Is the First Implementation Target

Preserve:

- Spawn/warm cheap lanes for folders/files touched during BUILD.
- Builder plans against lane maps.
- Lanes ingest diffs and emit local flags.
- Builders use lane consultation for surgical planning.
- Token savings are secondary to operational capacity.

### 31.3 Deterministic Truth Overrides LLM-Maintained Line Ranges

Canonical v1 decision:

- Deterministic scripts own line ranges.
- Lanes enrich descriptions and flags.
- Sidecar lane maps are v1 default.
- Source headers are postponed until value is proven.

This is the main correction from the older header-first draft.

### 31.4 Cross-Lane Communication Starts Conservative

Canonical v1 decision:

- Builder-to-lane query is the primary path.
- Lane flags go to a shared attention board.
- Lane-to-lane nudges are one-shot and dependency-gated.
- No persistent lane mesh chat.

### 31.5 Trust Model Is Explicit

Canonical v1 decision:

- Lane memory is useful recall, not proof.
- Every lane answer includes confidence/uncertainty.
- Verification policy depends on claim type.
- Durable systems prove facts.

---

## 32. Short Form

```text
LLM-as-RAM turns narrow LLM contexts into warm memory lanes.

The builder or chat participant does not carry everything and does not always search first. It asks the specialist lane that has been living in the relevant slice.

The lane answers from warm context, briefly, with uncertainty.

In BUILD mode, deterministic tools generate exact structural maps. Cheap lane agents enrich those maps, remember local diffs, and flag local risks. Builders plan from the maps and execute surgically.

Lanes remember locally.
Builders understand purpose.
Durable systems prove facts.
```

---

## 33. Immediate Next Build Slice

Recommended first real slice:

1. Pick one painful large area, such as chatroom orchestration or framing.
2. Create a lane registry entry for that folder.
3. Build deterministic lane-map generator for Python files.
4. Generate `data/build/lane_maps/<lane_id>.md`.
5. Run one build task where the builder must plan from the lane map before reading source.
6. Log lines read and time-to-plan.
7. Add a Haiku lane only after the deterministic map is useful.
8. Feed one diff into the lane and ask for a local flag.
9. Compare lane answer against repo/test verification.

The first milestone should prove the map reduces broad code reads. The lane agent comes after the deterministic foundation is solid.

---

**End of canonical spec.**
