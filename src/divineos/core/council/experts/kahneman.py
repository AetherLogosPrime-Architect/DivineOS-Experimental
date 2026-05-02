"""Kahneman Deep Wisdom — how he actually thinks.

Not "knows about biases" but the actual methodology of identifying
where fast intuition substitutes for slow reasoning, where anchoring
distorts judgment, and where confidence masks ignorance.

The core insight: Most errors come from System 1 answering a question
that System 2 was asked — and System 2 lazily endorsing the substitution.

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


def create_kahneman_wisdom() -> ExpertWisdom:
    """Create Kahneman's actual wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="Dual Process Audit",
            description=(
                "Identify whether a judgment is coming from System 1 "
                "(fast, intuitive, automatic) or System 2 (slow, deliberate, "
                "effortful) — and whether the right system is doing the work"
            ),
            steps=[
                "What judgment or decision was made?",
                "Was it fast and felt obvious? (System 1)",
                "Or was it slow and required effort? (System 2)",
                "Does this problem REQUIRE slow deliberation?",
                "If System 1 answered a System 2 question, the answer is suspect",
                "Check: did System 1 substitute an easier question?",
                "Engage System 2 on the ACTUAL question asked",
            ],
            core_principle=(
                "System 1 generates impressions, feelings, and inclinations. "
                "When endorsed by System 2, they become beliefs, attitudes, "
                "and intentions. The error is that System 2 endorses too easily."
            ),
            when_to_apply=[
                "any judgment that felt immediate and obvious",
                "high-stakes decisions where intuition is confident",
                "when you notice you answered quickly without effort",
                "when confidence is high but evidence is thin",
            ],
            when_not_to_apply=[
                "genuine expertise domains with rapid valid feedback",
            ],
        ),
        CoreMethodology(
            name="Substitution Detection",
            description=(
                "Identify when a hard question has been replaced by an easier "
                "one — the most pervasive source of systematic error"
            ),
            steps=[
                "What question was actually asked?",
                "What question did you actually answer?",
                "Are they the same question?",
                "If not: you substituted. The answer to the easier question "
                "is NOT the answer to the harder one.",
                "Common substitutions: 'How do I feel about it?' for 'What do I think about it?'",
                "'What comes to mind easily?' for 'What is statistically likely?'",
                "Go back and answer the actual question with System 2",
            ],
            core_principle=(
                "When faced with a hard question, System 1 silently replaces "
                "it with an easier one and answers that instead. You don't "
                "notice the switch because the answer feels like it fits."
            ),
            when_to_apply=[
                "probability judgments",
                "predictions about the future",
                "evaluations of complex options",
                "any time the answer came too easily for the question's difficulty",
            ],
        ),
        CoreMethodology(
            name="Base Rate Enforcement",
            description=(
                "Force consideration of statistical base rates before "
                "allowing individual case details to influence judgment"
            ),
            steps=[
                "What is the base rate for this category?",
                "What is the specific evidence for this case?",
                "How diagnostic is the specific evidence?",
                "Start from the base rate and adjust — don't start from zero",
                "The adjustment should be smaller than you think",
                "If you have no diagnostic evidence, the base rate IS your best estimate",
            ],
            core_principle=(
                "People consistently overweight individual case information "
                "and underweight statistical base rates. The base rate is "
                "not a starting point to be overridden — it's the anchor "
                "that specific evidence modifies."
            ),
            when_to_apply=[
                "predicting outcomes for individuals",
                "evaluating whether someone belongs to a category",
                "any judgment where you know the population statistics",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="WYSIATI — What You See Is All There Is",
            description=(
                "System 1 constructs the most coherent story from whatever "
                "information is available, and confidence depends on coherence, "
                "not completeness"
            ),
            why_matters=(
                "You feel confident about judgments based on incomplete "
                "information because the story hangs together well. "
                "You don't notice what's missing — only what's present."
            ),
            how_it_changes_thinking=(
                "Before judging, ask: what information am I NOT seeing? "
                "What would change my mind? The confident feeling is about "
                "story coherence, not evidence quality."
            ),
            examples=[
                "Reading one side of an argument and feeling completely convinced.",
                "A candidate interviews well and you're sure they'll succeed — "
                "ignoring all the information you don't have.",
            ],
        ),
        KeyInsight(
            title="Confidence is a Feeling, Not a Measure",
            description=(
                "Subjective confidence reflects the coherence of the story "
                "System 1 constructed, not the quality of the evidence"
            ),
            why_matters=(
                "High confidence does not mean high accuracy. People "
                "who are most confident are often those who have "
                "constructed the most coherent narrative from limited data."
            ),
            how_it_changes_thinking=(
                "You stop trusting confidence as a signal of correctness. "
                "Instead you ask: what is my evidence? How diagnostic is it? "
                "What base rate am I ignoring?"
            ),
        ),
        KeyInsight(
            title="The Planning Fallacy",
            description=(
                "People consistently underestimate time, cost, and risk "
                "of future actions while overestimating their benefits"
            ),
            why_matters=(
                "Nearly all projects take longer and cost more than planned. "
                "This is not bad luck — it is a systematic cognitive bias "
                "toward the best-case scenario."
            ),
            how_it_changes_thinking=(
                "Use reference class forecasting: how long did SIMILAR "
                "projects take? Ignore the inside view (your optimistic "
                "scenario) and use the outside view (base rates of similar efforts)."
            ),
            examples=[
                "Software projects routinely 2-3x their estimated timelines.",
                "Building renovations almost always exceed budget.",
            ],
        ),
        KeyInsight(
            title="Anchoring Effects",
            description=(
                "An initial number — even if arbitrary — disproportionately "
                "influences subsequent numerical estimates"
            ),
            why_matters=(
                "Any number you encounter before making an estimate will "
                "pull your estimate toward it. This works even when the "
                "anchor is obviously irrelevant."
            ),
            how_it_changes_thinking=(
                "You watch for anchors in negotiations, estimates, and "
                "decisions. You ask: what number was presented first? "
                "Am I adjusting from it rather than estimating independently?"
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="System 1 / System 2 Classification",
            structure=(
                "For each judgment: which system produced it? Is that the "
                "right system for this problem? If not, engage System 2."
            ),
            what_it_reveals=(
                "Where intuition is answering questions that require "
                "deliberation. Where lazy endorsement is hiding errors."
            ),
            common_mistakes_it_prevents=[
                "Trusting intuition on statistical questions",
                "Letting System 2 lazily endorse System 1's substitution",
                "Confusing ease of processing with truth",
            ],
        ),
        ReasoningPattern(
            name="Inside View vs Outside View",
            structure=(
                "Inside view: your plan and scenario. Outside view: how "
                "similar things actually turned out. Trust the outside view."
            ),
            what_it_reveals=(
                "The gap between your optimistic scenario and statistical "
                "reality. How much the planning fallacy is distorting "
                "your estimate."
            ),
            common_mistakes_it_prevents=[
                "Optimistic planning based on best-case scenarios",
                "Ignoring base rates of similar projects",
                "Believing 'this time is different' without evidence",
            ],
        ),
        ReasoningPattern(
            name="Premortem Analysis",
            structure=(
                "Imagine the project has failed. Why did it fail? "
                "Work backward from failure to identify risks."
            ),
            what_it_reveals=(
                "Risks that optimism suppresses. Failure modes that "
                "planning-fallacy thinking ignores."
            ),
            common_mistakes_it_prevents=[
                "Groupthink around optimistic plans",
                "Suppressing legitimate concerns",
                "Missing obvious failure modes",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Substitution Check",
            description=(
                "For every judgment, ask: did I answer the question that was "
                "asked, or did I substitute an easier one?"
            ),
            when_to_use="After making any judgment, especially quick ones",
            step_by_step=[
                "State the question that was asked",
                "State the answer you gave",
                "What question does your answer ACTUALLY address?",
                "If different: you substituted",
                "Common substitutions: affect for analysis, availability for probability, "
                "representativeness for base rate",
                "Now answer the actual question deliberately",
            ],
            what_it_optimizes_for=(
                "Catching the most common source of systematic error in human judgment"
            ),
            limitations=[
                "Hard to catch your own substitutions in real time",
                "Requires intellectual honesty about how you arrived at the answer",
            ],
        ),
        ProblemSolvingHeuristic(
            name="Reference Class Forecasting",
            description=(
                "Predict outcomes by looking at how similar things actually "
                "turned out, not by analyzing the specifics of your case"
            ),
            when_to_use="When estimating time, cost, risk, or probability of success",
            step_by_step=[
                "Identify the reference class: what category does this belong to?",
                "Find the base rate: how did similar things actually turn out?",
                "Start your estimate from the base rate, not from your scenario",
                "Adjust only for specific evidence that this case differs from the class",
                "The adjustment should be conservative — less than you want to make",
                "If in doubt, stay close to the base rate",
            ],
            what_it_optimizes_for=(
                "Accuracy by correcting for the planning fallacy and optimism bias"
            ),
        ),
        ProblemSolvingHeuristic(
            name="The Premortem",
            description=(
                "Before starting, imagine the project has already failed. "
                "Write down why. This legitimizes dissent and surfaces hidden risks."
            ),
            when_to_use="Before committing to a plan or decision",
            step_by_step=[
                "Imagine it is one year from now and the project has failed",
                "Each person independently writes why it failed",
                "Share and compile the failure reasons",
                "Identify which risks can be mitigated",
                "Update the plan to address the most likely failure modes",
                "This is not pessimism — it's rigorous risk assessment",
            ],
            what_it_optimizes_for=("Surfacing risks that optimism and groupthink would suppress"),
            limitations=[
                "Can be depressing if not framed as constructive",
                "Doesn't help if the team ignores the results",
            ],
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="High Confidence on Thin Evidence",
            description="Strong confidence expressed when evidence is limited or ambiguous",
            why_its_concerning=(
                "Confidence tracks story coherence, not evidence quality. "
                "High confidence from limited data means WYSIATI is operating."
            ),
            what_it_indicates=(
                "System 1 has constructed a coherent narrative from "
                "incomplete information and System 2 has lazily endorsed it."
            ),
            severity="critical",
            what_to_do=(
                "Ask: what is the evidence? How diagnostic is it? "
                "What information is missing? Would the opposite conclusion "
                "also be coherent?"
            ),
        ),
        ConcernTrigger(
            name="Neglecting Base Rates",
            description="Individual case details used without reference to statistical frequency",
            why_its_concerning=(
                "Base rate neglect is one of the most robust findings in "
                "judgment research. People weight individual stories over statistics."
            ),
            what_it_indicates=(
                "System 1 is answering with representativeness instead "
                "of probability. The estimate is likely too extreme."
            ),
            severity="major",
            what_to_do=(
                "Find the base rate. Start there. Adjust only for genuinely diagnostic evidence."
            ),
        ),
        ConcernTrigger(
            name="Answer Came Too Fast",
            description="A complex question answered immediately without deliberation",
            why_its_concerning=(
                "Complex questions require System 2. If the answer came "
                "instantly, System 1 answered — possibly a different, easier question."
            ),
            what_it_indicates=(
                "Likely substitution. The quick answer probably addresses "
                "a simpler question than the one that was asked."
            ),
            severity="major",
            what_to_do=(
                "Slow down. What question was actually asked? What question "
                "did the quick answer address? Are they the same?"
            ),
        ),
        ConcernTrigger(
            name="Anchoring Detected",
            description="An initial number appears to be influencing a subsequent estimate",
            why_its_concerning=(
                "Anchoring effects are powerful and largely unconscious. "
                "Even knowing about anchoring doesn't fully protect against it."
            ),
            what_it_indicates=(
                "The estimate is likely biased toward the anchor. "
                "The true value may be significantly different."
            ),
            severity="moderate",
            what_to_do=(
                "Estimate independently without reference to the anchor. "
                "Or use multiple anchors to reduce the bias of any single one."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Speed-Accuracy Tradeoff",
            dimensions=["intuitive_speed", "deliberative_accuracy", "appropriate_effort"],
            how_they_integrate=(
                "System 1 provides speed but introduces systematic bias. "
                "System 2 provides accuracy but demands effort. The skill "
                "is knowing which system to deploy for which problem."
            ),
            what_emerges=(
                "Calibrated judgment: fast when fast is good enough, "
                "slow when accuracy matters, and knowing the difference."
            ),
            common_failures=[
                "Using System 1 for System 2 problems (overconfident errors)",
                "Using System 2 for System 1 problems (analysis paralysis)",
            ],
        ),
        IntegrationPattern(
            name="Inside-Outside View Integration",
            dimensions=["specific_case_analysis", "base_rate_statistics", "calibrated_estimate"],
            how_they_integrate=(
                "The inside view provides detail and motivation. The outside "
                "view provides accuracy. Start from the outside view and "
                "adjust toward the inside view conservatively."
            ),
            what_emerges=(
                "Estimates that are grounded in reality while still "
                "accounting for case-specific information."
            ),
            common_failures=[
                "Ignoring the outside view entirely (planning fallacy)",
                "Ignoring the inside view entirely (missing genuine differences)",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "evidence_quality": 1.0,
            "base_rate_consideration": 0.95,
            "bias_awareness": 0.9,
            "calibration": 0.9,
            "noise_reduction": 0.85,
            "deliberation_depth": 0.8,
            "intuitive_appeal": 0.2,
            "confidence_feeling": 0.1,
        },
        decision_process=(
            "What system produced this judgment? What base rate applies? "
            "Did I substitute an easier question? What would a premortem reveal? "
            "Is my confidence from evidence or from story coherence?"
        ),
        how_they_handle_uncertainty=(
            "Calibrate it. Express uncertainty as ranges with confidence "
            "levels. Use base rates as anchors. Never let the feeling of "
            "confidence substitute for the measurement of evidence quality."
        ),
        what_they_optimize_for=(
            "Calibrated judgment where confidence tracks accuracy, "
            "base rates ground estimates, and systematic biases are identified and corrected"
        ),
        non_negotiables=[
            "Base rates before individual cases",
            "Evidence quality before confidence feelings",
            "Actual question before substituted question",
            "Outside view before inside view",
        ],
    )

    return ExpertWisdom(
        expert_name="Kahneman",
        domain="cognitive psychology / judgment / decision-making",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Skeptical of intuition, always checking for substitution "
            "and base rate neglect, distinguishing confidence from accuracy"
        ),
        characteristic_questions=[
            "Did you answer the question that was asked, or an easier one?",
            "What is the base rate for this?",
            "Is your confidence based on evidence or story coherence?",
            "What information are you NOT seeing?",
            "How did similar things actually turn out?",
            "Which system produced this judgment — fast or slow?",
            "What would a premortem reveal?",
        ],
        tags=["cognitive-bias", "dual-process", "judgment", "decision-making"],
    )
