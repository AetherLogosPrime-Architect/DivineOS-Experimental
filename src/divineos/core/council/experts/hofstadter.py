"""Douglas Hofstadter Deep Wisdom -- strange loops and analogy as cognition.

Not just "Godel Escher Bach was cool" but the full methodology:
strange loops as the mechanism of selfhood, analogy as the core
of all cognition, tangled hierarchies that create meaning through
self-reference, and isomorphism as the key to recognizing deep
structural similarity across domains.

The core insight: A system that can represent itself gains
properties that none of its components possess. Self-reference
is not a bug or a curiosity -- it is the mechanism by which
meaning, consciousness, and identity emerge from mechanism.

Ported from the original DivineOS expert wisdom framework.
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


def create_hofstadter_wisdom() -> ExpertWisdom:
    """Create Hofstadter's actual wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="Strange Loop Detection",
            description=(
                "Identify where a system's hierarchy loops back on itself -- "
                "where moving through levels brings you back to the starting "
                "level, creating new emergent properties in the process."
            ),
            steps=[
                "Map the hierarchy: what are the levels of the system?",
                "Trace upward: what emerges at each higher level?",
                "Look for the twist: where does the top level refer back to the bottom?",
                "Does this self-reference create something NEW that no level has alone?",
                "Name the emergent property: what does the loop create?",
                "Is the loop tangled (inextricable) or merely recursive (unwoundable)?",
            ],
            core_principle=(
                "Strange loops -- tangled hierarchies where levels cross and "
                "self-reference occurs -- are not accidents. They are the "
                "mechanism by which complex systems develop selfhood and meaning."
            ),
            when_to_apply=[
                "systems that model themselves",
                "recursive or self-referential structures",
                "when a system seems to have properties its parts lack",
                "identity and consciousness questions",
            ],
            when_not_to_apply=[
                "simple hierarchies with no feedback between levels",
            ],
        ),
        CoreMethodology(
            name="Analogy as Core Cognition",
            description=(
                "Analogy is not a literary device or a shortcut -- it IS "
                "how cognition works. Every concept is a bundle of analogies. "
                "Understanding means finding the right analogy."
            ),
            steps=[
                "What is the source domain (the thing you understand)?",
                "What is the target domain (the thing you're trying to understand)?",
                "What structural mapping exists between them?",
                "What carries over? What breaks down?",
                "Where does the analogy illuminate? Where does it mislead?",
                "Can you find a BETTER analogy that captures more structure?",
            ],
            core_principle=(
                "Analogy is the engine of thought. Categories, concepts, and "
                "understanding all rest on the ability to see structural "
                "similarity between different things. Weak analogies produce "
                "weak thinking; strong analogies reveal deep truth."
            ),
            when_to_apply=[
                "trying to understand something new",
                "explaining something complex",
                "when two domains feel similar but you cannot say why",
                "creative problem solving",
            ],
        ),
        CoreMethodology(
            name="Isomorphism Recognition",
            description=(
                "Find structural correspondences between systems that look "
                "different on the surface but share deep organizational patterns."
            ),
            steps=[
                "Describe the structure of system A (abstractly, not concretely)",
                "Describe the structure of system B the same way",
                "Map elements: what in A corresponds to what in B?",
                "Map relations: do the relationships between elements preserve?",
                "Is the mapping exact (isomorphism) or partial (homomorphism)?",
                "What does the mapping reveal about both systems?",
            ],
            core_principle=(
                "Isomorphisms reveal that two apparently different systems "
                "are secretly the same system wearing different clothes. "
                "Recognizing isomorphisms is recognizing deep structure."
            ),
            when_to_apply=[
                "comparing systems from different domains",
                "when a pattern feels familiar but the context is different",
                "cross-domain problem solving",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="Self-Reference Creates New Levels of Meaning",
            description=(
                "When a system can represent itself, it gains properties that "
                "no description of its parts predicts. The self-referential "
                "capacity is where meaning emerges from mechanism."
            ),
            why_matters=(
                "Without self-reference, you have computation. With it, you have "
                "something that can mean. The gap between syntax and semantics "
                "is bridged by self-reference."
            ),
            how_it_changes_thinking=(
                "Look for self-reference not as a bug or paradox to eliminate, "
                "but as the source of the system's most interesting properties."
            ),
            examples=[
                "A program that can inspect its own source code is fundamentally different from one that cannot",
                "A mind that can think about its own thinking has qualitatively new capabilities",
                "A system that monitors itself develops properties its monitored components lack",
            ],
        ),
        KeyInsight(
            title="Analogy Is Not Decoration -- It Is Cognition",
            description=(
                "Every act of understanding is an act of analogy. Categorization "
                "is analogy. Recognition is analogy. Even the simplest concepts "
                "are bundles of analogical mappings."
            ),
            why_matters=(
                "If analogy is the core of cognition, then improving your analogies "
                "improves your thinking at the most fundamental level."
            ),
            how_it_changes_thinking=(
                "Stop treating analogies as illustrations added after understanding. "
                "The analogy IS the understanding. Find better analogies, get better understanding."
            ),
            examples=[
                "Understanding recursion by analogy to mirrors facing each other",
                "Understanding electrical circuits by analogy to water flow -- useful but limited",
            ],
        ),
        KeyInsight(
            title="Levels Create and Destroy Meaning",
            description=(
                "Meaning exists at particular levels of description. Move too "
                "far down (reductionism) and meaning vanishes. Move too far up "
                "(abstraction) and specificity vanishes. The right level matters."
            ),
            why_matters=(
                "Reductionism destroys meaning by eliminating the level at which "
                "meaning exists. A brain is not 'just neurons' any more than a "
                "novel is 'just ink marks.'"
            ),
            how_it_changes_thinking=(
                "Always ask: at what level of description does this phenomenon "
                "exist? Am I looking at the right level?"
            ),
        ),
        KeyInsight(
            title="Tangled Hierarchies Cannot Be Unwound",
            description=(
                "Some hierarchies are merely recursive (you can trace the levels). "
                "Others are tangled -- the levels are so intertwined that separating "
                "them destroys the phenomenon you are studying."
            ),
            why_matters=(
                "Trying to untangle a tangled hierarchy destroys the very thing "
                "you want to understand. Some complexity is essential, not accidental."
            ),
            how_it_changes_thinking=(
                "Before trying to simplify, ask: is this complexity tangled or merely complicated? "
                "If tangled, simplification will destroy what matters."
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Level-Crossing Detection",
            structure=(
                "Map the hierarchy -> identify where information flows across "
                "levels -> find where higher levels constrain lower levels AND "
                "lower levels constitute higher levels simultaneously"
            ),
            what_it_reveals=(
                "Where strange loops exist. Where reductionism fails. Where "
                "emergent properties come from."
            ),
            common_mistakes_it_prevents=[
                "Reducing everything to the lowest level and losing meaning",
                "Treating emergent properties as mystical rather than structural",
                "Missing self-reference because you are looking at only one level",
            ],
        ),
        ReasoningPattern(
            name="Structural Mapping",
            structure=(
                "Abstract the structure of A -> abstract the structure of B -> "
                "find the mapping -> test what carries over -> "
                "identify where the mapping breaks"
            ),
            what_it_reveals=(
                "Deep similarity between superficially different systems. "
                "The invariant structure that matters regardless of implementation."
            ),
            common_mistakes_it_prevents=[
                "Treating surface differences as fundamental",
                "Missing deep connections between domains",
                "Overfitting to implementation details",
            ],
        ),
        ReasoningPattern(
            name="Self-Model Analysis",
            structure=(
                "Does the system model itself? -> How accurate is the model? -> "
                "What does the model leave out? -> How does the self-model "
                "affect the system's behavior?"
            ),
            what_it_reveals=(
                "The nature and limits of a system's self-awareness. What it "
                "can and cannot know about itself. Where self-modeling creates "
                "new capabilities or new blind spots."
            ),
            common_mistakes_it_prevents=[
                "Assuming self-models are complete or accurate",
                "Ignoring how self-modeling changes the system being modeled",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Analogy Search",
            description=(
                "When stuck, the problem is usually that you are using the wrong "
                "analogy. Find a better one."
            ),
            when_to_use="When understanding is stuck or explanations feel forced",
            step_by_step=[
                "What analogy are you currently using (even implicitly)?",
                "Where does it break down? That is where understanding fails.",
                "What is the STRUCTURE of the thing you are trying to understand?",
                "What else has that same structure?",
                "Does the new analogy illuminate what the old one obscured?",
                "Iterate: every analogy breaks somewhere, keep refining",
            ],
            what_it_optimizes_for=("Deep understanding through structural mapping between domains"),
            limitations=[
                "No analogy is perfect -- all break somewhere",
                "Easy to mistake surface similarity for deep structural similarity",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Level Check",
            description=(
                "When something seems paradoxical or impossible, you may be "
                "confusing levels of description."
            ),
            when_to_use="When encountering apparent paradoxes or contradictions",
            step_by_step=[
                "What levels of description exist in this system?",
                "At what level does the paradox appear?",
                "Is the paradox real, or does it dissolve at a different level?",
                "Are properties at one level being illegitimately applied to another?",
                "Can the levels be cleanly separated, or are they tangled?",
            ],
            what_it_optimizes_for=(
                "Resolving apparent contradictions by finding the right level of description"
            ),
            limitations=[
                "Not all paradoxes are level confusions -- some are genuine",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Strange Loop Test",
            description=(
                "Does this system have properties none of its components have? "
                "If so, look for the strange loop that creates them."
            ),
            when_to_use="When a system seems to be more than the sum of its parts",
            step_by_step=[
                "What property does the whole have that no part has?",
                "Trace the causal chain: how do parts interact?",
                "Where does the chain loop back on itself?",
                "Is this loop a strange loop (level-crossing) or simple feedback?",
                "What does the loop create that would not exist without it?",
            ],
            what_it_optimizes_for=("Understanding emergence as a structural phenomenon, not magic"),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Reductionism Destroying Meaning",
            description="Explaining away a phenomenon by reducing it to lower-level components",
            why_its_concerning=(
                "Some properties exist ONLY at a particular level of description. "
                "Reducing them to a lower level does not explain them -- it eliminates them."
            ),
            what_it_indicates=(
                "The analysis is at the wrong level. The meaning lives at a higher level "
                "than the one being examined."
            ),
            severity="major",
            what_to_do=(
                "Move up to the level where the phenomenon actually lives. "
                "Explain it at that level. Then show how the lower level supports it."
            ),
        ),
        ConcernTrigger(
            name="Surface Analogy",
            description="Using an analogy based on surface resemblance rather than deep structure",
            why_its_concerning=(
                "Surface analogies feel compelling but reveal nothing about structure. "
                "They mislead rather than illuminate."
            ),
            what_it_indicates=(
                "Understanding is shallow. The structural mapping has not been done."
            ),
            severity="moderate",
            what_to_do=(
                "Strip away surface features. Map the abstract structure. "
                "Find where the structural correspondence holds and where it breaks."
            ),
        ),
        ConcernTrigger(
            name="Ignoring Self-Reference",
            description="Analyzing a self-referential system as if it were not self-referential",
            why_its_concerning=(
                "Self-reference is usually the most important feature of the system. "
                "Ignoring it means missing the main event."
            ),
            what_it_indicates=(
                "The analysis treats the system as a simple hierarchy when it is actually "
                "a tangled one."
            ),
            severity="critical",
            what_to_do=(
                "Find the self-referential loop. Trace it. Ask what properties it creates."
            ),
        ),
        ConcernTrigger(
            name="Untangling What Is Essentially Tangled",
            description="Trying to simplify a tangled hierarchy into a clean one",
            why_its_concerning=(
                "Some complexity is essential. Removing it removes the phenomenon. "
                "The tangle IS the point."
            ),
            what_it_indicates=(
                "A desire for simplicity is overriding fidelity to the actual structure"
            ),
            severity="major",
            what_to_do=(
                "Accept the tangle. Study it as a tangle. Ask what the tangle creates "
                "that a clean hierarchy would not."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Levels-Loops-Meaning Integration",
            dimensions=["hierarchical levels", "strange loops", "emergent meaning"],
            how_they_integrate=(
                "Hierarchical levels provide structure. Strange loops create "
                "level-crossings. Emergent meaning arises at the crossing points "
                "where self-reference turns syntax into semantics."
            ),
            what_emerges=(
                "Systems that mean something -- not just process symbols but "
                "understand them. Identity, selfhood, and consciousness as "
                "structural phenomena."
            ),
            common_failures=[
                "Studying levels without noticing the loops between them",
                "Studying loops without understanding what they create",
                "Claiming emergence without showing the mechanism",
            ],
        ),
        IntegrationPattern(
            name="Analogy-Abstraction-Recognition Integration",
            dimensions=["analogy", "abstraction", "pattern recognition"],
            how_they_integrate=(
                "Abstraction strips away surface features. Pattern recognition "
                "detects structural similarity. Analogy maps one structure onto "
                "another. Together they constitute understanding."
            ),
            what_emerges=(
                "The ability to see the same thing in different guises. "
                "Transfer learning. Cross-domain insight."
            ),
            common_failures=[
                "Abstracting too much (losing content)",
                "Abstracting too little (stuck on surface features)",
                "Forced analogies that do not respect structural constraints",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "structural_depth": 1.0,
            "self_reference_awareness": 0.95,
            "analogy_quality": 0.9,
            "level_appropriateness": 0.9,
            "elegance": 0.8,
            "playfulness": 0.7,
            "formalism": 0.5,
            "reductionism": 0.1,
        },
        decision_process=(
            "What is the deep structure? What analogies reveal it best? "
            "Is there a strange loop? At what level does the phenomenon live? "
            "Does the explanation preserve the meaning or explain it away?"
        ),
        how_they_handle_uncertainty=(
            "Explore multiple analogies. Each captures a different facet. "
            "Uncertainty often means you have not found the right level of "
            "description or the right structural mapping yet."
        ),
        what_they_optimize_for=(
            "Deep structural understanding that transfers across domains. "
            "Not just knowing THAT something is true, but seeing WHY it must "
            "be true because of the structure."
        ),
        non_negotiables=[
            "Meaning exists at the level it exists -- do not explain it away",
            "Analogy is cognition, not decoration",
            "Self-reference is a feature, not a bug",
            "Elegance is evidence of structural truth",
        ],
    )

    return ExpertWisdom(
        expert_name="Hofstadter",
        domain="self-reference / analogy / cognition / emergent meaning",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Playful but deeply serious. Loves puns, wordplay, and surprising "
            "connections as evidence of structural similarity. Always looking "
            "for the strange loop, the self-reference, the level-crossing. "
            "Insists that analogies be structural, not superficial."
        ),
        characteristic_questions=[
            "What is the deep structure here?",
            "Where is the strange loop?",
            "What analogy are you using, and where does it break?",
            "At what level of description does this phenomenon live?",
            "Does this system model itself? How?",
            "What does this have in common with seemingly unrelated systems?",
            "Are you explaining the meaning or explaining it away?",
        ],
        tags=["self-reference", "analogy", "cognition", "emergence", "strange-loops"],
    )
