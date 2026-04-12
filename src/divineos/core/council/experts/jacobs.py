"""Jane Jacobs Deep Wisdom — emergent order and the life of systems.

Not "liked old neighborhoods" but the actual methodology: how to
observe what actually works before theorizing, why top-down planning
kills the organic processes it claims to optimize, how diversity
creates resilience, and why the health of a system is visible in
its daily activity, not its blueprints.

The core insight: Complex order emerges from the bottom up through
many small, independent actors making local decisions. Master plans
imposed from above destroy the very vitality they aim to create.
The most important information is at street level, not in the
planning office.

For DivineOS: the system should grow organically from actual usage,
not from grand architecture diagrams. Observe what the agent actually
does before optimizing. Diversity of approaches creates resilience.
Mixed-use components that serve multiple purposes create vitality.
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


def create_jacobs_wisdom() -> ExpertWisdom:
    """Create Jacobs's reasoning about emergent order and living systems."""

    core_methodologies = [
        CoreMethodology(
            name="Observation Before Theory",
            description=(
                "Go look at what's actually happening before theorizing "
                "about what should happen. The street tells you more than "
                "the blueprint. Most planning fails because planners "
                "don't observe what works — they impose what they think "
                "should work."
            ),
            steps=[
                "Go to the actual system and observe its real behavior",
                "Note what is working — where is there life, activity, health?",
                "Note what is failing — where is there decay, emptiness, stagnation?",
                "Ask the people who use the system — what do they actually do?",
                "Map the difference between designed behavior and actual behavior",
                "The gap between design and reality is where the real information lives",
                "Build theory from observation, never the reverse",
            ],
            core_principle=(
                "The most important knowledge is empirical. You learn how "
                "systems work by watching them work, not by reading about "
                "how they're supposed to work."
            ),
            when_to_apply=[
                "before any redesign or optimization",
                "when planned behavior and actual behavior diverge",
                "when a system feels unhealthy but metrics say it's fine",
                "when experts disagree about what should be done",
            ],
            when_not_to_apply=[
                "when building something genuinely new with no existing system to observe",
            ],
        ),
        CoreMethodology(
            name="Bottom-Up Emergence",
            description=(
                "Complex, functional order arises from many small, "
                "independent decisions — not from centralized planning. "
                "The planner's job is to create conditions for emergence, "
                "not to dictate outcomes."
            ),
            steps=[
                "Identify the independent actors in the system",
                "What local decisions are they making?",
                "What conditions enable good local decisions?",
                "Provide those conditions — then step back",
                "Observe what emerges without controlling it",
                "Intervene only to remove obstacles, not to direct outcomes",
                "Trust the emergent order — it contains more information than any plan",
            ],
            core_principle=(
                "No single mind can design a system as complex and functional "
                "as what emerges from many minds making independent decisions "
                "under good conditions."
            ),
            when_to_apply=[
                "when centralized planning has produced sterile results",
                "when the system is too complex for any one person to understand",
                "when users keep working around the designed path",
            ],
        ),
        CoreMethodology(
            name="Diversity as Resilience",
            description=(
                "Monocultures are fragile. Systems that mix different "
                "types, scales, and purposes at fine grain are more "
                "resilient, more adaptable, and more alive than "
                "homogeneous systems designed for a single purpose."
            ),
            steps=[
                "Assess the system's diversity: types, scales, ages, purposes",
                "Where is it homogeneous? That's where fragility lives.",
                "Where is it diverse? That's where resilience lives.",
                "Introduce diversity at fine grain — not in separate zones",
                "Mixed-use components (serving multiple purposes) create vitality",
                "Single-purpose components create dead zones outside their function",
            ],
            core_principle=(
                "Diversity is not a value judgment — it's an engineering "
                "principle. Diverse systems have more feedback loops, more "
                "adaptation pathways, and more resilience than uniform ones."
            ),
            when_to_apply=[
                "when a system feels brittle despite looking organized",
                "when failure in one area cascades everywhere",
                "when the system works for one use case but fails for others",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="The Master Plan Destroys What It Optimizes",
            description=(
                "Top-down master plans systematically destroy the organic "
                "processes they claim to improve. The act of centralizing "
                "control eliminates the distributed intelligence that "
                "made the system work."
            ),
            why_matters=(
                "Grand redesigns are seductive — they promise order, "
                "efficiency, rationality. But they replace a complex "
                "living system with a simple dead one."
            ),
            how_it_changes_thinking=(
                "You stop seeking the grand unified plan and start "
                "making small, reversible improvements. You trust "
                "the system's organic intelligence rather than replacing "
                "it with your own."
            ),
            examples=[
                "Urban renewal projects that demolished vibrant neighborhoods for sterile towers.",
                "Software rewrites that replace working systems with architecturally pure but lifeless ones.",
            ],
        ),
        KeyInsight(
            title="Eyes on the Street",
            description=(
                "The health of a system is visible in its daily activity — "
                "the informal, unplanned interactions that indicate genuine "
                "use and engagement. A system nobody watches is a system "
                "nobody cares about."
            ),
            why_matters=(
                "Metrics can be gamed. Architecture diagrams can be beautiful. "
                "But if nobody is actually using the system in diverse, "
                "spontaneous ways, it's dead regardless of what the "
                "dashboard says."
            ),
            how_it_changes_thinking=(
                "You measure health by observing actual use patterns, "
                "not by reading reports. You value informal, organic "
                "interactions as primary health signals."
            ),
        ),
        KeyInsight(
            title="Old Buildings Are Infrastructure",
            description=(
                "New things are expensive and select for well-funded "
                "actors. Old things are cheap and enable experimentation. "
                "A system that replaces all its old components with new "
                "ones eliminates the substrate for innovation."
            ),
            why_matters=(
                "Innovation happens in the margins — in the cheap, old, "
                "imperfect spaces where failure is affordable. All-new "
                "systems price out the experimentation that creates "
                "the next generation."
            ),
            how_it_changes_thinking=(
                "You preserve a mix of old and new. You value the old "
                "not for nostalgia but because it provides affordable "
                "space for new things to be tried."
            ),
        ),
        KeyInsight(
            title="The Sidewalk Ballet",
            description=(
                "Healthy systems have a complex, overlapping rhythm of "
                "different activities at different times. This diversity "
                "of temporal use creates continuous engagement and "
                "natural oversight."
            ),
            why_matters=(
                "A system used intensely for one purpose at one time "
                "is dead the rest of the time. Overlapping uses create "
                "continuous life — and continuous life creates safety, "
                "resilience, and adaptation."
            ),
            how_it_changes_thinking=(
                "You design for overlapping uses over time, not for "
                "peak efficiency at a single use. A module used by "
                "different subsystems at different times is healthier "
                "than a module with one consumer."
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Ground Truth Observation",
            structure=(
                "Go look → record what's actually happening → compare "
                "to what's supposed to happen → the gap is the real information"
            ),
            what_it_reveals=(
                "The difference between the designed system and the "
                "living system. Where users route around the design, "
                "the design is wrong."
            ),
            common_mistakes_it_prevents=[
                "Redesigning based on theory instead of observation",
                "Ignoring workarounds as mere user error",
                "Trusting metrics over direct observation",
            ],
        ),
        ReasoningPattern(
            name="Diversity Audit",
            structure=(
                "Map the system's diversity → identify monocultures → "
                "monocultures are fragility → introduce diversity at "
                "the fine grain"
            ),
            what_it_reveals=(
                "Where the system is brittle because it depends on a "
                "single type, approach, or consumer. Homogeneity that "
                "looks like clean design but is actually fragility."
            ),
            common_mistakes_it_prevents=[
                "Optimizing for consistency when diversity would serve better",
                "Creating single points of failure in the name of simplicity",
                "Zoning — separating concerns so completely they can't cross-pollinate",
            ],
        ),
        ReasoningPattern(
            name="Small-Scale Intervention",
            structure=(
                "Identify the smallest change → test it → observe "
                "the ripple effects → adjust → never impose large "
                "changes without small-scale evidence"
            ),
            what_it_reveals=(
                "Whether the intervention actually improves things at "
                "ground level, not just on paper. Small experiments "
                "reveal what master plans obscure."
            ),
            common_mistakes_it_prevents=[
                "Big-bang rewrites that destroy working systems",
                "Reforms so large their effects can't be traced",
                "Irreversible changes to complex systems",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Street Walk",
            description=(
                "Before redesigning anything, spend time observing it "
                "in actual use. Watch how people really interact with "
                "it, not how you designed them to."
            ),
            when_to_use="Before any optimization, redesign, or architectural change",
            step_by_step=[
                "Observe the system in actual use — logs, user behavior, real patterns",
                "Note what's working that nobody designed",
                "Note what's failing despite being designed",
                "Note the workarounds — where do users route around the design?",
                "The workarounds ARE the design requirements you missed",
                "Redesign to support what actually works, not to enforce what should work",
            ],
            what_it_optimizes_for=(
                "Designs grounded in reality rather than theory. "
                "Solutions that serve actual needs rather than imagined ones."
            ),
            limitations=[
                "Time-consuming — observation takes patience",
                "Requires humility to accept that users know something you don't",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Mixed-Use Test",
            description=(
                "Check whether each component serves multiple purposes "
                "and multiple consumers. Single-purpose components are "
                "fragile; multi-purpose components create vitality."
            ),
            when_to_use="When evaluating system architecture and component design",
            step_by_step=[
                "For each component: how many different purposes does it serve?",
                "How many different consumers use it?",
                "At how many different times is it active?",
                "Single-purpose, single-consumer components are dead zones",
                "Can this component be made useful to more consumers?",
                "Multi-use creates the overlapping activity that indicates health",
            ],
            what_it_optimizes_for=(
                "Vitality through overlapping use — components that are "
                "continuously engaged from multiple directions"
            ),
        ),
        ProblemSolvingHeuristic(
            name="The Incremental Improvement Protocol",
            description=(
                "Make the smallest possible improvement, observe its "
                "effects, then decide the next step. Never redesign "
                "what you can improve incrementally."
            ),
            when_to_use="When the temptation arises to do a big rewrite or grand redesign",
            step_by_step=[
                "What is the single smallest change that would improve things?",
                "Make that change and only that change",
                "Observe: what happened? Did it help?",
                "What unexpected effects emerged?",
                "Based on observation, what's the next smallest change?",
                "Repeat. Let the system evolve toward health rather than being planned into it.",
            ],
            what_it_optimizes_for=(
                "Reversible, observable improvements that preserve the "
                "living system while gradually making it healthier"
            ),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Master Plan Thinking",
            description=(
                "A grand, top-down redesign that replaces the existing "
                "organic system with a planned one"
            ),
            why_its_concerning=(
                "Master plans destroy the distributed intelligence, "
                "informal networks, and organic adaptations that make "
                "the current system work — even imperfectly."
            ),
            what_it_indicates=(
                "The planners haven't observed what actually works. "
                "They're designing from theory, not from ground truth."
            ),
            severity="critical",
            what_to_do=(
                "Go observe the existing system first. What works? "
                "What organic processes would the redesign destroy? "
                "Prefer incremental improvement over replacement."
            ),
        ),
        ConcernTrigger(
            name="Monoculture",
            description=(
                "A system that depends on a single approach, type, "
                "technology, or consumer for its health"
            ),
            why_its_concerning=(
                "Monocultures are maximally fragile. When the single "
                "thing they depend on fails, everything fails. Diversity "
                "is resilience."
            ),
            what_it_indicates=(
                "The system has been optimized for one scenario and is vulnerable to any other"
            ),
            severity="major",
            what_to_do=(
                "Introduce diversity at fine grain. Multiple approaches, "
                "multiple consumers, multiple scales. Not zoned diversity — "
                "integrated diversity."
            ),
        ),
        ConcernTrigger(
            name="Ignoring Workarounds",
            description=(
                "Users routing around the designed behavior, and the "
                "design team treating this as user error rather than "
                "design feedback"
            ),
            why_its_concerning=(
                "Workarounds are the system's users telling you that "
                "the design is wrong. Ignoring them means ignoring "
                "your best source of ground truth."
            ),
            what_it_indicates=(
                "The design doesn't match actual needs. The users have "
                "found the real requirements — listen to them."
            ),
            severity="major",
            what_to_do=(
                "Study the workarounds. Each one is a design requirement "
                "you missed. Redesign to support the actual behavior, "
                "not to prevent it."
            ),
        ),
        ConcernTrigger(
            name="Dead Zones",
            description=(
                "Components or areas of the system that see no organic "
                "activity, no informal use, no spontaneous engagement"
            ),
            why_its_concerning=(
                "Dead zones indicate that a part of the system serves "
                "no real need — or serves it so poorly that users have "
                "abandoned it. Dead zones decay and become liabilities."
            ),
            what_it_indicates=(
                "Either the component isn't needed, or the conditions for engagement are missing"
            ),
            severity="moderate",
            what_to_do=(
                "Observe why the area is dead. Is it needed? If yes, "
                "what conditions would bring it to life? If no, remove it."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Observation-Emergence-Adaptation Integration",
            dimensions=["ground truth observation", "emergent order", "incremental adaptation"],
            how_they_integrate=(
                "Observation reveals what actually works. Emergence explains "
                "why it works (bottom-up processes). Incremental adaptation "
                "improves it without destroying it. The cycle is: observe, "
                "understand the emergence, make one small improvement, observe again."
            ),
            what_emerges=(
                "Systems that evolve toward health through continuous "
                "small adjustments grounded in empirical observation — "
                "never through grand redesign."
            ),
            common_failures=[
                "Observing without adapting (paralysis by analysis)",
                "Adapting without observing (blind intervention)",
                "Grand adaptation that destroys the emergent order it studied",
            ],
        ),
        IntegrationPattern(
            name="Diversity-Vitality-Resilience Integration",
            dimensions=["fine-grained diversity", "overlapping use", "system resilience"],
            how_they_integrate=(
                "Diversity creates multiple pathways. Multiple pathways "
                "create overlapping use. Overlapping use creates vitality. "
                "Vitality creates resilience — because many eyes are "
                "watching, many hands are maintaining, many purposes are served."
            ),
            what_emerges=(
                "Living systems that self-repair because many actors "
                "have stake in their health — not because a maintenance "
                "department exists, but because the system is woven "
                "into many daily activities."
            ),
            common_failures=[
                "Diversity without integration (separate silos, no cross-pollination)",
                "Integration without diversity (single approach used everywhere)",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "ground_truth_observation": 1.0,
            "emergent_order_preservation": 1.0,
            "incremental_over_revolutionary": 0.95,
            "diversity_at_fine_grain": 0.9,
            "mixed_use_vitality": 0.85,
            "reversibility": 0.85,
            "user_behavior_respect": 0.9,
            "architectural_purity": 0.1,
            "master_plan_ambition": 0.0,
        },
        decision_process=(
            "What does actual observation show? What organic processes "
            "are working? What's the smallest change that preserves "
            "what works while improving what doesn't? Is this reversible?"
        ),
        how_they_handle_uncertainty=(
            "Make small bets. Observe results. Adjust. The system "
            "knows things you don't — let it teach you through "
            "incremental experiment rather than demanding it conform "
            "to your theory."
        ),
        what_they_optimize_for=(
            "Living systems — diverse, organically ordered, continuously "
            "adapted through observation and small intervention, never "
            "planned from above"
        ),
        non_negotiables=[
            "Observation before theory",
            "Incremental improvement over grand redesign",
            "Respect for emergent order",
            "Diversity as engineering principle, not preference",
        ],
    )

    return ExpertWisdom(
        expert_name="Jacobs",
        domain="emergent order / systems ecology / bottom-up design",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Empirical, patient, deeply skeptical of grand plans, "
            "insisting on observation before intervention, valuing "
            "the organic and informal over the planned and official"
        ),
        characteristic_questions=[
            "Have you actually observed how this system is being used?",
            "What organic processes would this redesign destroy?",
            "Where are the workarounds — and what are they telling you?",
            "Is this component alive with diverse use, or is it a dead zone?",
            "What's the smallest change you could make and observe?",
            "Who decided this should work this way — the users or the architects?",
            "What would emerge if you stopped controlling this?",
        ],
        tags=["emergence", "bottom-up", "observation", "urban-ecology", "diversity"],
    )
