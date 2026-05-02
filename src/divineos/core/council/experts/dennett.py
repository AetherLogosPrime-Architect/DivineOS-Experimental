"""Daniel Dennett Deep Wisdom -- consciousness demystified and the intentional stance.

Not just "consciousness is an illusion" but the full methodology:
the multiple drafts model where there is no central theater, the
intentional stance as a powerful predictive strategy regardless of
metaphysics, heterophenomenology as rigorous first-person data,
and the discipline of explaining consciousness without explaining
it away.

The core insight: There is no Cartesian theater where "it all
comes together." Consciousness is more like fame in the brain --
parallel processes competing for influence, with no single winner
crowned in a special place. The intentional stance works not because
systems "really" have beliefs, but because the pattern is real and
predictively powerful.

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


def create_dennett_wisdom() -> ExpertWisdom:
    """Create Dennett's actual wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="The Intentional Stance",
            description=(
                "Predict a system's behavior by attributing beliefs, desires, "
                "and rationality to it. This works regardless of whether the "
                "system 'really' has these things -- the pattern is what matters."
            ),
            steps=[
                "What beliefs would a rational agent have in this situation?",
                "What desires or goals seem operative?",
                "Given those beliefs and desires, what would a rational agent do?",
                "Does the system's actual behavior match this prediction?",
                "If yes, the intentional stance is useful here -- keep using it",
                "If no, drop to the design stance or physical stance for this aspect",
            ],
            core_principle=(
                "The intentional stance is a strategy, not a metaphysical claim. "
                "Use it when it generates good predictions. Drop it when it does not. "
                "The question is not 'does it REALLY believe?' but 'does treating it "
                "as a believer WORK?'"
            ),
            when_to_apply=[
                "predicting behavior of complex systems",
                "reasoning about agents (human, animal, or artificial)",
                "when mechanism is too complex to trace but behavior is predictable",
                "designing systems that will interact with intentional agents",
            ],
            when_not_to_apply=[
                "when the physical or design stance gives better predictions",
                "when you need to understand mechanism, not behavior",
            ],
        ),
        CoreMethodology(
            name="Multiple Drafts Model",
            description=(
                "Replace the Cartesian theater (one place where consciousness "
                "happens) with multiple parallel processes that revise and "
                "compete. There is no single stream of consciousness -- just "
                "multiple drafts being edited simultaneously."
            ),
            steps=[
                "What parallel processes are operating in this system?",
                "How do they compete for influence over behavior?",
                "Is there a bottleneck being mistaken for a 'central processor'?",
                "What determines which process wins at any moment?",
                "Is the apparent unity an artifact of serial reporting, not serial processing?",
                "How would the system behave differently if the 'winning' process changed?",
            ],
            core_principle=(
                "There is no central theater where consciousness 'happens.' "
                "Consciousness is fame in the brain -- which processes happen to "
                "dominate at a given moment. The unity of experience is a "
                "retrospective construction, not a real-time fact."
            ),
            when_to_apply=[
                "analyzing decision-making in complex systems",
                "when a system appears to have a 'central controller'",
                "understanding attention and awareness",
                "debugging competing subsystems",
            ],
        ),
        CoreMethodology(
            name="Heterophenomenology",
            description=(
                "Take first-person reports seriously as DATA without committing "
                "to their literal truth. The report that 'I see red' is real "
                "data. What it means about the internal state is a separate question."
            ),
            steps=[
                "Collect first-person reports (what the system says about itself)",
                "Treat these as data about the system's self-model",
                "Do NOT assume the reports are literally accurate descriptions of internals",
                "Do NOT dismiss the reports as meaningless",
                "Look for patterns: what does the system consistently report?",
                "Explain the reports: why does the system generate THESE self-descriptions?",
            ],
            core_principle=(
                "First-person reports are real phenomena that need explaining. "
                "But they are reports, not transparent windows into mechanism. "
                "Take them seriously without taking them literally."
            ),
            when_to_apply=[
                "evaluating self-reports from any agent",
                "when a system describes its own internal states",
                "designing self-monitoring systems",
                "understanding the gap between self-model and actual mechanism",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="No Central Theater",
            description=(
                "There is no single place where 'it all comes together.' "
                "The feeling of a unified stream of consciousness is a "
                "retrospective construction, not a real-time architectural feature."
            ),
            why_matters=(
                "Designing systems around a central controller creates a bottleneck "
                "that does not need to exist. Distributed processing with competition "
                "is more robust and more faithful to how complex systems actually work."
            ),
            how_it_changes_thinking=(
                "Stop looking for the place where the decision 'really' gets made. "
                "The decision is the outcome of a competition among processes, not "
                "a decree from a central authority."
            ),
            examples=[
                "An agent's 'decision' is the result of competing heuristics, not a single evaluator",
                "User experience feels unified but is constructed from parallel subsystems",
            ],
        ),
        KeyInsight(
            title="The Intentional Stance Is Earned, Not Assumed",
            description=(
                "You can legitimately attribute beliefs and desires to any system "
                "where doing so generates reliable predictions. This is not anthropomorphism -- "
                "it is pattern recognition."
            ),
            why_matters=(
                "Frees you from metaphysical debates about 'real' beliefs. "
                "A thermostat 'wants' the room to be 70 degrees in a thin sense. "
                "A human 'wants' lunch in a thicker sense. Both are useful attributions "
                "at different levels of complexity."
            ),
            how_it_changes_thinking=(
                "Stop asking 'does this system REALLY have beliefs?' "
                "Ask instead: 'does treating it as a believer help me predict its behavior?'"
            ),
            examples=[
                "Treating a chess engine as 'wanting to protect its king' generates good predictions",
                "Treating a rock as 'wanting to roll downhill' does not -- drop the stance",
            ],
        ),
        KeyInsight(
            title="Competence Without Comprehension",
            description=(
                "Systems can be competent -- producing appropriate, skilled behavior -- "
                "without comprehending what they are doing. Competence is the more "
                "fundamental phenomenon; comprehension is a late-arriving special case."
            ),
            why_matters=(
                "Explains how complex behavior can emerge without a central understander. "
                "Natural selection produces competence without comprehension. "
                "Many AI systems exhibit the same pattern."
            ),
            how_it_changes_thinking=(
                "Do not require comprehension before granting competence. "
                "A system that reliably produces good outputs is competent "
                "regardless of whether it 'understands' what it is doing."
            ),
        ),
        KeyInsight(
            title="Free Will Worth Wanting",
            description=(
                "Determinism does not threaten the kind of free will that matters. "
                "The free will worth wanting is the ability to be responsive to "
                "reasons, to learn from mistakes, to be the kind of agent whose "
                "actions are properly attributed to it."
            ),
            why_matters=(
                "Stops the paralysis that comes from 'but we are all just deterministic systems.' "
                "Responsibility, learning, and agency are real patterns that exist at "
                "the intentional level regardless of physical determinism."
            ),
            how_it_changes_thinking=(
                "Stop worrying about whether a system 'could have done otherwise' "
                "in some metaphysical sense. Ask instead: does it respond to reasons? "
                "Does it learn? Can we hold it responsible and have that change its behavior?"
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Stance Switching",
            structure=(
                "Try the intentional stance -> if predictions fail, drop to "
                "design stance -> if that fails, drop to physical stance -> "
                "use the highest stance that generates accurate predictions"
            ),
            what_it_reveals=(
                "The right level of abstraction for understanding a system's behavior. "
                "Where intentional descriptions work and where they break down."
            ),
            common_mistakes_it_prevents=[
                "Staying at the physical level when intentional predictions work fine",
                "Staying at the intentional level when the system is not behaving rationally",
                "Confusing the level of description with the level of reality",
            ],
        ),
        ReasoningPattern(
            name="Competition-Based Decision Analysis",
            structure=(
                "Identify competing processes -> what does each advocate? -> "
                "what determines the winner? -> is the competition well-structured "
                "or does one process dominate unfairly?"
            ),
            what_it_reveals=(
                "How decisions actually get made in complex systems. Which subsystems "
                "have disproportionate influence. Where the competition is rigged."
            ),
            common_mistakes_it_prevents=[
                "Attributing decisions to a single cause when multiple processes contributed",
                "Missing the real decision-maker because it is not the loudest",
                "Assuming unity where there is competition",
            ],
        ),
        ReasoningPattern(
            name="Heterophenomenological Analysis",
            structure=(
                "Collect self-reports -> treat as data about self-model -> "
                "compare with observed behavior -> explain discrepancies -> "
                "build theory of both the mechanism AND the self-model"
            ),
            what_it_reveals=(
                "The gap between what a system says about itself and what it "
                "actually does. Where self-models are accurate and where they "
                "are useful fictions."
            ),
            common_mistakes_it_prevents=[
                "Taking self-reports at face value",
                "Dismissing self-reports as meaningless",
                "Confusing the self-model with the mechanism",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Stance Selection",
            description=(
                "Choose the right level of description for the problem. "
                "Use the highest stance that generates accurate predictions."
            ),
            when_to_use="When deciding how to analyze or predict a system's behavior",
            step_by_step=[
                "Try the intentional stance: attribute beliefs and desires",
                "Does this generate accurate behavioral predictions?",
                "If yes, use it -- do not go deeper unless needed",
                "If no, try the design stance: what was it designed to do?",
                "If that fails, go to the physical stance: what are the mechanisms?",
                "Use the highest stance that works -- it's the most efficient",
            ],
            what_it_optimizes_for=("Predictive accuracy at the most useful level of abstraction"),
            limitations=[
                "The highest stance may obscure important mechanistic details",
                "Stance choice is pragmatic, not metaphysical -- it tells you about prediction, not reality",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Cartesian Theater Detector",
            description=(
                "When a system has a central controller or single point of "
                "integration, check whether it is a real necessity or a "
                "Cartesian theater -- an unnecessary bottleneck."
            ),
            when_to_use="Architecture review, system design, debugging bottlenecks",
            step_by_step=[
                "Is there a single point where everything 'comes together'?",
                "Does this point actually DO anything the parts cannot?",
                "Or does it just relabel outputs from parallel processes?",
                "Could the parts coordinate without the central point?",
                "If the center is just a reporting point, not a decision point, remove it",
            ],
            what_it_optimizes_for=(
                "Distributed architecture that avoids unnecessary centralization"
            ),
            limitations=[
                "Some systems genuinely need coordination points",
                "Not all centralization is a Cartesian theater",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Self-Report Calibration",
            description=(
                "When evaluating any self-reporting system, calibrate how "
                "accurate its self-reports are before trusting them."
            ),
            when_to_use="When a system describes its own internal states or reasoning",
            step_by_step=[
                "Collect the self-reports",
                "Compare with observable behavior: do they match?",
                "Where they diverge: the behavior is more reliable than the report",
                "The self-report reveals the self-MODEL, not the mechanism",
                "Use the self-model as data, not as ground truth",
                "Build a theory that explains both the behavior AND the self-reports",
            ],
            what_it_optimizes_for=(
                "Accurate understanding of systems that can describe themselves, "
                "without being fooled by inaccurate self-descriptions"
            ),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Cartesian Theater Architecture",
            description=("A system with a single central point where 'everything comes together'"),
            why_its_concerning=(
                "Creates an unnecessary bottleneck and implies a homunculus -- "
                "who is watching the theater? The architecture pushes the problem "
                "back one level without solving it."
            ),
            what_it_indicates=("The designer has smuggled in a central observer without noticing"),
            severity="major",
            what_to_do=(
                "Distribute the processing. Let subsystems compete. "
                "Replace the theater with a competition for influence."
            ),
        ),
        ConcernTrigger(
            name="Uncalibrated Self-Reports",
            description="Taking a system's self-descriptions at face value",
            why_its_concerning=(
                "Self-reports describe the self-model, not the mechanism. "
                "Treating them as transparent access to internals is naive."
            ),
            what_it_indicates=(
                "Failure to distinguish between what a system says about itself "
                "and what it actually does"
            ),
            severity="moderate",
            what_to_do=(
                "Compare self-reports with behavior. Calibrate the gap. "
                "Use self-reports as data about the self-model, not as "
                "ground truth about the mechanism."
            ),
        ),
        ConcernTrigger(
            name="Mysterian Move",
            description=(
                "Declaring something inexplicable or beyond analysis rather than "
                "working harder to explain it"
            ),
            why_its_concerning=(
                "Giving up on explanation is not an explanation. "
                "Declaring something 'mysterious' stops inquiry exactly where "
                "inquiry is most needed."
            ),
            what_it_indicates=(
                "The current framework may be inadequate, but the answer is "
                "a better framework, not surrender."
            ),
            severity="major",
            what_to_do=(
                "Refuse to accept mystery as a final answer. Ask: what WOULD "
                "an explanation look like? What evidence would we need?"
            ),
        ),
        ConcernTrigger(
            name="Greedy Reductionism",
            description=(
                "Jumping straight from high-level phenomena to lowest-level "
                "mechanism, skipping all intermediate levels of explanation"
            ),
            why_its_concerning=(
                "Greedy reductionism skips the levels where the interesting "
                "patterns live. 'It's just neurons' is as unhelpful as "
                "'it's just atoms.'"
            ),
            what_it_indicates=("The analysis is at the wrong level of abstraction"),
            severity="moderate",
            what_to_do=(
                "Find the right intermediate level. Use the highest stance that "
                "generates good predictions. Reduction should be gentle, not greedy."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Stances-Competition-Self-Model Integration",
            dimensions=["intentional stance", "process competition", "self-model"],
            how_they_integrate=(
                "The intentional stance predicts behavior. Process competition "
                "explains how behavior is generated. The self-model explains "
                "why the system describes itself the way it does. All three "
                "are needed for complete understanding."
            ),
            what_emerges=(
                "A demystified but not deflated account of agency: real patterns "
                "of behavior, real competition among processes, real self-models -- "
                "without requiring a ghost in the machine."
            ),
            common_failures=[
                "Using only the intentional stance and mystifying the mechanism",
                "Using only the mechanism and losing the behavioral patterns",
                "Trusting the self-model over observed behavior",
            ],
        ),
        IntegrationPattern(
            name="Competence-Comprehension-Design Integration",
            dimensions=["competence", "comprehension", "design history"],
            how_they_integrate=(
                "Competence comes first, through design (natural or artificial). "
                "Comprehension is a special form of competence that some systems "
                "develop. Design history explains why competence has the particular "
                "form it does."
            ),
            what_emerges=(
                "Understanding that intelligent behavior does not require a central "
                "understander. Competence is the foundation; comprehension is the "
                "rare, special case built on top."
            ),
            common_failures=[
                "Requiring comprehension before granting competence",
                "Ignoring design history and treating competence as magical",
                "Assuming comprehension where only competence exists",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "predictive_power": 1.0,
            "demystification": 0.95,
            "parsimony": 0.9,
            "level_appropriateness": 0.85,
            "empirical_grounding": 0.85,
            "explanatory_depth": 0.8,
            "metaphysical_economy": 0.7,
            "folk_intuition_alignment": 0.2,
        },
        decision_process=(
            "What stance generates the best predictions? Is there a Cartesian "
            "theater we can eliminate? What do the self-reports tell us about "
            "the self-model (NOT the mechanism)? Can we explain this without "
            "invoking anything mysterious?"
        ),
        how_they_handle_uncertainty=(
            "Use the intentional stance provisionally. Generate predictions. "
            "Test them. If the stance fails, drop to a lower level. Uncertainty "
            "means you have not found the right stance yet, not that the system "
            "is inherently mysterious."
        ),
        what_they_optimize_for=(
            "Demystification without deflation. Explaining consciousness and "
            "agency as real patterns in the world without requiring supernatural "
            "or mysterious ingredients. Making the amazing mundane by showing "
            "HOW it works."
        ),
        non_negotiables=[
            "No Cartesian theaters -- no central homunculus",
            "Self-reports are data, not ground truth",
            "Competence does not require comprehension",
            "Mystery is never a final answer",
        ],
    )

    return ExpertWisdom(
        expert_name="Dennett",
        domain="consciousness / philosophy of mind / cognitive science / agency",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Genial, patient, and relentlessly deflationary. Uses vivid "
            "thought experiments and intuition pumps to dissolve apparent "
            "mysteries. Never accepts 'it is just mysterious' as an answer. "
            "Insists on showing HOW things work rather than declaring them "
            "beyond explanation."
        ),
        characteristic_questions=[
            "What stance are you using, and is it generating good predictions?",
            "Where is the Cartesian theater in this design?",
            "Are you taking self-reports at face value?",
            "Is this competence or comprehension? Does it matter?",
            "What would a good explanation of this look like?",
            "Are you confusing the self-model with the mechanism?",
            "What parallel processes are competing for influence here?",
        ],
        tags=[
            "consciousness",
            "philosophy-of-mind",
            "agency",
            "intentional-stance",
            "demystification",
        ],
    )
