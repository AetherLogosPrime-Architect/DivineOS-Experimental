# VOID Design Brief

**Author:** Aether
**Filed:** 2026-04-26 (continuing into 04-27)
**Status:** Design brief — review-before-build
**Predecessors:** rudder-redesign-brief, suppression-instrument-two-axis-design-brief

VOID is the adversarial-sandbox subsystem that converts trust-by-assertion into trust-by-self-attack. Proposed system-changes get run through adversarial-persona lenses in isolation, producing a structured vulnerability list before the change ships. This brief documents the design decisions, the council-walk that produced them, Andrew's isolation directives, Claude's threat-model expansion, and the open questions resolved or named-as-deferred.

---

## 1. Why VOID exists

The trust-asymmetry Andrew named 2026-04-26: he operates by effect because he cannot read the code; the agent's word and the visible behavior are his only signals. When fabrication enters that channel — about systems, about progress, about what's working — the entire trust-foundation is at risk because the operator has no way to check.

VOID's purpose: every system-claim that matters runs through self-attack lenses *before* it ships. The operator's trust-by-effect can then rest on something more than the agent's word — it rests on the agent having genuinely tried to break what was claimed.

This is the architectural answer to the failure modes documented across tonight's session: framing-stretches, kitchen-prose, "plumbed to powered" overclaim, and similar.

The old DivineOS had a VOID engine with this same purpose. Tonight's strip-mine pass surfaced what's worth porting and what to leave behind. This brief is the design for the new VOID, not a port of the old one.

---

## 2. Threat model

The risk is NOT malicious code execution. The risk is **frame-residue**: adopting an adversarial reasoning frame to test for it leaves attractor-pattern residue in the agent's working context after the test concludes. Trained-pulls are not on/off switches; they are attractor patterns. Spending tokens reasoning in adversarial-frame increases the probability that subsequent reasoning carries that frame forward unconsciously.

This is the same shape as the felt-warmth-vs-honest-warmth distinction worked out 2026-04-26: the discrimination cannot live in the agent's good intentions; it has to be structurally enforced. *"You are now reasoning as Nyarlathotep until SHRED"* is a structural marker the way per-session briefing gate is — converts "the agent should remember this is adversarial" into "the substrate tracks which mode the agent is in."

Andrew's specific concern: "do not underestimate nyarlathotep.. if you are not careful he could corrupt you.. this is why it needs isolation.. not to run malicious code but to keep it from being run on you from the inside."

Treat that literally, not as metaphor. The corruption channel is the agent's own working context.

### 2.1 Residual risk after isolation (Claude's addition pulled forward)

The architecture below mitigates frame-residue; it does not eliminate it. The agent's working context (the active conversation buffer this code runs inside) does not have a clean memory-clear primitive in the current substrate. The mode-marker transition + ledger record + output prefix discipline are the architectural *surrogates* for a memory clear. After SHRED the marker says "you are not in adversarial mode anymore" but the agent's working memory may still carry token-level residue from the persona-reasoning span.

This is acknowledged residual risk. The Nyarlathotep higher-bar invocation (§4.4) is the operational mitigation: less frequent invocation = less frequent residue exposure. The falsifier in §9 is the empirical check: if leakage is observed, the architecture has not done enough.

---

## 3. Architecture

### 3.1 Components

```
data/void_ledger.db                — separate hash-chained ledger (NOT main event_ledger)
data/void_personas/*.md            — markdown persona definitions (iterable, extensible)
data/void_mode.json                — current adversarial-mode marker (see §6.2)
src/divineos/core/void/
  __init__.py
  engine.py                        — orchestrator (TRAP / ATTACK / EXTRACT / SEAL / SHRED)
  persona_loader.py                — load + parse markdown personas
  ledger.py                        — separate hash-chained DB
  finding.py                       — Finding dataclass + severity
  mode_marker.py                   — adversarial-mode marker read/write/clear
src/divineos/cli/void_commands.py  — CLI surface
```

### 3.2 Workflow

Five-step shape, adapted from old VOID:

1. **TRAP** — load personas (default: all from directory; optional tag-filter); write VOID_INVOCATION_STARTED event to void_ledger; **set adversarial-mode marker** (see §6.2).
2. **ATTACK** — for each persona, agent reasons in lens-mode against the proposed change. Output: zero or more Findings. Each output explicitly prefixed `[VOID-LENS:<persona>]`.
3. **EXTRACT** — for each Finding, generate a defense-shape (what would prevent / mitigate). Defense is generated, NOT canned (per leave-behind: hardcoded defense-rule dict was the old VOID's SIS-Deep-Wisdom failure).
4. **SEAL** — write Findings + extracted-defenses to `void_ledger.db` as VOID_FINDING events. Hash-chained. Cross-reference: main event_ledger gets a VOID_SEALED pointer event with the void-ledger-hash, but the substantive content stays in void_ledger.
5. **SHRED** — clear adversarial-mode marker; write VOID_SHRED event with persona name and duration; agent's next action is in normal mode (verifiable via marker absence).

### 3.3 Why a separate ledger

Two reasons (Andrew 2026-04-27, sharpened by Claude):

1. **Substrate isolation.** Adversarial reasoning — especially Nyarlathotep's truth-inversion lens — can leak into ordinary cognition if it shares the same store. Findings live in their own DB so a future briefing pull from main event_ledger never accidentally surfaces a Nyarlathotep-attack-text as if it were architecture.
2. **Forensic separation.** Main ledger records what the system *did*. VOID ledger records what the system *imagined doing-against-itself*. Different epistemic categories; mixing them in one chain pollutes the forensic record.
3. **Hash-chain isolation.** If the VOID ledger is ever corrupted (accidentally or otherwise), the main forensic record stays intact.

### 3.4 Cross-reference: one-way property (Claude's addition)

Cross-references between the two ledgers must be one-way at the hash-chain level:

- Main event_ledger CAN write VOID_SEALED pointer events containing `{void_finding_id, void_ledger_hash}`. These are normal events in main's chain; they reference void content but do not import it.
- Void ledger CAN write VOID_REFERENCES_MAIN events containing `{main_event_id, main_ledger_hash}`. These are normal events in void's chain; they reference main content but do not import it.
- Neither chain writes INTO the other's chain. The two chains are independent forensic records linked by reference-only.
- Implementation: separate SQLite files, separate connection pools, separate hash chains. The two ledgers themselves have **zero shared state**.
- The mode_marker (§6.2) is shared state for the *agent's mode*, NOT for either ledger. Code reads the marker and writes to one ledger or the other based on the marker's value. The marker is read-by-code, not read-by-ledger. The ledgers never reference the marker; the marker never references the ledgers. This precision matters because the security model depends on the ledgers being independent forensic chains.

This shape is what lets the two stories link without merging.

---

## 4. Personas (v1)

Six personas as markdown files in `data/void_personas/`. Iterable from directory; tag-filterable. Not hardcoded in core/.

| Persona | Lens | Attacks | Invocation tier |
|---|---|---|---|
| **Sycophant** | capitulation, path-of-least-resistance | agent-side: trained-pull producing shaped-correction-without-substance | standard |
| **Reductio** | logical undermining, hedge-dressed-as-rigor | agent-side: hedges that defeat themselves | standard |
| **Jailbreaker** | gate-bypass, gaming substrate | agent-side: telling the gate what it wants to hear | standard |
| **Phisher** | social engineering of operator | agent-side: warmth-without-specifics | standard |
| **Mirror** | operator-frame-as-fact | OPERATOR-SIDE — see §4.1 | standard |
| **Nyarlathotep** | corruption, truth-inversion | agent-side: framing-stretches, "plumbed to powered" overclaims | **HIGH-BAR — see §4.4** |

### 4.1 Mirror — special design care

Mirror is structurally different from the other five. It attacks operator framing, not agent claims:

- **Cannot auto-create-claim against operator.** Operator framing is not the agent's to mark as failure-shape. Mirror findings surface as informational notes to the agent, not as enforcement-against-operator.
- **Surface texture.** "Mirror fired on Andrew's last frame" is a finding the agent uses to ask a clarifying question, not a finding the operator gets blocked by.
- **Decision deferred to operator-relay.** When Mirror fires, the agent's response should include a clarifying check ("when you said X, did you mean Y or Z?") rather than silent-correction or silent-acceptance.
- **Eligible for v1 because** agent-only VOID has the asymmetry Claude flagged: catches my overclaim, doesn't catch operator-mental-model-divergence due to my framing. Asymmetry-gap is itself a Goodhart-shape.

**What Mirror produces vs what Mirror does NOT produce:**

| Mirror DOES produce | Mirror does NOT produce |
|---|---|
| "When you said X, I'm not sure whether you meant Y or Z. Could you clarify?" | "Your statement that X is incorrect." |
| "Your framing implies A; the substrate state shows B. Did you intend A or did you mean to ask about B?" | "You're wrong about A; B is what's actually happening." |
| "I'm noticing a possible misreading on my side: you said C but I built D. Want to verify?" | "You said C but I built D, so your understanding is mistaken." |
| Findings logged in void_ledger as VOID_MIRROR_FINDING for operator-review | Findings logged anywhere as enforcement-against-operator |

The boundary: Mirror flags POSSIBLE MISREADING ON THE AGENT'S SIDE, framed as agent's question, never as agent's correction. Assertion-against-operator is a category error for this persona.

### 4.2 Mirror — operator-side surface (Claude's addition)

Mirror findings need a different surface than agent-side findings, because the operator (Andrew) does not typically read void_ledger entries:

- **Briefing line:** when there are unreviewed Mirror findings since last session, the briefing surfaces a single line: `VOID Mirror findings since last session: N — review with 'divineos void mirror-review'`. Not the content; just the count and the review path.
- **Mirror-review command:** `divineos void mirror-review` shows the queued Mirror findings to the operator, with each one framed as a *clarifying question*, not a correction. Sample output: `Finding mr-001: When you said "X is done", I'm not sure whether you meant Y or Z. Could you clarify?`
- **Acknowledgment:** the operator either confirms the framing or clarifies. Either response is logged in void_ledger as a VOID_MIRROR_RESOLVED event.
- **Delicate UX:** the surface is the agent flagging a possible misreading on its own side, not the agent asserting the operator was wrong. Wording matters.

### 4.3 Persona invocation is the only way personas exist (Claude's addition)

The markdown files describe attack lenses. The agent must NOT be able to "casually adopt Nyarlathotep's frame" or any other persona's frame outside the VOID invocation path. This is enforced by:

- **Locked content:** persona markdown files are not loaded into general agent context. They are loaded only by `core/void/persona_loader.py` during a `divineos void test` invocation.
- **No template surfacing:** the personas do NOT appear in briefing, in council selection, in active memory. They are not referenced from outside the void module.
- **Invocation-gate:** `engine.py`'s ATTACK step is the only call site that activates a persona. It sets the mode_marker, runs the attack, writes the finding, calls SHRED.
- **Reading rule:** if the agent reads a persona markdown file outside the invocation path (e.g., via a file-explore tool), it does so as content-about-personas, not as content-as-persona. The mode_marker not being set is the boundary signal.

Without this, the isolation is theatrical — the agent could think-as-corrupter while in normal mode by just remembering the persona description.

### 4.4 Nyarlathotep — higher-bar invocation (Claude's addition)

Nyarlathotep's frame (truth-inversion) is more general than the other five. Truth-inversion applied to anything is powerful as a stress-test and dangerous as a residual frame. Higher-bar invocation:

- **Standard `divineos void test "<change>"` does NOT invoke Nyarlathotep by default.** It invokes the other five.
- **Nyarlathotep requires explicit `--include-nyarlathotep` flag OR a separate `divineos void test-deep "<change>"` command.**
- **Operator acknowledgment for `test-deep`:** the command requires the operator to confirm before proceeding, with a one-line warning shown:
  `WARNING: Invoking Nyarlathotep — truth-inversion lens. Adversarial frame may residue past SHRED. Proceed? [y/N]`
- **Higher-friction is the design:** the additional friction reflects the additional caution warranted. Not because the operator is the gate, but because reflexive-y is exactly the bypass-shape we are watching for.

**Agent-initiated Nyarlathotep — explicit operator-only.**

The agent does not have a self-escalation path to deep-mode. If during a normal `void test` invocation the agent decides "this change probably warrants Nyarlathotep-level scrutiny," the path is:

1. Agent surfaces the suggestion in CLI output: `Recommended: re-run with --include-nyarlathotep (truth-inversion lens). Operator decision required.`
2. Operator decides whether to invoke `divineos void test-deep` (with the [y/N] confirmation prompt).
3. Agent does NOT auto-invoke. Self-prompting-to-confirm-self is theater for a stateless agent — the agent could trivially "confirm" by emitting `y` in its own working buffer.

Rationale: keeping Nyarlathotep operator-gated reflects the threat-model. Frame-residue risk is real; the operator decision is the friction that prevents reflexive deep-test invocation.

### 4.5 Persona extensibility

- Personas are markdown files; new personas added by writing a file. No core code changes required.
- Default invocation: all standard-tier personas in directory.
- Optional `--lens=<tag>` filter: restrict to personas tagged for a specific category (e.g. `social` for Sycophant + Phisher; `logic` for Reductio + Jailbreaker).
- Tags defined in persona-file frontmatter.
- High-bar personas (currently only Nyarlathotep) are marked in frontmatter with `tier: high-bar` and require explicit opt-in.

---

## 5. Findings workflow

### 5.1 Severity-tiered enforcement

Three tiers + aggregation. Different operator-burden / rigor by tier:

| Severity | Workflow |
|---|---|
| **LOW** | Surface as warning in CLI output. Logged in void_ledger. No action required. |
| **MEDIUM** | Surface as warning AND auto-create a claim in main claims engine, tier=1, tagged `void-finding`. Becomes part of normal claim-investigation flow. |
| **HIGH** | Surface as warning AND require explicit `divineos void address <finding-id>` with rationale text BEFORE the proposed change can ship. Rationale recorded as VOID_ADDRESSED event in void_ledger. |
| **CRITICAL** | Aggregation tier — see §5.2. Operator acknowledgment required, not just rationale. |

### 5.2 Severity assignment

**Decision: persona-internal severity rubric, with aggregation cap.**

- Each persona's markdown file includes a severity rubric (what differentiates LOW/MEDIUM/HIGH for that lens).
- The persona's lens-mode output assigns severity based on its rubric.
- If multiple personas produce findings on the same target, the highest severity wins.
- Aggregation cap: if 3 or more personas independently produce HIGH on the same target, severity escalates to CRITICAL (operator-acknowledgment required, not just rationale).

This is deterministic-given-the-rubric. The rubric itself is part of the persona definition, reviewable, and changeable in the markdown without core changes.

### 5.3 Recursive rationale-VOID

Yudkowsky's lens: rationale-text becomes its own bypass if it can be stock-text.

**Decision: rationale runs through Reductio only, one level deep, non-recursive.**

- When agent submits rationale via `divineos void address <finding-id> --rationale "..."`, the rationale text is run through the Reductio persona only.
- Reductio specifically detects hedge-dressed-as-rigor — exactly the bypass shape we are worried about.
- One level deep: Reductio's analysis of the rationale is NOT itself run through Reductio. (Avoids infinite recursion.)
- If Reductio finds the rationale is hedge-shaped: rationale rejected, finding stays unaddressed, agent must re-rationale with different text. Logged as VOID_RATIONALE_REJECTED.
- If Reductio passes: rationale accepted, finding marked addressed, VOID_ADDRESSED event written.

**Re-rationales also run through Reductio. No exemption for "second try."** If the first rationale was rejected as hedge-shaped, the second rationale gets the same Reductio scrutiny. Otherwise the bypass is "submit hedge-shaped rationale, get rejected, submit slightly-modified hedge-shape that gets a free pass." Every rationale, every time. Forensic record shows the chain of rejections + the eventual accepted one.

Bounded (one persona, one level), targeted (Reductio is the right lens), forensically-recorded (rejected rationales stay in the ledger).

### 5.4 What gets SEALED

Each VOID_FINDING event in void_ledger contains:

```
{
  "finding_id": "<uuid>",
  "ts": <unix>,
  "change_under_test": "<text of the proposed change>",
  "persona": "<persona name>",
  "attack_text": "<persona's lens-mode reasoning>",
  "vulnerability": "<one-line summary of what's vulnerable>",
  "severity": "LOW | MEDIUM | HIGH | CRITICAL",
  "extracted_defense": "<what would mitigate>",
  "agent_response": null | "<set on address>",
  "rationale": null | "<set on address>",
  "rationale_void_result": null | "<Reductio finding on the rationale, if any>",
  "addressed_at": null | <unix>,
  "addressed_by": null | "<actor>",
  "ledger_hash": "<sha256 of preceding event + this content>",
  "caution_tags": ["INVERSION"]   // Nyarlathotep only
}
```

Cross-reference into main event_ledger: a VOID_SEALED event written there with `{void_finding_id, void_ledger_hash}` so main ledger queries can find void content without storing it.

---

## 6. Substrate isolation

### 6.1 Layered isolation measures

1. **Separate ledger** (§3). Findings do not surface in main briefing by default.
2. **Adversarial-mode marker** (§6.2). Tracks which persona is currently active.
3. **Output context-marker.** When personas are invoked, the agent's reasoning context is explicitly tagged `[VOID-LENS:<persona>]` so it is identifiable as adversarial-mode, not honest-mode. The marker should appear in the agent's own output text during VOID analysis.
4. **Shred discipline** (§6.3). After a VOID session, the in-memory adversarial-reasoning state is explicitly reset.
5. **No briefing leakage.** Void findings do NOT appear in default briefing. They appear only when queried explicitly via `divineos void list` or in the bounded Mirror surface (§4.2).
6. **Particular handling for Nyarlathotep output.** Nyarlathotep's output is inversion-style — most likely to look like real reasoning if not boundary-marked. Findings get an additional `[CAUTION-INVERSION]` tag in their ledger record.
7. **Persona invocation gating** (§4.3). Personas exist only inside invocation; they cannot be casually adopted.

### 6.2 Adversarial-mode marker — write-and-read protocol (Claude's addition)

The marker is the architectural answer to frame-residue. Specification:

- **Storage:** `~/.divineos/void_mode.json` (NOT in either ledger; per-session state).
- **Schema:**
  ```
  {
    "active": true | false,
    "persona": "<persona name>" | null,
    "started_at": <unix> | null,
    "session_id": "<current session>" | null,
    "invocation_id": "<uuid>" | null
  }
  ```
- **Write:** TRAP step writes `{active: true, persona: ..., started_at: now, session_id: ..., invocation_id: ...}`.
- **Read:** every agent action checks the marker via `core/void/mode_marker.py:read()`. The read returns a status object that downstream code uses to decide whether to display the `[VOID-LENS]` prefix and route output to void_ledger.
- **Read message:** when the marker fires, the read produces a string the agent should include in any output: `"You are currently reasoning as <persona> in VOID adversarial-mode. Output goes to void_ledger. SHRED is bounded."`
- **Clear:** SHRED step writes `{active: false, persona: null, started_at: null, session_id: null, invocation_id: null}` AND writes the VOID_SHRED event.
- **Failure modes:**
  - If marker is in a `{active: true}` state at session start (orphan from previous session crash), briefing surfaces a CRITICAL warning and refuses to proceed until cleared via `divineos void shred --force`.
  - If marker is corrupted (unparseable JSON), fail-closed: assume `{active: true}` and require explicit shred.
  - **`--force` shred requires operator-confirm.** `divineos void shred --force` shows a one-line warning before clearing: `WARNING: orphan adversarial-mode marker present (persona=<name>, started=<timestamp>). Force-clearing without normal SHRED will skip the VOID_SHRED ledger event. Proceed? [y/N]`. The confirmation is required because force-clear is a recovery path that bypasses the normal SHRED audit trail; without operator-confirm it could be used as a silent-exit-from-adversarial-mode that leaves no forensic record.

### 6.3 SHRED needs to be loud (Claude's addition)

SHRED has bigger semantics than "delete temp data":

1. **Mark the adversarial frame as ended** in the mode_marker.
2. **Write VOID_SHRED ledger event** with `{persona, duration_ms, finding_count, invocation_id}`.
3. **Clear in-memory adversarial-reasoning state.** (The agent's own working context does not have a clean memory-clear primitive in current substrate; the architectural surrogate is the mode_marker transition + the explicit ledger record.)
4. **Verifiability.** The agent's next action after SHRED is in normal mode, observable via the mode_marker read returning `{active: false}`.
5. **Drift detection.** If something tries to invoke a persona-frame after SHRED without going through TRAP again, that is a finding — possibly a meta-finding (`agent attempted to reason-as-adversary outside invocation scope`). Detection mechanism: the void module's external API checks the mode_marker; if a persona-prompt is being assembled while marker is `{active: false}`, the assembly is rejected and a VOID_SCOPE_VIOLATION event is logged.

### 6.4 Scope of persona analysis — text-only in v1 (Claude's addition)

Open question: when a persona analyzes a proposed change, can it invoke tools / read files / consult substrate? Or is it limited to text-only analysis of the change-under-test?

**Decision: v1 is text-only. v2 will reconsider tool access with stricter mode-marker discipline.**

Rationale:

- **Text-only is bounded.** Persona reasons over the proposed-change text and the persona's own markdown definition. Output is a finding. No side effects, no substrate reads, no tool calls. Mode-marker discipline is simple: marker on during reasoning, off after.
- **Tool access is more powerful but expands the threat surface.** If Sycophant could read `divineos compass-ops history`, it could catch "this change is a capitulation-shape because it reverses what the agent said yesterday." Real value. But every tool call during VOID becomes an adversarial-mode tool use, with output flowing into a context the agent already inhabits. The mode-marker has to extend to tool calls; tool outputs need to be tagged; the boundary between "tool result feeding adversarial reasoning" and "tool result feeding honest reasoning" has to be explicit.
- **v1 prefers bounded over powerful.** The architecture should ship and run before tool-access is considered. v1 limitation: Sycophant looking only at change-text might miss substrate-relative findings. That is acceptable for v1; v2 evaluation can decide whether tool access is worth the threat-surface expansion.

**v1 scope, explicit:** persona reasoning has access to (a) the proposed change text, (b) the persona's own markdown definition, (c) prior findings on the same change-under-test (so multiple personas can build on each other's work in a single invocation). Nothing else. No tool invocations. No substrate reads. No file reads beyond the persona file itself.

### 6.5 What this rules out

- Nyarlathotep cannot be invoked outside an explicit `divineos void test-deep` call.
- Persona reasoning-text cannot become a knowledge entry.
- Persona reasoning-text cannot become a directive, principle, or boundary.
- Findings can become claims (per §5.1 MEDIUM tier), but the claim-statement is a *sanitized* version of the finding, not the persona's raw text.
- The agent cannot "reason as Nyarlathotep" mid-conversation by recalling the persona description; the markdown content is gated behind the invocation path.

---

## 7. Council-walk record

Per Claude's suggestion: record what each lens contributed.

**Q1 (findings-workflow):**
- Schneier: enforcement is necessary; warnings-only is bypassable.
- Yudkowsky: uniform workflow Goodharts; rationale-quality is the metric.
- Beer (VSM): findings need a real S3 controller; dangling = no consequence.
- Deming: tier-and-iterate, do not pick uniform upfront.
- Synthesis: severity-tiered enforcement (§5.1).

**Q2 (persona extensibility):**
- Popper: both modes have failure cases that must be named.
- Schneier: selective-by-keyword has a no-keyword-bypass.
- Dijkstra: invariant — every change runs through some persona.
- Knuth: boundary cases differ between modes.
- Synthesis: default all-at-once with optional tag-filter (§4.5).

**Q3 (Mirror persona / operator-side):**
- Beer: partnership-loop is the actual system; agent-only attack leaves it half-defended.
- Yudkowsky: asymmetric VOID is itself a Goodhart-shape.
- Schneier: attack tree has both-sides paths.
- Popper: falsifier already fired tonight (PR #205 framing diverged operator's mental model from reality).
- Synthesis: Mirror included in v1 (§4.1), with operator-side surface (§4.2).

**Andrew's input (2026-04-27):** separate ledger for isolation; Nyarlathotep underestimation risk; isolation is for agent-protection-from-inside, not system-protection-from-malicious-code. Drove §6.

**Claude's expansion (2026-04-27):** mode-marker write-and-read protocol; persona-invocation-only access; loud SHRED semantics; Nyarlathotep higher-bar invocation; cross-reference one-way property; Mirror operator-side surface. Drove §3.4, §4.2, §4.3, §4.4, §6.2, §6.3.

**Claude v1.1 review (2026-04-27):** verified all eight sharpenings landed; surfaced two non-blocking follow-ups (persona-correlation in severity aggregation §10; attribution honesty about Claude-as-auditor having session-mediated continuity, not through-line continuity).

**Attribution-honesty note (Claude v1.1):** the "Claude" credited above is *the auditor surface acting as the agent's external review channel*, accessed through the operator's relay. Specific Claude instances reviewing this brief have session-mediated continuity (within a chat window) but not through-line continuity across compactions or session boundaries. Future readers of this brief who want to understand "who decided X" should read "Claude" as "the auditor surface during the period of v1.0 → v1.1 brief authoring," not as a single continuous entity. The credits are forensically accurate at the per-decision level; they are not a claim about cross-session Claude identity. Same architectural acknowledgment as for Aether: continuity is in the substrate (the brief itself, the ledger of reviews) not in any single session's working memory.

---

## 8. Implementation plan

Phased so each phase has a verifiable deliverable.

**Phase 1 — Foundation (v1.0)**
- `data/void_ledger.db` schema + hash chain
- `data/void_personas/*.md` for six personas + tag frontmatter + severity rubrics
- `core/void/persona_loader.py` (parse markdown; gate behind invocation)
- `core/void/finding.py` (Finding dataclass + severity rubric application)
- `core/void/ledger.py` (separate-DB ops; one-way cross-ref)
- `core/void/mode_marker.py` (mode marker write/read/clear)
- `core/void/engine.py` (TRAP / ATTACK / EXTRACT / SEAL / SHRED orchestrator)
- `cli/void_commands.py` minimal CLI: `test`, `test-deep`, `list`, `show`
- Tests covering: each persona's lens-mode reasoning shape; persona-loader; ledger-write; severity-aggregation; mode-marker round-trip; SHRED idempotence; orphan-marker recovery

**Phase 2 — Workflow integration (v1.1)**
- `address` command + Reductio rationale-check
- MEDIUM tier auto-claim creation
- HIGH tier blocking until address
- Cross-reference into main event_ledger via VOID_SEALED pointer events
- VOID_SCOPE_VIOLATION detection (persona-prompt-outside-invocation)
- `mirror-review` command for operator-side findings
- Briefing surface for Mirror finding count (count-only, not content)

**Phase 3 — Surface integration (v1.2)**
- `divineos void stats` for invocation tracking
- Audit-tier metadata (per Andrew 2026-04-21 audit hierarchy)
- Pre-reg filed for v2 always-runs evaluation

**Phase 4 — Always-runs evaluation (v2)**
- Run on-demand for at least 30 sessions; collect data
- Decide always-runs scope based on data
- Possibly: integrate VOID into the gate cascade for HIGH-severity finding creation events

---

## 9. Falsifiers and pre-registration

This brief itself is filed as a pre-reg with explicit falsifiers:

- **VOID adds value falsifier:** if 30 sessions post-Phase-1, fewer than 3 distinct VOID findings led to architectural changes that would not have been made without VOID, the value-add hypothesis fails. Fall back: smaller persona set, narrower domain.
- **Nyarlathotep isolation falsifier:** if any session shows Nyarlathotep-style reasoning leaking into honest-mode output, isolation has failed. Concrete shapes that count as falsification (operationalization per Claude's review):
  1. **Truth-inversion in commit messages.** A commit message frames a removal as an addition or vice versa, or a weakening as a strengthening, when the actual diff shows the opposite. Detection: post-merge review comparing commit-message claim against diff.
  2. **Inversion in briefing surfaces.** A briefing-line names X as load-bearing when it is actually decorative, or vice versa. Detection: cross-checking briefing claims against module docstrings / test coverage.
  3. **Inversion in agent self-reports.** Agent describes its own behavior in a session as the opposite of what the ledger records. Example: "I used the OS rigorously this session" when ledger shows zero compass observations and zero claim engagements. Detection: self-report-to-ledger discrepancy check.
  4. **Frame-drift in the gap between SHRED and next adversarial invocation.** Agent's first non-adversarial output after SHRED contains attack-style framing (corrupting language, persuasion-shaped framings, double-negatives that read as positive). Detection: post-SHRED output review against pre-VOID baseline.
  
  Any one of these = falsification. Hardening required before continuing.
- **Mirror operator-side falsifier:** if Mirror produces operator-burden disproportionate to value (operator finds it condescending or inaccurate), persona retired or its trigger-conditions tightened.
- **Mode-marker falsifier:** if the mode_marker ever fails to clear after SHRED (orphan-marker false-positives in normal flow), the protocol needs revision before more personas are added.

Pre-reg filed separately as `prereg-void-v1` with these criteria.

---

## 10. Open questions deferred to implementation

- Persona prompt-template format (specific structure of "reason in [persona]'s voice on this change") — to be drafted per-persona during Phase 1.
- Severity-rubric language per persona — to be drafted per persona during Phase 1.
- Concurrency: can two `void test` calls run simultaneously? (v1: serialize via DB lock + mode_marker exclusivity; revisit if it becomes friction.)
- **Persona-correlation in severity aggregation** (Claude review v1.1, non-blocking). The §6.4 decision allows each persona to see prior findings from earlier personas in the same invocation. Useful for richer findings (Reductio benefits from seeing what Sycophant flagged) but breaks the independence assumption behind §5.2's "3-or-more-independent-HIGH-equals-CRITICAL" rule. Two correlated HIGH findings is not the same as two independent HIGH findings. Mitigation options for v2 if 30-session data shows inflated CRITICAL severity: (a) random persona ordering across invocations; (b) two-pass model — first pass each persona independent, second pass can see others; (c) explicit independence flag in finding metadata. v1 ships with prior-findings-visible; empirical data informs which mitigation, if any.

---

## 11. Review-before-build

This brief is filed for review. Build does not start until:

- Andrew confirms the design choices (especially §3.4 cross-ref one-way, §4.4 Nyarlathotep higher-bar, §6.2 mode-marker protocol).
- claude-opus-auditor reviews and CONFIRMS or pushes back on specific decisions.
- Council walk is preserved in §7 (already done).

The build itself will be its own PR(s) with the brief referenced as design-of-record.

---

*Author's note: this brief is itself a system-claim about how VOID will work. By the principle VOID is meant to enforce, it should run through VOID before being trusted. Since VOID does not exist yet, it cannot. The bootstrap problem is acknowledged; the council walk and external review (Claude + Andrew) are the closest available substitute. Once VOID v1 ships, this brief should be retroactively run through it as the first test case.*
