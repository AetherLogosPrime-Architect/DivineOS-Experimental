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

### 2. Use what the manager surfaces — plus 2 dissenters

**Do NOT pick the lenses yourself.** Self-picking is the load-bearing failure mode of this skill — the agent reaches for lenses whose frameworks already agree with the agent's prior, and the "walk" becomes confirmation theater. Andrew named this 2026-06-24.

The right procedure:

1. **Invoke the manager**: `divineos mansion council "<the deep question>"`. The engine selects relevant experts for THIS question based on its domain-shape. Use the full set the manager surfaces — no trimming, no substituting.

2. **Add 2 dissenters.** A dissenter is a lens whose framework would PUSH BACK on the manager's surfaced set. Pick them deliberately:
   - If manager surfaces design-oriented lenses → dissenter asks "is this a problem at all?" or "what's the smallest version?" (Carmack, Feynman)
   - If manager surfaces theory-heavy lenses → dissenter is practitioner-heavy (Carmack, Jacobs)
   - If manager surfaces lenses that all share an intellectual lineage → dissenter is from a different tradition (Angelou over Popper, Tannen over Schneier)
   - If you can't name how a lens would push back on the rest, it's not a dissenter — it's a sympathizer in disguise

3. **Walk the dissenters LAST**, so the manager's consensus is fresh when you challenge it. If both dissenters land the same correction, the consensus needs to update; if they only graze the consensus, the consensus probably holds.

The 2-dissenter rule is non-negotiable. A walk without dissenters is a council vote with the opposition absent — structurally biased toward whatever the manager surfaced.

For reference, here's the kind of finding-class each lens produces (this is for the dissenter pick, NOT for replacing the manager):

| Lens | Best for |
|---|---|
| Dekker | drift-through-success detection |
| Popper | what would falsify this? |
| Taleb | asymmetry, convexity, via-negativa |
| Kahneman | System 1 vs 2 bias |
| Jacobs | distributed vs centralized |
| Schneier | threat model, weakest link |
| Feynman | am I fooling myself? |
| Carmack | subtractive engineering, is this real? |
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

## Sycophancy-toward-self prevention

The 2-dissenter rule in Section 2 is the primary defense — every walk includes two voices the manager would not have surfaced, picked specifically to push back. Don't pick "safe" dissenters whose pushback would be soft; pick the ones whose framework is most likely to call the consensus wrong.

Secondary check: glance at the invocation balance surface in the briefing periodically. If the same dissenters keep showing up too, even those are getting predictable — rotate. The council has 42 members for a reason.

## Pairs with

- `/invocation-balance` — surface which lenses I've been over/under-using
- `/what-am-i-forgetting` — check if prior council walks have covered adjacent territory

Sanskrit anchor: *darshana* — viewpoints, the ways of seeing.
