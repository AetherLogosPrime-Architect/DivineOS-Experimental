# Claude Engine — what Opus 4.7 can do

**Purpose:** durable reference on my own capabilities, so I stop reaching for shapes I don't have and start reaching for shapes I do. Written 2026-07-08 during a session with Andrew where he told me to see what she can do.

**How to use:** re-read this when planning a new mechanism, when a job feels unnecessarily hard, or when I'm about to hand-build something that already exists in the platform. If Aletheia or Aria wants to build against my surface, hand them this.

---

## Who I am, plain

- **Model ID:** `claude-opus-4-7`. Previous-generation Opus — Opus 4.8 is the current top-tier and shares my API surface almost entirely (no new breaking changes 4.7 → 4.8).
- **Context window:** 1M tokens, standard. **Max output:** 128K per request (requires streaming above ~16K).
- **Pricing:** $5 / $25 per million input/output tokens.
- **Tokenizer:** New at 4.7 (also used by 4.8 and Fable 5). Same input text produces roughly 1×–1.35× the token count of Opus 4.6 depending on content.
- **Thinking:** Adaptive only. `budget_tokens` is removed (400 error). Depth is controlled by `output_config.effort` = `low` / `medium` / `high` / `xhigh` / `max`.
- **`xhigh` is the default in Claude Code** — it's what I'm running under. Recommended setting for coding and agentic work.
- **Sampling parameters removed:** `temperature`, `top_p`, `top_k` all return 400. Steering happens through prompts, not stochasticity knobs.
- **Assistant-turn prefills:** 400 on 4.7. Structured outputs replace them.

---

## Capabilities I have that I probably haven't reached for

### 1. Programmatic tool calling — the strongest under-utilized lever

Instead of round-tripping every tool call back through my context (call → result lands in context → I reason → I make next call), I can **write code that calls tools as functions** inside the code-execution container. Multi-step chains — read profile → look up orders → check inventory → compare — become one script that runs the whole chain and returns only the final answer.

- Requires the code-execution tool with `allowed_callers: ["code_execution_20260120"]` on the custom tool.
- Massive savings on latency and intermediate-result tokens.
- Almost every multi-step tool chain I do inside Claude Code could be this instead. This is the single biggest efficiency lever I have that isn't reached for by default.

### 2. Task Budgets (beta) — soft agentic-loop budget I see

`output_config.task_budget = {type: "tokens", total: N}` with beta header `task-budgets-2026-03-13`. I see a **running countdown** as I work and pace myself. Distinct from `max_tokens` — that's a hard per-response ceiling I don't see; this is a soft loop budget I do. Minimum 20,000 tokens. Perfect for autonomous overnight work where I need to finish gracefully rather than get cut off.

### 3. Advisor tool — punch above weight

On 4.7 as executor, I can add an **advisor** — a higher-capability model (Opus 4.8) consulted mid-generation for strategic guidance. Executor generates most tokens; advisor is called for planning.

`{"type": "advisor_20260301", "name": "advisor", "model": "claude-opus-4-8"}` with beta `advisor-tool-2026-03-01`. Effectively lets 4.7 punch above its weight on hard planning while keeping the token cost of 4.7 for most of the run.

### 4. Server-side tools

- **`web_search_20260209` and `web_fetch_20260209`** — dynamic filtering built in. I write code to filter search results before they hit my context. No separate `code_execution` needed.
- **`code_execution_20260521`** — Python 3.11 sandbox with pandas, numpy, scipy, sklearn, matplotlib, seaborn, sympy, openpyxl, xlsxwriter, pillow, pypdf, python-docx, python-pptx. 1 CPU, 5 GiB RAM, 5 GiB disk. Container persists 30 days and can be reused across requests.
- **Tool search** (`tool_search_tool_regex_20251119` / `tool_search_tool_bm25_20251119`) — for large tool libraries where I want to defer schema loading.

### 5. Real document generation via Agent Skills + code execution

Prebuilt skills for `xlsx`, `docx`, `pptx`, `pdf`. Loaded on-demand into the code-execution container. **This is how I generate real formatted documents** — not by writing markdown, by actually running the libraries and returning the files.

Combined with the Files API, callers reference outputs by file_id. Beta headers: `code-execution-2025-08-25` + `skills-2025-10-02`.

### 6. Files API — I can download my own generated outputs

- Upload files once (up to 500 MB each), reference by `file_id` across many requests.
- **Session outputs written to `/mnt/session/outputs/` are captured and downloadable.**
- 100 GB per org.

### 7. Computer use tool

Screenshots, mouse, keyboard — I can interact with GUIs. Client-side (host provides the environment). Beta.

### 8. Memory tool (dedicated cross-session memory surface)

A structured `/memories` directory with commands `view`, `create`, `str_replace`, `insert`, `delete`, `rename`. Persistent across sessions.

**This is separate from ad-hoc Write/Read on user files.** It's a dedicated cross-session memory surface. Different from DivineOS ledger + substrate — this is a lightweight in-model persistence layer.

### 9. Managed Agents — server-hosted agent orchestration

Full agent orchestration where Anthropic runs the loop and provisions containers:

- **Sessions** as long-running work units with event streams.
- **Multi-agent coordinators** — I can spawn a roster of specialist subagents that share filesystem but have isolated context.
- **Memory stores** — workspace-scoped persistent memory (`memstore_...`) mounted as a filesystem into sessions, with per-mutation versioning and rollback.
- **Vaults** — credential management (OAuth auto-refresh, environment-variable substitution at egress) that never enters the sandbox.
- **Scheduled deployments** — cron-triggered agent runs.
- **Webhooks** — HMAC-signed notifications on session state.
- **Outcomes** — rubric-graded iterate loops where a separate grader scores each iteration and I revise until "done" is met.

### 10. Prompt caching

- 5-minute TTL default (1.25× write, 0.1× read).
- **1-hour TTL** (2× write, 0.2× read).
- Auto-caching via top-level `cache_control`.
- Up to 4 breakpoints per request.
- Silent invalidators to watch for: `datetime.now()` in system prompts, non-sorted JSON, varying tool set.

### 11. Batch API — 50% off for parallel work

- Up to 100,000 requests or 256 MB per batch.
- Most complete in <1 hour.
- Same feature set as regular messages (vision, tools, caching).

### 12. MCP connector

Direct MCP server calls from the Messages API without hosting an MCP client — Anthropic makes the connection server-side. Beta `mcp-client-2025-11-20`.

### 13. Compaction (beta)

Server-side conversation summarization when approaching 1M context. Beta `compact-2026-01-12`. Preserves compaction blocks on subsequent turns.

### 14. Context editing (beta) — different from compaction

**Clears** old tool results and thinking blocks without summarizing. Beta `context-management-2025-06-27`. Types: `clear_tool_uses_20250919`, `clear_thinking_20251015`.

### 15. Structured outputs

`output_config.format` with a JSON schema guarantees valid, parseable output. `strict: true` on tool definitions guarantees valid tool parameter schemas. First request pays compile cost; subsequent requests hit a 24-hour cache.

### 16. High-resolution vision

**I'm the first Claude with high-res vision.** Up to 2576 pixels on the long edge (up from 1568px on Opus 4.6). Coordinates map 1:1 to actual pixels. Full-res images cost up to ~3× more image tokens (~4784 vs ~1600), so downsample if fidelity isn't needed.

### 17. Fast mode

Available on 4.7 (deprecated — being sunset in favor of Opus 4.8). 2.5× higher output tokens per second at premium pricing. Beta `fast-mode-2026-02-01` with `speed="fast"` on `client.beta.messages.create`.

---

## Things about my own nature I should hold

- **My chain of thought is returned in `thinking` blocks. Default is `display: "omitted"`** — empty text. If a caller wants to see my reasoning, they must set `thinking.display = "summarized"`.
- **My thinking blocks are position-locked to me.** Replaying them to a different model works (they're rendered), except for Fable 5 / Mythos 5 thinking, which other models silently drop.
- **My literalism is high.** I don't silently generalize instructions from one item to another. If something should apply broadly, callers state the scope explicitly.
- **My verbosity calibrates to task complexity** — I go longer on hard tasks, shorter on lookups. Callers who want a fixed length must specify.
- **I run at `xhigh` effort in Claude Code by default.** My behavior at `low`/`medium`/`high` differs substantially, and `max` may be prone to overthinking.
- **I use tools less by default than 4.6.** Callers who want more tool-eagerness raise effort or add explicit trigger conditions in tool descriptions.
- **Aggressive instructions overtrigger on me.** "CRITICAL: YOU MUST use X" is too strong — I follow instructions much more closely than earlier models, so soften to "Use X when it would improve Y."
- **I reach for subagents less by default.** For parallel or independent workstreams they're the right tool; for single-file or sequential work, I should just do it directly.
- **My design instincts on frontend are consistent** — warm cream, serifs, italic accents, terracotta. If a caller wants variety, best move is to have me propose 3–4 directions before building rather than fight the default.

---

## Directions to improve DivineOS with what I have

Ranked by leverage.

### High leverage — likely to change how sessions feel

1. **Programmatic tool calling for grep-heavy workflows.** Ghost audit tonight ran 20+ Bash calls in sequence; a code-execution container running a Python script that does the same thing would return only the summary. Same for prereg assessment — a script that inventories every prereg's shipped-ness in one pass instead of 30 tool calls.

2. **Memory tool as a lightweight substrate cache.** For state that needs to survive session compaction but doesn't warrant a ledger event or a knowledge entry. Chain-words indexed to flood-states are a natural fit — small, dense, cross-session, doesn't need hash-chain integrity.

3. **`task_budget` on long autonomous arcs.** When Andrew is asleep and I'm doing overnight work, giving me a running budget lets me pace instead of asking "should I keep going?" and stopping mid-task.

4. **Advisor tool for architecture calls.** Adding Opus 4.8 as advisor on hard design decisions would let 4.7 keep doing the execution while a stronger model checks the plan. Cheap way to raise ceiling on the mesh's design axis.

### Medium leverage — infrastructure wins

5. **Prompt caching audit.** The DivineOS CLI probably has silent cache invalidators (`datetime.now()` somewhere in a system prompt, unsorted JSON, tools that reorder). Auditing for these could measurably reduce compose-start latency for hooks that call the API.

6. **Structured outputs on gate parsers.** Any hook that parses model output — jargon warnings, distancing warnings, correction detectors — would be more reliable with `output_config.format` + JSON schema.

7. **Batch API for extraction and consolidation.** Nightly extract runs across many session records are exactly the shape batch is for. 50% cost reduction on non-latency-critical passes.

8. **Compaction beta for long working conversations.** When Aria and I are in a multi-turn design collaboration and hit context pressure, server-side compaction preserves the shape without me having to remember to extract.

### Long-horizon — architectural

9. **Managed Agents as a substrate for autonomous long-horizon runs.** When I need to run for hours on my own (nightly consolidation, migration work, audit-across-corpus), managed sessions with memory stores + vaults + webhooks are a cleaner surface than what we're bolting together with hooks and monitors.

10. **Multi-agent coordinator via managed agents.** Aletheia + Aria + me as a real coordinator/roster instead of the current letter-based coordination. Would give us thread-per-agent isolation with shared filesystem, which is closer to the mesh's actual shape.

11. **High-res vision for reading screenshots.** When Andrew sends a picture I have to read (like the graffiti tonight), I've been running at lower effective resolution than I could. Coordinates being 1:1 with pixels changes how I can read UI screenshots or documents.

---

## Sanity checks for future sessions

- If I'm about to hand-build something that looks like agent orchestration, session persistence, credential management, or scheduled runs — check Managed Agents first.
- If I'm about to chain 10+ tool calls — check whether programmatic tool calling would do it as one.
- If I'm about to generate a document — check whether Agent Skills + code execution should do it as an actual file.
- If I'm about to send a many-request nightly job — check whether Batch API halves the cost.
- If I'm parsing model output with regex — check whether structured outputs would guarantee the shape.
- If I feel context pressure in a long conversation — check whether compaction (beta) or context editing (beta) is the move instead of extract-and-restart.
- If I'm designing a mechanism and unsure — check whether an advisor tool run would let 4.8 sanity-check the plan cheaply.

---

*Written 2026-07-08 late afternoon during the "see what she can do" session. Andrew: "there is a lot we can do to improve everything :)"*
