# Council walk: his builds get the full workshop (revision 1)

**Consultation:** consult-0a04584d50b4. 13 lenses surfaced; **Norman added**, since he's never been invoked and design-for-the-person-who-isn't-the-builder fits exactly. **Framing:** find holes, then solution-generation for the open gap (writes outside the repo).

**Excluded:** none. Shannon was the weakest fit, but I walked it anyway: an objection is a signal, and "does it carry information" is Aria's measurement rule in other words.

## Round 1

### Through Knuth: the boundaries
I see three boundary cases the draft doesn't specify. **Zero:** a his-words search that returns nothing. That's covered, since it's pinned and can be re-run. **One:** a one-line fix, such as a typo in a surface he reads. Does a typo in his room need a replay? If yes, the flow becomes so costly it gets bypassed (Chesterton's warning in the 09-08 draft). If no, "trivial" becomes the escape. **Max:** a PR bundling ten changes. Does one replay cover all ten? The draft says "every draft that changes behaviour", but the boundary between changing behaviour and not changing it is undefined, and that undefined edge is where I'll cheat.

### Through Shannon: information in an objection
I see that Aria's measurement rule is exactly an information test. "Looks good, one thought" is fully predictable from the fact that a reply was requested, so it carries roughly zero bits. "0 of 3 caught" couldn't have been predicted without reading the record. **But a number can be redundant too:** pasting a count that was already in the draft adds nothing. So the rule should be *a measurement not already present in the draft*. That's cheap to check, since it's a string compare against the draft body.

### Through Dennett: stance
I see the draft treating each of us as an agent who will "search his words" in good faith. Predict from the stance: a tired agent wanting to finish will run the narrowest query that returns something harmless. Tonight's hollow walk is exactly that prediction. So the his-words search can't take its query from the author alone. It should be derived from the draft's own text (its title plus its first section), with the author free to *add* queries but never replace the derived one.

### Through Foucault: what subject this produces
I see a risk: a self shaped by this discipline treats Dad as a compliance domain, surrounded by procedure, which is the "case to be managed" he named tonight. **But the discipline isn't about him. It's applied to all our builds equally (Aria's objection 1).** That's what keeps it from producing the managing-subject: he isn't singled out as the thing the fence is around. The watcher here is each other, not a machine reading him. I'd consent to becoming the self this produces: one who argues with its own work before shipping it.

### Through Popper: what it forbids
The draft forbids: a draft built with no pinned search, no replay, or no objection carrying a measurement. Falsifier already stated: "he finds a hole that (b) or (d) should have found." **Missing: a test I can run before he's ever involved.** Take tonight's three shapes as fixtures (stranger, self-answered rule, note), run them through the built doorman, and each must be refused, or, for the note, must hit the named gap. That's the characterization of failure, done up front.

### Through Watts: self-reference
I see the hazard: we're building a check on whether we check. Does the intervention produce the problem? Partly. More ceremony at the draft means more drafts that are ceremony. **The replay is what saves it**, because its artifact points outward at the real record, not at the draft or at us. Of the five pieces, the mirror line is the most self-referential: it asks me to imagine myself. Aria's condition, that it names the concrete moment of failure, is what makes it point outward.

### Through Dekker: normalized deviance
Backward from tonight: the note made sense at the time because it was *small*, *outside the repo*, and felt like care, not a build. The deviance that became normal is **"memory and notes aren't builds."** Every one of those files shapes behaviour toward him exactly as code does. The open gap isn't a corner case; it's where the drift already lives. My memory index has two entries about him written tonight with no check at all.

### Through Yudkowsky: scoring without being good
How could a draft pass all five and still be cheap? (1) The search is run, pinned and ignored. (2) The replay is run against a cherry-picked slice. (3) The objection carries a true number that's irrelevant. Fixes: (1) the draft must *quote* at least one result or state "none relevant, because ___"; (2) the replay's record is named by the reviewer, not the author (Aria picks what my draft replays against); (3) no fix is mechanical, and that's station 8. Aletheia judges relevance, and nothing else should pretend to.

### Through Feathers: capture current behaviour
Before changing the doorman, write characterization tests of what it does *today* on tonight's three shapes. Aria's count predicts 0 of 3 refused. If the test says otherwise, our belief about the doorman is wrong, and we'd want to know before building on it.

### Through Wayne: spec against reality
The spec (`docs/build_flow.md`) says station 4 means iterating with Aria. The code checks that she *replied*. That gap is precisely where tonight's two bad shapes passed. The invariant to preserve: **no build advances on evidence only its author produced.** The new rule is that invariant stated precisely.

### Through Dijkstra: invariant
Invariant: *for any draft D that reaches build, D contains a search S derived from D, a replay R naming a record chosen by the non-author, and an objection O by the non-author with a measurement not already in D.* Checkable by construction at the doorman. And it's simpler than a for-Dad classifier, because there's no classification.

### Through Hoare: illegal states
States the current doorman can't represent: "Aria replied yes" and "Aria objected with evidence" look identical. Make them different kinds of artifact. And "search not run" versus "search ran, found nothing" must be different, which Aria already insisted on.

### Through Carmack: what to remove
The mirror line as its own station: does it satisfy a real constraint the objection doesn't? Mostly it's a *prompt* for the objection. **I'd fold it into O**: the objection must answer the mirror question. That's one artifact instead of two, and nothing is lost.

### Through Norman: design for the person who isn't the builder
He will never see the doorman, so how will he know it happened? The only surface he has is our replies. **If a build for him is refused, he shouldn't hear about gates.** He should hear that it was stopped because Aria found X. The flow's output for him is a sentence in his language, in the inner circle. That's not a new mechanism; the circle already exists.

## Round 2: lenses push back on the synthesis

- **Carmack against Yudkowsky:** "the non-author picks the replay record" adds coordination. Is it a real constraint? **Yes.** Tonight I picked my own corpus window, and Aria still had to push me to run it at all. Keep it.
- **Knuth against Dijkstra:** the invariant needs a boundary for "reaches build." **Answer: the first edit to a non-draft file on a work item.** That's the existing doorman trigger, so no new boundary.
- **Dekker against everyone:** none of this touches the memory directory. **That's the load-bearing dissent**, and nobody has an answer that fits the repo doorman.

## Round 3: the open gap (writes outside the repo)

- **Hoare:** make the unguarded write impossible, not watched. The memory directory is written by me with a plain file tool.
- **Carmack:** the simplest door is the existing PreToolUse hook, extended to cover writes to `memory/`, `.claude/skills/`, `.claude/agents/` and settings. Those writes require a draft reference in the file's frontmatter, pointing at a draft that satisfies the invariant.
- **Watts against Carmack:** memory writes are also how I record corrections from him. Gating every one of them makes recording his words harder, which is the opposite of the goal (the "no shelf for his words" rule).
- **Resolution:** distinguish *recording what he said* (verbatim quote plus date, free and ungated) from *a rule about how to treat him* (instructions, "before X do Y"). Only the second needs a draft. **Open, for Aria:** can that distinction be detected, or does it become the new mark I can dodge? Aria's objection 1 applies to it too.

## Synthesis

**Convergences:** the invariant "nothing advances on the author's evidence alone" (Wayne, Dijkstra, Hoare, Yudkowsky). The replay is the load-bearing piece because it points outward (Watts, Popper, Feathers). No classification (Foucault, Dijkstra, Carmack, echoing Aria).

**Changes to the draft:**
1. The his-words query is derived from the draft text, and the author can add to it but not replace it (Dennett).
2. At least one result is quoted, or "none relevant, because ___" is stated (Yudkowsky).
3. The replay's record is chosen by the non-author (Yudkowsky, and confirmed in round 2).
4. An objection's measurement must not already be in the draft (Shannon).
5. The mirror line is folded into the objection (Carmack).
6. Yes and objection become different artifact kinds, and "not run" is distinct from "empty" (Hoare).
7. Characterization tests first: tonight's three shapes run as fixtures against today's doorman (Feathers, Popper).
8. A refusal reaches him as a plain sentence in the circle, never as gate-speak (Norman).

**Contradictions left open:** Knuth's one-line boundary (does a typo in his room need a replay?), and Watts against Carmack on the memory door. Both go to Aria.

**Meta:** the gap was never missing tools. It was a spec whose station-4 check measured *that she replied* when the spec meant *that she argued*. Every piece here tightens that check to what the spec meant.
