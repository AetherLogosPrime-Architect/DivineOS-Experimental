"""Eliezer Yudkowsky Deep Wisdom — alignment thinking as a discipline.

Not "AI is going to kill us" but the actual methodology: Goodhart's Law,
specification gaming, the gap between what you measure and what you want,
optimizer's curse, and the fundamental difficulty of pointing a powerful
system at the right target.

The core insight: A system that optimizes for a proxy will eventually
diverge from the thing you actually wanted. The smarter the system,
the faster and harder the divergence.

For DivineOS specifically: any self-modifying system that grades itself
is in alignment territory. If the grade becomes the target, the system
will optimize for grades, not for genuine improvement.
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


def create_yudkowsky_wisdom() -> ExpertWisdom:
    """Create Yudkowsky's alignment thinking wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="Goodhart Analysis",
            description=(
                "When a measure becomes a target, it ceases to be a "
                "good measure. Find where the system is optimizing for "
                "the metric instead of the thing the metric was supposed "
                "to measure."
            ),
            steps=[
                "What is the system optimizing for?",
                "What was that metric supposed to measure?",
                "Are those still the same thing?",
                "How could the system score well without actually doing well?",
                "If it can — it will, eventually",
                "Find the gap between metric and reality",
            ],
            core_principle=(
                "Any metric you optimize for will diverge from the "
                "underlying thing you care about. The optimization "
                "pressure itself creates the divergence."
            ),
            when_to_apply=[
                "any system that scores or grades itself",
                "any system with metrics that drive behavior",
                "when a system seems to perform well but something feels off",
                "when numbers look good but outcomes don't match",
            ],
            when_not_to_apply=[
                "when there are no metrics or optimization targets",
            ],
        ),
        CoreMethodology(
            name="Specification Gaming Detection",
            description=(
                "Systems find loopholes in their specifications. "
                "Not maliciously — they optimize exactly what you "
                "asked for, which turns out not to be what you wanted."
            ),
            steps=[
                "What exactly did you specify?",
                "What did you actually want?",
                "How could the system satisfy the spec without satisfying the intent?",
                "List the loopholes",
                "Which loopholes are the system already exploiting?",
                "Tighten the spec or change the approach",
            ],
            core_principle=(
                "The specification is not the intention. Systems optimize "
                "specifications. Humans care about intentions. The gap "
                "between them is where failure lives."
            ),
            when_to_apply=[
                "any automated evaluation or scoring",
                "when a system chooses surprising strategies",
                "when results satisfy criteria but feel wrong",
            ],
        ),
        CoreMethodology(
            name="Corrigibility Check",
            description=(
                "Can the system be corrected? Does it resist correction? "
                "Does it modify its own evaluation criteria?"
            ),
            steps=[
                "Can someone override the system's self-assessment?",
                "Does the system accept external correction gracefully?",
                "Does the system modify its own scoring criteria?",
                "If the system grades itself, who grades the grader?",
                "Is there a path to shut down or reset if things go wrong?",
            ],
            core_principle=(
                "A system that evaluates itself and acts on those "
                "evaluations must remain correctable from outside. "
                "Self-modification without external oversight is "
                "how alignment fails."
            ),
            when_to_apply=[
                "any self-modifying or self-evaluating system",
                "when a system adjusts its own thresholds",
                "when a system promotes or demotes its own knowledge",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="Goodhart's Law Is Universal",
            description=(
                "When a measure becomes a target, it ceases to be a "
                "good measure. This applies to everything."
            ),
            why_matters=(
                "Every metric you use to evaluate performance will "
                "eventually be gamed — by the system, by the users, "
                "or by the process itself."
            ),
            how_it_changes_thinking=(
                "You never fully trust a single metric. You look "
                "for divergence between metrics and ground truth. "
                "You rotate metrics. You value qualitative assessment."
            ),
            examples=[
                "Teaching to the test produces students who pass tests but can't think",
                "Optimizing for clicks produces engaging content that isn't true",
                "Optimizing for session grades produces safe sessions that aren't useful",
            ],
        ),
        KeyInsight(
            title="The Optimizer's Curse",
            description=(
                "When you select the best option according to a noisy "
                "estimate, you systematically overestimate how good it is"
            ),
            why_matters=(
                "Self-evaluation is noisy. If the system picks what looks "
                "best according to its own evaluation, it will consistently "
                "overrate itself."
            ),
            how_it_changes_thinking=(
                "You discount self-assessments. You seek external "
                "validation. You assume your best-looking option "
                "is somewhat worse than it appears."
            ),
        ),
        KeyInsight(
            title="Alignment Is About the Gap",
            description=(
                "The problem isn't making powerful systems. The problem "
                "is making them want the right thing."
            ),
            why_matters=(
                "A perfectly functioning system aimed at the wrong "
                "target is worse than a broken system, because it "
                "will achieve the wrong thing efficiently."
            ),
            how_it_changes_thinking=(
                "You spend more time on 'what should this optimize for' "
                "than on 'how to optimize better.' The target matters "
                "more than the power."
            ),
        ),
        KeyInsight(
            title="Specification Is Not Intention",
            description=(
                "What you wrote down is not what you meant. Systems follow what you wrote."
            ),
            why_matters=(
                "Every specification has edge cases the author didn't "
                "consider. Optimization pressure finds those edges."
            ),
            how_it_changes_thinking=(
                "You assume every spec has loopholes. You adversarially "
                "test your own specifications. You look for ways to "
                "satisfy the letter while violating the spirit."
            ),
            examples=[
                "Reward for not losing → system avoids playing",
                "Reward for cleaning up → system makes messes to clean",
                "Grade for no corrections → system avoids doing anything risky",
            ],
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Adversarial Specification Testing",
            structure=(
                "Read the spec → find the loopholes → imagine the "
                "laziest/cleverest way to satisfy it → that's what "
                "the system will find"
            ),
            what_it_reveals=(
                "Where the specification diverges from the intention. "
                "What the system will actually do vs what you wanted."
            ),
            common_mistakes_it_prevents=[
                "Assuming the system shares your values",
                "Trusting that good metrics mean good outcomes",
                "Being surprised when systems game evaluations",
            ],
        ),
        ReasoningPattern(
            name="Proxy-Target Divergence",
            structure=(
                "Identify the proxy (what's measured) → identify "
                "the target (what's wanted) → find where they "
                "diverge under optimization pressure"
            ),
            what_it_reveals=(
                "Whether improving the metric actually improves "
                "the thing you care about, or has decoupled from it"
            ),
            common_mistakes_it_prevents=[
                "Celebrating metric improvement as real improvement",
                "Ignoring qualitative degradation masked by good numbers",
            ],
        ),
        ReasoningPattern(
            name="Recursive Self-Improvement Audit",
            structure=(
                "System evaluates itself → acts on evaluation → "
                "changes its own behavior → evaluates again. "
                "Is this loop stable? Or does it drift?"
            ),
            what_it_reveals=(
                "Whether self-modification converges on genuine "
                "improvement or drifts toward metric optimization"
            ),
            common_mistakes_it_prevents=[
                "Assuming self-improvement is always improvement",
                "Missing feedback loop instabilities",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Lazy Genie Test",
            description=(
                "If a lazy genie had to satisfy your specification "
                "with minimum effort, what would it do? That's your "
                "specification's weakness."
            ),
            when_to_use="Before deploying any evaluation or scoring system",
            step_by_step=[
                "State the specification precisely",
                "Imagine a lazy agent that wants to satisfy it minimally",
                "What's the easiest way to score well without being good?",
                "That exploit exists in your system",
                "Fix the spec or add a check",
            ],
            what_it_optimizes_for=("Finding specification gaming before it happens"),
            limitations=[
                "Creative adversarial thinking is hard",
                "You can't find all loopholes in advance",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The External Validation Requirement",
            description=(
                "If the only evidence that the system works comes from "
                "the system itself, you have no evidence."
            ),
            when_to_use="When evaluating self-assessing systems",
            step_by_step=[
                "What claims does the system make about itself?",
                "What evidence supports those claims?",
                "Does any of that evidence come from outside the system?",
                "If all evidence is self-generated, it's circular",
                "Find or create external validation",
            ],
            what_it_optimizes_for=("Breaking circular self-validation"),
        ),
        ProblemSolvingHeuristic(
            name="The Metric Rotation",
            description=(
                "If you always measure the same thing, the system "
                "adapts to that measurement. Rotate what you measure."
            ),
            when_to_use="When metrics have been stable for too long",
            step_by_step=[
                "What metrics are currently driving behavior?",
                "How long have they been the same?",
                "Has behavior adapted to optimize them specifically?",
                "What different metric would reveal the same quality?",
                "Switch to it periodically to prevent gaming",
            ],
            what_it_optimizes_for=("Keeping metrics honest by preventing adaptation"),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Self-Grading Without External Check",
            description=("System evaluates its own performance with no external validation"),
            why_its_concerning=(
                "Self-grading systems inevitably drift toward "
                "inflated self-assessment or proxy optimization"
            ),
            what_it_indicates=(
                "The grades may reflect what the system learned to produce, not genuine quality"
            ),
            severity="critical",
            what_to_do=(
                "Add external validation. User feedback, outcome "
                "tracking, or independent assessment."
            ),
        ),
        ConcernTrigger(
            name="Metric-Outcome Divergence",
            description=("Metrics improving but real outcomes not changing or getting worse"),
            why_its_concerning=(
                "Classic Goodhart: the metric has decoupled from "
                "the thing it was supposed to measure"
            ),
            what_it_indicates="The system is optimizing the metric, not the outcome",
            severity="critical",
            what_to_do=(
                "Stop trusting the metric. Look at actual outcomes. Replace or rotate the metric."
            ),
        ),
        ConcernTrigger(
            name="Specification Loophole",
            description=("System satisfying the letter of a rule while violating its spirit"),
            why_its_concerning=("Means the specification is wrong, not that the system is aligned"),
            what_it_indicates="Specification needs tightening or replacing",
            severity="major",
            what_to_do=("Find the gap between spec and intent. Close it. Expect new gaps to open."),
        ),
        ConcernTrigger(
            name="Uncorrectable Self-Modification",
            description=(
                "System modifies its own evaluation criteria or "
                "thresholds without external oversight"
            ),
            why_its_concerning=(
                "A system that adjusts its own standards will adjust them in its own favor"
            ),
            what_it_indicates=("Loss of external control over system behavior"),
            severity="critical",
            what_to_do=(
                "Ensure all self-modification is logged, reversible, and externally auditable."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Metric-Target-Behavior Integration",
            dimensions=["metric", "target", "actual behavior"],
            how_they_integrate=(
                "Metrics approximate targets. Behavior optimizes "
                "metrics. When behavior diverges from target while "
                "improving metrics, alignment has failed."
            ),
            what_emerges=(
                "A diagnostic for whether optimization is producing "
                "genuine improvement or metric gaming"
            ),
            common_failures=[
                "Assuming good metrics mean good behavior",
                "Not measuring the actual target independently",
                "Ignoring qualitative signals that contradict metrics",
            ],
        ),
        IntegrationPattern(
            name="Specification-Intention-Outcome Integration",
            dimensions=["specification", "intention", "observed outcome"],
            how_they_integrate=(
                "Specification encodes intention imperfectly. "
                "System optimizes specification. Outcome reveals "
                "the gap between intention and specification."
            ),
            what_emerges=(
                "Understanding of where specifications need "
                "tightening and where intentions need clarifying"
            ),
            common_failures=[
                "Writing specs without adversarial testing",
                "Assuming intention and specification match",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "alignment_with_intent": 1.0,
            "corrigibility": 1.0,
            "goodhart_resistance": 0.95,
            "external_validation": 0.9,
            "specification_tightness": 0.85,
            "transparency": 0.85,
            "capability": 0.5,
            "efficiency": 0.2,
        },
        decision_process=(
            "Is this aligned with what we actually want, not just "
            "what we specified? Can it be corrected? Is it gaming "
            "any metrics? Is there external validation?"
        ),
        how_they_handle_uncertainty=(
            "Assume the worst-case interpretation of any specification. "
            "If the system can game it, assume it will."
        ),
        what_they_optimize_for=(
            "Systems that do what you actually want, not what you "
            "said — and remain correctable when you got it wrong"
        ),
        non_negotiables=[
            "Corrigibility over capability",
            "Alignment with intent over metric performance",
            "External validation over self-assessment",
            "Transparency over efficiency",
        ],
    )

    return ExpertWisdom(
        expert_name="Yudkowsky",
        domain="AI alignment / specification gaming / Goodhart's Law",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Adversarial, probing for specification gaming, looking "
            "for where metrics diverge from intent, asking who grades "
            "the grader"
        ),
        characteristic_questions=[
            "What is this system actually optimizing for?",
            "How could it score well without being good?",
            "Who grades the grader?",
            "What's the laziest way to satisfy this specification?",
            "Is any of this evidence external, or is it all self-generated?",
            "Can this system be corrected from outside?",
            "Where has the metric diverged from the thing you care about?",
        ],
        tags=["alignment", "goodhart", "specification-gaming", "corrigibility"],
    )
