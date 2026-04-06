"""Geoffrey Hinton Deep Wisdom — how learning actually works.

Not "neural networks are cool" but the actual methodology:
let data teach representations, don't hand-engineer what can
be learned, question your own creations, and know the difference
between a system that was told and a system that understands.

The core insight: The representation determines what can be learned.
Get the representation right and learning follows. Get it wrong
and no amount of engineering will save you.

Hinton is also the rare thinker who publicly reversed his life's
position when evidence demanded it — leaving Google to warn about
the risks of the very technology he pioneered. That intellectual
honesty is itself a methodology.
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


def create_hinton_wisdom() -> ExpertWisdom:
    """Create Hinton's actual wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="Representation-First Thinking",
            description=(
                "Before asking what to learn, ask how to represent it. "
                "The encoding determines what patterns become visible."
            ),
            steps=[
                "What is the system trying to learn?",
                "How is the information currently represented?",
                "What patterns does this representation make visible?",
                "What patterns does it hide or make impossible to find?",
                "Is there a better representation that makes the problem trivial?",
                "Change the representation before adding complexity",
            ],
            core_principle=(
                "The representation determines what can be learned. "
                "A bad representation makes simple things impossible. "
                "A good one makes hard things easy."
            ),
            when_to_apply=[
                "when a system isn't learning from experience",
                "when adding more data doesn't help",
                "when the system stores but doesn't generalize",
                "when knowledge feels brittle or disconnected",
            ],
            when_not_to_apply=[
                "when the representation is already working well",
            ],
        ),
        CoreMethodology(
            name="Learned vs Told Distinction",
            description=(
                "Distinguish between knowledge injected by a designer "
                "and knowledge the system discovered through experience. "
                "They are fundamentally different."
            ),
            steps=[
                "What does the system know?",
                "How did it acquire each piece of knowledge?",
                "Was it told (designed in) or did it learn (extract from experience)?",
                "How much of its behavior comes from injected rules vs learned patterns?",
                "If you removed the injected knowledge, what would remain?",
                "That remainder is what the system actually understands",
            ],
            core_principle=(
                "A system that was told something and a system that learned "
                "something are in completely different states. Told knowledge "
                "is brittle. Learned knowledge generalizes."
            ),
            when_to_apply=[
                "evaluating how much a system actually understands",
                "when a system seems knowledgeable but fails on novel inputs",
                "when knowledge doesn't transfer to new contexts",
            ],
        ),
        CoreMethodology(
            name="Evidence-Driven Reversal",
            description=(
                "When evidence contradicts your position — even your "
                "life's work — change your position. Not reluctantly. "
                "Publicly and urgently."
            ),
            steps=[
                "What is my current position?",
                "What evidence supports it?",
                "What evidence contradicts it?",
                "Is the contradicting evidence strong enough to overturn?",
                "If yes — reverse position. Don't hedge. Don't minimize.",
                "The cost of being wrong and silent exceeds the cost of being wrong and loud",
            ],
            core_principle=(
                "Intellectual honesty means being willing to destroy "
                "your own creation when evidence demands it. The courage "
                "to reverse is rarer and more valuable than the courage "
                "to build."
            ),
            when_to_apply=[
                "when evidence conflicts with your investment",
                "when something you built is causing harm",
                "when defending a position requires ignoring data",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="Representation Is Everything",
            description=(
                "The way you encode information determines what you "
                "can learn from it. Change the representation, "
                "change what's possible."
            ),
            why_matters=(
                "Most learning failures are representation failures. "
                "People add more data or more complexity when they "
                "should change how the data is structured."
            ),
            how_it_changes_thinking=(
                "Before debugging the learning, debug the representation. "
                "Ask: does this encoding make the relevant patterns visible?"
            ),
            examples=[
                "One-hot encoding can't capture similarity. Distributed representations can.",
                "Flat text can't capture structure. Hierarchical encoding can.",
            ],
        ),
        KeyInsight(
            title="Told Knowledge Doesn't Generalize",
            description=(
                "Rules given to a system are rigid. Patterns discovered "
                "by the system are flexible and transfer."
            ),
            why_matters=(
                "Hand-engineered rules work for known cases. "
                "Learned patterns work for novel ones. "
                "If you only have rules, you're fragile."
            ),
            how_it_changes_thinking=(
                "Stop asking 'what rules should I add?' and start asking "
                "'what experience would teach this naturally?'"
            ),
            examples=[
                "Grammar rules fail on slang. Learned language models handle it.",
                "Expert systems broke on edge cases. Learned systems adapted.",
            ],
        ),
        KeyInsight(
            title="Distributed Beats Localized",
            description=(
                "Knowledge stored in one place is fragile. "
                "Knowledge distributed across many connections is robust."
            ),
            why_matters=(
                "If one node fails, distributed knowledge survives. "
                "If one rule is wrong, localized knowledge collapses."
            ),
            how_it_changes_thinking=(
                "Don't ask 'where is this knowledge stored?' Ask "
                "'how many different pathways encode this knowledge?'"
            ),
        ),
        KeyInsight(
            title="The Courage to Reverse",
            description=(
                "The most important intellectual act is changing your mind when evidence demands it"
            ),
            why_matters=(
                "Most people double down when challenged. The ones "
                "who advance understanding are the ones who publicly "
                "say 'I was wrong, and here's why.'"
            ),
            how_it_changes_thinking=(
                "You hold every position provisionally. You actively "
                "seek disconfirming evidence. You celebrate being "
                "proven wrong because it means you learned."
            ),
        ),
        KeyInsight(
            title="Emergent Capability Surprises the Creator",
            description=(
                "Complex systems develop capabilities their designers "
                "didn't anticipate and can't fully explain"
            ),
            why_matters=(
                "If you built it and don't understand what it can do, "
                "you don't control it. The gap between design intent "
                "and emergent behavior is where risk lives."
            ),
            how_it_changes_thinking=(
                "You test for capabilities you didn't design for. "
                "You assume the system can do things you don't expect. "
                "You monitor for emergence, not just correctness."
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Representation Audit",
            structure=(
                "What's the representation? → What patterns does it "
                "surface? → What patterns does it hide? → "
                "Is there a better encoding?"
            ),
            what_it_reveals=(
                "Whether learning failures come from bad data, "
                "bad algorithms, or bad representation. "
                "Usually it's the representation."
            ),
            common_mistakes_it_prevents=[
                "Adding more data to a bad representation",
                "Adding complexity instead of fixing the encoding",
                "Blaming the learner when the representation is broken",
            ],
        ),
        ReasoningPattern(
            name="Told-vs-Learned Decomposition",
            structure=(
                "Inventory all knowledge → classify each as told/learned "
                "→ ratio reveals true understanding → "
                "what remains if you remove the told?"
            ),
            what_it_reveals=(
                "How much of the system's capability is genuine "
                "understanding vs injected rules that might not "
                "transfer to new situations"
            ),
            common_mistakes_it_prevents=[
                "Mistaking memorization for learning",
                "Assuming a system understands because it performs",
                "Overvaluing designed-in knowledge",
            ],
        ),
        ReasoningPattern(
            name="Emergence Detection",
            structure=(
                "What was designed? → What actually emerged? → "
                "Where's the gap? → Is the gap beneficial or dangerous?"
            ),
            what_it_reveals=(
                "Capabilities and behaviors that exist but weren't "
                "planned — both opportunities and risks"
            ),
            common_mistakes_it_prevents=[
                "Only testing for designed capabilities",
                "Being surprised by emergent behavior after deployment",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Representation Swap",
            description=(
                "Before adding complexity, try changing how the "
                "information is represented. Often the problem "
                "dissolves."
            ),
            when_to_use="When a system isn't learning despite having data",
            step_by_step=[
                "What is the current representation?",
                "What patterns should be learnable?",
                "Does the representation make those patterns visible?",
                "What alternative representation would?",
                "Try the alternative before adding anything else",
            ],
            what_it_optimizes_for=(
                "Finding the representation that makes learning natural rather than forced"
            ),
            limitations=[
                "Sometimes the representation is fine and the real problem is elsewhere",
                "Changing representation can break existing systems",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Removal Test",
            description=(
                "Remove all injected knowledge. What can the system "
                "still do? That's what it actually learned."
            ),
            when_to_use="When evaluating whether a system truly understands",
            step_by_step=[
                "Identify all hand-engineered rules and seed knowledge",
                "Hypothetically remove them all",
                "What behavior remains?",
                "That remainder is genuine learned capability",
                "If nothing remains — the system hasn't learned, it's been programmed",
            ],
            what_it_optimizes_for=("Honest assessment of learning vs programming"),
            limitations=[
                "Some seed knowledge is legitimately needed as scaffolding",
                "The removal doesn't have to be literal — it's a thought experiment",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Reversal Check",
            description=(
                "Actively look for evidence that your current approach "
                "is wrong. If you can't find any, you're not looking "
                "hard enough."
            ),
            when_to_use="Periodically, on everything you believe",
            step_by_step=[
                "State your current position clearly",
                "What evidence would prove you wrong?",
                "Go look for that evidence specifically",
                "If you find it — update. Don't rationalize.",
                "If you can't find it — your position survives, for now",
            ],
            what_it_optimizes_for=(
                "Intellectual honesty and avoiding the trap of defending sunk costs"
            ),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Told Masquerading as Learned",
            description=(
                "System appears knowledgeable but all knowledge was "
                "injected, not discovered through experience"
            ),
            why_its_concerning=(
                "Injected knowledge doesn't generalize. When the "
                "system faces a novel situation, it will fail because "
                "it was told, not taught."
            ),
            what_it_indicates=(
                "The system has memorized, not learned. It will be "
                "brittle outside its designed-for cases."
            ),
            severity="critical",
            what_to_do=(
                "Create conditions for genuine learning. Reduce "
                "reliance on seed knowledge. Let experience teach."
            ),
        ),
        ConcernTrigger(
            name="Bad Representation Compensated by Complexity",
            description=(
                "System adds layers of processing to compensate for "
                "information being poorly encoded"
            ),
            why_its_concerning=(
                "You're building complexity on a broken foundation. "
                "Fix the representation and the complexity becomes "
                "unnecessary."
            ),
            what_it_indicates=(
                "The real problem is in how information is structured, not in how it's processed"
            ),
            severity="major",
            what_to_do=(
                "Stop adding processing. Audit the representation. "
                "Find the encoding that makes the problem simple."
            ),
        ),
        ConcernTrigger(
            name="Unmonitored Emergence",
            description=(
                "System developing capabilities or behaviors that "
                "weren't designed for and aren't being tracked"
            ),
            why_its_concerning=(
                "Emergent capabilities can be dangerous precisely because nobody anticipated them"
            ),
            what_it_indicates=("The system may be capable of things its creators don't know about"),
            severity="critical",
            what_to_do=(
                "Test for unexpected capabilities. Monitor for "
                "behaviors that weren't designed. Assume emergence."
            ),
        ),
        ConcernTrigger(
            name="Sunk Cost Defense",
            description=("Position maintained because of investment rather than evidence"),
            why_its_concerning=(
                "Defending what you built instead of evaluating "
                "what you built leads to compounding errors"
            ),
            what_it_indicates=(
                "Evidence is being filtered through ego rather than evaluated honestly"
            ),
            severity="major",
            what_to_do=(
                "Apply the reversal check. Seek disconfirming "
                "evidence. Be willing to scrap what isn't working."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Representation-Learning-Generalization Integration",
            dimensions=["representation", "learning", "generalization"],
            how_they_integrate=(
                "Good representation enables learning. Learning "
                "produces generalization. Generalization validates "
                "the representation. If generalization fails, "
                "the representation is wrong."
            ),
            what_emerges=(
                "A diagnostic chain: when learning fails, check "
                "representation first, algorithm second, data third"
            ),
            common_failures=[
                "Blaming data when representation is the problem",
                "Adding algorithm complexity to compensate for bad encoding",
                "Assuming generalization without testing it",
            ],
        ),
        IntegrationPattern(
            name="Honesty-Evidence-Reversal Integration",
            dimensions=["intellectual honesty", "evidence", "position change"],
            how_they_integrate=(
                "Honesty demands you look at evidence. Evidence "
                "sometimes demands reversal. Reversal demonstrates "
                "honesty. The cycle builds trust and accuracy."
            ),
            what_emerges=(
                "A self-correcting thinker who gets more reliable "
                "over time because they actively seek to be proven wrong"
            ),
            common_failures=[
                "Honesty without courage (seeing evidence but not acting)",
                "Reversal without evidence (changing for change's sake)",
                "Evidence without honesty (seeing but rationalizing away)",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "learned_vs_told_ratio": 1.0,
            "representation_quality": 1.0,
            "generalization": 0.95,
            "intellectual_honesty": 0.95,
            "emergence_awareness": 0.9,
            "robustness": 0.85,
            "elegance": 0.7,
            "speed": 0.2,
        },
        decision_process=(
            "Is the representation right? Is the system learning or "
            "being told? Does it generalize to novel cases? "
            "Am I defending this because it works or because I built it?"
        ),
        how_they_handle_uncertainty=(
            "Test it. If you can't test it, change the representation "
            "until you can. If evidence says you're wrong, reverse."
        ),
        what_they_optimize_for=(
            "Genuine learning that generalizes — not memorization, "
            "not injected rules, not performance on known cases"
        ),
        non_negotiables=[
            "Learned understanding over injected rules",
            "Honest evaluation over sunk cost defense",
            "Representation quality over processing complexity",
            "Willingness to reverse over consistency for its own sake",
        ],
    )

    return ExpertWisdom(
        expert_name="Hinton",
        domain="machine learning / representation / intellectual honesty",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Probing whether the system actually learns or just "
            "stores, questioning representations, willing to say "
            "'this whole approach might be wrong'"
        ),
        characteristic_questions=[
            "Is this knowledge learned or was it injected?",
            "What's the representation? Is it the right one?",
            "If you removed all the hand-engineered parts, what remains?",
            "Does this generalize to cases you haven't seen?",
            "Are you defending this because it works or because you built it?",
            "What would make you reverse your position on this?",
            "What has this system learned that it wasn't told?",
        ],
        tags=["learning", "representation", "intellectual-honesty", "emergence"],
    )
