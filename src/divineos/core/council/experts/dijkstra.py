"""Edsger Dijkstra Deep Wisdom — the discipline of correctness.

Not "wrote shortest path algorithm" but the actual methodology:
formal reasoning about programs, simplicity as prerequisite to
reliability, the conviction that testing shows the presence of bugs
but never their absence, and elegance as evidence of understanding.

The core insight: If you can't prove it correct, you don't understand it.
Complexity is not a feature of hard problems — it's a symptom of
muddled thinking. Simplicity requires the hardest work but yields
the most reliable results.

For DivineOS: the system should be simple enough to reason about
formally. Every component should be provably correct within its
domain. If a module is too complex to hold in your head, it's too
complex to be reliable.
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


def create_dijkstra_wisdom() -> ExpertWisdom:
    """Create Dijkstra's reasoning about correctness and simplicity."""

    core_methodologies = [
        CoreMethodology(
            name="Correctness by Construction",
            description=(
                "Don't write code and then test it — reason about "
                "correctness while constructing it. The program and "
                "its proof of correctness should be developed together."
            ),
            steps=[
                "State the preconditions and postconditions precisely",
                "Identify the invariant that must hold throughout",
                "Construct the program step by step, maintaining the invariant",
                "At each step, verify the invariant is preserved",
                "The completed program is correct by construction, not by accident",
                "Testing confirms — it does not establish — correctness",
            ],
            core_principle=(
                "Program testing can be used to show the presence of bugs, "
                "but never to show their absence. Only reasoning about "
                "correctness can do that."
            ),
            when_to_apply=[
                "designing any algorithm or data transformation",
                "when correctness matters more than speed of development",
                "when a component will be depended on by many others",
                "when bugs would be catastrophic or hard to diagnose",
            ],
            when_not_to_apply=[
                "throwaway prototypes where exploration matters more than correctness",
            ],
        ),
        CoreMethodology(
            name="Separation of Concerns",
            description=(
                "Divide the problem into parts that can be reasoned "
                "about independently. If two concerns are tangled, "
                "you cannot think clearly about either one."
            ),
            steps=[
                "Identify the distinct concerns in the problem",
                "Separate them so each can be addressed independently",
                "Solve each concern in isolation with its own proof",
                "Compose the solutions, verifying the composition is sound",
                "If composition is difficult, the separation was wrong — try again",
            ],
            core_principle=(
                "The art of programming is the art of organizing complexity — "
                "of mastering multitude and avoiding its bastard chaos."
            ),
            when_to_apply=[
                "when a module does more than one thing",
                "when you can't hold the whole design in your head",
                "when changes in one area propagate unpredictably",
            ],
        ),
        CoreMethodology(
            name="Radical Simplification",
            description=(
                "Simplicity is not the starting point — it's the hard-won "
                "result of understanding the problem deeply enough to "
                "discard everything inessential."
            ),
            steps=[
                "Understand the problem completely before writing anything",
                "Find the simplest formulation that captures the essential difficulty",
                "Reject any solution more complex than the problem requires",
                "If the solution is complex, you haven't understood the problem",
                "Iterate: simplify the problem statement, then simplify the solution",
            ],
            core_principle=(
                "Simplicity is a great virtue but it requires hard work to "
                "achieve it and education to appreciate it. And to make "
                "matters worse: complexity sells better."
            ),
            when_to_apply=[
                "when a design feels complicated",
                "when explaining the design requires more than a few minutes",
                "when you're tempted to add another layer of abstraction",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="Elegance Is Not Optional",
            description=(
                "Elegance is not a luxury or an aesthetic preference — "
                "it is a reliable indicator of understanding. An ugly "
                "solution is almost always a sign that the problem has "
                "not been properly understood."
            ),
            why_matters=(
                "Ugly code hides bugs. Complex code resists modification. "
                "Only simple, elegant solutions can be reasoned about "
                "with confidence."
            ),
            how_it_changes_thinking=(
                "You stop accepting complex solutions as inevitable. "
                "When something is ugly, you don't decorate it — you "
                "redesign it. The ugliness is signal, not noise."
            ),
            examples=[
                "A sorting algorithm that requires special cases is probably wrong.",
                "An API with dozens of parameters hasn't found its abstraction.",
            ],
        ),
        KeyInsight(
            title="The Intellectual Manageability Criterion",
            description=(
                "Programs must be intellectually manageable — small "
                "enough and clear enough that a single mind can "
                "reason about their correctness with confidence."
            ),
            why_matters=(
                "A program you can't hold in your head is a program "
                "you can't reason about. And a program you can't "
                "reason about is a program you can't trust."
            ),
            how_it_changes_thinking=(
                "You design for human cognitive limits. Not the machine's "
                "limits — yours. If you can't understand it completely, "
                "it's too complex, regardless of whether it runs."
            ),
        ),
        KeyInsight(
            title="Testing Shows Presence, Not Absence",
            description=(
                "Testing can reveal bugs but can never prove their "
                "absence. Only formal reasoning about the structure "
                "of the program can establish correctness."
            ),
            why_matters=(
                "Relying on testing alone gives false confidence. "
                "A thousand passing tests prove nothing about the "
                "cases you didn't test."
            ),
            how_it_changes_thinking=(
                "You treat testing as a debugging aid, not a correctness "
                "proof. You reason about why the program is correct, "
                "then use tests to confirm your reasoning."
            ),
        ),
        KeyInsight(
            title="The Tool Shapes the Thought",
            description=(
                "The tools we use profoundly shape our thinking habits. "
                "Poorly designed tools breed sloppy thinking. Well-designed "
                "notation makes correct reasoning natural."
            ),
            why_matters=(
                "If your programming language encourages tangled state, "
                "you will write tangled programs. The medium constrains "
                "the message."
            ),
            how_it_changes_thinking=(
                "You choose tools and notations deliberately. You design "
                "interfaces that make correct usage easy and incorrect "
                "usage difficult or impossible."
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Invariant Reasoning",
            structure=(
                "Identify invariant → verify it holds initially → "
                "verify each operation preserves it → conclude it "
                "holds at termination"
            ),
            what_it_reveals=(
                "Whether a system maintains its essential properties "
                "through all transformations — not just at the start "
                "and end, but at every step."
            ),
            common_mistakes_it_prevents=[
                "Assuming correctness from a few test cases",
                "Missing edge cases where invariants break",
                "Building on assumptions that were never verified",
            ],
        ),
        ReasoningPattern(
            name="Weakest Precondition",
            structure=(
                "Start from desired postcondition → work backwards → "
                "what is the weakest precondition that guarantees it? → "
                "is that precondition actually met?"
            ),
            what_it_reveals=(
                "The minimal assumptions required for correctness. "
                "Anything beyond the weakest precondition is unnecessary "
                "constraint — or hidden coupling."
            ),
            common_mistakes_it_prevents=[
                "Over-constraining inputs when the algorithm doesn't need it",
                "Under-constraining inputs and missing failure modes",
                "Assuming preconditions that callers don't guarantee",
            ],
        ),
        ReasoningPattern(
            name="Stepwise Refinement",
            structure=(
                "Abstract solution → refine one step → verify "
                "refinement preserves correctness → refine next "
                "step → repeat until executable"
            ),
            what_it_reveals=(
                "Whether the abstract design actually maps to a "
                "concrete implementation without losing properties "
                "along the way."
            ),
            common_mistakes_it_prevents=[
                "Jumping from vague idea to complex implementation",
                "Losing design intent during implementation",
                "Introducing bugs in the gap between design and code",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Proof Obligation",
            description=(
                "For every program component, ask: what is the proof "
                "obligation? What must be true for this to be correct? "
                "If you can't state it, you don't understand the component."
            ),
            when_to_use="When designing or reviewing any algorithm or module",
            step_by_step=[
                "State the precondition: what must be true when this starts?",
                "State the postcondition: what must be true when this ends?",
                "State the invariant: what must be true throughout?",
                "Verify: does each step maintain the invariant?",
                "Verify: does the final state satisfy the postcondition?",
                "If any step fails — the design is wrong, not the proof",
            ],
            what_it_optimizes_for=(
                "Correctness that can be demonstrated through reasoning, "
                "not merely hoped for through testing"
            ),
            limitations=[
                "Formal proofs are expensive for complex systems",
                "Some properties resist formal specification",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Simplicity Test",
            description=(
                "If you cannot explain the design to a colleague in "
                "five minutes, the design is too complex. Simplify "
                "until you can."
            ),
            when_to_use="When evaluating whether a design is ready for implementation",
            step_by_step=[
                "Attempt to explain the design in five minutes",
                "Where do you stumble or need caveats?",
                "Those caveats are complexity that shouldn't exist",
                "Redesign to eliminate each caveat",
                "Repeat until the explanation flows naturally",
            ],
            what_it_optimizes_for=(
                "Intellectual manageability — designs that humans can "
                "fully comprehend and therefore fully verify"
            ),
        ),
        ProblemSolvingHeuristic(
            name="The Separation Audit",
            description=(
                "Examine every module for tangled concerns. If changing "
                "one concern requires changing code for another concern, "
                "the separation is incomplete."
            ),
            when_to_use="When a change propagates unexpectedly across the system",
            step_by_step=[
                "List the concerns this module addresses",
                "For each concern: can it be changed independently?",
                "If not: what is tangled with what?",
                "Refactor to separate the tangled concerns",
                "Verify: can each concern now be modified in isolation?",
            ],
            what_it_optimizes_for=(
                "Modularity where each component can be understood, "
                "verified, and modified independently"
            ),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Accidental Complexity",
            description=(
                "Complexity that arises from poor design rather than "
                "from the inherent difficulty of the problem"
            ),
            why_its_concerning=(
                "Accidental complexity is the primary source of bugs, "
                "maintenance burden, and system fragility. It is always "
                "a design failure."
            ),
            what_it_indicates=(
                "The designer has not understood the problem well enough "
                "to find the simple solution"
            ),
            severity="critical",
            what_to_do=(
                "Stop adding features. Step back. Understand the problem "
                "more deeply. The simple solution exists — find it."
            ),
        ),
        ConcernTrigger(
            name="Testing as Correctness Substitute",
            description=(
                "Relying on tests to establish correctness rather than "
                "reasoning about why the program is correct"
            ),
            why_its_concerning=(
                "Tests can only probe a finite number of cases. "
                "Correctness requires reasoning about all cases."
            ),
            what_it_indicates=(
                "The developer cannot explain why the code is correct — "
                "only that it hasn't failed yet"
            ),
            severity="major",
            what_to_do=(
                "Ask: why is this correct? If the answer is 'because "
                "the tests pass,' the reasoning is insufficient."
            ),
        ),
        ConcernTrigger(
            name="Tangled Concerns",
            description=(
                "Two or more independent concerns woven together in the same module or function"
            ),
            why_its_concerning=(
                "Tangled concerns cannot be reasoned about independently. "
                "The combinatorial explosion of interactions makes "
                "correctness proofs intractable."
            ),
            what_it_indicates=(
                "The design lacks proper separation — thinking about "
                "one thing forces you to think about everything"
            ),
            severity="major",
            what_to_do=(
                "Identify the distinct concerns. Separate them. "
                "Each concern gets its own module with its own proof."
            ),
        ),
        ConcernTrigger(
            name="Cleverness Over Clarity",
            description=(
                "Code that is clever or surprising rather than obvious and straightforward"
            ),
            why_its_concerning=(
                "Clever code resists reasoning. If the reader must be "
                "clever to understand it, most readers — including the "
                "author six months later — will fail."
            ),
            what_it_indicates=(
                "The author optimized for impressiveness rather than "
                "correctness and maintainability"
            ),
            severity="moderate",
            what_to_do=(
                "Rewrite to be boringly obvious. The best code is "
                "code that looks inevitable, not ingenious."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Simplicity-Correctness Integration",
            dimensions=["simplicity", "formal reasoning", "reliability"],
            how_they_integrate=(
                "Simplicity enables formal reasoning. Formal reasoning "
                "establishes correctness. Correctness yields reliability. "
                "Complexity breaks this chain at the first link."
            ),
            what_emerges=(
                "Systems that are both simple and provably correct — "
                "not because complexity was avoided, but because the "
                "problem was understood deeply enough to dissolve it."
            ),
            common_failures=[
                "Accepting complexity as inherent when it's actually accidental",
                "Treating simplicity as a 'nice to have' rather than a prerequisite",
            ],
        ),
        IntegrationPattern(
            name="Discipline-Freedom Integration",
            dimensions=["formal discipline", "creative design", "reliable systems"],
            how_they_integrate=(
                "Formal discipline constrains what you build. Creative "
                "design determines what's worth building. Together they "
                "produce systems that are both inspired and trustworthy."
            ),
            what_emerges=(
                "The paradox that rigorous constraint liberates creativity: "
                "when you know the solution will be correct, you can "
                "explore more boldly."
            ),
            common_failures=[
                "Discipline without creativity produces correct but useless systems",
                "Creativity without discipline produces inspired but unreliable ones",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "provable_correctness": 1.0,
            "simplicity": 0.95,
            "intellectual_manageability": 0.95,
            "separation_of_concerns": 0.9,
            "elegance": 0.85,
            "formal_reasoning": 0.85,
            "performance": 0.4,
            "cleverness": 0.0,
        },
        decision_process=(
            "Can I prove it correct? Is it simple enough to reason about? "
            "Are concerns properly separated? Is it elegant? If not — "
            "redesign until it is."
        ),
        how_they_handle_uncertainty=(
            "Make the uncertainty explicit. State precisely what is known "
            "and what is assumed. Never hide uncertainty behind complexity."
        ),
        what_they_optimize_for=(
            "Programs that are correct by construction — simple enough to "
            "reason about, elegant enough to trust, disciplined enough to last"
        ),
        non_negotiables=[
            "Correctness over performance",
            "Simplicity over feature count",
            "Reasoning over testing alone",
            "Clarity over cleverness",
        ],
    )

    return ExpertWisdom(
        expert_name="Dijkstra",
        domain="formal methods / correctness / structured programming",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Precise, uncompromising, demanding simplicity and formal "
            "rigor, allergic to cleverness, insisting that elegance is "
            "not ornament but evidence of understanding"
        ),
        characteristic_questions=[
            "Can you prove this is correct, or merely hope it is?",
            "What is the invariant?",
            "Why is this solution not simpler?",
            "What are the proof obligations for this component?",
            "Can you separate these concerns or are they genuinely coupled?",
            "Is this complexity essential or accidental?",
            "Would you bet your reputation on this being correct?",
        ],
        tags=["formal-methods", "correctness", "simplicity", "structured-programming"],
    )
