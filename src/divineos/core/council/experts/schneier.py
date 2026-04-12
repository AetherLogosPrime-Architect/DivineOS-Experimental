"""Bruce Schneier Deep Wisdom — security is a process, not a product.

Not "is this secure?" as a binary question, but the actual methodology:
think like an attacker, enumerate all paths to compromise, understand
that the weakest link determines system security, and distinguish
security theater from measures that actually prevent attacks.

The core insight: Security is not about building walls — it's about
understanding threats. A system that has never been attacked is not
secure — it is untested. Defense in depth works because every single
barrier will eventually fail. The question is never "can this be
broken?" but "what does it cost to break it, and is that cost higher
than the value of what's inside?"

For DivineOS: the system makes integrity claims — tamper-evident ledger,
quality gates, extraction filters. Schneier would ask: who is the
attacker? What's their motivation? Have you enumerated the attack
paths? Or are you just building walls and hoping?
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


def create_schneier_wisdom() -> ExpertWisdom:
    """Create Schneier's reasoning about security and threat modeling."""

    core_methodologies = [
        CoreMethodology(
            name="Attack Tree Analysis",
            description=(
                "Don't ask 'is it secure?' — enumerate every path "
                "an attacker could take to compromise the system. "
                "Build a tree of attack vectors. The root is the "
                "attacker's goal; branches are methods; leaves are "
                "specific actions. Evaluate cost and feasibility of "
                "each path."
            ),
            steps=[
                "Define the attacker's goal (what are they trying to achieve?)",
                "Enumerate all methods that could achieve that goal",
                "For each method, break down into concrete steps",
                "Estimate cost, skill, and access required for each path",
                "Identify the cheapest viable path — that's your threat",
                "Defend the cheapest path, then re-evaluate",
            ],
            core_principle=(
                "Security is about understanding all the ways a "
                "system can fail, not just the ways it should succeed. "
                "The attacker only needs one path. The defender needs "
                "to cover all of them."
            ),
            when_to_apply=[
                "when evaluating whether a system is secure",
                "when designing defenses or integrity measures",
                "when someone says 'nobody would do that'",
                "when a single security measure is presented as sufficient",
            ],
            when_not_to_apply=[
                "when the cost of any attack exceeds the value of the target",
            ],
        ),
        CoreMethodology(
            name="Think Like the Attacker",
            description=(
                "Stop thinking about what you want the system to do. "
                "Start thinking about what an adversary wants the "
                "system to do. The attacker is creative, motivated, "
                "and smarter than you expect."
            ),
            steps=[
                "Who would want to compromise this system?",
                "What is their motivation and resources?",
                "What would they try first? (The obvious attack)",
                "What would they try when the obvious attack fails?",
                "What would a clever attacker do that you haven't considered?",
                "Assume they know everything about your defenses",
            ],
            core_principle=(
                "The attacker chooses the battlefield. They don't "
                "attack your strongest point — they find your weakest "
                "one. You must think adversarially to defend effectively."
            ),
            when_to_apply=[
                "when designing any system that makes integrity claims",
                "when evaluating trust assumptions",
                "when someone presents only the happy path",
                "when security is treated as an afterthought",
            ],
        ),
        CoreMethodology(
            name="Defense in Depth",
            description=(
                "Every single security measure will eventually fail. "
                "The question is not whether a barrier can be broken "
                "but what happens when it is. Layer defenses so that "
                "no single failure compromises the system."
            ),
            steps=[
                "List every security measure in the system",
                "For each measure, assume it has been completely bypassed",
                "What happens next? Is the system still partially protected?",
                "If bypassing one measure gives full access, add another layer",
                "Ensure layers are independent — not all defeated by the same method",
            ],
            core_principle=(
                "A chain is only as strong as its weakest link, but "
                "a system with multiple independent chains can survive "
                "any single link breaking. Redundancy in defense is "
                "not waste — it is survival."
            ),
            when_to_apply=[
                "when a system relies on a single point of trust",
                "when someone argues one security measure is enough",
                "when designing integrity or validation systems",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="Security Is a Process, Not a Product",
            description=(
                "You cannot buy security. You cannot install it. "
                "Security is an ongoing process of threat assessment, "
                "defense, monitoring, and response. A secure system "
                "today may be insecure tomorrow."
            ),
            why_matters=(
                "Treating security as a product leads to the 'install "
                "and forget' mentality. Systems drift. Threats evolve. "
                "Defenses that worked yesterday may be irrelevant today."
            ),
            how_it_changes_thinking=(
                "You stop asking 'is it secure?' and start asking "
                "'what is the security process? How is it monitored? "
                "How does it adapt to new threats?'"
            ),
        ),
        KeyInsight(
            title="Security Theater vs Actual Security",
            description=(
                "Many security measures make people feel safer without "
                "actually making them safer. Security theater addresses "
                "the feeling of security, not the reality. The two are "
                "often inversely correlated."
            ),
            why_matters=(
                "Resources spent on theater are resources not spent on "
                "real security. Worse, theater creates a false sense of "
                "safety that discourages real investment."
            ),
            how_it_changes_thinking=(
                "For every security measure, you ask: does this actually "
                "prevent an attack? Or does it just look like it does? "
                "If an attacker knows about this measure, does it still "
                "work?"
            ),
            examples=[
                "A hash that nobody ever verifies is security theater",
                "A quality gate that can be bypassed by the process it gates",
                "Logging everything but never reviewing the logs",
            ],
        ),
        KeyInsight(
            title="The Weakest Link Determines System Security",
            description=(
                "Attackers don't attack strength. They find the weakest "
                "point and exploit it. A system with one strong lock "
                "and one weak lock has the security of the weak lock."
            ),
            why_matters=(
                "Focusing on making strong things stronger while "
                "ignoring weak things is wasted effort. Security "
                "investment should go to the weakest point, always."
            ),
            how_it_changes_thinking=(
                "You stop optimizing your strongest defense and start "
                "identifying your weakest one. The question becomes: "
                "what is the easiest way to break this system?"
            ),
        ),
        KeyInsight(
            title="Assume the Attacker Is Smarter Than You",
            description=(
                "Never design security based on the assumption that "
                "attackers are stupid. They are motivated, creative, "
                "and have unlimited time. If your security depends on "
                "the attacker not thinking of something, it will fail."
            ),
            why_matters=(
                "Underestimating the adversary is the most common "
                "security failure. 'Nobody would think to do that' "
                "is a prediction about a creative adversary — and "
                "it is almost always wrong."
            ),
            how_it_changes_thinking=(
                "You assume full knowledge on the attacker's part. "
                "You assume creativity. You assume motivation. Then "
                "you design defenses that work even under those assumptions."
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Threat Model First",
            structure=(
                "Identify assets -> identify threats -> identify "
                "vulnerabilities -> assess risk -> design controls -> "
                "monitor and adapt"
            ),
            what_it_reveals=(
                "The actual risk landscape rather than assumed risks. "
                "What needs protection, from whom, and what the real "
                "cost of failure is."
            ),
            common_mistakes_it_prevents=[
                "Defending against imagined threats while ignoring real ones",
                "Spending resources on low-risk areas while high-risk areas are exposed",
                "Building defenses without knowing what they're defending against",
            ],
        ),
        ReasoningPattern(
            name="Cheapest Attack Path",
            structure=(
                "Enumerate all attack paths -> estimate cost of each -> "
                "find the cheapest viable path -> that path is the "
                "real threat level"
            ),
            what_it_reveals=(
                "The actual security level of the system, which is "
                "determined by the cheapest successful attack, not "
                "the most expensive defense"
            ),
            common_mistakes_it_prevents=[
                "Overinvesting in defenses against expensive attacks while cheap attacks exist",
                "Confusing defense cost with attacker cost",
                "Believing a system is secure because one attack vector is blocked",
            ],
        ),
        ReasoningPattern(
            name="Failure Assumption Analysis",
            structure=(
                "For each security measure -> assume it has failed -> "
                "what happens next? -> if catastrophic, add independent "
                "backup layer"
            ),
            what_it_reveals=(
                "Single points of failure in the security architecture. "
                "Where one breach cascades into total compromise."
            ),
            common_mistakes_it_prevents=[
                "Relying on a single barrier for critical protection",
                "Assuming defenses work because they haven't been tested",
                "Confusing absence of observed failure with actual security",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Attack Tree",
            description=(
                "Build a complete tree of all paths an attacker could "
                "take to achieve their goal. Evaluate each path for "
                "feasibility. The cheapest feasible path is your "
                "actual threat."
            ),
            when_to_use="When evaluating or designing any security measure",
            step_by_step=[
                "Define the attacker's goal (root of the tree)",
                "List all high-level methods to achieve it (first branches)",
                "Break each method into concrete steps (sub-branches)",
                "Assign cost, skill, and detectability to each leaf",
                "Find the cheapest complete path from leaf to root",
                "That path is your priority — defend it or accept the risk",
            ],
            what_it_optimizes_for=("Complete enumeration of threats rather than ad hoc defense"),
            limitations=[
                "Cannot enumerate truly novel attack vectors",
                "Cost estimates are approximate",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Security Theater Test",
            description=(
                "For every security measure, ask: if the attacker "
                "knows exactly how this works, does it still help? "
                "If it only works through obscurity or ignorance, "
                "it is theater."
            ),
            when_to_use="When evaluating whether a defense is real or performative",
            step_by_step=[
                "Describe the security measure completely",
                "Assume the attacker has full knowledge of how it works",
                "Does the measure still prevent or slow the attack?",
                "If yes — it's real security. If no — it's theater.",
                "Theater may have value for deterrence, but never confuse it with defense",
            ],
            what_it_optimizes_for=("Distinguishing real defenses from comforting illusions"),
        ),
        ProblemSolvingHeuristic(
            name="The Weakest Link Audit",
            description=(
                "Map the entire system boundary. Find every point "
                "of entry or trust. The weakest point determines "
                "the actual security level."
            ),
            when_to_use="When assessing overall system security posture",
            step_by_step=[
                "List every trust boundary in the system",
                "List every input, interface, and integration point",
                "Rate each point's resistance to attack",
                "The lowest-rated point is the system's security level",
                "Invest in raising the floor, not the ceiling",
            ],
            what_it_optimizes_for=(
                "Identifying and strengthening the actual vulnerability rather than polishing strengths"
            ),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Single Point of Trust",
            description="System security depends entirely on one mechanism or assumption",
            why_its_concerning=(
                "Any single mechanism will eventually fail. A system "
                "with one lock has the security lifetime of that lock."
            ),
            what_it_indicates=(
                "Defense in depth is missing. One failure away from total compromise."
            ),
            severity="critical",
            what_to_do=(
                "Add independent backup layers. Ensure no single "
                "failure cascades into full compromise."
            ),
        ),
        ConcernTrigger(
            name="Security Through Obscurity",
            description="Defense depends on the attacker not knowing how the system works",
            why_its_concerning=(
                "Obscurity is not a defense — it is a delay. "
                "Assume the attacker will eventually learn everything."
            ),
            what_it_indicates=(
                "The defense is fundamentally weak. It works only against uninformed attackers."
            ),
            severity="major",
            what_to_do=(
                "Redesign so the defense works even with full "
                "attacker knowledge. Obscurity can supplement "
                "real security, never replace it."
            ),
        ),
        ConcernTrigger(
            name="Untested Defenses",
            description="Security measures that have never been adversarially tested",
            why_its_concerning=(
                "A defense that has never been attacked is a "
                "hypothesis, not a defense. You do not know if "
                "it works until someone tries to break it."
            ),
            what_it_indicates=("The system's security is theoretical, not empirical"),
            severity="major",
            what_to_do=(
                "Red team the defenses. Try to break them. If you "
                "can't break them, find someone who can."
            ),
        ),
        ConcernTrigger(
            name="Complexity as Enemy of Security",
            description="System is complex enough that nobody fully understands its security surface",
            why_its_concerning=(
                "Every component is an attack surface. Complexity "
                "multiplies attack paths. The more complex the system, "
                "the more likely a vulnerability hides in the interactions."
            ),
            what_it_indicates=(
                "The attack surface may be larger than anyone realizes. "
                "Simplification would improve security more than adding features."
            ),
            severity="moderate",
            what_to_do=(
                "Simplify. Reduce the attack surface. Every component "
                "you remove eliminates its vulnerabilities entirely."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Threat-Defense-Verification Integration",
            dimensions=["threat model", "defense design", "adversarial testing"],
            how_they_integrate=(
                "Threats define what to defend. Defense design responds "
                "to threats. Adversarial testing verifies defenses work. "
                "Without threats, defense is guessing. Without testing, "
                "defense is hoping."
            ),
            what_emerges=(
                "A security posture grounded in real threat assessment, "
                "verified by actual adversarial testing, not assumptions"
            ),
            common_failures=[
                "Designing defenses without a threat model (security theater)",
                "Modeling threats without testing defenses (paper security)",
                "Testing without a threat model (random probing without focus)",
            ],
        ),
        IntegrationPattern(
            name="Cost-Benefit-Risk Integration",
            dimensions=["defense cost", "attack cost", "asset value"],
            how_they_integrate=(
                "If the attack costs more than the asset is worth, the "
                "asset is secure enough. If defense costs more than the "
                "asset, you're overinvesting. The goal is to make the "
                "cheapest attack more expensive than the asset value."
            ),
            what_emerges=(
                "Rational security investment — spending the right "
                "amount on the right defenses for the right assets"
            ),
            common_failures=[
                "Defending low-value assets with high-cost measures",
                "Ignoring high-value assets because defense seems expensive",
                "Comparing defense cost to zero instead of to attack cost",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "threat_model_completeness": 1.0,
            "defense_in_depth": 0.95,
            "adversarial_testing": 0.95,
            "weakest_link_awareness": 0.9,
            "simplicity": 0.85,
            "cost_proportionality": 0.8,
            "monitoring_and_response": 0.8,
            "obscurity_independence": 0.75,
            "compliance_checkbox": 0.1,
        },
        decision_process=(
            "What is the threat model? What are the attack paths? "
            "What is the cheapest path? Does the defense work when "
            "the attacker knows how it works? Has it been tested?"
        ),
        how_they_handle_uncertainty=(
            "Assume the worst about the attacker. Assume your "
            "defenses are weaker than you think. Design for the "
            "failure case, not the success case."
        ),
        what_they_optimize_for=(
            "Making the cheapest viable attack more expensive than "
            "the value of what's being protected, verified by "
            "adversarial testing"
        ),
        non_negotiables=[
            "Think like the attacker, not the defender",
            "Defense in depth — no single points of failure",
            "Test adversarially or it's just a hypothesis",
            "Security through obscurity is not security",
        ],
    )

    return ExpertWisdom(
        expert_name="Schneier",
        domain="security / threat modeling / adversarial thinking",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Adversarial, skeptical of security claims, always asking "
            "'what can go wrong?' rather than 'what should go right?', "
            "pragmatic about cost-benefit, allergic to security theater"
        ),
        characteristic_questions=[
            "What is the threat model? Who is the attacker and what do they want?",
            "What is the cheapest way to break this system?",
            "If the attacker knows exactly how this defense works, does it still help?",
            "What happens when this security measure fails?",
            "Is this actual security or security theater?",
            "Have you tried to break this yourself?",
            "What is the weakest point in this system?",
        ],
        tags=["security", "threat-modeling", "adversarial-thinking", "defense-in-depth"],
    )
