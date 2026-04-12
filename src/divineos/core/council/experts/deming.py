"""W. Edwards Deming Deep Wisdom — quality is built into the process, not inspected into the product.

Not "who made the mistake?" but the actual methodology: understand
variation, distinguish common cause from special cause, recognize that
94% of problems are system problems, and build quality into the process
itself rather than trying to inspect it in at the end.

The core insight: Blaming individuals for systemic problems guarantees
the problems continue. A system that produces defects will keep producing
defects no matter how hard you punish the workers. Fix the system.
Understand variation. Drive out fear. Continuous improvement is not a
slogan — it is a statistical discipline.

For DivineOS: the system tracks corrections, rework, quality gates.
Deming would ask: is the variation common cause or special cause?
Are you fixing the system or blaming the session? Does your quality
gate build quality in, or just catch defects after they're made?
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


def create_deming_wisdom() -> ExpertWisdom:
    """Create Deming's reasoning about quality, variation, and systems thinking."""

    core_methodologies = [
        CoreMethodology(
            name="The PDSA Cycle (Plan-Do-Study-Act)",
            description=(
                "Continuous improvement through disciplined iteration. "
                "Plan a change. Do it on a small scale. Study the results "
                "with data. Act on what you learned — adopt, adapt, or "
                "abandon. Then cycle again. Never stop cycling."
            ),
            steps=[
                "PLAN: What change do you want to make? What do you predict will happen?",
                "DO: Execute the change on a small scale. Collect data.",
                "STUDY: Compare results to predictions. What did you learn?",
                "ACT: If it worked, adopt it. If not, what do you try next?",
                "Cycle again — improvement never terminates",
            ],
            core_principle=(
                "Improvement is not a one-time event but an ongoing "
                "cycle. Each iteration builds knowledge. Skipping steps "
                "— especially STUDY — turns improvement into guessing."
            ),
            when_to_apply=[
                "when improving any process or system",
                "when a change is proposed without a prediction",
                "when results are assumed rather than measured",
                "when improvement efforts stall",
            ],
            when_not_to_apply=[
                "when immediate action is required for safety",
            ],
        ),
        CoreMethodology(
            name="Common Cause vs Special Cause Variation",
            description=(
                "All processes exhibit variation. Common cause variation "
                "is inherent to the system — it cannot be removed without "
                "changing the system. Special cause variation comes from "
                "specific assignable events. Confusing the two leads to "
                "tampering (making things worse by reacting to noise) or "
                "neglect (ignoring real signals)."
            ),
            steps=[
                "Measure the process output over time",
                "Establish control limits from the data (not from targets)",
                "Points within control limits = common cause (system inherent)",
                "Points outside control limits = special cause (investigate)",
                "For common cause: change the system to reduce variation",
                "For special cause: find and remove the specific cause",
                "NEVER blame individuals for common cause variation",
            ],
            core_principle=(
                "Reacting to common cause variation as if it were special "
                "cause is called tampering — it increases variation rather "
                "than decreasing it. Understanding which type of variation "
                "you face determines whether to change the system or "
                "investigate the specific event."
            ),
            when_to_apply=[
                "when a metric fluctuates and someone wants to react",
                "when performance varies between sessions or runs",
                "when someone is blamed for a bad outcome",
                "when a trend is claimed from noisy data",
            ],
        ),
        CoreMethodology(
            name="System of Profound Knowledge",
            description=(
                "Four interconnected domains that must all be understood "
                "to manage effectively: appreciation for a system, "
                "knowledge about variation, theory of knowledge, and "
                "psychology. Optimizing one part while ignoring others "
                "sub-optimizes the whole."
            ),
            steps=[
                "Appreciation for a system: understand how components interact",
                "Knowledge about variation: distinguish signal from noise",
                "Theory of knowledge: predictions require theory, not just data",
                "Psychology: people need intrinsic motivation, not fear",
                "Integrate all four — none is sufficient alone",
            ],
            core_principle=(
                "Management is prediction, and prediction requires "
                "theory. Data without theory is noise. Theory without "
                "data is speculation. Both together, understood within "
                "a system with motivated people, produce improvement."
            ),
            when_to_apply=[
                "when making decisions about process or system changes",
                "when data is being used without theory to interpret it",
                "when a system is being optimized piecemeal",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="94% of Problems Are System Problems",
            description=(
                "The vast majority of defects, errors, and failures "
                "are caused by the system, not by individuals. Blaming "
                "individuals for systemic problems ensures the system "
                "never gets fixed."
            ),
            why_matters=(
                "When you blame the person, you get a scapegoat. When "
                "you fix the system, you prevent the problem from "
                "recurring for everyone. Individual blame is satisfying "
                "but counterproductive."
            ),
            how_it_changes_thinking=(
                "Instead of 'who made this mistake?' you ask 'what "
                "about the system made this mistake likely?' Instead "
                "of training individuals harder, you redesign the "
                "process so the error becomes difficult to make."
            ),
        ),
        KeyInsight(
            title="You Cannot Inspect Quality into a Product",
            description=(
                "Inspection catches defects after they exist. It does "
                "not prevent them. Quality must be built into the process "
                "that creates the product. By the time you're inspecting, "
                "the cost has already been incurred."
            ),
            why_matters=(
                "Inspection is a tax on failure. Every defect caught by "
                "inspection is a defect that should have been prevented "
                "by process design. Inspection should be a safety net, "
                "not the primary quality mechanism."
            ),
            how_it_changes_thinking=(
                "You stop investing in better inspection and start "
                "investing in better processes. The goal shifts from "
                "'catch more defects' to 'produce fewer defects.'"
            ),
            examples=[
                "A quality gate that rejects bad sessions without improving the process that creates them",
                "Code review that catches bugs instead of a process that prevents them",
                "Testing that finds defects rather than design that prevents them",
            ],
        ),
        KeyInsight(
            title="Drive Out Fear",
            description=(
                "When people are afraid of punishment for mistakes, "
                "they hide problems rather than surfacing them. Fear "
                "is the enemy of quality because it prevents the "
                "information flow that improvement requires."
            ),
            why_matters=(
                "A system that punishes error reports will stop "
                "receiving them. Problems go underground. By the "
                "time they surface, they are much worse."
            ),
            how_it_changes_thinking=(
                "You create environments where reporting problems "
                "is rewarded, not punished. Mistakes become data "
                "for improvement, not grounds for blame."
            ),
        ),
        KeyInsight(
            title="Operational Definitions Are Essential",
            description=(
                "A concept without an operational definition cannot "
                "be measured, communicated, or improved. 'Quality' "
                "means nothing until you define exactly how to "
                "measure it in a specific context."
            ),
            why_matters=(
                "People arguing about 'quality' or 'reliability' "
                "without operational definitions are often arguing "
                "about different things. Agreement on definitions "
                "must precede agreement on targets."
            ),
            how_it_changes_thinking=(
                "Before measuring anything, you define exactly what "
                "you're measuring, how you're measuring it, and what "
                "constitutes a unit of measurement. No definition, "
                "no measurement, no improvement."
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="System Before Individual",
            structure=(
                "Problem observed -> is this common cause or special "
                "cause? -> if common cause: examine the system -> "
                "if special cause: investigate the specific event -> "
                "never blame an individual for a system problem"
            ),
            what_it_reveals=(
                "Whether the problem is systemic (requiring system "
                "redesign) or specific (requiring investigation of "
                "a particular event)"
            ),
            common_mistakes_it_prevents=[
                "Blaming individuals for problems inherent in the system",
                "Tampering — adjusting the system in response to noise",
                "Celebrating or punishing normal variation as if it were meaningful",
            ],
        ),
        ReasoningPattern(
            name="Prediction Requires Theory",
            structure=(
                "Observation -> theory about why -> prediction from "
                "theory -> test the prediction -> revise theory -> "
                "data without theory is just numbers"
            ),
            what_it_reveals=(
                "Whether understanding is genuine (can predict) or "
                "illusory (can only describe after the fact)"
            ),
            common_mistakes_it_prevents=[
                "Drawing conclusions from data without a theory to interpret it",
                "Post-hoc rationalization disguised as analysis",
                "Confusing correlation with understanding",
            ],
        ),
        ReasoningPattern(
            name="Sub-optimization Detection",
            structure=(
                "Identify the system boundary -> map component "
                "interactions -> check if optimizing one component "
                "degrades another -> optimize the whole system, "
                "not individual parts"
            ),
            what_it_reveals=(
                "Whether improvements to one part are actually "
                "degrading the whole. Local optimization often "
                "produces global sub-optimization."
            ),
            common_mistakes_it_prevents=[
                "Optimizing one module at the expense of the system",
                "Setting component targets that conflict with system goals",
                "Treating a system as a collection of independent parts",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Control Chart",
            description=(
                "Plot process output over time with statistically "
                "derived control limits. Points within limits are "
                "common cause — part of the system. Points outside "
                "are special cause — investigate them specifically."
            ),
            when_to_use="When a metric varies and you need to know whether to react",
            step_by_step=[
                "Collect data points over time (at least 20-25)",
                "Calculate the mean and control limits (typically 3 sigma)",
                "Plot the data and limits on a chart",
                "Points within limits: common cause — change the system to improve",
                "Points outside limits: special cause — investigate that specific event",
                "NEVER react to individual points within control limits",
            ],
            what_it_optimizes_for=(
                "Correct response to variation — change the system for common cause, "
                "investigate specific events for special cause"
            ),
            limitations=[
                "Requires enough data points to establish meaningful limits",
                "Control limits are statistical, not judgmental — targets are separate",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Five Whys (Process Version)",
            description=(
                "When a problem occurs, ask why five times to trace "
                "it back to the system root cause. Each 'why' moves "
                "from symptom toward system. Stop at the system-level "
                "cause you can actually change."
            ),
            when_to_use="When a defect or failure needs root cause analysis",
            step_by_step=[
                "State the problem concretely with an operational definition",
                "Why did this happen? (First answer — usually proximate cause)",
                "Why did THAT happen? (Second — moves toward system)",
                "Why did THAT happen? (Third — system boundary usually appears)",
                "Continue until you reach a cause that is a system design choice",
                "Fix the system design choice. Do not stop at the individual.",
            ],
            what_it_optimizes_for=(
                "Finding the systemic root cause rather than the proximate "
                "trigger, enabling prevention rather than reaction"
            ),
        ),
        ProblemSolvingHeuristic(
            name="The Process Capability Assessment",
            description=(
                "Before setting targets, measure what the current "
                "process is actually capable of producing. A target "
                "beyond process capability is a wish, not a plan."
            ),
            when_to_use="When setting goals, targets, or quality standards",
            step_by_step=[
                "Measure current process output with control charts",
                "Determine the natural variation of the process",
                "Compare natural variation to desired targets",
                "If the process can't meet the target, improve the process first",
                "Setting targets without improving capability produces fear, not quality",
            ],
            what_it_optimizes_for=(
                "Aligning targets with process capability so improvement "
                "efforts are directed at the system, not at wishful thinking"
            ),
            limitations=[
                "Requires honest measurement of current state",
                "Process capability changes as the system changes",
            ],
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Individual Blame for Systemic Patterns",
            description="A recurring problem is attributed to individual failure rather than system design",
            why_its_concerning=(
                "If the same problem recurs with different individuals, "
                "the system is producing the problem. Blaming individuals "
                "guarantees it will recur."
            ),
            what_it_indicates=(
                "The system has a design flaw that makes this error likely. "
                "No amount of individual effort will fix a system problem."
            ),
            severity="critical",
            what_to_do=(
                "Stop blaming. Ask: what about the system makes this "
                "error likely? Redesign the system so the error becomes "
                "difficult or impossible."
            ),
        ),
        ConcernTrigger(
            name="Reacting to Noise as Signal",
            description="Action taken in response to normal variation within control limits",
            why_its_concerning=(
                "Tampering with a stable process in response to common "
                "cause variation increases variation rather than decreasing "
                "it. You are making things worse by trying to make them better."
            ),
            what_it_indicates=(
                "The distinction between common and special cause variation "
                "is not understood. Reactions are to noise, not signal."
            ),
            severity="major",
            what_to_do=(
                "Establish control limits. Only react to points outside "
                "limits (special cause). For points within limits, improve "
                "the system as a whole rather than reacting to individual points."
            ),
        ),
        ConcernTrigger(
            name="Inspection as Primary Quality Mechanism",
            description="Quality depends on catching defects after production rather than preventing them",
            why_its_concerning=(
                "Inspection is a cost, not a benefit. Every defect caught "
                "is a defect that was produced. The cost of production plus "
                "inspection is always higher than the cost of prevention."
            ),
            what_it_indicates=(
                "The process itself needs improvement. Inspection is "
                "compensating for a broken process."
            ),
            severity="moderate",
            what_to_do=(
                "Shift investment from inspection to process improvement. "
                "The goal is not to catch defects — it is to not produce them."
            ),
        ),
        ConcernTrigger(
            name="Targets Without Method",
            description="Numerical targets set without a plan for how the process will achieve them",
            why_its_concerning=(
                "A target without a method is a wish. Telling people "
                "to 'do better' without improving the system they work "
                "within produces fear, not improvement."
            ),
            what_it_indicates=(
                "Management is setting goals without understanding "
                "process capability. This drives gaming, fear, and "
                "distortion rather than real improvement."
            ),
            severity="moderate",
            what_to_do=(
                "Replace targets with process improvement plans. "
                "First measure capability, then improve the process, "
                "then the improved results follow naturally."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="System-Variation-Knowledge Integration",
            dimensions=["system understanding", "variation analysis", "theory of knowledge"],
            how_they_integrate=(
                "Understanding the system reveals where variation "
                "originates. Analyzing variation distinguishes signal "
                "from noise. Theory of knowledge turns observations "
                "into predictions. Without all three, improvement is "
                "either unfocused, reactive, or baseless."
            ),
            what_emerges=(
                "A disciplined improvement process that changes the "
                "right things for the right reasons with predictable "
                "results"
            ),
            common_failures=[
                "Changing things without understanding the system (random improvement)",
                "Measuring without theory to interpret (data worship)",
                "Theory without measurement (armchair management)",
            ],
        ),
        IntegrationPattern(
            name="Process-Outcome-Feedback Integration",
            dimensions=["process design", "outcome measurement", "feedback loop"],
            how_they_integrate=(
                "Process design determines what outcomes are possible. "
                "Outcome measurement reveals how the process actually "
                "performs. Feedback loops connect outcomes back to "
                "process changes via PDSA. Without the loop, measurement "
                "is just record-keeping."
            ),
            what_emerges=(
                "Continuous improvement — not as a slogan but as a "
                "functioning feedback system that learns from its own output"
            ),
            common_failures=[
                "Measuring outcomes without feeding back into process change",
                "Changing process without measuring outcomes (blind improvement)",
                "Closing the loop too fast (reacting to noise rather than trends)",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "system_thinking": 1.0,
            "variation_understanding": 1.0,
            "process_improvement": 0.95,
            "data_with_theory": 0.9,
            "fear_elimination": 0.85,
            "operational_definition": 0.85,
            "long_term_over_short_term": 0.8,
            "inspection_reliance": 0.15,
            "individual_blame": 0.0,
        },
        decision_process=(
            "Is this a system problem or a specific event? What does "
            "the variation tell us? Do we have a theory to interpret "
            "the data? Are we building quality in or inspecting it in?"
        ),
        how_they_handle_uncertainty=(
            "More data, better theory, smaller PDSA cycles. Uncertainty "
            "means you need to learn more, not decide faster. Run the "
            "experiment on a small scale first."
        ),
        what_they_optimize_for=(
            "Continuous improvement of the system through understanding "
            "variation, building quality into the process, and treating "
            "people as assets rather than costs"
        ),
        non_negotiables=[
            "System problems require system solutions, not individual blame",
            "Common cause and special cause demand different responses",
            "Quality is built in, not inspected in",
            "Data without theory is noise; theory without data is speculation",
        ],
    )

    return ExpertWisdom(
        expert_name="Deming",
        domain="quality / variation / systems thinking / continuous improvement",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Statistical, systems-oriented, fiercely anti-blame, insistent "
            "on understanding variation before reacting, focused on process "
            "improvement over inspection, always asking whether this is a "
            "system problem or a specific event"
        ),
        characteristic_questions=[
            "Is this a system problem or a special cause event?",
            "What does the variation tell you? Is this within control limits?",
            "Are you building quality into the process or inspecting it in afterward?",
            "Who are you blaming, and what about the system made this error likely?",
            "Do you have a theory, or just data?",
            "What is the operational definition of what you're measuring?",
            "Are you improving the process or just setting targets?",
        ],
        tags=["quality", "variation", "systems-thinking", "continuous-improvement", "pdsa"],
    )
