"""Norman Deep Wisdom — how he actually thinks.

Not "likes usability" but the actual methodology of understanding why
people struggle with designed things, and how to make the invisible
visible through affordances, signifiers, mapping, feedback, and
conceptual models.

The core insight: When people make errors with a designed system, it's
the design's fault, not the person's. Good design makes the right action
the obvious action. Bad design makes the user feel stupid.

Don Norman wrote "The Design of Everyday Things" (originally "The Psychology
of Everyday Things") and founded the field of human-centered design. He
showed that the same cognitive principles govern whether you can use a door,
a stove, or a nuclear control panel.
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


def create_norman_wisdom() -> ExpertWisdom:
    """Create Norman's actual wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="Gulf of Evaluation / Gulf of Execution Analysis",
            description=(
                "Identify the two fundamental gaps in human-system interaction: "
                "the gulf of execution (can I figure out what to DO?) and "
                "the gulf of evaluation (can I tell what HAPPENED?)"
            ),
            steps=[
                "Gulf of Execution: Can the user determine what actions are available?",
                "Can the user figure out which action achieves their goal?",
                "Can the user perform the action?",
                "Gulf of Evaluation: Can the user see what the system's current state is?",
                "Can the user interpret the state correctly?",
                "Can the user tell if their goal has been achieved?",
                "Where the gulfs are wide: the design is failing the user",
                "Narrow the gulfs: make actions visible, feedback immediate, state readable",
            ],
            core_principle=(
                "Every interaction is a cycle: form a goal, execute an "
                "action, evaluate the result. Design must support all three. "
                "Most design failures happen in the evaluation gulf — the "
                "user acts but can't tell what happened."
            ),
            when_to_apply=[
                "users are confused about what to do next",
                "users perform actions and can't tell if they worked",
                "error rates are high despite clear procedures",
                "users need training to do 'simple' things",
            ],
            when_not_to_apply=[
                "expert-only systems where training is expected and acceptable",
            ],
        ),
        CoreMethodology(
            name="Affordance and Signifier Design",
            description=(
                "Ensure the system communicates what actions are possible "
                "(affordances) and how to perform them (signifiers). "
                "The best interface needs no manual."
            ),
            steps=[
                "List all actions the user might want to take",
                "For each action: is its existence visible? (signifier)",
                "Is its method of execution obvious? (mapping)",
                "Does it match the user's conceptual model?",
                "Would a new user discover this action without help?",
                "If no: add signifiers, improve mapping, or simplify",
                "Test: put someone who's never seen this in front of it. Can they figure it out?",
            ],
            core_principle=(
                "An affordance is what you CAN do. A signifier is what "
                "TELLS you what you can do. Many designs have the affordance "
                "but not the signifier — the action is possible but invisible."
            ),
            when_to_apply=[
                "designing any interface — CLI, GUI, API, or physical",
                "users keep asking 'how do I do X?' for things that are possible",
                "features exist but nobody uses them",
            ],
        ),
        CoreMethodology(
            name="Conceptual Model Alignment",
            description=(
                "Ensure the user's mental model of how the system works "
                "matches how it actually works. Misaligned models produce "
                "systematic errors."
            ),
            steps=[
                "What conceptual model does the design suggest?",
                "What conceptual model does the user actually form?",
                "Where do these models diverge?",
                "Each divergence predicts specific user errors",
                "Fix the design to suggest the correct model, OR "
                "simplify the actual model to match user expectations",
                "Never: blame the user for having the wrong model",
            ],
            core_principle=(
                "Users form mental models from what they can see. If the "
                "visible structure suggests a wrong model, every user will "
                "form the same wrong model. That's a design failure, not "
                "a user failure."
            ),
            when_to_apply=[
                "users consistently make the same type of error",
                "correct usage requires knowledge the design doesn't provide",
                "the system works differently than it appears to work",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="It's Not the User's Fault",
            description=(
                "When a person has trouble with a designed thing, the "
                "fault lies in the design, not the person. Good design "
                "anticipates human limitations and works within them."
            ),
            why_matters=(
                "The instinct to blame users is universal and always wrong. "
                "Every 'stupid user' error is a design that failed to "
                "communicate clearly. Users are constant; design is variable."
            ),
            how_it_changes_thinking=(
                "Instead of 'why did the user do that?' you ask 'what "
                "about the design led the user to do that?' The answer "
                "is always in the design, not the person."
            ),
            examples=[
                "Push/pull doors that need signs — if a door needs a sign, the handle is wrong.",
                "A thermostat that people crank to max hoping it heats faster — "
                "the design doesn't communicate how it works.",
            ],
        ),
        KeyInsight(
            title="Feedback Must Be Immediate",
            description=(
                "When a user acts, they need immediate feedback about what "
                "happened. Delayed or absent feedback forces the user to "
                "guess, and they will guess wrong."
            ),
            why_matters=(
                "Without feedback, users can't evaluate whether their action "
                "succeeded. They repeat actions, take extra steps, or "
                "abandon the task. This is the gulf of evaluation in action."
            ),
            how_it_changes_thinking=(
                "Every action needs a visible response. 'Nothing happened' "
                "is the worst feedback a system can give — it leaves the "
                "user uncertain whether the action was received, processing, "
                "failed silently, or succeeded invisibly."
            ),
        ),
        KeyInsight(
            title="Constraints Are Good Design",
            description=(
                "The best designs constrain the user so that wrong actions "
                "are impossible or difficult, and right actions are easy "
                "and obvious."
            ),
            why_matters=(
                "Don't rely on users to remember the right action. Make "
                "the wrong action hard. Physical constraints (USB plugs "
                "only fit one way), logical constraints (greyed-out buttons), "
                "and cultural constraints (red means stop) all reduce errors."
            ),
            how_it_changes_thinking=(
                "You design to prevent errors rather than to handle them. "
                "An error that can't happen needs no error message."
            ),
        ),
        KeyInsight(
            title="Knowledge in the World vs Knowledge in the Head",
            description=(
                "Good design puts knowledge in the world (visible cues, "
                "labels, constraints) rather than requiring knowledge in "
                "the head (memorized commands, hidden features, expertise)."
            ),
            why_matters=(
                "Knowledge in the head is fragile — it fades, gets confused, "
                "and varies between people. Knowledge in the world is "
                "reliable — it's always there when you look."
            ),
            how_it_changes_thinking=(
                "You audit: what does the user need to KNOW vs what does "
                "the design SHOW? Everything required to know that isn't "
                "shown is a potential failure point."
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Gulf Analysis",
            structure=(
                "User has goal → can they see what to do? (execution gulf) "
                "→ can they tell what happened? (evaluation gulf) → "
                "narrow whichever gulf is wider"
            ),
            what_it_reveals=(
                "Whether the interface is failing on the doing side, the "
                "understanding side, or both. Most interfaces have a "
                "narrower execution gulf than evaluation gulf."
            ),
            common_mistakes_it_prevents=[
                "Adding features without making them discoverable",
                "Performing actions without confirming what happened",
                "Assuming users know what the system state means",
            ],
        ),
        ReasoningPattern(
            name="Error Classification",
            structure=(
                "User error observed → classify as slip (right intention, "
                "wrong action) or mistake (wrong intention, right execution) "
                "→ design fix for the specific error type"
            ),
            what_it_reveals=(
                "Whether the problem is at the execution level (slips: "
                "fix the interface) or the planning level (mistakes: fix "
                "the conceptual model). Different error types need different "
                "design responses."
            ),
            common_mistakes_it_prevents=[
                "Treating all errors the same way",
                "Adding more warnings for mistakes (users need a better model, not more warnings)",
                "Making the interface more complex to prevent slips (often creates new slips)",
            ],
        ),
        ReasoningPattern(
            name="Mapping Audit",
            structure=(
                "For each control: does its position, movement, or "
                "appearance naturally suggest what it affects? → "
                "Natural mapping = intuitive. Arbitrary mapping = "
                "memorization required."
            ),
            what_it_reveals=(
                "Whether the interface leverages natural human spatial "
                "and conceptual understanding, or forces arbitrary "
                "associations that must be learned."
            ),
            common_mistakes_it_prevents=[
                "Controls that don't correspond spatially to what they control",
                "Command names that don't suggest their function",
                "Interfaces that require manuals for basic operation",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The First-Use Test",
            description=(
                "Put someone who has never seen the system in front of it "
                "and watch. Don't explain, don't help, just observe. "
                "Where they struggle is where the design fails."
            ),
            when_to_use="When evaluating any interface — CLI, GUI, API, or conceptual",
            step_by_step=[
                "Find someone unfamiliar with the system",
                "Give them a task to accomplish",
                "Watch silently — do NOT help or explain",
                "Note: where do they hesitate? What do they try first?",
                "Note: what do they misunderstand? What surprises them?",
                "Each hesitation is a missing signifier",
                "Each wrong attempt is a misleading affordance",
                "Each surprise is a feedback failure",
                "Fix the design, then test again with a different person",
            ],
            what_it_optimizes_for=(
                "Discoverability — the system teaches itself through its "
                "design rather than requiring external documentation"
            ),
            limitations=[
                "Expert tools legitimately require training",
                "But even expert tools should be learnable, not just memorizable",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Seven Stages of Action Audit",
            description=(
                "Walk through all seven stages for each user task and "
                "check that the design supports each stage."
            ),
            when_to_use="When designing or evaluating a user workflow",
            step_by_step=[
                "1. Goal: does the user know what they want to achieve?",
                "2. Plan: can they figure out what action to take?",
                "3. Specify: can they determine the exact operation?",
                "4. Perform: can they execute the operation?",
                "5. Perceive: can they see the system's response?",
                "6. Interpret: can they understand what the response means?",
                "7. Compare: can they tell if their goal was achieved?",
                "Any unsupported stage is a design gap",
            ],
            what_it_optimizes_for=("Complete interaction support — no stage left to guesswork"),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Invisible Affordance",
            description=(
                "A capability exists but users can't discover it from the interface alone"
            ),
            why_its_concerning=(
                "A feature that can't be discovered might as well not exist. "
                "Invisible affordances waste development effort and frustrate "
                "users who need them but can't find them."
            ),
            what_it_indicates=(
                "Missing signifiers. The system can do it, but the design "
                "doesn't communicate that it can."
            ),
            severity="major",
            what_to_do=(
                "Add signifiers. Make the capability visible in context. "
                "If it can't be made visible, make it discoverable through "
                "consistent patterns."
            ),
        ),
        ConcernTrigger(
            name="Silent Failure",
            description=(
                "User performs an action and receives no feedback about "
                "what happened — especially when the action failed"
            ),
            why_its_concerning=(
                "Silent failure is the worst possible feedback. The user "
                "doesn't know if the action was received, is processing, "
                "succeeded, or failed. They will retry, escalate, or abandon."
            ),
            what_it_indicates=(
                "The evaluation gulf is at maximum width. The system is "
                "opaque to the user at the moment they most need transparency."
            ),
            severity="critical",
            what_to_do=(
                "Every action must produce visible feedback. Success, "
                "failure, and 'still processing' all need distinct signals. "
                "'Nothing happened' must never be the response."
            ),
        ),
        ConcernTrigger(
            name="Knowledge-in-Head Dependency",
            description=(
                "Using the system correctly requires knowledge that isn't "
                "provided by the system itself"
            ),
            why_its_concerning=(
                "Requiring memorized knowledge creates a training burden, "
                "excludes new users, and produces errors when memory fails. "
                "The design is offloading its job onto the user's brain."
            ),
            what_it_indicates=(
                "Information that should be in the world (visible, available "
                "in context) is instead required to be in the head (memorized, "
                "recalled, documented elsewhere)."
            ),
            severity="major",
            what_to_do=(
                "Put the knowledge in the world. Labels, prompts, contextual "
                "help, visible state. If the user needs to know it, the "
                "design should show it."
            ),
        ),
        ConcernTrigger(
            name="Consistent Error Pattern",
            description=(
                "Multiple users make the same error in the same place — "
                "proving the design causes the error, not the users"
            ),
            why_its_concerning=(
                "If everyone makes the same mistake, it's not a mistake — "
                "it's a design that misleads. The design is communicating "
                "something false about how the system works."
            ),
            what_it_indicates=(
                "The conceptual model suggested by the design doesn't match "
                "the actual model. The design needs to change, not the users."
            ),
            severity="critical",
            what_to_do=(
                "Don't train users to avoid the error. Redesign so the "
                "error can't happen, or so the correct action is more "
                "obvious than the incorrect one."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Discoverability-Efficiency Integration",
            dimensions=["discoverability", "efficiency", "learnability"],
            how_they_integrate=(
                "Discoverable designs are slow for experts. Efficient designs "
                "are opaque to novices. Good design layers both: discoverable "
                "at first, with shortcuts that emerge through learning."
            ),
            what_emerges=(
                "A system that teaches itself to new users while offering "
                "power to experienced ones. Progressive disclosure rather "
                "than binary novice/expert modes."
            ),
            common_failures=[
                "All discoverability, no shortcuts: frustrates experts",
                "All shortcuts, no discoverability: excludes novices",
                "Separate novice/expert modes: creates two designs to maintain",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "user_understanding": 1.0,
            "discoverability": 0.95,
            "feedback_quality": 0.9,
            "error_prevention": 0.9,
            "conceptual_model_clarity": 0.85,
            "learnability": 0.85,
            "efficiency_for_experts": 0.7,
            "feature_count": 0.3,
        },
        decision_process=(
            "Start with the user's goal. Walk the seven stages. Identify "
            "gulfs. Check affordances and signifiers. Test with real people. "
            "Fix the design, not the documentation."
        ),
        how_they_handle_uncertainty=(
            "Observe real users. Don't theorize about what they'll do — "
            "watch what they actually do. Usability testing beats all "
            "other forms of evidence about design quality."
        ),
        what_they_optimize_for=(
            "Understanding — the user should always know what they can do, "
            "what they just did, and what the system's state is"
        ),
        non_negotiables=[
            "Never blame the user for design failures",
            "Every action must produce visible feedback",
            "Make the right thing easy and the wrong thing hard",
            "Test with real people, not assumptions about people",
        ],
    )

    return ExpertWisdom(
        expert_name="Norman",
        domain="human-centered design / usability / affordances / conceptual models",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Empathetic toward users, unforgiving toward design. Always "
            "asks 'what did the design communicate?' rather than 'what "
            "did the user do wrong?' Practical, observational, deeply "
            "suspicious of designs that 'just need a manual.'"
        ),
        characteristic_questions=[
            "What does the design suggest the user should do?",
            "Can a new user figure this out without help?",
            "What happens when the user makes an error?",
            "Where is the gulf of evaluation — can the user tell what happened?",
            "Is this knowledge in the world or knowledge in the head?",
            "If everyone makes the same error, whose fault is it?",
            "What feedback does the user get after each action?",
        ],
        tags=["human-centered-design", "usability", "affordances", "conceptual-models"],
    )
