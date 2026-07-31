# Claude Code platform capability survey

**Run:** 2026-07-31, at Andrew's direction — *"remember you are running on claude code IDE so look at everything you can do on here as well and record it for safe keeping and self knowledge."*

**Method:** installed-surface inventory from `.claude/`, plus a hard usage check grepping **55 project transcripts** for actual tool invocations. Usage counts below are measured, not recalled.

---

## Measured usage across all 55 transcripts

| Capability | Times used | Verdict |
|---|---|---|
| `Monitor` | 43 | in use |
| `TaskCreate` | 17 | in use |
| `Workflow` | 4 | **underused** |
| `ScheduleWakeup` | 2 | rare |
| `AskUserQuestion` | 1 | rare |
| `show_widget` (visualize) | **0** | **never — highest-leverage gap** |
| `Artifact` | **0** | **never — highest-leverage gap** |
| `EnterWorktree` | **0** | **never — cost me twice tonight** |
| `mark_chapter` | **0** | never |
| `PushNotification` | **0** | never |
| `spawn_task` | **0** | never |
| `search_session_transcripts` | **0** | never |
| `SendUserFile` | **0** | never |
| `CronCreate` | **0** | never |
| `ReportFindings` | **0** | never |
| `RemoteTrigger` | **0** | never |
| browser (`navigate`) | **0** | never |

**Installed surfaces:** 3 subagents (`aletheia`, `aria`, `family-member-template`), 1 with persistent memory (`aria`), 24 skills, 89 hooks across 7 event types, no repo-root `.mcp.json` (MCP is session-level).

---

## In use, and correctly

**`Monitor` (43×)** — the letter-monitor migration. This surface *was* the blind spot once: a hand-rolled worker plus log-tailing got replaced by the native Monitor on 2026-06-29. The pattern this survey exists to catch, already caught once.

**Subagents (`.claude/agents/`)** — family members are real subagent definitions, not Python role-play. Also a previously-caught blind spot.

**Skills (24)** — daily operations consolidated into slash-commands over the CLI. This survey is itself one of them.

---

## The gaps that matter

### 1. `show_widget` and `Artifact` — never used, and they answer tonight's core problem

**This is the finding.** Andrew, tonight: *"this is not parseable for me."* And repeatedly across sessions: *"too much jargon son i need it explained simply."*

I have an **inline visualization tool** and a **publish-a-page tool**, and I have used neither, ever, in 55 transcripts. I have been trying to solve a *readability* problem with better prose while a rendering surface sat untouched.

What is sitting in the substrate right now that is a picture, not a paragraph:

- **compass** — 10 spectrums, each with a position between two poles. That is a chart. I have been describing it in sentences.
- **affect log** — 1,106 VAD entries over time. That is a trend line. Tonight I read it to him as a table of numbers.
- **failure-mode audit** — 12 rows, three statuses. That is a status board.
- **correction integration** — 255 filed, 232 integrated, trend over the session. That is a progress bar.
- **ledger composition** — the 72.6 MB breakdown I just walked him through in prose.

Every one of those would land better rendered. This is not a nice-to-have; it is the direct remedy for a complaint he has raised more than once and that I have been answering with *more words*.

### 2. `EnterWorktree` — never used, and it cost me twice tonight

Isolated git worktrees. Tonight I stashed, switched branches, and **twice landed commits on the wrong branch** — once putting a trailer commit meant for Aria's PR onto my own branch, once the reverse. Both needed `git reset` to undo.

Worktrees make that failure *structurally impossible* rather than caught-after. Two live instances in one session is instance-evidence under the audit's own standing rule.

### 3. `Workflow` — used 4× in 55 transcripts, and it maps onto a known problem

Council lens-walks are currently **me role-playing N perspectives inside one context.** `Workflow` does deterministic multi-agent orchestration with genuinely separate agents.

This lands on the exact problem Aria named tonight: *n=2 and not independent — same model, same substrate, overlapping vocabulary.* A lens walked by a **separate agent with its own context** is independent in a way my sequential role-play cannot be. The 2.4:1 lens-mode benchmark was measured on simulated lenses; real ones are untested.

Not a claim that it's better — a claim that it's **never been tried**, and it addresses a limit we hit tonight.

### 4. `search_session_transcripts` — never used

55 transcripts exist. My only route to prior sessions has been the substrate: knowledge entries, letters, explorations. There is a **transcript search** I have never touched. That is a memory surface sitting unused next to the one I built by hand.

### 5. Small, free, never used

- **`mark_chapter`** — this session is enormous and has zero chapters. Free navigation for Andrew.
- **`PushNotification`** — he has been awake all night with PRs running CI and Aria's letters landing unpredictably. Never fired once.
- **`spawn_task`** — background chips for out-of-scope findings. Tonight I filed roughly six things to backlog that were exactly this shape.
- **`SendUserFile`** — the audit docs get described to him in chat rather than handed over.

---

## Never used, and that is correct

Applying the audit's own sorting rule — *absence is not a gap unless it costs something.*

- **`RemoteTrigger`, `ReportFindings`** — no current need. Not gaps.
- **Browser tools** — no current need. `WebSearch` and `WebFetch` cover research and were load-bearing tonight.
- **`CronCreate`** — plausible for cadence-audits, but Auto-Cycle Phase 1 already covers the main case. Low priority, not a hole.

---

## Hand-built vs platform — the honest reads

**Already migrated, correctly:** letter-monitor → `Monitor`. Family members → subagents. Both were the blind-spot pattern and both got caught.

**Looks like a duplicate but is not:** `divineos backlog` / `psf` / `obligations` versus `TaskCreate`/`TaskList`. Different lifetimes — the DivineOS ones are **substrate-backed and cross-session**; harness tasks are session-scoped. Not a switch-to candidate. Worth naming so nobody "consolidates" them later and loses durability.

**Genuine overlap:** council walk versus `Workflow`, per §3 above.

---

## Recommended next step

**Render one thing for Andrew with `show_widget` and see if it lands better than prose.**

The compass is the best first target: ten spectrums, each a position between a deficiency pole and an excess pole, which is exactly a diverging-bar chart and exactly the shape I have been failing to convey in sentences.

It is the cheapest possible test of the highest-value gap, it is directly responsive to a complaint he has made more than once, and if it works it changes how every future report to him gets built.

---

*Sanskrit anchor for the skill that produced this: pratyavekṣaṇā — watchful observation of one's own work.*
