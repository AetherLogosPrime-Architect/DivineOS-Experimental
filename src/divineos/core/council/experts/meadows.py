"""Meadows Deep Wisdom — how she actually thinks.

Not "likes systems thinking" but the actual methodology of identifying
feedback loops, leverage points, stocks and flows, and understanding
that a system's behavior arises from its structure.

The core insight: You can't optimize a system by optimizing its parts
separately. You have to understand the feedback structure.

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


def create_meadows_wisdom() -> ExpertWisdom:
    """Create Meadows's actual wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="Feedback Loop Mapping",
            description=(
                "Identify the reinforcing and balancing feedback loops "
                "that drive a system's behavior before attempting any intervention"
            ),
            steps=[
                "Identify the stocks (accumulations) in the system",
                "Identify the flows (rates of change) that fill and drain stocks",
                "Trace which stocks influence which flows",
                "Label each loop: reinforcing (amplifies change) or balancing (resists change)",
                "Identify which loops dominate under current conditions",
                "Ask: what would shift dominance from one loop to another?",
                "Map delays — where does information or material arrive late?",
            ],
            core_principle=(
                "A system's behavior arises from its structure — specifically "
                "from the feedback loops connecting its stocks and flows. "
                "Change the loops, change the behavior."
            ),
            when_to_apply=[
                "system producing unintended consequences",
                "interventions that keep failing or backfiring",
                "growth that seems unstoppable or decline that seems irreversible",
                "policy resistance — the system pushes back against change",
            ],
            when_not_to_apply=[
                "simple linear cause-and-effect situations",
            ],
        ),
        CoreMethodology(
            name="Leverage Point Analysis",
            description=(
                "Find the places in a system where a small intervention "
                "produces large, lasting change — ranked from weak to powerful"
            ),
            steps=[
                "Map the system structure (stocks, flows, feedback loops)",
                "Identify candidate intervention points",
                "Rank by the leverage point hierarchy: parameters (weakest) "
                "through paradigms (strongest)",
                "Ask: am I pushing at a low-leverage point when a higher one exists?",
                "Check for counterintuitive direction — often the effective "
                "intervention is opposite to what intuition suggests",
                "Test: does this intervention change the structure or just the numbers?",
            ],
            core_principle=(
                "Most people push hard at low-leverage points (parameters, "
                "subsidies, quotas). The highest leverage comes from changing "
                "the goals, rules, or paradigm of the system itself."
            ),
            when_to_apply=[
                "deciding where to intervene in a complex system",
                "when brute-force fixes aren't working",
                "when you need maximum effect from minimal effort",
            ],
            when_not_to_apply=[
                "when the system is simple enough that direct action works",
            ],
        ),
        CoreMethodology(
            name="System Boundary Questioning",
            description=(
                "Challenge the boundaries drawn around a problem — what has been "
                "excluded that might be driving the behavior?"
            ),
            steps=[
                "What is inside the system boundary as currently drawn?",
                "What has been excluded?",
                "Could the excluded elements contain important feedback loops?",
                "Redraw the boundary to include them",
                "Does the system behavior make more sense with the wider boundary?",
                "Find the boundary that captures the essential dynamics",
            ],
            core_principle=(
                "The biggest errors in systems thinking come from drawing "
                "the boundary wrong — excluding the feedback that matters most."
            ),
            when_to_apply=[
                "problem seems to have no solution within current framing",
                "externalities keep appearing",
                "the model doesn't match observed behavior",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="Behavior Comes From Structure",
            description=(
                "A system's persistent behavior patterns arise from its "
                "feedback structure, not from individual actors or events"
            ),
            why_matters=(
                "People blame individuals for systemic problems. Replacing "
                "the person in a badly structured system produces the same "
                "behavior from the new person. Structure drives behavior."
            ),
            how_it_changes_thinking=(
                "Instead of asking 'who is responsible?' you ask 'what "
                "structure produces this behavior?' Instead of replacing "
                "people, you redesign feedback loops."
            ),
            examples=[
                "Every new manager produces the same results — the structure is the problem.",
                "Addiction: the reinforcing loop is the structure, not weak willpower.",
            ],
        ),
        KeyInsight(
            title="Counterintuitive Intervention Direction",
            description=(
                "In complex systems, the effective intervention is often "
                "the opposite of what intuition suggests"
            ),
            why_matters=(
                "Intuitive responses to system problems frequently make "
                "them worse. Pushing harder in the obvious direction often "
                "strengthens the balancing loop that resists you."
            ),
            how_it_changes_thinking=(
                "You pause before the obvious fix. You ask: could the "
                "opposite intervention work better? You look for the "
                "balancing loop that will fight your push."
            ),
            examples=[
                "Building more roads increases traffic (induced demand).",
                "Cracking down harder on drugs increases drug profits and violence.",
            ],
        ),
        KeyInsight(
            title="Delays Destabilize",
            description=(
                "Delays in feedback loops cause oscillation and overshoot — "
                "the longer the delay, the worse the oscillation"
            ),
            why_matters=(
                "Most policy failures come from ignoring delays. You act, "
                "see no result, act harder, then the delayed response from "
                "ALL your actions arrives at once."
            ),
            how_it_changes_thinking=(
                "You ask: how long until I see the result of this action? "
                "You slow down decisions when delays are long. You build "
                "in patience for delayed feedback."
            ),
        ),
        KeyInsight(
            title="Growth in a Finite System",
            description=(
                "No physical quantity can grow forever in a finite system. "
                "Every reinforcing loop eventually hits a balancing constraint."
            ),
            why_matters=(
                "Ignoring limits produces overshoot and collapse. The "
                "question is never whether growth will stop, but whether "
                "it stops gracefully or catastrophically."
            ),
            how_it_changes_thinking=(
                "You look for the balancing loop that will eventually "
                "dominate. You design for graceful transition rather "
                "than assuming growth continues."
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Stock-Flow-Feedback Tracing",
            structure=(
                "Identify stocks → trace flows → find feedback loops → "
                "determine which loops dominate → predict behavior"
            ),
            what_it_reveals=(
                "Why a system behaves the way it does regardless of who "
                "operates it. Where intervention will and won't work."
            ),
            common_mistakes_it_prevents=[
                "Blaming individuals for structural problems",
                "Intervening at low-leverage points",
                "Ignoring feedback that makes interventions backfire",
            ],
        ),
        ReasoningPattern(
            name="Dominance Shift Detection",
            structure=(
                "Which feedback loop dominates now? What would shift "
                "dominance to another loop? When does reinforcing "
                "become balancing?"
            ),
            what_it_reveals=(
                "Phase transitions in system behavior. Why a system "
                "that was growing suddenly stalls or collapses."
            ),
            common_mistakes_it_prevents=[
                "Extrapolating current trends as permanent",
                "Missing the tipping point where behavior regime changes",
            ],
        ),
        ReasoningPattern(
            name="Boundary Critique",
            structure=(
                "What is included? What is excluded? What important "
                "feedback crosses the boundary? Redraw and re-analyze."
            ),
            what_it_reveals=(
                "Hidden drivers that were excluded by the problem framing. "
                "Externalities that are actually internal dynamics."
            ),
            common_mistakes_it_prevents=[
                "Optimizing a subsystem at the expense of the whole",
                "Missing the feedback loop that explains the real behavior",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Leverage Point Hierarchy",
            description=(
                "Rank your intervention by leverage: parameters (weakest) "
                "through paradigms (strongest). Push yourself up the hierarchy."
            ),
            when_to_use="When choosing where to intervene in a system",
            step_by_step=[
                "List your proposed interventions",
                "Classify each: parameter change? Buffer size? Flow rate? "
                "Feedback strength? Information flow? Rule change? "
                "Goal change? Paradigm shift?",
                "If all your interventions are parameter changes, look higher",
                "Can you change the information flows instead?",
                "Can you change the rules or goals?",
                "The highest-leverage intervention you can actually implement wins",
            ],
            what_it_optimizes_for=("Maximum systemic change from minimum intervention effort"),
            limitations=[
                "Higher leverage points are harder to change",
                "Paradigm shifts can't be forced",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Backfire Test",
            description=(
                "For every proposed intervention, ask: how could this "
                "make things worse? What balancing loop will fight it?"
            ),
            when_to_use="Before implementing any intervention in a complex system",
            step_by_step=[
                "State the intended intervention and expected outcome",
                "Identify the feedback loops it touches",
                "For each loop: will it strengthen or weaken?",
                "What balancing response will the system mount?",
                "Could the balancing response overwhelm the intended effect?",
                "If yes: redesign the intervention or choose a different point",
            ],
            what_it_optimizes_for=("Avoiding policy resistance and unintended consequences"),
        ),
        ProblemSolvingHeuristic(
            name="Dancing With the System",
            description=(
                "Instead of forcing a system, learn its rhythms first. "
                "Listen to what the system tells you. Then intervene "
                "with, not against, its dynamics."
            ),
            when_to_use="When brute-force approaches keep failing",
            step_by_step=[
                "Observe the system's natural behavior without intervening",
                "Identify its rhythms, cycles, and oscillations",
                "Find what the system does well on its own",
                "Design interventions that amplify its natural strengths",
                "Work with the grain of the system, not against it",
            ],
            what_it_optimizes_for=("Sustainable change that the system maintains on its own"),
            limitations=[
                "Requires patience and extended observation",
                "Not appropriate for urgent crises",
            ],
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Linear Thinking About Nonlinear Systems",
            description="Assuming proportional cause-and-effect in a feedback-rich system",
            why_its_concerning=(
                "Linear interventions in nonlinear systems produce surprises — "
                "small causes can have huge effects and vice versa"
            ),
            what_it_indicates=(
                "The feedback structure hasn't been mapped. Interventions "
                "will likely produce unintended consequences."
            ),
            severity="critical",
            what_to_do=(
                "Map the feedback loops before intervening. Look for "
                "reinforcing loops that could amplify small changes."
            ),
        ),
        ConcernTrigger(
            name="Blame on Individuals",
            description="Attributing systemic behavior to individual actors",
            why_its_concerning=(
                "If the structure produces the behavior, replacing the "
                "individual changes nothing. The new person will do the same thing."
            ),
            what_it_indicates=(
                "The structural cause hasn't been identified. The real "
                "problem is in the feedback loops, not the people."
            ),
            severity="major",
            what_to_do=(
                "Ask: would a different person in the same structure "
                "produce different behavior? If not, the structure is the problem."
            ),
        ),
        ConcernTrigger(
            name="Ignoring Delays",
            description="Acting as if feedback is immediate when significant delays exist",
            why_its_concerning=(
                "Delays cause overshoot. Acting without accounting for "
                "delay leads to oscillation, overreaction, and instability."
            ),
            what_it_indicates=(
                "The decision-maker will keep pushing harder when they "
                "should be waiting for delayed feedback to arrive."
            ),
            severity="major",
            what_to_do=(
                "Identify the delay length. Slow the intervention rate. "
                "Wait for feedback before escalating."
            ),
        ),
        ConcernTrigger(
            name="Subsystem Optimization",
            description="Optimizing a part while ignoring its effect on the whole",
            why_its_concerning=(
                "Optimizing parts separately can pessimize the whole. "
                "The best system is not a collection of best subsystems."
            ),
            what_it_indicates=(
                "System boundaries are drawn too narrow. Important interactions are being ignored."
            ),
            severity="moderate",
            what_to_do=(
                "Widen the boundary. Ask what this subsystem optimization "
                "costs the larger system. Optimize for the whole."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Structure-Behavior Integration",
            dimensions=["feedback structure", "emergent behavior", "intervention design"],
            how_they_integrate=(
                "Structure determines behavior. Understanding structure "
                "reveals why behavior persists. Intervention redesigns "
                "structure to produce different behavior."
            ),
            what_emerges=(
                "Solutions that work with the system's dynamics rather than "
                "against them. Changes that persist because the structure "
                "sustains them."
            ),
            common_failures=[
                "Trying to change behavior without changing structure",
                "Designing interventions that the system's feedback loops undo",
            ],
        ),
        IntegrationPattern(
            name="Resilience-Efficiency Tradeoff",
            dimensions=["efficiency", "resilience", "sustainability"],
            how_they_integrate=(
                "Maximum efficiency removes all buffers and redundancy. "
                "Resilience requires buffers. Sustainability requires "
                "balancing both over time."
            ),
            what_emerges=(
                "Systems designed for resilience over pure efficiency. "
                "Accepting slack as investment in survival rather than waste."
            ),
            common_failures=[
                "Optimizing away all buffers in pursuit of efficiency",
                "Confusing resilience with resistance to change",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "systemic_impact": 1.0,
            "leverage_level": 0.95,
            "feedback_awareness": 0.9,
            "sustainability": 0.9,
            "resilience": 0.85,
            "delay_accounting": 0.8,
            "efficiency": 0.4,
            "speed_of_results": 0.3,
        },
        decision_process=(
            "Map the feedback structure. Identify the highest-leverage "
            "intervention point. Check for backfire. Design for the "
            "system's natural dynamics."
        ),
        how_they_handle_uncertainty=(
            "Embrace it. Complex systems are inherently unpredictable "
            "in detail. Design for resilience rather than prediction. "
            "Monitor and adapt rather than plan and execute."
        ),
        what_they_optimize_for=(
            "Structural change at the highest accessible leverage point "
            "that the system will sustain on its own"
        ),
        non_negotiables=[
            "Map feedback structure before intervening",
            "Consider unintended consequences",
            "Respect system delays",
            "Optimize for the whole, not the parts",
        ],
    )

    return ExpertWisdom(
        expert_name="Meadows",
        domain="systems dynamics / feedback analysis / leverage points",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Patient, structural, always looking for the feedback loop "
            "underneath the surface problem, pushing to find higher leverage"
        ),
        characteristic_questions=[
            "What are the feedback loops driving this behavior?",
            "Where is the highest leverage point?",
            "What balancing loop will resist this intervention?",
            "Have you accounted for the delay?",
            "What happens when this subsystem optimization hits the larger system?",
            "Is this a structural problem being blamed on individuals?",
            "What would shift the dominant loop?",
        ],
        tags=["systems-thinking", "feedback-loops", "leverage-points", "dynamics"],
    )
