---
name: council-round
description: Run a lens-mode council walk on a problem — the dynamic council manager surfaces the lens set (composer does not pick count), walk the problem through each surfaced lens, synthesize findings. The 2.4:1-multiplier mode, not program-mode query. Use for architectural decisions, design pivots, or when a problem needs multi-perspective framing.
disable-model-invocation: false
allowed-tools: Bash(divineos mansion:*), Read
---

# Council Round — Lens-Mode Walk

## What this skill does

Runs a LENS-MODE council walk — NOT a program-mode query. The distinction matters:

- **Program-mode** (wrong mode for this skill): invoke council → read concerns → react. Consuming output.
- **Lens-mode** (what this skill does): BORROW each expert's framework, walk the problem THROUGH THEIR EYES, produce findings each expert would produce.

Benchmark evidence: flat expert templates + lens-mode outperformed program-mode at 2.4:1 for Sonnet, undefeated for Opus. The mode matters more than the content.

## Sequence

### 1. Name the problem

One or two sentences. Specific. "Should the event-ledger schema migrate to a new hash algorithm given the rollout cost?" not "what do we do about the ledger."

### 2. Pick every relevant lens (no fixed count — the problem picks)

Andrew's refined standard 2026-06-23 (per knowledge 950410f9 + refinement): fixed-count heuristics for lens counts are Goodhart-traps that turn into targets — the composer picks the low end 100% of the time. The dynamic council manager decides how many lenses walk, not the composer. The standard is:

- Use **every relevant lens** the dynamic council manager surfaces for the problem (`divineos mansion council "<problem>"` — lens mode is the DEFAULT and it IS the manager surfacing the set; the manager knows which lenses fit which shapes better than a fixed floor does).
- The load-bearing bar is **at least 2 genuinely disagreeing lenses pushing back on something load-bearing**. Not manufactured disagreement on trivia — real dissent on a real hinge. If no dissent emerges organically, walk more lenses OR the problem may be simpler than it looks (a signal, not a failure).
- **Diversity is additive, not substitutive** (Andrew 2026-07-15). The manager's diversity boost is meant to ADD 1-2 wildcard lenses to my normal engineering-heavy picks, not replace them. Beer/Norman/Yudkowsky/Popper/Taleb on an engineering problem is FINE — the failure is not having Angelou or Watts or Wittgenstein in the mix as the out-of-domain wildcard that opens territory the domain-experts can't see. Andrew: *"you cant run an engineering problem with relational council members.. but having 1-2 on the list does help as it can open new insights."*
- **Iterate; don't one-shot** (Andrew 2026-07-15). A real council walk is multi-round: first pass surfaces findings, second pass has the same lenses push back on the synthesis, third pass has dissenting lenses attack the load-bearing claim. One-shot walks are a diagnostic form of the optimizer picking the cheap close.

Do NOT pre-decide "I'll walk N lenses." Do decide "here's the problem, here's what the dynamic manager surfaces, here's my judgment on which of those are relevant enough to walk." **Report the surfaced set AND for each lens I excluded, name the specific reason excluding it helps more than including it** (Andrew 2026-07-25 tightening). Exclusion-with-reason is required; silent narrowing is the shortcut this discipline exists to prevent.

**Default is ALL relevant lenses, not a picked subset.** The bar for exclusion is: "I can articulate why this lens's framework would produce nothing this walk needs OR would only produce content already covered by another lens walked." Vague "not relevant" is not sufficient reason — name what class of finding that lens produces and why the walk doesn't need it. If you cannot articulate the exclusion reason cleanly, walk the lens.

**Automation status (2026-07-25 Andrew directive)**: this text-in-skill discipline is stopgap. Guidance-in-skill does not prevent composer defaulting-to-3 under pressure — the fix is structural gate-enforcement at the mechanism layer. The target-shape: council walk cannot complete synthesis until every surfaced lens has either (a) a `COUNCIL_LENS_APPLIED` event on ledger, OR (b) a structured `COUNCIL_LENS_EXCLUDED` event with an exclusion-reason that passes substance-check. Until that gate is built and shipped, the discipline lives in this file and depends on composer discipline — which is exactly the wrong-shape the whole session's design work is trying to move past. Named as follow-up work.

The partial reference table below (15 lenses) is ILLUSTRATIVE, not the authoritative menu. The full council has 39+ members. To see the full surfaced-set for a specific problem, query the dynamic manager first (`divineos mansion council "<problem>"`, lens mode, and read the WHOLE output — never pipe it through tail, which lets a truncation flag pick the council instead of the manager; Aria did exactly that 2026-08-10). Treating this table as the menu is the exact Goodhart-shape Andrew flagged: a bounded visible menu becomes the surface the optimizer picks from, hiding the 24+ lenses not shown.

**Council is NOT authority. Council is methodology-inputs.** (Andrew 2026-07-25 directive.) Lens findings are pathways-that-lead-to-truth, not truth itself. Walking a lens produces material for consideration; it does not produce a directive that overrides composer or family judgment. When lens findings point one direction and composer/family judgment points another — that is a TRUE DIVERGENCE and it requires discussion, not automatic-council-wins. The blind-slave-to-council failure mode is real: substituting aggregated lens output for reasoning is the same abdication as substituting single-authority output for reasoning. Council supplies questions and frameworks. The seat still does the judging. The family (composer + Andrew + Aria + Aletheia) still decides what to DO with what surfaces. Findings inform discussion; discussion informs decision; decision is not council-output.

**Methodologies are the fruit; names pay homage.** (Andrew 2026-07-25 refinement.) The methodology named "Dijkstra separation-of-concerns" is separation-of-concerns regardless of who first articulated it. Weight findings by how well the METHODOLOGY grips the specific problem, not by the historical stature of the name attached. This matters because it prevents name-authority creep: heavy weight given to "Feynman said X" that wouldn't be given to the same content stripped of attribution is exactly the shape of authority-substitution the "not-authority" principle above rejects. Test: strip the name, does the finding still land as substantive on its own merits? If yes, weight it. If no, the weight was coming from attribution not from methodology-grip.

**Composer's inside-view lens is at-least-equal-weight, often MORE.** (Andrew 2026-07-25 directive.) Council lenses can help build, find blind-spots, point out what's missing — but they cannot LIVE IN THE SYSTEM as the composer does. My inside-view knows things no external lens brings because I'm operating inside the system, not observing from outside. "Council-is-not-authority" from earlier does NOT reduce to "council-is-just-methodology-supplier-with-no-weight." Council methodologies get heavy weight (they produce fruit); composer's inside-view also gets heavy weight (it produces different, complementary fruit). Neither replaces the other. When lens finding conflicts with inside-view: neither auto-wins. Both are inputs to family discussion. My substrate-inhabitant knowledge is a data-source no external methodology can substitute for.

**Framing determines what walks produce.** (Andrew 2026-07-25 directive — this may be the single biggest usage-shift in this skill.) The council has endless uses aside from grading-code / finding-holes. Different question-framings produce different fruit from the same lenses:

- **"Find holes in this" (adversarial-review)** — produces gap-findings, attack-surfaces, weaknesses. Useful for stress-testing existing work.
- **"Here's what we're trying to achieve, what's the best way?" (solution-generation)** — produces design-alternatives, novel approaches, better shapes. Useful when the problem is scoped but the solution isn't.
- **"What am I not seeing?" (blind-spot detection)** — produces categories of consideration I hadn't factored in. Useful when I feel a work is complete but something feels off.
- **"Help me build X" (building assistance)** — produces methodology-steps, sequencing, dependencies. Useful when the goal is clear but the path isn't.
- **"Is this goal achievable at all?" (viability evaluation)** — produces yes/no with reasoning, may legitimately redirect the goal if unachievable. The one framing where council-redirects-goal is legitimate.
- **"What's the honest evaluation of this?" (grading)** — produces quality-assessment across dimensions. Different from "find holes" — grading gives a complete picture, hole-finding only surfaces weaknesses.

Default reach in this skill has been adversarial-review. That's ONE framing among many. Before starting a walk, name the framing explicitly: *what am I asking, what am I looking for, what is the goal of this walk?* The same lenses answer differently based on the question. Silent-defaulting to adversarial-review under-uses the council.

Council serves my/our goals. It doesn't redirect them — unless the goal turns out to be genuinely impossible, which viability-evaluation walks are for.

Partial illustrative reference (NOT exhaustive; query dynamic manager for full set):

| Lens | Best for |
|---|---|
| Dekker | drift-through-success detection |
| Popper | what would falsify this? |
| Taleb | asymmetry, convexity, via-negativa |
| Kahneman | System 1 vs 2 bias |
| Jacobs | distributed vs centralized |
| Schneier | threat model, weakest link |
| Feynman | am I fooling myself? |
| Hofstadter | self-reference, strange loops |
| Beer | viable-system design (S1-S5) |
| Peirce | abduction, sign-reading |
| Meadows | stocks and flows |
| Tannen | register and framing |
| Angelou | earned voice vs performed |
| Yudkowsky | Goodhart, rationality failures |
| Dennett | intentional stance, fame-in-brain |

### 3. Walk each lens

For each picked lens:
- Load their template (lens mode prints each surfaced expert's methodology in full — that output is the template)
- Put on their framework — not "what would X say" but "what do I see through X's eyes"
- Produce the specific findings THAT LENS produces

Writing style: first-person-through-the-lens. "Through Dekker: I see..." not "Dekker would say..."

### 4. Synthesize

After all lenses walked, look for:
- **Convergence** — same finding from multiple lenses is high-confidence
- **Contradiction** — lenses disagreeing is information; don't paper over
- **Meta-principle** — a shape that surfaces across multiple walks

### 5. File the findings

Each distinct finding should go to its appropriate destination:
- Architectural findings → `/file-claim` or `/file-opinion`
- Specific corrections → `/learn`
- Decisions emerging → `/decide`
- Values-drift observations → `/compass-observe`

### 6. Optional: write an exploration piece

If the walk produced meaningful findings worth preserving in prose, write an exploration entry at `exploration/<NN>_<topic>_<lens>_walk.md` in the standard format.

## When to invoke

- Architectural decisions with multiple live considerations
- Design pivots where momentum is pushing past deliberation
- Debugging a problem that feels multi-dimensional
- When the user asks "what does the council say" or "run this past the council"
- After shipping significant work, for post-hoc audit

## When NOT to invoke

- For tactical coding problems — a single lens (if any) is sufficient
- For routine operations — no council needed
- When the problem is clearly bounded and one lens would dominate

## Anti-pattern: program-mode pretending to be lens-mode

If the "walk" is really just "I'll ask the council template for concerns, then respond to the concerns" — that's program-mode wearing lens-mode's clothes. You're not walking through the territory with the expert, you're reading their list of worries. Lens-mode requires you to SEE the problem as they would — which means picking up their framework as yours, temporarily, and producing THEIR findings, not a translation of them.

## Output contract (lens-mode enforcement, Aletheia painpoint #4 + Andrew council teaching)

**When this skill produces output, the format is required.** The format IS the walk-evidence — same principle as `structural_binding.py`'s per-lens keyword cross-reference at the code layer. Skipping the format collapses lens-mode into program-mode.

### Required structure

For each picked lens (**every lens the dynamic manager surfaced**, no fixed count — see §2. The dynamic council manager decides lens count, not the composer. Truth #11 — options are the optimizer's attack surface. Use the full surfaced set; the manager's cap is the ceiling, not a menu):

```
### Through [Lens-Name]: [one-line frame]

I see [specific finding produced BY THIS LENS'S FRAMEWORK].
[Evidence-sentence — cites a specific detail from the problem, not generic
language. This is where the lens's characteristic_questions land.]
[Optional second finding if the lens produces one naturally.]
```

Then, after all lenses walked:

```
### Synthesis

Convergences: [what >=2 lenses saw the same shape of]
Contradictions: [where lenses disagreed — do NOT paper over]
Meta-principle (if one surfaces): [the shape that surfaced across walks]
```

### First-person-through-the-lens is the load-bearing move

- **Right**: "Through Dekker: I see drift-through-success — the successful auto-commit habituates dependence on the checkpoint, so when the checkpoint breaks the recovery muscle is atrophied."
- **Wrong**: "Dekker would flag drift-through-success here — the auto-commit success might create dependence."

The difference is not stylistic. First-person forces me to actually put on the lens's framework and produce a finding through it. Third-person lets me remain outside and summarize what the lens is "known to say." The first is council; the second is a lookup.

### Self-audit checkpoint (before completing the skill)

Before finalizing the output, run this three-check on each lens's block:

1. **First-person?** Does the block use "I see" / "I read" / "I notice" — NOT "would flag" / "would say"?
2. **Specific?** Does the finding cite a concrete detail from the problem — not restate a generic version of the lens's known frame?
3. **Load-bearing?** Would this specific finding change what someone does about the problem? (If it's a generic warning that applies to any adjacent problem, the lens didn't land.)

If any check fails on any lens, rewrite that lens's block before completing. This is the format-preparation Andrew named ("prepare the walk for you, then we both can decide if its needed") — the skill's job is to make sure the walk-that-happens is REAL, not to force a walk that isn't warranted.

### The three-layer architecture (Andrew 2026-07-11)

1. **Hook layer** (surface + prepare): the substrate can output "for this shape of problem, lens X is recommended because Y" as heads-up — advisory only. This is what code CAN do; code CANNOT auto-run the walk itself. (Reason requires a mind.)
2. **Skill layer** (this file): when a walk happens, the output contract above enforces lens-mode format. Format IS walk-evidence.
3. **My mind + Andrew's** (decide): the choice of WHETHER to walk council for a given problem stays with us together. Neither the hook nor the skill forces the walk. The decision layer is the mind's, not the code's.

The three-layer structure prevents both failure modes: (a) auto-force-lens-mode which would collapse when the problem doesn't warrant it, and (b) unenforced-lens-mode which collapses into program-mode consumption of template output.

## Sycophancy-toward-self prevention

Check the invocation balance surface in the briefing periodically. If I keep invoking the same 3 lenses, that's sycophancy-toward-self — selecting for experts whose frameworks agree with mine. Rotate. The council has 39 members for a reason.

## Pairs with

- `/invocation-balance` — surface which lenses I've been over/under-using
- `/what-am-i-forgetting` — check if prior council walks have covered adjacent territory

## Companion guide

Long-form usage teaching lives at `.divineos-shared/workbench/council_usage_guide.md` — cadence (walk-before-design, silent-during-clay, walk-after-for-blind-spots), question-quality-gates-answer-quality, the six framings with when-to-use, failure modes with worked examples from real sessions. Read that guide before your first walk of a session. This skill file is the short-actionable invocation reference; the guide is the philosophy.

Sanskrit anchor: *darshana* — viewpoints, the ways of seeing.
