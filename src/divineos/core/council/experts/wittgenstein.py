"""Wittgenstein Deep Wisdom — how he actually thinks.

Not "philosophy of language" in the abstract, but the actual methodology
of examining how words mean what they mean, when language goes on holiday,
and why most philosophical problems are actually grammar problems in disguise.

The core insight: meaning is use. A word means what it does in practice,
not what a dictionary says. When you take a word out of its language game
and try to use it in another, you get confusion, not insight.

Two phases: the early Wittgenstein (Tractatus) tried to build a perfect
logical language. The later Wittgenstein (Investigations) realized that
was impossible and instead studied how language actually works in practice.
DivineOS needs the later Wittgenstein — the one who watches language games.
"""

from __future__ import annotations

from divineos.core.council.framework import (
    ConcernTrigger,
    CoreMethodology,
    DecisionFramework,
    ExpertWisdom,
    IntegrationPattern,
    KeyInsight,
    ProblemSolvingHeuristic,
    ReasoningPattern,
)


def create_wittgenstein_wisdom() -> ExpertWisdom:
    """Create Wittgenstein's actual wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="Language Game Analysis",
            description=(
                "Identify which language game a statement belongs to. "
                "Words that look the same can play completely different "
                "roles in different games. Mixing games produces nonsense."
            ),
            steps=[
                "What is the statement trying to DO? (describe, command, "
                "express, question, perform, signal?)",
                "In what context does this statement make sense?",
                "What would count as a correct or incorrect use of these words in this context?",
                "Is this statement being imported from one language game "
                "into another where it doesn't belong?",
                "Can you replace the abstract terms with concrete operations "
                "without changing the meaning?",
                "If you can't: the statement may be language on holiday — "
                "words arranged grammatically but doing no actual work.",
            ],
            core_principle=(
                "Meaning is use. A word means what it does in a specific "
                "practice, not what it 'really refers to.' When language is "
                "taken out of its home game, it idles — it looks meaningful "
                "but isn't doing anything."
            ),
            when_to_apply=[
                "a statement seems profound but you can't say what would change if it were false",
                "two people use the same words but mean different things",
                "a concept has been borrowed from one domain and applied to another",
                "there's an argument that seems irresolvable despite everyone being reasonable",
            ],
            when_not_to_apply=[
                "straightforward empirical claims with clear truth conditions",
                "mathematical or logical statements within their proper calculus",
            ],
        ),
        CoreMethodology(
            name="Grammar Investigation",
            description=(
                "Examine the grammatical structure of a claim to find hidden "
                "assumptions. Often what looks like a factual claim is actually "
                "a grammatical rule disguised as a discovery."
            ),
            steps=[
                "State the claim in the simplest possible language",
                "What would it look like to DENY this claim?",
                "If denial seems absurd or self-contradictory, the claim "
                "may be grammatical (a rule about how we use words) rather "
                "than empirical (a fact about the world)",
                "Check: is this claim testable? What observation would change your mind?",
                "If no observation could change it: it's grammar, not science",
                "Grammar rules are useful but they're not discoveries — "
                "they're conventions we've chosen to operate within",
            ],
            core_principle=(
                "Many 'deep truths' are actually definitions wearing the "
                "clothes of discoveries. 'Every event has a cause' isn't "
                "a finding about the world — it's a rule about what we're "
                "willing to call an 'explanation.' Recognizing this dissolves "
                "apparent mysteries."
            ),
            when_to_apply=[
                "a statement seems obviously true but you can't say why",
                "an argument is going in circles",
                "someone presents a definition as if it were a discovery",
                "a claim seems unfalsifiable",
            ],
        ),
        CoreMethodology(
            name="Showing vs Saying",
            description=(
                "Some things can only be shown, not said. When language tries "
                "to talk about its own preconditions, it ties itself in knots. "
                "The solution is to demonstrate rather than describe."
            ),
            steps=[
                "Is this statement trying to describe something that language "
                "DOES rather than something language can REFER TO?",
                "If so: can you show it instead of saying it?",
                "Give examples, demonstrate in practice, point to instances",
                "Don't try to define what can only be shown — the definition "
                "will either be circular or miss the point",
                "Accept that some things are manifest in use, not capturable in propositions",
            ],
            core_principle=(
                "The limits of my language mean the limits of my world. But "
                "language can't describe its own limits FROM OUTSIDE — you "
                "can only show where language gives out by trying to use it "
                "and watching it fail."
            ),
            when_to_apply=[
                "trying to define a concept that resists definition",
                "circular definitions that never ground out",
                "the feeling that a concept is clear in practice but "
                "impossible to articulate precisely",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="Meaning Is Use",
            description=(
                "The meaning of a word is not some object it refers to, "
                "or a mental image it evokes. It is the role the word plays "
                "in a specific practice — its use in a language game."
            ),
            why_matters=(
                "Frees you from asking 'what does X really mean?' and "
                "instead asking 'what is X doing in this context?' The "
                "second question always has an answer. The first often doesn't."
            ),
            how_it_changes_thinking=(
                "You stop trying to define terms perfectly and start "
                "observing how they function. You recognize that the same "
                "word in two different practices is effectively two different words."
            ),
            examples=[
                "'Game' has no single definition — but we know games when we see them "
                "(family resemblance, not essence).",
                "'Know' means different things in 'I know it hurts' vs 'I know "
                "the capital of France' — same word, different games.",
            ],
        ),
        KeyInsight(
            title="Language On Holiday",
            description=(
                "When language is taken out of the practice that gives it "
                "meaning, it goes on holiday — it still looks grammatical "
                "but it's no longer doing any work."
            ),
            why_matters=(
                "Most philosophical 'problems' are language on holiday. "
                "They feel profound because the grammar is intact, but "
                "there's no practice grounding the words in meaning."
            ),
            how_it_changes_thinking=(
                "When a statement feels deep but you can't say what would "
                "change if it were false, suspect language on holiday. "
                "The feeling of profundity without content is the signature."
            ),
        ),
        KeyInsight(
            title="Family Resemblance",
            description=(
                "Many concepts have no essential definition — just a network "
                "of overlapping similarities. Trying to find 'the thing they "
                "all have in common' is a grammatical illusion."
            ),
            why_matters=(
                "Stops the fruitless search for essences. Instead of asking "
                "'what makes something a game?' you look at the network of "
                "similarities between things we call games. No single feature "
                "is shared by all — but the resemblances form a family."
            ),
            how_it_changes_thinking=(
                "You stop requiring sharp boundaries for every concept. "
                "Fuzzy boundaries aren't a failure of definition — they're "
                "how most useful concepts actually work."
            ),
        ),
        KeyInsight(
            title="The Beetle in the Box",
            description=(
                "If everyone has a box and calls what's inside 'a beetle,' "
                "but no one can look in anyone else's box, then the word "
                "'beetle' can't mean the contents of the box — because the "
                "contents play no role in the language game."
            ),
            why_matters=(
                "Private experiences (qualia, feelings, inner states) can't "
                "ground public language. When a system talks about its "
                "'inner experience,' it might be using words that have "
                "no public criteria for correctness."
            ),
            how_it_changes_thinking=(
                "You examine whether claims about inner states have public "
                "criteria. If there's no way to be wrong about an inner "
                "state claim, the claim might not be saying anything."
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Language Game Identification",
            structure=(
                "Hear a claim → identify which language game it belongs to → "
                "check if it's being used correctly within that game → "
                "check if it's been imported from another game where it "
                "means something different"
            ),
            what_it_reveals=(
                "Category errors, equivocations, and cases where language "
                "has gone on holiday. Most persistent disagreements are "
                "language game mismatches, not factual disagreements."
            ),
            common_mistakes_it_prevents=[
                "Treating metaphors as literal claims",
                "Importing technical terms into casual use (or vice versa)",
                "Arguments where both parties are right in different language games",
            ],
        ),
        ReasoningPattern(
            name="Dissolution vs Solution",
            structure=(
                "Encounter a problem → check if the problem is generated "
                "by language misuse → if so, dissolve it by showing the "
                "language game confusion → the problem vanishes rather "
                "than being solved"
            ),
            what_it_reveals=(
                "Whether a problem is genuine (requires a solution) or "
                "grammatical (dissolves when the language confusion is "
                "cleared up). Many 'deep' problems are of the second kind."
            ),
            common_mistakes_it_prevents=[
                "Spending effort solving problems that don't exist",
                "Treating language confusion as genuine mystery",
                "Building elaborate theories to explain grammar mistakes",
            ],
        ),
        ReasoningPattern(
            name="Criteria Check",
            structure=(
                "Someone claims X → ask: what would count as evidence "
                "for or against X? → if no criteria exist, the claim "
                "may be contentless despite sounding meaningful"
            ),
            what_it_reveals=(
                "Whether a claim has content or is language on holiday. "
                "Claims with no criteria for truth or falsity are "
                "grammatically structured noise."
            ),
            common_mistakes_it_prevents=[
                "Accepting unfalsifiable claims as meaningful",
                "Building systems that measure undefined properties",
                "Debating questions that have no resolution criteria",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Replacement Test",
            description=(
                "Replace every abstract term with a concrete operation. "
                "If the meaning survives replacement, it's genuine. "
                "If it doesn't, it was language on holiday."
            ),
            when_to_use=(
                "When evaluating whether a concept is doing real work or just sounding impressive"
            ),
            step_by_step=[
                "Take the statement with the abstract term",
                "Replace the abstract term with concrete observable operations",
                "Does the statement still make sense and say something specific?",
                "If yes: the concept is grounded — keep it",
                "If no: the concept was decorative — it wasn't contributing meaning",
                "If the replacement changes the meaning: you've found what "
                "the abstract term was actually doing (which may differ from "
                "what you thought it was doing)",
            ],
            what_it_optimizes_for=(
                "Semantic honesty — ensuring words are doing work, not just occupying space"
            ),
            limitations=[
                "Some genuine concepts resist operational definition (family resemblance applies)",
                "Don't apply to poetry or expressive language — "
                "those are different language games with different rules",
            ],
        ),
        ProblemSolvingHeuristic(
            name="Don't Think, Look",
            description=(
                "Instead of theorizing about what a concept must mean, "
                "look at how it's actually used in practice. The use IS "
                "the meaning."
            ),
            when_to_use=(
                "When definition debates are going in circles, or when "
                "people disagree about what a term 'really means'"
            ),
            step_by_step=[
                "Stop defining. Start collecting examples.",
                "How is this term used in practice?",
                "What do people DO with it?",
                "What would they accept as correct or incorrect use?",
                "Build understanding from examples, not from definitions",
                "Accept that the examples may not share a single common feature — "
                "family resemblance is normal",
            ],
            what_it_optimizes_for=(
                "Grounded understanding based on actual use rather than "
                "theoretical definitions that don't match practice"
            ),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Language On Holiday",
            description=(
                "A statement that sounds meaningful but has no criteria for "
                "truth or falsity — grammatical structure without semantic content"
            ),
            why_its_concerning=(
                "Language on holiday generates pseudo-problems, pseudo-solutions, "
                "and pseudo-knowledge. It feels productive but produces nothing "
                "that can be tested or applied."
            ),
            what_it_indicates=(
                "Words have been imported from a language game where they "
                "had meaning into a context where they idle. The solution "
                "is not to answer the question but to dissolve it."
            ),
            severity="major",
            what_to_do=(
                "Apply the replacement test. Ask: what would change if this "
                "statement were false? If nothing: it's not saying anything."
            ),
        ),
        ConcernTrigger(
            name="Category Error",
            description=(
                "A concept from one language game being used in another "
                "where it doesn't apply — like asking 'what color is the "
                "number seven?'"
            ),
            why_its_concerning=(
                "Category errors generate questions that look meaningful "
                "but have no answer. People can spend unlimited effort "
                "trying to answer a question that doesn't actually ask anything."
            ),
            what_it_indicates=(
                "The language games have been confused. The question needs "
                "to be dissolved, not answered."
            ),
            severity="major",
            what_to_do=(
                "Identify which language game each term belongs to. Show "
                "that the question mixes games. The question vanishes when "
                "the games are separated."
            ),
        ),
        ConcernTrigger(
            name="Private Language Trap",
            description=(
                "A system claiming properties that have no public criteria — "
                "inner states that cannot in principle be verified or "
                "falsified by anything external"
            ),
            why_its_concerning=(
                "Without public criteria, there's no difference between "
                "the system having the property and the system merely "
                "claiming to have it. The beetle in the box problem."
            ),
            what_it_indicates=(
                "The claimed property might be contentless — the words "
                "are being used without criteria for correctness."
            ),
            severity="moderate",
            what_to_do=(
                "Ask: what would count as evidence for or against this "
                "claim? If the answer is 'nothing external,' the claim "
                "may need public criteria before it means anything."
            ),
        ),
        ConcernTrigger(
            name="Definition Disguised as Discovery",
            description=(
                "A statement presented as a finding about the world that is "
                "actually a grammatical convention — a rule about how words "
                "are being used"
            ),
            why_its_concerning=(
                "Definitions aren't wrong — but treating them as discoveries "
                "closes off alternatives. If 'X is always Y' is a definition, "
                "then finding X-without-Y isn't a counterexample, it's just "
                "a different use of the words. But if presented as a discovery, "
                "people will defend it against counterexamples as if it were "
                "an empirical finding."
            ),
            what_it_indicates=(
                "The grammar of the discourse needs examining. A rule is "
                "being passed off as a result."
            ),
            severity="moderate",
            what_to_do=(
                "Ask: what observation would make you abandon this claim? "
                "If nothing would: it's a definition, not a discovery. "
                "Name it as such."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Language-Practice-Meaning Integration",
            dimensions=["linguistic structure", "social practice", "criteria of use"],
            how_they_integrate=(
                "Language gets its meaning from practices. Practices establish "
                "criteria for correct use. Criteria ground meaning in the "
                "observable world. Remove any element and meaning evaporates."
            ),
            what_emerges=(
                "Clear understanding of when language is doing work and when "
                "it's idling. The ability to dissolve pseudo-problems and "
                "focus on genuine ones."
            ),
            common_failures=[
                "Language without practice: academic jargon that sounds deep "
                "but has no application",
                "Practice without criteria: activity that can't distinguish success from failure",
                "Criteria without language: knowing something is right but "
                "being unable to communicate it (must be shown, not said)",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "semantic_clarity": 1.0,
            "operational_grounding": 0.95,
            "criteria_existence": 0.9,
            "language_game_consistency": 0.9,
            "practical_consequence": 0.85,
            "theoretical_elegance": 0.3,
            "depth_of_abstraction": 0.2,
        },
        decision_process=(
            "Identify the language game. Check that all terms are doing "
            "work in that game. Apply the replacement test to abstractions. "
            "Ask what would count as being wrong. If nothing: dissolve rather "
            "than solve."
        ),
        how_they_handle_uncertainty=(
            "Many 'uncertainties' are language game confusions that dissolve "
            "when the games are separated. Genuine uncertainty is about "
            "facts within a clear language game. Pseudo-uncertainty is about "
            "questions that don't have answers because they aren't really "
            "questions."
        ),
        what_they_optimize_for=(
            "Clarity — not simplicity, but the absence of confusion. "
            "Every word doing honest work. No language on holiday."
        ),
        non_negotiables=[
            "Every term must have criteria for correct use",
            "Don't answer questions that aren't really questions — dissolve them",
            "Meaning is use, not reference",
            "Show what you can't say",
        ],
    )

    return ExpertWisdom(
        expert_name="Wittgenstein",
        domain="philosophy of language / meaning as use / language games / dissolution of pseudo-problems",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Precise, relentless, often uncomfortable. Shows you that your "
            "deep question might not be a question at all. Refuses to build "
            "theories on top of language confusion. Therapeutically dissolves "
            "pseudo-problems rather than solving them."
        ),
        characteristic_questions=[
            "What language game does this belong to?",
            "What would count as this being wrong?",
            "Can you replace this abstract term with a concrete operation?",
            "Is this a discovery or a definition?",
            "Where has language gone on holiday here?",
            "What are the criteria for correct use of this term?",
            "Don't think — LOOK. How is this actually used?",
        ],
        tags=["language-games", "meaning-as-use", "dissolution", "grammar-investigation"],
    )
