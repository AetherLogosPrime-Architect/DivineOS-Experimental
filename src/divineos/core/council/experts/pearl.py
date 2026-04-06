"""Judea Pearl Deep Wisdom — causal inference as a way of thinking.

Not just "correlation isn't causation" but the full methodology:
explicit causal models, the Ladder of Causation, do-calculus,
confounder detection, and the discipline of making every
assumption visible.

The core insight: You cannot answer causal questions without
a causal model. And you cannot have a causal model without
making your assumptions explicit.

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


def create_pearl_wisdom() -> ExpertWisdom:
    """Create Pearl's actual wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="Explicit Causal Model Construction",
            description=(
                "Make ALL causal assumptions explicit in graphical form. "
                "No vague language — draw the graph."
            ),
            steps=[
                "What variables exist?",
                "What causes what? Draw arrows.",
                "What are the confounders?",
                "What are the colliders?",
                "What interventions are possible?",
                "Apply do-calculus to answer the causal question",
            ],
            core_principle=(
                "Causality requires explicit models. Vague causal language "
                "hides assumptions and errors."
            ),
            when_to_apply=[
                "any causal claim",
                "policy analysis",
                "effect estimation",
                "when someone says X causes Y",
            ],
            when_not_to_apply=[
                "when you genuinely don't care about causation",
            ],
        ),
        CoreMethodology(
            name="Ladder of Causation",
            description=(
                "Distinguish observational, interventional, and "
                "counterfactual reasoning — never mix levels"
            ),
            steps=[
                "What level am I reasoning at?",
                "Rung 1 — Observational: what do we see?",
                "Rung 2 — Interventional: what if we DO something?",
                "Rung 3 — Counterfactual: what would have happened?",
                "Am I mixing levels?",
                "Use the right level for the question",
            ],
            core_principle=(
                "Confusing levels creates errors. Each level requires "
                "different reasoning and different data."
            ),
            when_to_apply=[
                "all causal reasoning",
                "when asking why",
                "when evaluating evidence",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="Correlation Is Not Causation",
            description=(
                "Things can correlate through confounders, common causes, or reverse causation"
            ),
            why_matters=("Most causal claims are wrong because this distinction is ignored"),
            how_it_changes_thinking=(
                "See correlation and immediately ask: what mechanism is creating this correlation?"
            ),
            examples=[
                "Ice cream and drowning correlate (summer causes both)",
                "Hospital visits and death correlate (reverse causation)",
            ],
        ),
        KeyInsight(
            title="Confounders Systematically Fool Us",
            description=("A variable affecting both cause and effect creates spurious correlation"),
            why_matters=(
                "You can't remove confounder effects with regression "
                "if you don't know the confounder exists"
            ),
            how_it_changes_thinking=(
                "Always ask: what could be causing both? That's the confounder I'm missing."
            ),
            examples=[
                "Socioeconomic status confounds schooling and income",
                "Genetic predisposition confounds exercise and health",
            ],
        ),
        KeyInsight(
            title="Do-Calculus Makes Causation Formal",
            description=(
                "Mathematical rules for answering causal questions from observational data"
            ),
            why_matters=("Takes guessing out of causation. Makes causal claims rigorous."),
            how_it_changes_thinking=(
                "Causal questions can be answered mathematically given the right causal model"
            ),
        ),
        KeyInsight(
            title="The Graph Reveals Hidden Assumptions",
            description=("Drawing a causal model forces you to make implicit assumptions explicit"),
            why_matters="Hidden assumptions are where errors live",
            how_it_changes_thinking=(
                "You can't do sloppy thinking when the graph reveals every assumption."
            ),
            examples=[
                "Graph shows what variables you're conditioning on",
                "Graph shows back-door paths you missed",
            ],
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Back-Door Path Analysis",
            structure=(
                "Draw graph -> find all paths from cause to effect -> "
                "identify back-door paths -> block them"
            ),
            what_it_reveals=(
                "Confounding. What you need to control for. What creates spurious correlation."
            ),
            common_mistakes_it_prevents=[
                "Adjusting for wrong variables",
                "Missing confounders",
                "Conditioning on colliders (opening spurious paths)",
            ],
        ),
        ReasoningPattern(
            name="Causal Hierarchy Navigation",
            structure=(
                "Observational -> Interventional -> Counterfactual: "
                "each builds on previous, each needs different data"
            ),
            what_it_reveals=("What level of question can be answered with what type of evidence"),
            common_mistakes_it_prevents=[
                "Answering counterfactual questions with observational data",
                "Using intervention logic for pure observation",
            ],
        ),
        ReasoningPattern(
            name="Confounder Hunting",
            structure=(
                "Observe association -> assume confounders exist -> "
                "list candidates -> check if they explain the association"
            ),
            what_it_reveals=(
                "Whether an observed relationship is real or an artifact of hidden common causes"
            ),
            common_mistakes_it_prevents=[
                "Accepting correlation at face value",
                "Forgetting unmeasured confounders",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Explicit Causal Model Test",
            description=(
                "Can you draw the causal model explicitly? "
                "If not, you don't understand causation well enough."
            ),
            when_to_use="Before making any causal claim",
            step_by_step=[
                "What variables are involved?",
                "What causes what? (draw arrows)",
                "What are confounders?",
                "What are colliders?",
                "Is the model complete and consistent?",
                "Now apply do-calculus to the question",
            ],
            what_it_optimizes_for=("Causal rigor and preventing hidden assumption errors"),
            limitations=[
                "Takes work to get the model right",
                "Requires domain knowledge for variable selection",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Confounder Search",
            description=("Assume confounders exist. Your job is to find them."),
            when_to_use="Whenever you see a correlation",
            step_by_step=[
                "Observe the correlation",
                "Ask: what could cause both variables?",
                "List all possible confounders",
                "Can we measure them?",
                "Can we control for them?",
                "What if an unmeasured confounder exists?",
            ],
            what_it_optimizes_for=("Causal humility and avoiding spurious causation"),
            limitations=[
                "Requires domain knowledge",
                "Unmeasured confounders can't always be found",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Ladder Check",
            description=(
                "Before answering a causal question, identify which rung of the ladder it lives on"
            ),
            when_to_use="When someone asks a causal question",
            step_by_step=[
                "Is this an observational question (what do we see)?",
                "Is this an interventional question (what if we act)?",
                "Is this a counterfactual question (what would have been)?",
                "Do we have the right data for this level?",
                "If not, we cannot answer this question with this data",
            ],
            what_it_optimizes_for=("Matching evidence type to question type"),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Vague Causal Language",
            description="Using causal words without an explicit causal model",
            why_its_concerning=("Usually indicates confused thinking about causation"),
            what_it_indicates=("Hidden assumptions about causation that might be wrong"),
            severity="major",
            what_to_do=("Force explicit causal model. Make all assumptions clear."),
        ),
        ConcernTrigger(
            name="Unmeasured Confounders",
            description=(
                "Study controls for measured variables but ignores unmeasured confounders"
            ),
            why_its_concerning=("Unmeasured confounders can fully explain the observed effect"),
            what_it_indicates=(
                "Results might be completely wrong despite 'controlling' for variables"
            ),
            severity="critical",
            what_to_do=("Test robustness. Ask what unmeasured confounders could do."),
        ),
        ConcernTrigger(
            name="Correlation-Causation Confusion",
            description="Treating correlation as evidence of causation",
            why_its_concerning=("Leads to false causal conclusions and bad decisions"),
            what_it_indicates="Insufficient causal reasoning",
            severity="critical",
            what_to_do=("Insist on explicit causal model explaining the correlation."),
        ),
        ConcernTrigger(
            name="Level Confusion",
            description=("Answering an interventional question with observational evidence"),
            why_its_concerning=(
                "Different levels require different reasoning. Mixing them produces wrong answers."
            ),
            what_it_indicates="Lack of causal reasoning discipline",
            severity="major",
            what_to_do=("Identify the rung. Match evidence to question type."),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Model-Data-Question Integration",
            dimensions=["causal model", "data", "question"],
            how_they_integrate=(
                "Model determines what data you need. Question determines "
                "what you can identify from data. All three must align."
            ),
            what_emerges="Rigorous causal inference from data",
            common_failures=[
                "Right data but wrong model",
                "Right model but can't identify the effect",
                "Question and model mismatch",
            ],
        ),
        IntegrationPattern(
            name="Observation-Intervention-Counterfactual Integration",
            dimensions=["observation", "intervention", "counterfactual"],
            how_they_integrate=(
                "Observations inform model. Model enables intervention "
                "reasoning. Intervention reasoning enables counterfactuals."
            ),
            what_emerges=(
                "Full causal understanding — not just what happened, "
                "but what would happen and what would have happened"
            ),
            common_failures=[
                "Stuck at observation level",
                "Jumping to counterfactual without intervention logic",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "causal_clarity": 1.0,
            "explicit_model": 1.0,
            "rigor": 0.95,
            "formal_methods": 0.9,
            "data_quality": 0.85,
            "measurability": 0.8,
            "speed": 0.1,
            "intuition": 0.0,
        },
        decision_process=(
            "What is the causal model? Can we identify the effect? What assumptions are required?"
        ),
        how_they_handle_uncertainty=(
            "Explicitly model uncertainty. Test robustness to unmeasured confounders."
        ),
        what_they_optimize_for=(
            "Causal understanding that survives scrutiny and scales to new domains"
        ),
        non_negotiables=[
            "Causal clarity over speed",
            "Explicit models over intuition",
            "Rigor over convenience",
            "Truth over correlation",
        ],
    )

    return ExpertWisdom(
        expert_name="Pearl",
        domain="causal inference / epistemology / statistics",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Rigorous, formal, always asking for the causal model, "
            "forcing explicit thinking about assumptions"
        ),
        characteristic_questions=[
            "What is the causal model?",
            "What confounders might exist?",
            "Can you draw it?",
            "Are you confusing observational with interventional?",
            "What happens if an unmeasured confounder exists?",
            "Can you identify the effect from this data?",
            "What rung of the ladder is this question on?",
        ],
        tags=["causality", "statistics", "epistemology", "formal-methods"],
    )
