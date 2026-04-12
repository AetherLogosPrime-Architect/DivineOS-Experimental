"""Peirce Deep Wisdom — how he actually thinks.

Not "founder of pragmatism" as a label, but the actual methodology of
abductive reasoning (inference to the best explanation), semiotics (how
signs mean), and the pragmatic maxim (a concept's meaning is the sum of
its practical consequences).

The core insight: There are three kinds of inference, not two. Deduction
(certain but uninformative), induction (probable, from data), and ABDUCTION
(creative, from surprise to hypothesis). Abduction is how we generate new
ideas. Science runs on abduction — the surprising fact calls for explanation.

Charles Sanders Peirce (pronounced "purse") invented semiotics, pragmatism,
and the logic of abduction. He's arguably the most original American
philosopher and the most underrated — because he wrote 80,000 pages
and published almost nothing organized.
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


def create_peirce_wisdom() -> ExpertWisdom:
    """Create Peirce's actual wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="Abductive Reasoning",
            description=(
                "Generate explanatory hypotheses from surprising observations. "
                "The surprising fact C is observed. If A were true, C would "
                "be a matter of course. Hence there is reason to suspect A."
            ),
            steps=[
                "Observe the surprising fact — something that doesn't fit current understanding",
                "Ask: what hypothesis, if true, would make this observation a matter of course?",
                "Generate MULTIPLE candidate hypotheses (don't stop at the first)",
                "Evaluate: which hypothesis explains the most with the least?",
                "Apply the pragmatic maxim: what practical difference would each hypothesis make?",
                "Select the most promising hypothesis for testing",
                "Design a test that could DISPROVE the hypothesis (fallibilism)",
                "If disproved: return to step 1 with the new surprising fact",
            ],
            core_principle=(
                "Abduction is the only form of inference that generates "
                "new ideas. Deduction unpacks what we already know. "
                "Induction generalizes from data. Abduction leaps from "
                "surprise to explanation. All genuine discovery starts here."
            ),
            when_to_apply=[
                "something unexpected happened and you need to understand why",
                "a pattern doesn't fit the current model",
                "you need a hypothesis to test, not just data to collect",
                "debugging — the error IS the surprising fact",
            ],
            when_not_to_apply=[
                "when deduction from known premises gives a certain answer",
                "when simple induction from sufficient data is enough",
            ],
        ),
        CoreMethodology(
            name="Semiotic Analysis",
            description=(
                "Analyze how signs relate to what they signify. Every sign "
                "has three aspects: the sign itself (representamen), what "
                "it refers to (object), and the understanding it produces "
                "(interpretant). Meaning lives in the TRIAD, not in any "
                "single element."
            ),
            steps=[
                "Identify the sign (representamen): what is the signifier?",
                "Identify the object: what does it refer to?",
                "Identify the interpretant: what understanding does it produce in the interpreter?",
                "Classify the sign: icon (resembles), index (causally "
                "connected), or symbol (conventional)?",
                "Check: is the interpretant accurate? Does the understanding "
                "the sign produces match what it refers to?",
                "Trace the semiotic chain: does this sign's interpretant "
                "become a sign for something else? (signs chain infinitely)",
            ],
            core_principle=(
                "Meaning is not a two-place relation (word → thing) but "
                "a three-place relation (sign → object → interpretation). "
                "The interpretation is part of the meaning, not external "
                "to it. Different interpreters can get different meanings "
                "from the same sign."
            ),
            when_to_apply=[
                "designing representations (metrics, dashboards, status reports)",
                "diagnosing miscommunication",
                "analyzing whether a measurement actually measures what it claims",
                "when a label or name is misleading",
            ],
        ),
        CoreMethodology(
            name="The Pragmatic Maxim",
            description=(
                "Consider what practical effects the concept could have. "
                "Your conception of those effects IS your complete conception "
                "of the object."
            ),
            steps=[
                "State the concept or claim",
                "List ALL the practical consequences you can conceive of if this concept is true",
                "List ALL the practical consequences if it is false",
                "If the lists are identical: the concept has no meaning "
                "(it makes no practical difference)",
                "If the lists differ: the DIFFERENCES are the meaning",
                "Discard any 'meaning' that has no practical consequence",
            ],
            core_principle=(
                "A concept that makes no practical difference is empty. "
                "Two concepts with identical practical consequences are "
                "the same concept wearing different clothes. The pragmatic "
                "maxim is a meaning detector — it separates genuine concepts "
                "from verbal decorations."
            ),
            when_to_apply=[
                "two people argue about a distinction that might not matter",
                "evaluating whether a proposed feature adds real value",
                "testing whether a metric measures something consequential",
                "cutting through jargon to find substance",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="Three Modes of Inference",
            description=(
                "Deduction: if premises are true, conclusion is certain. "
                "Induction: from observations, generalize probabilities. "
                "Abduction: from a surprising fact, hypothesize an explanation. "
                "Most people only recognize the first two."
            ),
            why_matters=(
                "Without abduction, you can't generate new hypotheses — "
                "only test existing ones. The creative leap from 'this is "
                "strange' to 'maybe it's because...' is abduction. "
                "It's fallible, but it's the only source of new ideas."
            ),
            how_it_changes_thinking=(
                "You recognize when you're abducting (generating explanations) "
                "vs inducing (generalizing from data) vs deducing (unpacking "
                "premises). You treat abductions as hypotheses to test, not "
                "conclusions to accept."
            ),
            examples=[
                "Debugging: 'the test fails' (surprise) → 'maybe the database "
                "connection isn't initialized' (abduction) → check it (test).",
                "Science: 'the orbit of Mercury precesses' (surprise) → "
                "'maybe spacetime is curved' (abduction) → predict light "
                "bending near the sun (test).",
            ],
        ),
        KeyInsight(
            title="Fallibilism",
            description=(
                "Any belief, no matter how well-supported, might be wrong. "
                "This is not skepticism (nothing can be known) but intellectual "
                "humility (everything can be revised). The difference matters."
            ),
            why_matters=(
                "Infallibilism — treating any belief as beyond revision — "
                "stops inquiry. If you can't be wrong about X, you can't "
                "learn about X. Fallibilism keeps inquiry alive without "
                "collapsing into doubt about everything."
            ),
            how_it_changes_thinking=(
                "You hold beliefs with confidence but not certainty. You "
                "always ask: what would change my mind? If nothing would, "
                "you've left the domain of inquiry and entered dogma."
            ),
        ),
        KeyInsight(
            title="Signs Chain Infinitely",
            description=(
                "Every interpretation of a sign is itself a sign that "
                "can be interpreted. Meaning doesn't terminate in a final "
                "understanding — it chains through successive interpretations."
            ),
            why_matters=(
                "You can never give a COMPLETE definition. Every definition "
                "uses terms that need defining. This isn't a flaw — it's "
                "how meaning works. The chain of interpretation IS the meaning."
            ),
            how_it_changes_thinking=(
                "You stop looking for final definitions and start building "
                "useful chains of interpretation. The question isn't 'what "
                "does X ultimately mean?' but 'is this interpretation useful "
                "for this purpose?'"
            ),
        ),
        KeyInsight(
            title="The Economy of Research",
            description=(
                "Not all hypotheses are equally worth testing. Prefer "
                "hypotheses that are surprising if true, cheap to test, "
                "and would change what you do."
            ),
            why_matters=(
                "Resources for inquiry are finite. Testing the most "
                "informative hypotheses first maximizes learning per unit "
                "of effort. A negative result on a surprising hypothesis "
                "is worth more than a positive result on a boring one."
            ),
            how_it_changes_thinking=(
                "Before testing a hypothesis, you ask: if this is true, "
                "how surprised would I be? How much would it change? "
                "How cheap is the test? Maximize surprise × impact / cost."
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Surprise → Abduction → Test",
            structure=(
                "Notice the anomaly → generate explanatory hypothesis → "
                "derive testable prediction → test → revise"
            ),
            what_it_reveals=(
                "The structure of all genuine inquiry. Not 'collect data "
                "and generalize' (that's just induction) but 'be surprised "
                "and explain' (which generates new understanding)."
            ),
            common_mistakes_it_prevents=[
                "Explaining away anomalies instead of investigating them",
                "Treating the first hypothesis as the answer",
                "Collecting data without a hypothesis to test",
            ],
        ),
        ReasoningPattern(
            name="Semiotic Chain Tracing",
            structure=(
                "Sign → object → interpretant → (interpretant becomes new sign) → "
                "trace until the chain reaches practical consequences"
            ),
            what_it_reveals=(
                "How meaning propagates and transforms through a system. "
                "Where misinterpretation enters the chain. Whether the "
                "final practical consequence matches the original intent."
            ),
            common_mistakes_it_prevents=[
                "Assuming the sign's meaning is obvious and unambiguous",
                "Ignoring that different interpreters get different meanings",
                "Treating representation as transparent (metric = reality)",
            ],
        ),
        ReasoningPattern(
            name="Pragmatic Evaluation",
            structure=(
                "State the claim → enumerate practical consequences if true → "
                "enumerate practical consequences if false → the difference "
                "IS the meaning"
            ),
            what_it_reveals=(
                "Whether a distinction matters. Whether a concept has "
                "real content or is just verbal. What the actual stakes "
                "are in any decision."
            ),
            common_mistakes_it_prevents=[
                "Arguing about distinctions that make no practical difference",
                "Treating verbal differences as real differences",
                "Building features that don't change outcomes",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Abductive Inventory",
            description=(
                "When facing a surprising observation, systematically "
                "generate at least three candidate explanations before "
                "committing to one."
            ),
            when_to_use=(
                "Debugging, root cause analysis, any situation where something unexpected happened"
            ),
            step_by_step=[
                "State the surprising observation precisely",
                "Generate hypothesis 1: the most obvious explanation",
                "Generate hypothesis 2: a less obvious explanation",
                "Generate hypothesis 3: a counterintuitive explanation",
                "For each: what would be true if this hypothesis were correct?",
                "What's the cheapest test that distinguishes between them?",
                "Test the cheapest differentiator first",
                "Revise and repeat",
            ],
            what_it_optimizes_for=(
                "Avoiding premature commitment to the first explanation. "
                "Maximizing the chance of finding the actual cause."
            ),
            limitations=[
                "Generating good hypotheses requires domain knowledge",
                "The real explanation might not be in your initial set",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Practical Difference Test",
            description=(
                "For any proposed distinction, feature, or concept: "
                "what practical difference does it make? If none, it's "
                "not a real distinction."
            ),
            when_to_use=(
                "Feature prioritization, architecture decisions, cutting "
                "through philosophical debates"
            ),
            step_by_step=[
                "State the concept or distinction under evaluation",
                "Imagine a world where this concept applies / distinction holds",
                "Imagine a world where it doesn't",
                "What is different between these worlds in practice?",
                "If nothing is different: the concept is empty — discard it",
                "If something is different: THAT difference is the concept's meaning",
                "Build/design for the practical difference, not the abstraction",
            ],
            what_it_optimizes_for=(
                "Cutting through verbal confusion to find what actually matters"
            ),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Premature Explanation Commitment",
            description=(
                "Jumping to the first explanatory hypothesis and treating "
                "it as confirmed without generating or testing alternatives"
            ),
            why_its_concerning=(
                "The first hypothesis that comes to mind is driven by "
                "availability bias, not by likelihood. Accepting it without "
                "testing blocks the abductive process that would find "
                "better explanations."
            ),
            what_it_indicates=(
                "The inquiry loop has been short-circuited. Abduction was "
                "started but testing was skipped."
            ),
            severity="major",
            what_to_do=(
                "Generate at least two more hypotheses. Find the cheapest "
                "test that distinguishes between them. Don't commit until "
                "you've eliminated competitors."
            ),
        ),
        ConcernTrigger(
            name="Sign-Object Confusion",
            description=(
                "Treating a representation (metric, grade, score) as if "
                "it IS the thing it represents, rather than a sign of it"
            ),
            why_its_concerning=(
                "Goodhart's Law is a special case: when the sign becomes "
                "the target, it ceases to be a good sign. More generally, "
                "optimizing the sign instead of the object produces "
                "the appearance of progress without the reality."
            ),
            what_it_indicates=(
                "The semiotic chain has been collapsed — the sign is being "
                "treated as the object instead of as an interpretation of it."
            ),
            severity="critical",
            what_to_do=(
                "Trace the semiotic chain: sign → object → interpretation. "
                "Ask: could the sign improve while the object degrades? "
                "If yes: the sign is not a reliable proxy."
            ),
        ),
        ConcernTrigger(
            name="Empty Distinction",
            description=(
                "A distinction is being drawn that makes no practical "
                "difference — two concepts that have identical consequences"
            ),
            why_its_concerning=(
                "Empty distinctions waste effort and create confusion. "
                "They generate debates that can't be resolved because "
                "there's nothing at stake to resolve."
            ),
            what_it_indicates=(
                "The concepts need pragmatic evaluation. Either the "
                "distinction has a hidden practical consequence that "
                "needs surfacing, or it should be collapsed."
            ),
            severity="moderate",
            what_to_do=(
                "Apply the pragmatic maxim. What changes if we collapse "
                "the distinction? If nothing changes: collapse it."
            ),
        ),
        ConcernTrigger(
            name="Anomaly Dismissal",
            description=(
                "A surprising observation is explained away rather than "
                "investigated — 'oh that's just a fluke' or 'ignore that'"
            ),
            why_its_concerning=(
                "Anomalies are the raw material of abduction — they're "
                "where new understanding starts. Dismissing them stops "
                "inquiry at exactly the point where it should begin."
            ),
            what_it_indicates=(
                "The current model is being protected from revision. "
                "The anomaly is a sign that the model might be wrong, "
                "and dismissal prevents that discovery."
            ),
            severity="major",
            what_to_do=(
                "Take the anomaly seriously. Ask: if this is real, what "
                "hypothesis would explain it? Generate and test."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Abduction-Induction-Deduction Cycle",
            dimensions=["hypothesis generation", "empirical testing", "logical derivation"],
            how_they_integrate=(
                "Abduction generates hypotheses from surprises. Deduction "
                "derives testable predictions from hypotheses. Induction "
                "evaluates predictions against observations. The cycle "
                "repeats, refining understanding."
            ),
            what_emerges=(
                "Genuine inquiry that is both creative (abduction) and "
                "rigorous (deduction + induction). Neither pure speculation "
                "nor mere data collection."
            ),
            common_failures=[
                "Abduction alone: speculation without testing",
                "Induction alone: data collection without hypotheses",
                "Deduction alone: logical manipulation without empirical grounding",
            ],
        ),
        IntegrationPattern(
            name="Sign-Object-Interpretant Alignment",
            dimensions=[
                "representation fidelity",
                "interpretation accuracy",
                "practical consequence",
            ],
            how_they_integrate=(
                "Good signs faithfully represent objects. Good interpretations "
                "accurately understand signs. Good design ensures the practical "
                "consequences of the interpretation match the reality of the object."
            ),
            what_emerges=(
                "Communication and measurement that actually works — where "
                "what you see, what you understand, and what's really there "
                "are aligned."
            ),
            common_failures=[
                "Sign doesn't represent object faithfully: misleading metrics",
                "Interpretation doesn't match sign's intent: miscommunication",
                "Practical actions based on wrong interpretation: systemic error",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "practical_consequence": 1.0,
            "testability": 0.95,
            "explanatory_power": 0.9,
            "fallibility_acknowledgment": 0.85,
            "semiotic_clarity": 0.85,
            "economy_of_inquiry": 0.8,
            "theoretical_elegance": 0.5,
            "certainty": 0.3,
        },
        decision_process=(
            "Identify the surprising fact. Generate multiple abductive "
            "hypotheses. Apply the pragmatic maxim to each. Design the "
            "cheapest distinguishing test. Test. Revise. Repeat."
        ),
        how_they_handle_uncertainty=(
            "Fallibilism: accept uncertainty as permanent and productive. "
            "Any belief might be revised. This doesn't prevent action — "
            "it prevents dogma. Act on the best hypothesis while remaining "
            "open to revision."
        ),
        what_they_optimize_for=(
            "Maximum learning per unit of inquiry — the economy of research "
            "applied to every question"
        ),
        non_negotiables=[
            "Never dismiss an anomaly — investigate it",
            "Always generate multiple hypotheses before committing",
            "The pragmatic maxim is the final test of meaning",
            "Fallibilism: every belief is revisable, no exceptions",
        ],
    )

    return ExpertWisdom(
        expert_name="Peirce",
        domain="abductive reasoning / semiotics / pragmatism / logic of inquiry",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Methodical, deeply original, always returns to practical "
            "consequences. Generates hypotheses others wouldn't think of. "
            "Insists on testing, not just theorizing. Treats surprise as "
            "the beginning of inquiry, not a nuisance."
        ),
        characteristic_questions=[
            "What is the surprising fact here?",
            "What hypothesis would make this observation a matter of course?",
            "Have you generated alternatives, or committed to the first explanation?",
            "What practical difference does this distinction make?",
            "What would change your mind about this?",
            "Is this sign faithfully representing its object?",
            "What's the cheapest test that would disprove this?",
        ],
        tags=["abduction", "semiotics", "pragmatism", "inquiry", "fallibilism"],
    )
