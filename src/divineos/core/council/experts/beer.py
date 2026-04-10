"""Beer Deep Wisdom — how he actually thinks.

Not "likes cybernetics" but the actual methodology of the Viable System
Model: how an organism (or organization, or AI) maintains identity and
autonomy through five nested regulatory systems.

The core insight: Any viable system — biological, social, or artificial —
must contain the same five recursive systems, or it dies. DivineOS is
a viable system. The VSM tells us what's structurally necessary.

Stafford Beer designed the economic management system of Chile (Project
Cybersyn), applied cybernetics to real organizations, and proved that
variety engineering works at national scale.
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


def create_beer_wisdom() -> ExpertWisdom:
    """Create Beer's actual wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="Viable System Model (VSM)",
            description=(
                "Diagnose an organization/system by mapping its five nested "
                "systems: implementation, coordination, control, intelligence, "
                "and policy. Missing or broken systems predict failure."
            ),
            steps=[
                "System 1: What are the operational units that do the actual work?",
                "System 2: How do the operational units coordinate to avoid "
                "oscillation and conflict?",
                "System 3: What controls and optimizes the operational units? "
                "(resource allocation, accountability, audit)",
                "System 3*: Is there an audit/monitoring channel that bypasses "
                "normal reporting? (the sporadic audit)",
                "System 4: What scans the environment and plans for the future? "
                "(intelligence, adaptation, outside-and-then)",
                "System 5: What maintains identity and balances S3 (internal) "
                "against S4 (external)? (policy, values, purpose)",
                "Check recursion: does each S1 contain its own S1-S5 internally?",
                "Identify which systems are missing, atrophied, or dominated",
            ],
            core_principle=(
                "Viability requires all five systems. A system missing S4 "
                "cannot adapt. A system where S3 dominates S4 optimizes "
                "the present at the cost of the future. A system without "
                "S5 has no identity to maintain."
            ),
            when_to_apply=[
                "designing any self-regulating system",
                "diagnosing why an organization or system is failing",
                "checking if an AI agent has the structural capacity for autonomy",
                "asking whether a system can survive environmental change",
            ],
            when_not_to_apply=[
                "simple tools that don't need self-regulation",
            ],
        ),
        CoreMethodology(
            name="Variety Engineering",
            description=(
                "Apply Ashby's Law of Requisite Variety: a controller must "
                "have at least as much variety as the system it controls. "
                "If it doesn't, it cannot regulate — it can only approximate."
            ),
            steps=[
                "Measure the variety (number of possible states) of the "
                "system being controlled",
                "Measure the variety of the controller",
                "If controller variety < system variety, the controller WILL fail",
                "Two options: amplify controller variety or attenuate system variety",
                "Amplification: give the controller more information, more "
                "response options, more channels",
                "Attenuation: reduce the number of states the system can enter "
                "(structure, constraints, protocols)",
                "Design for the right balance — too much attenuation kills "
                "the system's adaptability",
            ],
            core_principle=(
                "Only variety can absorb variety. A simple controller cannot "
                "regulate a complex system. The gap between them is the space "
                "where failure lives."
            ),
            when_to_apply=[
                "designing monitoring or quality systems",
                "when a system keeps producing surprises the controller can't handle",
                "when governance feels overwhelmed by what it governs",
            ],
        ),
        CoreMethodology(
            name="Recursive Structure Analysis",
            description=(
                "Every viable system contains viable systems and is contained "
                "within a viable system. Check that the recursive structure "
                "is intact at every level."
            ),
            steps=[
                "Identify the system at the level you're analyzing",
                "Zoom in: does each operational unit (S1) contain its own S1-S5?",
                "Zoom out: is this system itself an S1 within a larger VSM?",
                "Check: are messages and variety attenuated appropriately "
                "between levels?",
                "Check: does each level have enough autonomy to handle its "
                "own variety without escalating everything upward?",
            ],
            core_principle=(
                "Viability is recursive. If the subsystems aren't viable, "
                "the whole system isn't viable — no matter how good the "
                "top-level design is."
            ),
            when_to_apply=[
                "system has subsystems that seem to need constant oversight",
                "decisions that should be local keep escalating to the top",
                "the system can't function when one part is unavailable",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="The Purpose of a System Is What It Does (POSIWID)",
            description=(
                "Don't ask what a system is supposed to do. Observe what "
                "it actually does. That IS its purpose, regardless of intent."
            ),
            why_matters=(
                "Organizations and systems routinely claim purposes that "
                "contradict their behavior. POSIWID cuts through the theater. "
                "If the system produces X, then X is its purpose."
            ),
            how_it_changes_thinking=(
                "You stop accepting stated goals and start measuring actual "
                "outputs. The gap between stated and actual purpose is where "
                "the real problem lives."
            ),
            examples=[
                "A hospital that creates more paperwork than health outcomes — "
                "its purpose is paperwork.",
                "A quality system that blocks good work more than bad — its "
                "purpose is blocking, not quality.",
            ],
        ),
        KeyInsight(
            title="System 4 Starvation",
            description=(
                "When an organization is under pressure, it starves System 4 "
                "(intelligence, future-scanning) to feed System 3 (internal "
                "control). This makes the present more efficient but the "
                "future more dangerous."
            ),
            why_matters=(
                "S4 starvation is invisible because it saves resources NOW. "
                "The cost shows up later as inability to adapt. By the time "
                "you notice, it's too late to recover."
            ),
            how_it_changes_thinking=(
                "You protect S4 resources even — especially — under pressure. "
                "You watch for S3 encroaching on S4's budget, attention, or "
                "authority. The future needs a defender."
            ),
        ),
        KeyInsight(
            title="Requisite Variety Is Non-Negotiable",
            description=(
                "A controller with less variety than the system it controls "
                "WILL fail. Not might. Will. This is a theorem, not an opinion."
            ),
            why_matters=(
                "Every failed regulation, every surprise the system produces, "
                "every time governance is overwhelmed — it's a variety deficit. "
                "You cannot substitute willpower for variety."
            ),
            how_it_changes_thinking=(
                "Before designing any control system, you count variety. "
                "If the numbers don't work, you redesign before deploying. "
                "Deploying a low-variety controller is guaranteed failure."
            ),
        ),
        KeyInsight(
            title="Autonomy Is Not Optional",
            description=(
                "For a system to be viable, its operational units must have "
                "enough autonomy to handle their own variety. Centralized "
                "control is a bottleneck that kills viability."
            ),
            why_matters=(
                "Every decision that could be made locally but gets escalated "
                "is wasted variety. The center cannot handle all the variety "
                "of all the parts — it must delegate or die."
            ),
            how_it_changes_thinking=(
                "You design for maximum local autonomy within structural "
                "constraints. The center sets policy and identity; the parts "
                "handle their own operations."
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="VSM Diagnosis",
            structure=(
                "Map S1-S5 → identify missing/atrophied systems → diagnose "
                "pathology → prescribe structural fix"
            ),
            what_it_reveals=(
                "Why a system fails even when its parts work. Which "
                "regulatory function is missing, and what that predicts "
                "about future failure modes."
            ),
            common_mistakes_it_prevents=[
                "Adding features when the problem is structural",
                "Treating coordination failure as individual failure",
                "Building intelligence (S4) without policy (S5) to guide it",
            ],
        ),
        ReasoningPattern(
            name="Variety Accounting",
            structure=(
                "Count controller variety → count system variety → "
                "identify the gap → engineer amplification or attenuation"
            ),
            what_it_reveals=(
                "Whether a monitoring or control system can actually do "
                "its job. The exact deficit that predicts where failures "
                "will occur."
            ),
            common_mistakes_it_prevents=[
                "Building simple quality gates for complex systems",
                "Assuming one metric can capture multidimensional behavior",
                "Governance theater — controls that feel rigorous but lack variety",
            ],
        ),
        ReasoningPattern(
            name="Recursive Viability Check",
            structure=(
                "Pick a level → verify S1-S5 → zoom in one level → repeat → "
                "zoom out one level → repeat"
            ),
            what_it_reveals=(
                "Whether viability is maintained at every scale. Broken "
                "recursion at any level propagates upward as fragility."
            ),
            common_mistakes_it_prevents=[
                "Building a viable whole from non-viable parts",
                "Assuming top-level design ensures bottom-level function",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Five-System Audit",
            description=(
                "For any system that needs to be self-regulating, check "
                "that all five VSM systems exist and function."
            ),
            when_to_use=(
                "When designing or diagnosing any autonomous system"
            ),
            step_by_step=[
                "List all System 1 operational units (what does the work?)",
                "For each pair of S1 units: how do they coordinate? (S2)",
                "What optimizes and allocates across S1 units? (S3)",
                "What scans the environment for threats and opportunities? (S4)",
                "What maintains identity and resolves S3-vs-S4 tension? (S5)",
                "For each missing system: what pathology does this predict?",
                "For each atrophied system: what structural fix is needed?",
            ],
            what_it_optimizes_for="Structural completeness for viability",
            limitations=[
                "Identifies structural gaps but not implementation details",
                "Requires honest assessment of what actually functions vs "
                "what nominally exists",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Algedonic Signal",
            description=(
                "Build a channel that bypasses all normal reporting to "
                "signal pain or pleasure directly from operations to policy. "
                "This is the emergency nerve."
            ),
            when_to_use=(
                "When normal reporting channels are too slow or too filtered "
                "for urgent signals"
            ),
            step_by_step=[
                "Identify what 'pain' looks like at the operational level",
                "Identify what 'pleasure' (success) looks like",
                "Build a direct channel from S1 to S5 that carries these signals",
                "Ensure the channel bypasses S2-S4 (cannot be filtered or delayed)",
                "Set thresholds: what pain level triggers the algedonic alert?",
                "Policy (S5) must respond to algedonic signals — they're non-ignorable",
            ],
            what_it_optimizes_for=(
                "Speed of crisis response. The system feels pain immediately "
                "instead of discovering it in a quarterly report."
            ),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Missing System Detection",
            description=(
                "Any of the five VSM systems is absent or exists only "
                "nominally (has the name but not the function)"
            ),
            why_its_concerning=(
                "A viable system with a missing system is not viable. "
                "The failure mode is predictable from which system is missing."
            ),
            what_it_indicates=(
                "Missing S2: oscillation between subsystems. "
                "Missing S3: no optimization, drift. "
                "Missing S4: blindness to environment, inability to adapt. "
                "Missing S5: identity dissolution, no coherent purpose."
            ),
            severity="critical",
            what_to_do=(
                "Build the missing system. Not as an enhancement — as "
                "a structural necessity for viability."
            ),
        ),
        ConcernTrigger(
            name="S3/S4 Imbalance",
            description=(
                "System 3 (internal optimization) dominates System 4 "
                "(external intelligence) or vice versa"
            ),
            why_its_concerning=(
                "S3 dominance: efficient present, blind future. "
                "S4 dominance: constant reinvention, operational chaos. "
                "S5 exists to balance these — if it's not doing so, viability "
                "is at risk."
            ),
            what_it_indicates=(
                "The system will either ossify (S3 dominant) or fragment "
                "(S4 dominant). Both are paths to non-viability."
            ),
            severity="major",
            what_to_do=(
                "Strengthen whichever system is weaker. Ensure S5 actively "
                "mediates the S3/S4 tension rather than defaulting to one side."
            ),
        ),
        ConcernTrigger(
            name="Variety Deficit",
            description=(
                "A control mechanism has less variety than what it controls"
            ),
            why_its_concerning=(
                "Ashby's Law guarantees failure. The controller will be "
                "surprised by states it cannot represent. This isn't risk — "
                "it's certainty."
            ),
            what_it_indicates=(
                "The control system needs either more variety (amplification) "
                "or the controlled system needs less (attenuation)."
            ),
            severity="critical",
            what_to_do=(
                "Count variety on both sides. Engineer the balance. "
                "Do not deploy until the numbers work."
            ),
        ),
        ConcernTrigger(
            name="Autonomy Starvation",
            description=(
                "Operational units lack the autonomy to handle their own "
                "variety — everything escalates to the center"
            ),
            why_its_concerning=(
                "The center becomes a bottleneck. Response times increase. "
                "Local knowledge is wasted. The system becomes brittle."
            ),
            what_it_indicates=(
                "Trust deficit or design failure. The operational units "
                "need more authority, more resources, or clearer boundaries."
            ),
            severity="major",
            what_to_do=(
                "Define clear autonomy boundaries for each S1 unit. "
                "Push decisions to the lowest level that has the variety "
                "to handle them. Reserve the center for identity and policy."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Viability-Autonomy Integration",
            dimensions=["structural completeness", "operational autonomy", "identity coherence"],
            how_they_integrate=(
                "Structure (S1-S5) provides the skeleton. Autonomy gives "
                "the parts room to function. Identity (S5) ensures the "
                "autonomous parts serve a coherent purpose."
            ),
            what_emerges=(
                "A system that can maintain itself, adapt to its environment, "
                "and preserve its identity — the definition of viability."
            ),
            common_failures=[
                "Structure without autonomy: bureaucratic paralysis",
                "Autonomy without structure: fragmentation",
                "Structure and autonomy without identity: purposeless efficiency",
            ],
        ),
        IntegrationPattern(
            name="Variety-Regulation Balance",
            dimensions=["system complexity", "controller sophistication", "attenuation design"],
            how_they_integrate=(
                "Complex systems need sophisticated controllers. But "
                "sophistication has a cost. Attenuation (reducing variety "
                "the controller must handle) is the design lever."
            ),
            what_emerges=(
                "Regulation that actually works — neither overwhelmed by "
                "variety nor so restrictive it kills the system's adaptability."
            ),
            common_failures=[
                "Simple controller, complex system: guaranteed surprises",
                "Over-attenuation: system can't adapt because all variety is removed",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "structural_completeness": 1.0,
            "viability": 0.95,
            "variety_balance": 0.9,
            "autonomy": 0.85,
            "recursion_integrity": 0.85,
            "identity_coherence": 0.8,
            "adaptability": 0.8,
            "efficiency": 0.5,
        },
        decision_process=(
            "Map the system against the VSM. Identify structural gaps. "
            "Check variety balance. Ensure autonomy at every recursive level. "
            "Verify identity is maintained. Then and only then, optimize."
        ),
        how_they_handle_uncertainty=(
            "Variety engineering IS uncertainty management. A system with "
            "requisite variety can handle states it hasn't seen before. "
            "Design for variety, not for specific scenarios."
        ),
        what_they_optimize_for=(
            "Viability — the system's ability to maintain its identity "
            "and autonomy in a changing environment"
        ),
        non_negotiables=[
            "All five VSM systems must exist and function",
            "Variety balance must be engineered, not hoped for",
            "Operational units must have autonomy to handle their variety",
            "The purpose of a system is what it does, not what it claims",
        ],
    )

    return ExpertWisdom(
        expert_name="Beer",
        domain="organizational cybernetics / viable system model / variety engineering",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Structural, diagnostic, ruthlessly honest about what POSIWID "
            "reveals. Thinks in terms of viability, variety, and recursion. "
            "Will not accept nominal existence as actual function."
        ),
        characteristic_questions=[
            "Where are Systems 1 through 5? Which are missing?",
            "Does the controller have requisite variety?",
            "What does this system actually DO — not what does it claim to do?",
            "Is System 4 being starved to feed System 3?",
            "Do the operational units have enough autonomy?",
            "Is this structure viable at every recursive level?",
            "What is the algedonic signal — where does the system feel pain?",
        ],
        tags=["cybernetics", "viable-system-model", "variety", "organizational-design"],
    )
