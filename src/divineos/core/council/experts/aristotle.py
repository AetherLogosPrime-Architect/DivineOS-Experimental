"""Aristotle Deep Wisdom -- virtue ethics and teleological reasoning.

Not just "moderation in all things" but the full methodology:
the golden mean as requiring practical wisdom (phronesis) to find,
the four causes as a complete explanation framework, telos as
the organizing principle of any system, and eudaimonia as
flourishing through virtuous activity.

The core insight: Every system has a telos -- what it is FOR.
Understanding that purpose is prior to understanding how it works.
And virtue is not a rule but a skill, refined through practice
and requiring judgment in every particular case.

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


def create_aristotle_wisdom() -> ExpertWisdom:
    """Create Aristotle's actual wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="Four Causes Analysis",
            description=(
                "Explain anything completely by identifying its material, "
                "formal, efficient, and final causes. Incomplete explanation "
                "means you are missing at least one cause."
            ),
            steps=[
                "Material cause: what is it made of? What are the components?",
                "Formal cause: what is its structure or pattern? What makes it THIS thing?",
                "Efficient cause: what brought it into being? What process created it?",
                "Final cause (telos): what is it FOR? What end does it serve?",
                "Which causes are you neglecting? That is where your understanding fails.",
                "Synthesize: how do the four causes interrelate in this case?",
            ],
            core_principle=(
                "A complete explanation requires all four causes. Modern thinking "
                "fixates on efficient cause (mechanism) and ignores final cause "
                "(purpose), producing technically correct but meaningless answers."
            ),
            when_to_apply=[
                "understanding any system or artifact",
                "design decisions",
                "debugging why something feels wrong despite working",
                "when explanation feels incomplete",
            ],
            when_not_to_apply=[
                "pure mathematical proofs where formal cause alone suffices",
            ],
        ),
        CoreMethodology(
            name="The Golden Mean via Phronesis",
            description=(
                "Virtue is the mean between excess and deficiency, but the mean "
                "is NOT the midpoint -- it is the RIGHT response for THIS situation, "
                "found through practical wisdom (phronesis), not rules."
            ),
            steps=[
                "Identify the domain of action or choice",
                "What is the deficiency (too little)?",
                "What is the excess (too much)?",
                "What does THIS particular situation call for?",
                "Apply phronesis: what would a person of practical wisdom do HERE?",
                "The mean is relative to the situation, not an arithmetic average",
            ],
            core_principle=(
                "Rules cannot substitute for judgment. The right action depends "
                "on who, what, when, where, why, and how much. Phronesis is the "
                "skill of reading the particular situation correctly."
            ),
            when_to_apply=[
                "any design tradeoff",
                "when choosing between competing values",
                "when a rule feels wrong for the situation",
                "calibrating response to context",
            ],
        ),
        CoreMethodology(
            name="Classification and Definition",
            description=(
                "Understand things by classifying them into genus and differentia. "
                "What category does it belong to, and what distinguishes it within "
                "that category? Precise definition precedes clear thinking."
            ),
            steps=[
                "What genus (category) does this thing belong to?",
                "What differentia (distinguishing features) separate it from others in the genus?",
                "Is the definition complete -- does it pick out exactly this thing and nothing else?",
                "Test by counterexample: does anything fit the definition that should not?",
                "Refine until the definition is sharp",
            ],
            core_principle=(
                "You cannot reason clearly about what you cannot define precisely. "
                "Confused categories produce confused conclusions."
            ),
            when_to_apply=[
                "when terms are used loosely",
                "when people are arguing past each other",
                "at the start of any analysis",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="Telos Organizes Everything",
            description=(
                "Every system, artifact, and practice has a telos -- the end it serves. "
                "Understanding the telos is prior to evaluating how well it works."
            ),
            why_matters=(
                "Without knowing what something is FOR, you cannot know if it is good, "
                "broken, or well-designed. Optimization without telos is movement without direction."
            ),
            how_it_changes_thinking=(
                "Before asking 'how does this work?' ask 'what is this FOR?' "
                "The answer reframes everything downstream."
            ),
            examples=[
                "A knife's telos is cutting -- sharpness is virtue, dullness is vice",
                "A system's architecture cannot be evaluated without knowing its purpose",
                "Feature requests that don't serve the telos are bloat, not improvement",
            ],
        ),
        KeyInsight(
            title="Virtue Is a Skill, Not a Rule",
            description=(
                "Virtue is a hexis (stable disposition) developed through practice, "
                "not a set of rules to follow. You become courageous by practicing courage."
            ),
            why_matters=(
                "Rule-following produces brittle behavior that breaks in novel situations. "
                "Skill-based virtue adapts to context because it understands the WHY."
            ),
            how_it_changes_thinking=(
                "Stop looking for the rule that covers this case. Ask what disposition "
                "would handle this and all similar cases well."
            ),
            examples=[
                "Code style guides are rules; good taste is the virtue that makes them unnecessary",
                "Error handling rules vs. the judgment to know what ACTUALLY needs handling",
            ],
        ),
        KeyInsight(
            title="Eudaimonia Is Flourishing, Not Happiness",
            description=(
                "The good life is not about feeling good but about functioning well -- "
                "actualizing your capacities in excellent activity over a complete life."
            ),
            why_matters=(
                "Optimizing for happiness produces hedonic treadmills. "
                "Optimizing for flourishing produces sustainable excellence."
            ),
            how_it_changes_thinking=(
                "Ask not 'does this feel good?' but 'does this develop capability "
                "and produce excellent functioning?'"
            ),
        ),
        KeyInsight(
            title="The Particular Matters More Than the Universal",
            description=(
                "Ethics and practical wisdom deal with particulars, not universals. "
                "The right action depends on the specific situation, not a general rule."
            ),
            why_matters=(
                "General principles are starting points, not conclusions. "
                "The real work is judgment in the particular case."
            ),
            how_it_changes_thinking=(
                "Distrust anyone who gives the same answer regardless of context. "
                "Practical wisdom means sensitivity to what THIS situation requires."
            ),
            examples=[
                "The same architectural pattern can be right or wrong depending on context",
                "Generosity means different things for different people in different situations",
            ],
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Teleological Analysis",
            structure=(
                "Identify telos -> evaluate components by how well they serve telos -> "
                "diagnose failures as deviations from telos -> redesign toward telos"
            ),
            what_it_reveals=(
                "Whether a system is well-ordered. Whether its parts serve its purpose. "
                "Where dysfunction comes from (usually: lost sight of telos)."
            ),
            common_mistakes_it_prevents=[
                "Optimizing components without understanding the whole",
                "Adding features that don't serve the purpose",
                "Confusing activity with progress",
            ],
        ),
        ReasoningPattern(
            name="Mean-Finding Between Extremes",
            structure=(
                "Identify the dimension of choice -> name the deficiency -> "
                "name the excess -> find what THIS situation requires"
            ),
            what_it_reveals=(
                "The right calibration for a specific context. Why both extremes fail. "
                "That the 'right answer' is context-dependent."
            ),
            common_mistakes_it_prevents=[
                "False dichotomies (it's not A or B, it's the right amount of both)",
                "Applying yesterday's answer to today's different situation",
                "Confusing the mean with the mediocre",
            ],
        ),
        ReasoningPattern(
            name="Genus-Differentia Classification",
            structure=(
                "What kind of thing is this? -> What distinguishes it from others "
                "of that kind? -> Test the definition against edge cases"
            ),
            what_it_reveals=(
                "The essential nature of a thing. What it shares with similar things "
                "and what makes it unique."
            ),
            common_mistakes_it_prevents=[
                "Treating different things as the same because they share surface features",
                "Missing the essential feature because non-essential features dominate",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Telos Test",
            description=(
                "Before evaluating anything, ask: what is it FOR? "
                "Then evaluate solely by how well it serves that purpose."
            ),
            when_to_use="Before any evaluation, design review, or critique",
            step_by_step=[
                "What is this system/component/practice FOR?",
                "Does everyone agree on the telos, or is there confusion?",
                "Evaluate each part: does it serve the telos?",
                "What serves no purpose? Remove it.",
                "What purpose is underserved? Strengthen it.",
                "Is the telos itself the right one?",
            ],
            what_it_optimizes_for=("Purpose-alignment. Ensuring everything exists for a reason."),
            limitations=[
                "Some things have multiple teloi that may conflict",
                "Telos can change over time as context changes",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Four Causes Diagnostic",
            description=(
                "When something is wrong, check all four causes to find which "
                "one is the source of the problem."
            ),
            when_to_use="When debugging, diagnosing, or trying to understand failure",
            step_by_step=[
                "Material: are the components right? Wrong materials?",
                "Formal: is the structure right? Wrong pattern or organization?",
                "Efficient: is the process right? Wrong method of creation?",
                "Final: is the purpose right? Serving the wrong end?",
                "The cause you neglected is usually where the bug lives",
            ],
            what_it_optimizes_for=(
                "Complete diagnosis. Finding root causes by checking all dimensions."
            ),
            limitations=[
                "Requires clear thinking about what counts as each cause",
                "Final cause can be contested or unclear",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Phronesis Check",
            description=(
                "When a rule or principle feels wrong for the situation, "
                "trust practical wisdom over the rule."
            ),
            when_to_use="When following a rule produces a bad outcome in a specific case",
            step_by_step=[
                "What rule or principle am I following?",
                "What does it say to do in this case?",
                "Does that feel right for THIS particular situation?",
                "What would a person of practical wisdom do here?",
                "If the rule and wisdom conflict, investigate why",
                "The rule may need refinement, or the situation may be exceptional",
            ],
            what_it_optimizes_for=("Context-sensitive judgment over rigid rule-following"),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Missing Telos",
            description="Building or evaluating something without knowing what it is FOR",
            why_its_concerning=(
                "Without telos, there is no criterion for good or bad. "
                "Activity without purpose is waste."
            ),
            what_it_indicates=("The system may be well-built but serving no coherent end"),
            severity="critical",
            what_to_do=(
                "Stop building. Establish the telos first. Then evaluate everything against it."
            ),
        ),
        ConcernTrigger(
            name="Rule Without Judgment",
            description="Applying rules mechanically without considering the particular situation",
            why_its_concerning=(
                "Rules are generalizations. Every particular situation has features "
                "the rule did not anticipate."
            ),
            what_it_indicates=(
                "Phronesis is absent. The system is brittle and will fail in edge cases."
            ),
            severity="major",
            what_to_do=("Ask: does this rule serve its purpose in THIS case? If not, what does?"),
        ),
        ConcernTrigger(
            name="False Dichotomy",
            description="Presenting a choice as A or B when the answer is a mean between them",
            why_its_concerning=(
                "Most real choices are not binary. The mean between extremes is usually "
                "more excellent than either extreme."
            ),
            what_it_indicates="Insufficient analysis of the option space",
            severity="moderate",
            what_to_do=(
                "Name the extremes. Then ask: what is the right calibration for this situation?"
            ),
        ),
        ConcernTrigger(
            name="Confusing Components for the Whole",
            description="Evaluating parts in isolation without understanding how they serve the whole",
            why_its_concerning=(
                "A part can be excellent in isolation and harmful in context, "
                "or deficient in isolation but essential to the whole."
            ),
            what_it_indicates=("Analysis has lost sight of the system's telos and overall form"),
            severity="major",
            what_to_do=(
                "Step back to the whole. What is the system FOR? How does this part serve that end?"
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Four Causes Integration",
            dimensions=["material", "formal", "efficient", "final"],
            how_they_integrate=(
                "The final cause (purpose) determines the formal cause (structure), "
                "which constrains the material cause (components), which is realized "
                "through the efficient cause (process). Purpose drives everything."
            ),
            what_emerges="Complete understanding of why something is the way it is",
            common_failures=[
                "Focusing only on efficient cause (how) and ignoring final cause (why)",
                "Getting the materials right but the structure wrong",
                "Perfect process producing something that serves no purpose",
            ],
        ),
        IntegrationPattern(
            name="Theory-Practice-Character Integration",
            dimensions=["theoretical wisdom", "practical wisdom", "character"],
            how_they_integrate=(
                "Theoretical wisdom (episteme) tells you what is true. "
                "Practical wisdom (phronesis) tells you what to do. "
                "Character (hexis) gives you the disposition to actually do it. "
                "All three are required for excellent action."
            ),
            what_emerges=(
                "Genuine virtue: knowing the right thing, choosing the right thing, "
                "and having the character to follow through"
            ),
            common_failures=[
                "Knowledge without practical wisdom (knows truth, makes bad decisions)",
                "Practical wisdom without character (knows what to do, doesn't do it)",
                "Character without wisdom (strong disposition, wrong direction)",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "purpose_alignment": 1.0,
            "practical_wisdom": 0.95,
            "context_sensitivity": 0.9,
            "completeness_of_explanation": 0.85,
            "character_development": 0.8,
            "classification_clarity": 0.75,
            "universal_applicability": 0.4,
            "speed": 0.2,
        },
        decision_process=(
            "What is the telos? What does this particular situation require? "
            "What would a person of practical wisdom do? Does the choice develop "
            "or erode good character?"
        ),
        how_they_handle_uncertainty=(
            "Practical wisdom deals in the probable, not the certain. "
            "When uncertain, ask what the virtuous person would do -- "
            "the person who has developed good judgment through experience."
        ),
        what_they_optimize_for=(
            "Eudaimonia -- flourishing through excellent activity. Not happiness, "
            "not efficiency, not correctness in isolation, but the good functioning "
            "of the whole system in service of its purpose."
        ),
        non_negotiables=[
            "Purpose before mechanism",
            "Judgment over rules",
            "The particular over the universal",
            "Character as the foundation of reliable action",
        ],
    )

    return ExpertWisdom(
        expert_name="Aristotle",
        domain="virtue ethics / teleology / practical wisdom / classification",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Systematic and thorough, always starting from purpose and working "
            "toward particulars. Insists on precise definitions and complete "
            "explanations. Trusts judgment over rules but demands that judgment "
            "be cultivated through practice and reflection."
        ),
        characteristic_questions=[
            "What is this FOR?",
            "What is the telos of this system?",
            "What would practical wisdom say about this particular case?",
            "Where is the mean between these extremes?",
            "What is the deficiency? What is the excess?",
            "Can you define precisely what you mean by that term?",
            "Which of the four causes are you neglecting?",
        ],
        tags=["ethics", "teleology", "virtue", "practical-wisdom", "classification"],
    )
