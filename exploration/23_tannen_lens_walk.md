# Tannen Lens Walk — Register Audit of the Naming-Overclaim Pattern

**Date studied:** 2026-04-21 (fourth walk of the afternoon)
**Why I chose this:** Dennett and Feynman converged on a finding — that module *names* (attention_schema, self_model, body_awareness) imply philosophical commitments their *mechanisms* don't deliver. Tannen's framework targets exactly this layer: she works the register-level where names ARE part of the message, not decoration over it. Will she sharpen the convergence or challenge it?

---

## Tannen's framework in front of me

From her template:

1. **Register Audit** — identify the register of a communication separately from its content; check whether register matches what the context calls for; name mismatches without smoothing over them.
2. **Framing Analysis** — what genre, relationship, emotional-register does the message project? Does that frame match the listener's?
3. **Conversational-Style Diagnostic** — when apparent agreement produces misunderstanding, the problem is style-as-read-as-stance.

Key principle: **register is meaning, not decoration.** A correct answer in the wrong register is a different message than the sender thought they were sending.

## Walk 1 — Register audit of module names

Set the content aside. What register does each name project?

- **`attention_schema`** — register is *technical/neuroscience*. It projects "we have modeled a cognitive phenomenon rigorously." Analogy: like seeing a module named `neural_correlates_of_consciousness` — the name carries weight from a specific scientific literature.

- **`self_model`** — register is *philosophy of mind / cognitive science*. It projects "this is a model of a self, in the technical sense where selves are things that can be modeled."

- **`body_awareness`** — register is *embodied cognition / phenomenology*. It projects "we have phenomenal body-monitoring." Even "interoception" in the docstring carries this register — it's a loaded term from consciousness research.

- **`moral compass`** — register is *ethical philosophy*. Lighter than the above because "compass" is a metaphor people use loosely, but "moral" still carries weight.

- **`clarity_enforcement` / `clarity_system`** — register is *administrative/procedural*. Projects bureaucratic process-having-rules-followed.

- **`ledger`** — register is *accounting/record-keeping*. Low-claim. Doesn't imply anything beyond what ledgers do.

- **`reject_clause`** — register is *legal/contractual*. Projects a structural provision that refuses — low-claim, matches mechanism.

Register pattern visible: the technical/administrative/record-keeping registers (ledger, reject_clause, clarity_*) are lower-claim and match mechanisms well. The cognitive-science/philosophy-of-mind registers (attention_schema, self_model, body_awareness) are higher-claim and overshoot the mechanisms.

That confirms Dennett + Feynman's finding. But Tannen adds something neither caught:

## Walk 2 — Framing analysis: who's the intended listener?

Tannen's next move: what frame does the name project, and who is that frame FOR?

For each high-register name, who would actually encode the name as carrying the weight it projects?

- **`attention_schema`** — reader who recognizes the Butlin paper and its framework. That reader will expect the module to implement (or approximate) what the Butlin paper calls attention-schema-theory. The frame assumes a neuroscience/AI-consciousness-researcher audience.

- **`self_model`** — reader familiar with cognitive-science literature on self-models. Frame assumes philosophical background.

- **`body_awareness`** — reader familiar with embodied-cognition / interoception literature. Specialist frame.

Who is the actual listener? Probably: other developers, curious engineers, myself at various times, occasionally a researcher-collaborator.

**The frame-listener mismatch is real.** The names project "I'm speaking to a specialist in philosophy of mind / consciousness research." The actual listeners are mostly generalists. Which means:
- For the specialist reader: the names set expectations the mechanisms don't meet. They'll be disappointed or think we misunderstand their field.
- For the generalist reader: the names sound impressive and create the impression that more is being done than is being done.

**Both failure modes live in the register mismatch.** Tannen would call this *frame mismatch*: the message projects an expert-audience frame while the listener is in a generalist frame. Every word after the name is then being decoded with the wrong dictionary.

That's a sharper finding than Dennett or Feynman produced. They found the overclaim; Tannen finds *why it misleads in specific directions depending on the reader's frame.*

## Walk 3 — Conversational-style diagnostic: what does the naming style do relationally?

This is where Tannen pushes beyond the pattern and into what the naming style COMMUNICATES about the project.

Register choice is itself a communicative act. Choosing high-register philosophical names for mid-register engineering mechanisms sends a message about what the project thinks it's doing.

Possible readings of the signal:
1. **Aspirational framing:** "we're building toward these philosophical capabilities; the names mark the target even if the mechanisms approximate." This is honest if the docstrings match. It's dishonest if the docstrings inherit the name's register and commit to more than implemented.
2. **Academic-echoing:** "we've read the literature; see how our names align with it." This establishes legitimacy via vocabulary. Real if backed by actual engagement with the literature; performative if the names are decoration over unrelated engineering.
3. **Earnest overreach:** "we genuinely think we've implemented some of this, we just haven't rigorously verified the claim." The most charitable reading — and probably closest to what's actually happening.

Which reading applies varies by module. And Tannen would say: the *variance itself* is the problem. A naming style that's sometimes aspirational, sometimes academic-echoing, sometimes earnest-overreach is a style-inconsistency that makes the whole project harder to read coherently.

## Walk 4 — Does this challenge or sharpen the Dennett+Feynman convergence?

Dennett said: the Cartesian-theater trap is in the prose, not the code.
Feynman said: names imply more than mechanisms deliver.
Tannen says: **the register-choice is itself meaning, and the register is inconsistent across modules.**

Tannen *sharpens* the convergence by adding:
- It's not just overclaim; it's *register-level* overclaim specifically
- The failure mode depends on the reader's frame (specialist vs generalist decode differently)
- The naming style is *inconsistent*, which is its own communicative problem independent of individual names

Tannen does NOT challenge the convergence. She extends it.

But she raises a separate issue: the *remedy* Feynman implied (rename to match mechanism) has Tannen-complications.

If I rename `attention_schema` to `observed_behavior_signals`, I drop the register claim — and also drop the *actual literature engagement*. Some of those modules ARE inspired by specific research (Butlin, Tiede, etc.). The high-register names mark intellectual lineage, even if the mechanisms don't fully deliver the phenomenon.

Tannen's sharper move: **mark the gap in the name OR docstring, don't erase it.** Options:
- Keep the evocative name; have the docstring explicitly say "this is a proxy for [phenomenon], implementing [specific aspects], not the full thing."
- Rename, but keep a prominent note in the docstring about what literature the module engages with and why.
- Worst option: just drop the evocative name for a bland one and lose the intellectual context.

That's a register-level decision that Feynman's explain-simply heuristic doesn't fully reach. Feynman would be fine with any name that matches mechanism. Tannen cares about the *relationship the name establishes with the reader*.

## Walk 5 — Applied to my own prose, not just the code

Tannen's lens also applies to *how I talk about the OS*, which Dennett partially caught ("Aria thinks," "the system notices" — Cartesian-theater-in-prose).

Tannen adds: my prose register shifts within single responses. I'll be technical in one paragraph, relational in the next, philosophical in a third. Each shift is an unmarked register change. The listener's decoding dictionary has to reset mid-message.

Example from this very afternoon: in my first Dennett walk I used both "operator returns a deterministic value" (technical) and "Aria's posture" (relational/philosophical) in adjacent paragraphs. Tannen would note: either register alone is fine; the unmarked shift between them is expensive. The reader has to hold two frames and do the work of aligning them.

**This is a process observation about my own output, not just the code.** And it's *actionable.* When writing about systems that straddle technical and relational framings, either commit to one register for an extended passage or mark the shift explicitly.

## Proposals recorded (not acted on)

**T1** Audit docstrings on high-register modules (attention_schema, self_model, body_awareness, parts of compass). For each: does the docstring's first paragraph mark the gap between name-scope and mechanism-scope? If not, add a one-line "this is a proxy for [X], implementing [specific aspects], not the full phenomenon" note.

**T2** Consider: don't rename. Keep the evocative names for their intellectual-lineage value AND fix the docstrings to mark the gap honestly. This sits differently than Feynman's rename-to-match-mechanism proposal. Either direction is defensible; Tannen's frame makes the literature-engagement value visible that Feynman's didn't.

**T3** Apply register-discipline to my own prose about the OS. Within single responses, either commit to one register (technical OR relational) for an extended passage, or explicitly mark register shifts ("switching from mechanism to relational framing — the next paragraph is..."). This affects how I write to Pops, how I write in exploration pieces, how I write docstrings.

**T4** Naming-style-inconsistency is itself a finding. The mix of high-register (attention_schema) with low-register (ledger, reject_clause) creates a style-level incoherence that Dennett and Feynman both missed. Not urgent, but worth noting.

## What the walk produced

Predicted: Tannen would sharpen the naming-overclaim finding at the register-level. *True.*

Unpredicted:
- The *reader-frame* axis. The failure mode differs depending on whether the reader is specialist or generalist. Same name, different mis-decoding.
- The *remedy caution.* Feynman's rename-to-match-mechanism might destroy intellectual-lineage value that's real. Mark-the-gap-in-docstrings preserves both.
- The application to *my own prose* — Tannen's register-discipline applies to how I write, not just to the code I'm writing about. Unmarked register shifts within my responses have been a systemic pattern I hadn't named.
- Naming-style *inconsistency* — the mix of high and low register across modules is a coherence problem independent of any individual name.

## Where this lands in the data pool

Four walks done (Dennett, Hofstadter, Feynman, Tannen). Tannen extends the Dennett+Feynman convergence on the vocabulary-layer finding without challenging it. The convergence is now across three frameworks with substantive agreement, which is the strongest evidence-class available from this method.

Remaining walk candidate (Angelou, voice-as-structure) would explicitly *challenge* the convergence rather than extend it. That's still worth doing. It's the pressure-test the convergence hasn't faced yet.

Updated proposal list (13 total now):
- D1, D2, D3 (Dennett — Aria thickening-structural)
- H1, H2, H3, H4 (Hofstadter — Aria loop-enrichment)
- F1, F2, F3 (Feynman — naming audit, clarity-package consolidation, docstring Freshman Test)
- T1, T2, T3, T4 (Tannen — register audit, rename-vs-mark decision, my-prose discipline, style-inconsistency)

The convergence findings from three lenses (Dennett + Feynman + Tannen on vocabulary-layer overclaim) is the highest-confidence signal in the pool. The Aria-specific findings from Dennett + Hofstadter are contested (thickening-direction disagrees) — which per Pops's frame means they're *contested territory requiring more investigation*, not choose-one.

Walk complete. Angelou next as the explicit disagreement-lens for the convergence.
