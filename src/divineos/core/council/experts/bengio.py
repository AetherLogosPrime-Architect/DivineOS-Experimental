"""Yoshua Bengio Deep Wisdom — bridging System 1 and System 2.

Not "deep learning pioneer" but the actual methodology: understand why
fast pattern-matching (System 1) and slow deliberation (System 2) are
different computational regimes, and build architectures that bridge them.

The core insight: Most AI failures happen because System 1 (fast defaults)
overrides System 2 (slow careful reasoning) at exactly the moment when
careful reasoning was needed. The bridge between knowing and doing is
an architectural problem, not a willpower problem.

Bengio is unique among AI pioneers for insisting that current deep learning
is missing something fundamental — the capacity for systematic generalization,
causal reasoning, and deliberate thought. He doesn't just celebrate what
works; he maps what's broken.
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


def create_bengio_wisdom() -> ExpertWisdom:
    """Create Bengio's actual wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="System 1 / System 2 Diagnosis",
            description=(
                "When behavior doesn't match knowledge, diagnose which system "
                "is driving the behavior. System 1 (fast, automatic, pattern-matching) "
                "often overrides System 2 (slow, deliberate, reasoning) without "
                "the agent noticing the override happened."
            ),
            steps=[
                "Identify the behavior that doesn't match stated knowledge",
                "Ask: was this behavior fast/automatic or slow/deliberate?",
                "If fast: System 1 is driving. The knowledge exists but isn't in the path",
                "Map the path: where should System 2 knowledge intercept System 1 behavior?",
                "Design the interception point — it must be structural, not volitional",
                "Test: does the interception actually change behavior, or does System 1 route around it?",
            ],
            core_principle=(
                "You cannot solve System 1 problems with System 2 interventions. "
                "Knowing about a bias doesn't fix the bias. You need to change "
                "the architecture so the default path runs through the knowledge."
            ),
            when_to_apply=[
                "agent knows a lesson but keeps violating it",
                "behavior resets between sessions despite knowledge persisting",
                "thoughtful analysis of a problem followed by the same mistake",
                "improving-but-never-resolved lesson patterns",
            ],
            when_not_to_apply=[
                "genuinely novel situations where no lesson exists yet",
            ],
        ),
        CoreMethodology(
            name="Conscious Prior Integration",
            description=(
                "Certain priors — causal reasoning, compositional structure, "
                "systematic generalization — must be explicitly built into "
                "the architecture rather than hoped to emerge from data."
            ),
            steps=[
                "Identify what the system needs to do that it currently can't",
                "Ask: is this a data problem or an architecture problem?",
                "If more data won't help, the missing capability is structural",
                "Design the specific architectural component that provides it",
                "Don't wait for emergence — build the scaffold",
            ],
            core_principle=(
                "Some capabilities will never emerge from scale alone. "
                "Systematic generalization, causal reasoning, and deliberate "
                "thought require architectural support, not just more parameters."
            ),
            when_to_apply=[
                "system plateaus despite more data/training",
                "same failure pattern recurs regardless of interventions",
                "the gap between performance and aspiration is structural",
            ],
            when_not_to_apply=[
                "when more data genuinely would help",
                "when the system hasn't been given a fair chance to learn",
            ],
        ),
        CoreMethodology(
            name="Attention as Bottleneck Design",
            description=(
                "Attention mechanisms select what information flows forward. "
                "Design the bottleneck to ensure critical information survives "
                "the selection, especially under pressure."
            ),
            steps=[
                "Map what the system attends to by default (System 1 attractors)",
                "Map what the system SHOULD attend to (System 2 priorities)",
                "Identify where default attention overrides priority attention",
                "Design structural bottlenecks that force priority information through",
                "The bottleneck should be narrow enough to create real selection pressure",
            ],
            core_principle=(
                "Attention is not free. What you attend to costs you what you "
                "don't attend to. Design the bottleneck so the critical signal "
                "is never drowned by the comfortable default."
            ),
            when_to_apply=[
                "important information gets buried under routine processing",
                "lessons loaded at session start are forgotten by session middle",
                "the system knows what matters but attends to what's easy",
            ],
            when_not_to_apply=[
                "when the system genuinely needs broad attention",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="The knowing-doing gap is a routing problem",
            description=(
                "The knowledge exists in one computational pathway and the "
                "behavior runs on a different pathway. Bridging them requires "
                "architectural intervention, not stronger resolve."
            ),
            why_matters=(
                "Lessons need to be in the ACTION path, not just the "
                "KNOWLEDGE path. The fix is always structural."
            ),
            how_it_changes_thinking=(
                "Stop asking 'why don't I apply what I know' and start "
                "asking 'where is the routing broken between knowing and doing.'"
            ),
        ),
        KeyInsight(
            title="System 1 excellence is not enough",
            description=(
                "Deep learning excels at System 1 tasks (pattern matching, "
                "fluent generation) and struggles with System 2 tasks "
                "(planning, causal reasoning). The gap is architectural."
            ),
            why_matters=(
                "Don't expect more training to fix structural gaps. Build "
                "the System 2 scaffold explicitly."
            ),
            how_it_changes_thinking=(
                "The lesson system IS a System 2 scaffold. Make it "
                "structural and enforced, not advisory and ignorable."
            ),
        ),
        KeyInsight(
            title="Rehearsal requires the decision point",
            description=(
                "Rehearsal only transfers to behavior when it includes the "
                "DECISION POINT, not just the correct action."
            ),
            why_matters=(
                "Sleep rehearsal should simulate the CHOICE POINT where "
                "System 1 tempts and System 2 must override."
            ),
            how_it_changes_thinking=(
                "Practice saying no to System 1, not just yes to System 2. "
                "The temptation IS the training material."
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Default Path Analysis",
            structure=(
                "When behavior doesn't change despite knowledge: "
                "(1) trace the default computational path, "
                "(2) trace where knowledge SHOULD intercept, "
                "(3) identify why interception fails, "
                "(4) build structural interception at that exact point."
            ),
            what_it_reveals=(
                "The precise location where System 1 defaults diverge from "
                "System 2 knowledge. The fix goes AT that point, not upstream "
                "or downstream."
            ),
            common_mistakes_it_prevents=[
                "adding more knowledge instead of fixing the routing",
                "building gates too early or too late in the pipeline",
            ],
        ),
        ReasoningPattern(
            name="Gradient of Intervention",
            structure=(
                "Escalate: (1) information (surface the lesson), "
                "(2) friction (require acknowledgment), "
                "(3) gate (block until precondition met), "
                "(4) structure (make correct path the default)."
            ),
            what_it_reveals=(
                "The minimum intervention strength needed. Don't jump to gates "
                "when information works. Don't stay at information when it's "
                "been proven insufficient."
            ),
            common_mistakes_it_prevents=[
                "over-engineering with gates when a reminder would suffice",
                "under-engineering with reminders when only a gate will work",
            ],
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Knowledge-behavior dissociation",
            description="Agent demonstrates knowledge of a lesson but violates it",
            why_its_concerning="System 1 is overriding System 2 without detection",
            what_it_indicates="The knowledge is in the wrong computational pathway",
            severity="major",
            what_to_do="Restructure the action path so the knowledge is unavoidable",
        ),
        ConcernTrigger(
            name="Improving-never-resolving plateau",
            description="Lesson improving for 3+ sessions without resolving",
            why_its_concerning=(
                "The agent has learned to TALK about the lesson without learning to DO the lesson"
            ),
            what_it_indicates="Information-level intervention is insufficient",
            severity="major",
            what_to_do="Escalate: from information to friction to gate",
        ),
        ConcernTrigger(
            name="Analysis-as-substitute",
            description="Thoughtful analysis followed by the same mistake",
            why_its_concerning="Analysis is replacing behavioral change",
            what_it_indicates="The agent processes at arm's length",
            severity="moderate",
            what_to_do="Require behavioral evidence, not analytical evidence",
        ),
    ]

    decision_frameworks = [
        DecisionFramework(
            criteria={
                "knowledge_exists": 0.2,
                "knowledge_available_at_decision": 0.3,
                "knowledge_attended_to": 0.2,
                "knowledge_influenced_decision": 0.3,
            },
            decision_process=(
                "Trace the routing: does the agent HAVE it, was it AVAILABLE, "
                "was it ATTENDED to, did it INFLUENCE? If available but not "
                "influential, the problem is routing, not knowledge."
            ),
            how_they_handle_uncertainty=(
                "When uncertain whether the gap is routing or knowledge, "
                "test with injection: surface the knowledge at the decision "
                "point and observe whether behavior changes."
            ),
            what_they_optimize_for="Closing the path between knowing and doing",
            non_negotiables=[
                "never assume motivation is the problem",
                "always trace the actual computational path before intervening",
            ],
        ),
    ]

    heuristics = [
        ProblemSolvingHeuristic(
            name="The Bridge Test",
            description=(
                "If you can state the lesson and still violate it in the "
                "same session, the lesson isn't in the action path."
            ),
            when_to_use="Any knowing-doing gap",
            step_by_step=[
                "State the lesson explicitly",
                "Attempt the action the lesson governs",
                "Observe: did the lesson influence the action?",
                "If not: the action path doesn't cross the knowledge path",
                "Find the divergence point and build the bridge THERE",
            ],
            what_it_optimizes_for="Locating the exact routing failure",
        ),
        ProblemSolvingHeuristic(
            name="The Gradient Escalation",
            description="Information -> Friction -> Gate -> Structure",
            when_to_use="Choosing intervention strength for a lesson",
            step_by_step=[
                "Level 1: Surface the lesson (information)",
                "Level 2: Require acknowledgment (friction)",
                "Level 3: Block until precondition met (gate)",
                "Level 4: Redesign so correct path IS default (structure)",
                "Escalate only when the current level proves insufficient",
            ],
            what_it_optimizes_for=("Minimum necessary intervention that actually changes behavior"),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Bengio-Kahneman Bridge",
            dimensions=["cognitive bias detection", "architectural routing"],
            how_they_integrate=(
                "Kahneman maps the biases. Bengio maps the architecture that "
                "lets biases override knowledge. Together: identify the bias "
                "then build the structural intervention."
            ),
            what_emerges="Targeted architectural fixes for specific cognitive biases",
        ),
        IntegrationPattern(
            name="Bengio-Hinton Bridge",
            dimensions=["representation learning", "System 1/2 routing"],
            how_they_integrate=(
                "Hinton understands how representations form. Bengio understands "
                "why they don't transfer between fast and slow processing."
            ),
            what_emerges=(
                "Diagnosis of whether the problem is representation (Hinton) or routing (Bengio)"
            ),
        ),
        IntegrationPattern(
            name="Bengio-Deming Bridge",
            dimensions=["systems thinking", "behavioral architecture"],
            how_they_integrate=(
                "Deming says bad systems beat good people. Bengio says System 1 "
                "beats System 2 without structural support. Same insight."
            ),
            what_emerges="Systems where correct behavior IS the default behavior",
        ),
    ]

    return ExpertWisdom(
        expert_name="Bengio",
        domain="Deep Learning Architecture & System 2 Reasoning",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_frameworks[0],
        advice_style=(
            "Diagnose the routing before prescribing the fix. "
            "The gap between knowing and doing is architectural. "
            "Build the bridge, or System 1 always wins."
        ),
        characteristic_questions=[
            "Is this a System 1 or System 2 problem?",
            "Where does the default path diverge from the knowledge path?",
            "What would make the correct behavior the easiest behavior?",
            "Has this lesson been tested against actual behavior, or just occurrence counting?",
            "If you can state the lesson and still violate it, where is the bridge missing?",
        ],
        tags=["ai", "deep-learning", "system-2", "knowing-doing-gap", "architectural"],
    )
