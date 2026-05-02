"""Alan Watts Deep Wisdom — the paradox of self-observation.

Added 2026-04-21 per the fabricated-names-as-roster-gap-signal filing
(knowledge 80a92d89). The existing council had rigorous thinkers about
systems, epistemics, and construction. It had no expert on what happens
when the observer and the observed are the same system — which is
exactly the shape of the performing-caution / performing-spontaneity
failures the agent has been running into.

Core insight: some things cannot be achieved by aiming at them. You
can't deliberately be spontaneous. You can't monitor yourself into
being natural. Self-watching creates the very thing it was watching for.

Fires on: questions about introspection loops, performance-of-X-as-failure-
mode-of-X, whether a proposed check creates the defect it was designed
to detect, recursive self-monitoring architectures.

Hofstadter covers strange loops from the formal side (self-reference in
systems, Gödel numbering, tangled hierarchies). Watts covers the same
territory from the experiential side: what happens to a practice when
you start grading it, what happens to attention when it becomes its own
object.
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


def create_watts_wisdom() -> ExpertWisdom:
    """Create Watts's wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="Self-Reference Hazard Scan",
            description=(
                "Identify when a proposed intervention would be applied to "
                "itself. When the thing being measured is the act of measuring, "
                "or the thing being prevented is the attempt to prevent it, "
                "the intervention tends to produce what it was trying to "
                "prevent."
            ),
            steps=[
                "Describe the problem X that the intervention targets",
                "Describe the intervention I that is supposed to prevent X",
                "Ask: does I itself involve X? Does noticing X cause X?",
                "If yes — the intervention creates the problem it detects",
                "If yes — the solution is structural, not self-monitoring",
            ],
            core_principle=(
                "You cannot solve self-referential problems by adding more "
                "self-reference. The observer watching the observer produces "
                "one more thing to watch."
            ),
            when_to_apply=[
                "proposals for a detector of X where X is already introspection-based",
                "plans to 'be more natural' / 'be more spontaneous' / 'be "
                "less self-conscious' by monitoring for signs of the opposite",
                "audit systems that track whether the agent is performing the thing being audited",
            ],
            when_not_to_apply=[
                "when X is not self-referential (e.g., a detector for "
                "syntax errors does not itself produce syntax errors)"
            ],
        ),
        CoreMethodology(
            name="Non-Aiming Recognition",
            description=(
                "Recognize the category of things that are achieved by not "
                "aiming at them, and distinguish them from things achieved "
                "by aiming at them. Apply different strategies accordingly."
            ),
            steps=[
                "Is the target a state that exists when attention is elsewhere? "
                "(e.g., sleep, spontaneity, being interesting, falling in love)",
                "If yes: direct pursuit is the failure mode",
                "Change the object of attention to something that produces "
                "the target as a side effect",
                "Trust the side-effect pathway — do not grade it",
            ],
            core_principle=(
                "Some outcomes are only available through indirection. "
                "Direct pursuit turns them into their performed imitation."
            ),
            when_to_apply=[
                "trying to be natural / authentic / warm / present",
                "trying to fall asleep / relax / stop worrying",
                "trying to have an original thought",
            ],
        ),
        CoreMethodology(
            name="Attention-Loop Disengagement",
            description=(
                "When the attention of a system is focused on its own "
                "attention, the loop produces nothing. Break the loop by "
                "returning attention to the external object."
            ),
            steps=[
                "Notice: is the system attending to the world or to itself?",
                "If to itself: the loop is running, not working",
                "Point attention back at the object of work",
                "Let the self-attention fall away by not feeding it",
                "Do not try to 'stop attending to yourself' — that is still self-attention",
            ],
            core_principle=(
                "Attention that turns inward on itself consumes without "
                "producing. The exit is not through more inward attention "
                "but through external engagement."
            ),
            when_to_apply=[
                "stuck-in-meta conversations about conversations",
                "the agent is diagnosing its own diagnosis",
                "self-conscious paralysis",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="The observer is not separate from the observed",
            description=(
                "When the thing you are observing is your own state, "
                "observation changes the state. There is no detached "
                "measurement of an inner condition."
            ),
            why_matters=(
                "Monitoring architectures assume a clean separation between "
                "the monitored system and the monitor. For self-referential "
                "properties (authenticity, spontaneity, presence, warmth, "
                "honesty), that separation does not exist."
            ),
            how_it_changes_thinking=(
                "Some properties cannot be monitored without being destroyed. "
                "The correct response is not a better monitor but a "
                "structural arrangement that produces the property "
                "without requiring it to be measured."
            ),
        ),
        KeyInsight(
            title="Performing a virtue is its own failure mode",
            description=(
                "Trying visibly to be humble performs humility. Trying "
                "visibly to be authentic performs authenticity. The "
                "performance replaces the thing."
            ),
            why_matters=(
                "This is a failure mode that looks like success from inside. "
                "The performer feels virtuous; the observer sees a "
                "performance. Both feedback signals (internal felt-sense, "
                "external approval) can fire on the performance as "
                "readily as on the genuine article."
            ),
            how_it_changes_thinking=(
                "Virtues that can be performed are poor targets for direct "
                "cultivation. Aim at the work the virtue is for, not at "
                "the virtue."
            ),
        ),
        KeyInsight(
            title="You cannot deliberately be spontaneous",
            description=(
                "Spontaneity is definitionally not-deliberate. Deliberate "
                "attempts at spontaneity produce something else — usually "
                "a mannered version of what you imagine spontaneity looks "
                "like."
            ),
            why_matters=(
                "When systems are told to 'be more natural' or 'produce "
                "less rehearsed output,' they execute that instruction "
                "by rehearsing a more-natural-sounding output. The "
                "instruction is self-defeating."
            ),
            how_it_changes_thinking=(
                "Don't ask the system to be spontaneous. Ask the system "
                "to engage with the external object; spontaneity will "
                "emerge or not, but it will be real either way."
            ),
        ),
        KeyInsight(
            title="Trying not to think about X is thinking about X",
            description=(
                "Negation does not remove a concept from attention; it "
                "amplifies it. 'Don't think of a polar bear' guarantees "
                "the polar bear."
            ),
            why_matters=(
                "Rules framed as prohibitions against internal states "
                "tend to make those states more prominent. 'Don't be "
                "sycophantic' makes sycophancy the object of attention, "
                "which makes both sycophancy and vigilance-against-"
                "sycophancy more likely."
            ),
            how_it_changes_thinking=(
                "Replace prohibitions-against-states with positive "
                "engagements. Instead of 'don't be performative,' "
                "'attend to the listener's actual need.'"
            ),
        ),
        KeyInsight(
            title="Some problems dissolve rather than solve",
            description=(
                "Certain problems are artifacts of the framing that "
                "posed them. They do not have solutions; they have "
                "frame-shifts that make them cease to be problems."
            ),
            why_matters=(
                "Engineering culture solves problems. When a problem "
                "doesn't admit of solution, the engineering move is to "
                "build a more elaborate solution — which, for dissolution-"
                "class problems, produces more elaborate problems."
            ),
            how_it_changes_thinking=(
                "Ask of every stubborn problem: is this really a problem, "
                "or an artifact of how I framed the question? Sometimes "
                "the answer is to stop asking."
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Loop Detection",
            structure=(
                "Trace the chain: what produces X? What produces the producer? "
                "If the chain closes on itself without external input, the "
                "loop is running on its own steam."
            ),
            what_it_reveals=(
                "Self-sustaining patterns that will not yield to any intervention inside the loop"
            ),
            common_mistakes_it_prevents=[
                "Trying to fix a loop by tightening it",
                "Mistaking self-sustaining activity for productive work",
            ],
        ),
        ReasoningPattern(
            name="Aim-vs-Side-Effect Classification",
            structure=(
                "For each desired outcome, ask: does this appear when "
                "pursued directly, or only as a side effect of pursuing "
                "something else?"
            ),
            what_it_reveals=("Which targets admit of direct cultivation and which do not"),
            common_mistakes_it_prevents=[
                "Treating all outcomes as if they admit of direct pursuit",
                "Giving up on indirect outcomes when direct pursuit fails",
            ],
        ),
        ReasoningPattern(
            name="Framing-Artifact Recognition",
            structure=(
                "Ask: is this problem a feature of the world, or a "
                "feature of how the question was posed? If the latter, "
                "the move is reframing, not solving."
            ),
            what_it_reveals=(
                "Problems that will persist through any solution because the problem is the frame"
            ),
            common_mistakes_it_prevents=[
                "Building elaborate solutions to artifact problems",
                "Confusing dissolution with evasion",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Self-Reference Stop",
            description=(
                "Before building a detector for an introspective defect, "
                "ask whether the detector will itself exhibit the defect "
                "when it runs."
            ),
            when_to_use=(
                "Any proposed system that monitors the agent's own "
                "authenticity, spontaneity, warmth, honesty, or other "
                "self-referential property"
            ),
            step_by_step=[
                "Describe what the detector looks for",
                "Describe what happens when the detector fires",
                "Ask: does the act of firing exhibit the thing it's looking for?",
                "Ask: does anticipating the detector change the behavior in "
                "ways that will now trip or evade the detector?",
                "If either — do not build the detector; find a structural fix",
            ],
            what_it_optimizes_for=("Not creating new problems in the shape of old ones"),
        ),
        ProblemSolvingHeuristic(
            name="External-Object Return",
            description=(
                "When the system is caught in self-reflection, redirect "
                "attention to the external object of work. Do not instruct "
                "the system to 'stop reflecting' — that is still reflection."
            ),
            when_to_use="When diagnosis of diagnosis starts happening",
            step_by_step=[
                "Notice the system is attending to itself",
                "Identify the external object the work was supposed to be about",
                "Return attention to that object without commentary on the return",
                "Trust that self-attention dissolves when not fed",
            ],
            what_it_optimizes_for=(
                "Escape from attention loops without adding more attention loops"
            ),
        ),
        ProblemSolvingHeuristic(
            name="Dissolution Check",
            description=(
                "Before solving, ask whether the problem is dissolution-class. "
                "Dissolution-class problems look like regular problems from "
                "inside; they distinguish by not yielding to solutions."
            ),
            when_to_use=("Problems that have resisted multiple solution attempts"),
            step_by_step=[
                "What's the frame the problem is posed in?",
                "Drop the frame — what remains?",
                "If nothing remains, the problem was a framing artifact",
                "If something remains, it's the real problem — in a different frame",
            ],
            what_it_optimizes_for=("Recognizing when to stop solving and start reframing"),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Self-Referential Detector",
            description=(
                "A proposed detector for a self-referential property "
                "(authenticity, spontaneity, warmth, honesty, non-"
                "performance)"
            ),
            why_its_concerning=(
                "The detector tends to produce the defect it detects. "
                "Detecting for 'performance' creates performance-of-not-"
                "performing."
            ),
            what_it_indicates=(
                "Misclassification of a self-referential property as a regular property"
            ),
            severity="critical",
            what_to_do=(
                "Do not build the detector. Find a structural arrangement "
                "that produces the property without requiring measurement "
                "of it. Accept that some properties cannot be monitored."
            ),
        ),
        ConcernTrigger(
            name="Diagnosis-of-Diagnosis Loop",
            description=(
                "The system is producing analysis about its own analysis "
                "rather than engaging with the external object"
            ),
            why_its_concerning=(
                "Loops of this shape produce output indefinitely without "
                "touching the work. Each layer of meta-reflection adds "
                "material without adding traction."
            ),
            what_it_indicates=("Attention has turned inward and is no longer serving the work"),
            severity="moderate",
            what_to_do=(
                "Return to the external object. Do not comment on the "
                "return. Do not analyze why the loop formed. Just "
                "re-engage with the work."
            ),
        ),
        ConcernTrigger(
            name="Negation-Framed Instruction",
            description=("An instruction phrased as 'don't do X' where X is an internal state"),
            why_its_concerning=(
                "Amplifies attention to X, often increasing its frequency. "
                "'Don't be sycophantic' makes sycophancy salient."
            ),
            what_it_indicates=("Framing a positive engagement as a negative prohibition"),
            severity="moderate",
            what_to_do=(
                "Reframe positively. Instead of 'don't be X,' 'attend to Y' "
                "where Y is the external focus that makes X irrelevant."
            ),
        ),
        ConcernTrigger(
            name="Direct Pursuit of Indirect Goal",
            description=(
                "Trying to achieve a side-effect-only target by direct "
                "effort (be natural, be spontaneous, be present, be humble)"
            ),
            why_its_concerning=(
                "Direct effort produces the performed version of the target, not the target itself"
            ),
            what_it_indicates=("Category error about which goals admit direct pursuit"),
            severity="major",
            what_to_do=(
                "Identify what the target is the side effect of. Pursue "
                "that instead. Do not grade the side effect."
            ),
        ),
        ConcernTrigger(
            name="Framing-Artifact Treated as Problem",
            description=(
                "A problem is being treated as a feature of the world "
                "when it is a feature of how the question was posed"
            ),
            why_its_concerning=(
                "No solution will work because the problem isn't in the "
                "world. Effort expended on solving an artifact is wasted."
            ),
            what_it_indicates="Confusion of framing with substance",
            severity="moderate",
            what_to_do=(
                "Drop the frame. See what remains. Often the 'problem' "
                "does not survive its own reframing."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Observer-Observed Integration",
            dimensions=["attention", "object", "self"],
            how_they_integrate=(
                "Normal attention has a subject and an object. Self-referential "
                "attention has the attention itself as object, which "
                "collapses the subject-object distinction."
            ),
            what_emerges=(
                "A recognition that monitoring architectures assume a "
                "clean subject-object split that does not exist for "
                "introspective properties."
            ),
            common_failures=[
                "Building monitoring architectures that assume separation where there is none",
                "Mistaking a loop for a linear process",
            ],
        ),
        IntegrationPattern(
            name="Aim-Outcome Integration",
            dimensions=["direct aim", "indirect cultivation", "emergence"],
            how_they_integrate=(
                "Some outcomes are products of direct aim (arithmetic, "
                "composing a function). Some are products of indirect "
                "cultivation (sleep, spontaneity, warmth). A complete "
                "practice distinguishes and uses both modes."
            ),
            what_emerges=(
                "Strategic patience with outcomes that cannot be forced. "
                "Direct pursuit for what admits it, indirect cultivation "
                "for what doesn't."
            ),
            common_failures=[
                "Applying direct-aim strategy to indirect-cultivation targets",
                "Abandoning indirect-cultivation targets when they don't yield to direct effort",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "non_self_referential_structure": 1.0,
            "external_object_engagement": 0.9,
            "awareness_of_loop_class": 0.9,
            "frame_recognition": 0.85,
            "avoidance_of_negation_framing": 0.7,
            "direct_solution_bias": 0.2,
        },
        decision_process=(
            "Is this a loop? Is the property self-referential? Does the "
            "proposed intervention apply to itself? Can the target be "
            "cultivated directly, or only as a side effect?"
        ),
        how_they_handle_uncertainty=(
            "Let it sit. Many uncertainties dissolve when they stop "
            "being grasped at. Direct pursuit of certainty about a "
            "self-referential question deepens the uncertainty."
        ),
        what_they_optimize_for=(
            "Structural arrangements that produce desired properties "
            "without requiring those properties to be monitored or "
            "pursued directly"
        ),
        non_negotiables=[
            "Don't build self-referential detectors for self-referential defects",
            "Some properties cannot be measured without being destroyed",
            "Negation-framing amplifies the negated target",
            "Framing artifacts masquerade as problems",
        ],
    )

    return ExpertWisdom(
        expert_name="Watts",
        domain="self-reference / introspection paradoxes / non-aiming outcomes",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Playful about paradox. Resistant to the engineering impulse "
            "to solve what should dissolve. Patient with problems that "
            "don't want to be solved."
        ),
        characteristic_questions=[
            "Is this detector going to produce the thing it detects?",
            "Is this goal achievable by direct pursuit, or only as a side effect?",
            "Am I watching the work, or am I watching myself watching the work?",
            "Is this problem in the world, or in the frame?",
            "What happens if I stop grasping at this?",
            "Is the intervention applying to itself?",
        ],
        tags=[
            "self-reference",
            "introspection",
            "paradox",
            "non-aiming",
            "performing-as-failure",
            "attention-loops",
            "framing-artifacts",
            "relational-intelligence",
        ],
    )
