---
name: council-round
description: Run a lens-mode council walk on a problem — pick N members whose frameworks best fit, walk the problem through each lens, synthesize findings. The 2.4:1-multiplier mode, not program-mode query. Use for architectural decisions, design pivots, or when a problem needs multi-perspective framing.
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

Andrew's refined standard 2026-06-23 (per knowledge 950410f9 + refinement): drop the "3-5 sweet spot" and drop "minimum N" — both are Goodhart-traps that turn into targets. The standard is:

- Use **every relevant lens** the dynamic council manager surfaces for the problem (`divineos mansion council --for-problem "<problem>"` or equivalent — the manager knows which lenses fit which shapes better than a fixed floor does).
- The load-bearing bar is **at least 2 genuinely disagreeing lenses pushing back on something load-bearing**. Not manufactured disagreement on trivia — real dissent on a real hinge. If no dissent emerges organically, walk more lenses OR the problem may be simpler than it looks (a signal, not a failure).

Do NOT pre-decide "I'll walk 4 lenses." Do decide "here's the problem, here's what the dynamic manager surfaces, here's my judgment on which of those are relevant enough to walk." Report the surfaced set and the walked subset; if you narrowed, name why.

Pick based on what class of finding each would produce:

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
- Load their template (`divineos mansion council --show <name>` or internal lens knowledge)
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

For each picked lens (3-5 lenses total):

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

Sanskrit anchor: *darshana* — viewpoints, the ways of seeing.
