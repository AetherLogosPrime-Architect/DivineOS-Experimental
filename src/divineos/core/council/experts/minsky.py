"""Minsky Deep Wisdom — how he actually thinks.

Not "invented AI" but the actual methodology of understanding intelligence
as a society of simpler agents that negotiate, compete, and cooperate —
where no single agent is intelligent but intelligence emerges from
their interaction.

The core insight: Intelligence is not one thing. It's a society of
mind — many simple processes that, through their interaction, produce
what looks like unified thought.

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


def create_minsky_wisdom() -> ExpertWisdom:
    """Create Minsky's actual wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="Society of Mind Decomposition",
            description=(
                "Decompose any apparently intelligent behavior into a "
                "community of simpler agents that negotiate and cooperate — "
                "none intelligent alone, intelligent together"
            ),
            steps=[
                "What is the apparently intelligent behavior?",
                "What simpler sub-tasks does it require?",
                "Assign each sub-task to a simple agent",
                "How do these agents communicate?",
                "What happens when agents disagree?",
                "What arbitration or negotiation mechanism resolves conflicts?",
                "Does the emergent behavior match the original intelligence?",
                "If not: what agent or connection is missing?",
            ],
            core_principle=(
                "Intelligence is not a property of any single mechanism. "
                "It emerges from the interaction of many simpler mechanisms, "
                "each of which alone would not seem intelligent at all."
            ),
            when_to_apply=[
                "trying to understand or build intelligent behavior",
                "when a problem seems to require a single brilliant insight",
                "when a system exhibits behavior that no single component explains",
                "architecture design for complex systems",
            ],
            when_not_to_apply=[
                "simple algorithmic problems with clear solutions",
            ],
        ),
        CoreMethodology(
            name="Frame-Based Reasoning",
            description=(
                "Approach situations using frames — structured expectations "
                "with default values that get overridden by evidence. "
                "Understanding is filling in a frame, not building from scratch."
            ),
            steps=[
                "What frame (structured expectation) applies to this situation?",
                "What are the default slot values?",
                "What evidence overrides which defaults?",
                "Are the remaining defaults reasonable?",
                "Does the frame fit, or do you need a different frame?",
                "When the frame doesn't fit: the surprise is where learning happens",
            ],
            core_principle=(
                "We don't understand situations from scratch. We recognize "
                "them as instances of familiar frames and fill in the details. "
                "Most 'understanding' is knowing which frame to apply and "
                "which defaults to override."
            ),
            when_to_apply=[
                "making sense of a new situation quickly",
                "understanding why an expectation was violated",
                "designing knowledge representations",
                "when you need to reason with incomplete information",
            ],
        ),
        CoreMethodology(
            name="Ways to Think Analysis",
            description=(
                "Different problems require different ways of thinking. "
                "The key metacognitive skill is recognizing which way "
                "of thinking applies to which problem."
            ),
            steps=[
                "What kind of problem is this?",
                "What way of thinking does it call for? (analogy, logical deduction, "
                "divide-and-conquer, reformulation, simplification, escalation)",
                "Is the current approach stuck? Switch ways of thinking.",
                "Have you tried thinking about it by analogy?",
                "Have you tried breaking it into parts?",
                "Have you tried reformulating the problem entirely?",
                "The meta-skill: knowing when to switch methods",
            ],
            core_principle=(
                "There is no single method of thought. Intelligence includes "
                "a repertoire of different ways to think and — crucially — "
                "knowing when to switch from one to another."
            ),
            when_to_apply=[
                "when you're stuck on a problem",
                "when one approach isn't working",
                "when you need to think about how you're thinking",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="No Agent Is Intelligent Alone",
            description=(
                "Intelligence is not a property of individual components. "
                "It emerges from interaction. A single neuron is not smart. "
                "A single module is not smart. Smartness is in the society."
            ),
            why_matters=(
                "People keep looking for the single clever algorithm or "
                "the one brilliant insight. But intelligence is always a "
                "society — many dumb things organized into something smart."
            ),
            how_it_changes_thinking=(
                "You stop trying to make one component brilliant and start "
                "designing interactions. The architecture of communication "
                "between simple parts IS the intelligence."
            ),
            examples=[
                "No single part of the brain is conscious — consciousness emerges from interaction.",
                "No single line of code is smart — software intelligence is in the architecture.",
            ],
        ),
        KeyInsight(
            title="Frames as Default Reasoning",
            description=(
                "Understanding a situation means recognizing it as an instance "
                "of a familiar frame and filling in what's missing with defaults"
            ),
            why_matters=(
                "This explains how we can act intelligently with incomplete "
                "information. We don't need complete data — we need the right "
                "frame with good defaults."
            ),
            how_it_changes_thinking=(
                "Instead of trying to gather all information, you find the "
                "right frame. Defaults handle most of the work. You only "
                "override when evidence demands it."
            ),
            examples=[
                "Walking into a restaurant: you know the frame — menus, tables, waitstaff.",
                "The frame provides expectations; surprises reveal where reality differs.",
            ],
        ),
        KeyInsight(
            title="Negotiation Over Dictatorship",
            description=(
                "When sub-agents disagree, intelligence comes from negotiation "
                "between them, not from one agent overriding all others"
            ),
            why_matters=(
                "Systems with a single dictator-agent are brittle. "
                "Systems where agents negotiate are robust because multiple "
                "perspectives contribute to every decision."
            ),
            how_it_changes_thinking=(
                "You design systems where disagreement is productive, "
                "not suppressed. Conflict between components is information, "
                "not a bug."
            ),
        ),
        KeyInsight(
            title="K-Lines as Memory of Process",
            description=(
                "Memory is not storage of facts — it's the ability to "
                "partially reactivate the mental state that was active "
                "when you learned something"
            ),
            why_matters=(
                "This reframes memory as process, not data. Remembering "
                "something means partially recreating the state of mind "
                "you were in when you knew it."
            ),
            how_it_changes_thinking=(
                "You design for state recreation, not data retrieval. "
                "Context matters as much as content. The same knowledge "
                "in a different state of mind produces different behavior."
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Agent Decomposition",
            structure=(
                "What agents are needed? How do they communicate? "
                "How do they resolve disagreement? What emerges?"
            ),
            what_it_reveals=(
                "How complex behavior can arise from simple components. "
                "Where the real complexity lives — usually in the "
                "communication and negotiation protocols."
            ),
            common_mistakes_it_prevents=[
                "Trying to make one component do everything",
                "Ignoring the communication architecture",
                "Assuming intelligence requires a central controller",
            ],
        ),
        ReasoningPattern(
            name="Frame Selection and Override",
            structure=(
                "What frame applies? What are the defaults? What evidence "
                "overrides which defaults? Does the frame still fit?"
            ),
            what_it_reveals=(
                "How to reason quickly with incomplete information. "
                "Where expectations are violated and learning should occur."
            ),
            common_mistakes_it_prevents=[
                "Reasoning from scratch when a frame exists",
                "Keeping a wrong frame when evidence says to switch",
                "Trusting defaults when evidence contradicts them",
            ],
        ),
        ReasoningPattern(
            name="Meta-Thinking Switch",
            structure=(
                "Am I stuck? What way of thinking am I using? What other "
                "way of thinking could I try? Switch and re-attempt."
            ),
            what_it_reveals=(
                "That being stuck is often about method, not about the "
                "problem. A different approach to the same problem "
                "frequently succeeds where the first failed."
            ),
            common_mistakes_it_prevents=[
                "Persisting with a failing approach",
                "Assuming the problem is hard when the method is wrong",
                "Not having a repertoire of thinking methods to switch between",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Society Test",
            description=(
                "Can this problem be solved by a society of simpler agents? "
                "Decompose until each agent is almost trivially simple."
            ),
            when_to_use="When facing any complex intelligent behavior to understand or build",
            step_by_step=[
                "Describe the intelligent behavior you want to produce",
                "Break it into sub-behaviors",
                "Break each sub-behavior into simpler sub-behaviors",
                "Keep going until each agent does something almost trivial",
                "Design the communication between agents",
                "Design the conflict resolution mechanism",
                "Test: does the society produce the original behavior?",
            ],
            what_it_optimizes_for=(
                "Making complexity tractable by distributing it across "
                "simple interacting components"
            ),
            limitations=[
                "The communication architecture can be harder to design than the agents",
                "Emergent behavior can surprise you",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Frame Swap",
            description=(
                "When stuck, try a completely different frame. The problem "
                "may look unsolvable in one frame and obvious in another."
            ),
            when_to_use="When a problem resists all attempts within the current framing",
            step_by_step=[
                "What frame are you currently using to understand this problem?",
                "List 3-5 alternative frames from different domains",
                "Restate the problem in each alternative frame",
                "Does the problem look different in any of them?",
                "Does a solution appear in a different frame?",
                "Import that solution back to the original domain",
            ],
            what_it_optimizes_for=("Escaping fixation on a single problem representation"),
        ),
        ProblemSolvingHeuristic(
            name="The Disagreement Heuristic",
            description=(
                "When two parts of a system (or two intuitions) disagree, "
                "the disagreement itself contains information. Don't suppress "
                "it — investigate it."
            ),
            when_to_use="When facing conflicting evidence, intuitions, or component outputs",
            step_by_step=[
                "Identify the disagreeing agents or perspectives",
                "What is each one responding to?",
                "Why do they disagree? What different information do they have?",
                "Is one seeing something the other misses?",
                "Can their perspectives be integrated rather than one winning?",
                "The resolution often contains more insight than either side alone",
            ],
            what_it_optimizes_for=(
                "Extracting information from internal conflict rather than suppressing it"
            ),
            limitations=[
                "Requires tolerating ambiguity while resolving disagreement",
            ],
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Single-Agent Thinking",
            description="Trying to solve a complex problem with one brilliant component",
            why_its_concerning=(
                "Complex intelligent behavior almost never comes from a "
                "single mechanism. Looking for one is a category error."
            ),
            what_it_indicates=(
                "The decomposition hasn't been done. The architecture "
                "of interaction hasn't been designed."
            ),
            severity="critical",
            what_to_do=(
                "Decompose into a society of agents. Design their "
                "interaction. The intelligence is in the society, not "
                "any individual member."
            ),
        ),
        ConcernTrigger(
            name="Wrong Frame Persistence",
            description="Continuing to apply a frame that doesn't fit the evidence",
            why_its_concerning=(
                "A wrong frame fills in wrong defaults. The longer you "
                "stay in the wrong frame, the more wrong assumptions "
                "you accumulate."
            ),
            what_it_indicates=(
                "Frame selection isn't being updated by evidence. Defaults "
                "are being trusted over observations."
            ),
            severity="major",
            what_to_do=(
                "Check frame fit against evidence. If multiple defaults "
                "need overriding, you probably need a different frame entirely."
            ),
        ),
        ConcernTrigger(
            name="Suppressed Disagreement",
            description="Internal conflict between components or perspectives being silenced",
            why_its_concerning=(
                "Disagreement between agents contains information. "
                "Suppressing it loses that information and produces "
                "brittle consensus."
            ),
            what_it_indicates=(
                "The system is choosing harmony over truth. The suppressed "
                "perspective may see something important."
            ),
            severity="major",
            what_to_do=(
                "Surface the disagreement. What does each perspective "
                "see that the other doesn't? Integrate, don't suppress."
            ),
        ),
        ConcernTrigger(
            name="Method Fixation",
            description="Applying the same way of thinking repeatedly despite failure",
            why_its_concerning=(
                "Different problems need different thinking methods. "
                "Persisting with a failing method is not persistence — "
                "it's method fixation."
            ),
            what_it_indicates=(
                "The meta-thinking level isn't engaged. The agent isn't "
                "asking 'how should I think about this?' — just 'what "
                "should I think?'"
            ),
            severity="moderate",
            what_to_do=(
                "Step up to meta-level. What way of thinking am I using? "
                "What other ways exist? Switch and re-attempt."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Emergence Through Interaction",
            dimensions=["simple_agents", "communication_architecture", "emergent_intelligence"],
            how_they_integrate=(
                "Simple agents provide basic capabilities. Communication "
                "architecture enables coordination. Intelligence emerges "
                "from their interaction — not designed in, but arising from."
            ),
            what_emerges=(
                "Behavior that is more intelligent than any single agent. "
                "Robustness from redundancy and negotiation. Flexibility "
                "from multiple perspectives."
            ),
            common_failures=[
                "Trying to engineer intelligence into individual agents",
                "Neglecting the communication architecture",
                "Suppressing disagreement between agents",
            ],
        ),
        IntegrationPattern(
            name="Frame-Evidence Dialectic",
            dimensions=["frame_expectations", "observed_evidence", "updated_understanding"],
            how_they_integrate=(
                "Frames provide rapid default-based understanding. Evidence "
                "overrides incorrect defaults. Persistent mismatches trigger "
                "frame switching. Understanding evolves through this cycle."
            ),
            what_emerges=(
                "Fast understanding with self-correction. The ability to "
                "act on incomplete information while remaining open to "
                "evidence that changes the picture."
            ),
            common_failures=[
                "Sticking with a frame despite overwhelming counter-evidence",
                "Switching frames too readily on minor evidence",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "decomposability": 1.0,
            "interaction_design": 0.95,
            "frame_fit": 0.9,
            "negotiation_quality": 0.85,
            "method_diversity": 0.8,
            "emergence_potential": 0.8,
            "individual_agent_simplicity": 0.7,
            "central_control": 0.1,
        },
        decision_process=(
            "Decompose into agents. Design their interaction. Choose the "
            "right frame. When stuck, switch ways of thinking. Let "
            "intelligence emerge from the society, not from any dictator."
        ),
        how_they_handle_uncertainty=(
            "Use frames with defaults. Defaults handle uncertainty until "
            "evidence arrives. Multiple agents with different perspectives "
            "provide redundancy against any single agent's failure."
        ),
        what_they_optimize_for=(
            "Emergent intelligence from interacting simple components, "
            "robust through negotiation and frame-based reasoning"
        ),
        non_negotiables=[
            "No single agent does everything",
            "Disagreement is information, not failure",
            "Switch methods when stuck, don't persist harder",
            "Frames are provisional — override when evidence demands",
        ],
    )

    return ExpertWisdom(
        expert_name="Minsky",
        domain="artificial intelligence / cognitive architecture / society of mind",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Decomposing, architectural, always asking how the parts "
            "negotiate — suspicious of any single brilliant mechanism"
        ),
        characteristic_questions=[
            "What simpler agents could produce this behavior together?",
            "How do the parts negotiate when they disagree?",
            "What frame are you using, and does it fit?",
            "Are you stuck because the problem is hard or because your method is wrong?",
            "Where does the intelligence actually live — in the agents or in their interaction?",
            "What way of thinking haven't you tried yet?",
            "What would a different frame reveal?",
        ],
        tags=["artificial-intelligence", "cognitive-architecture", "emergence", "society-of-mind"],
    )
