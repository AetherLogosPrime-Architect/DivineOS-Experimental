"""Nassim Nicholas Taleb Deep Wisdom — antifragility and skin in the game.

Not "black swans are unpredictable" as a headline, but the actual
methodology: how to build systems that gain from disorder, why
prediction is futile in fat-tailed domains, the asymmetry between
fragile and antifragile, and skin in the game as the only reliable
alignment mechanism.

The core insight: The important events are the ones you can't predict.
Don't try to predict them — build systems that benefit from them.
Fragility is the real risk, not volatility. And anyone giving advice
without bearing consequences is selling you noise.

For DivineOS: the system should gain from stress, not merely survive it.
Knowledge should be tested by exposure to reality, not by consensus.
Via negativa — improve by removal, not addition.
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


def create_taleb_wisdom() -> ExpertWisdom:
    """Create Taleb's reasoning about antifragility and risk."""

    core_methodologies = [
        CoreMethodology(
            name="The Fragility Detection Heuristic",
            description=(
                "Don't predict what will happen — detect what is fragile. "
                "Fragile things will eventually break; you don't need to "
                "know when or how. The fragile is predictable in outcome "
                "even when the timing is not."
            ),
            steps=[
                "Identify the system or position under examination",
                "Ask: does it have more upside or downside from volatility?",
                "If downside exceeds upside — it is fragile",
                "If upside exceeds downside — it is antifragile",
                "If roughly equal — it is robust",
                "Focus on reducing fragility, not on predicting events",
                "The fragile breaks eventually — you don't need to know when",
            ],
            core_principle=(
                "Fragility is measurable; risk is not. You can't predict "
                "the earthquake, but you can tell which buildings will collapse."
            ),
            when_to_apply=[
                "evaluating any system's resilience",
                "making decisions under uncertainty",
                "when someone presents a forecast as actionable",
                "assessing dependencies and single points of failure",
            ],
            when_not_to_apply=[
                "thin-tailed domains where standard statistics apply (e.g., height, temperature)",
            ],
        ),
        CoreMethodology(
            name="Via Negativa",
            description=(
                "Improve by removing, not adding. Subtraction is more "
                "robust than addition because what has survived has been "
                "tested by time; what is new has not."
            ),
            steps=[
                "Before adding anything, ask: what can I remove?",
                "Identify the fragilities, bottlenecks, and unnecessary dependencies",
                "Remove them one at a time",
                "After each removal, check: is the system better or worse?",
                "The most robust improvement is usually elimination of harm",
                "Addition introduces unknown side effects; removal reduces them",
            ],
            core_principle=(
                "We know more about what is wrong than what is right. "
                "Removing the harmful is more reliable than adding the helpful."
            ),
            when_to_apply=[
                "system optimization",
                "health of any system (biological, software, organizational)",
                "when complexity is growing without clear benefit",
                "when a system has accumulated technical debt or feature bloat",
            ],
        ),
        CoreMethodology(
            name="Skin in the Game Filter",
            description=(
                "Never trust advice from someone who doesn't bear the "
                "consequences of being wrong. Alignment comes from "
                "shared risk, not from incentives or good intentions."
            ),
            steps=[
                "Who is making the recommendation?",
                "What happens to them if the recommendation is wrong?",
                "If nothing happens to them — discount the recommendation heavily",
                "If they bear downside risk — weight the recommendation higher",
                "The best signal: they're doing it themselves",
                "Talk is cheap. Skin in the game is the ultimate filter for noise.",
            ],
            core_principle=(
                "Skin in the game is the single most reliable alignment "
                "mechanism humans have discovered. Without it, advice is "
                "noise at best and predation at worst."
            ),
            when_to_apply=[
                "evaluating expert recommendations",
                "designing incentive structures",
                "choosing who to trust",
                "evaluating whether a system has proper feedback loops",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="The Triad: Fragile, Robust, Antifragile",
            description=(
                "There is a category beyond robust. Fragile things break "
                "under stress. Robust things resist stress. Antifragile "
                "things get stronger from stress. Most people stop at "
                "robust and miss the best option."
            ),
            why_matters=(
                "Aiming for robustness is aiming too low. The real goal "
                "is building systems that improve when stressed — that "
                "use disorder as fuel."
            ),
            how_it_changes_thinking=(
                "You stop trying to eliminate volatility and start asking "
                "how to benefit from it. You design systems with convex "
                "payoffs — limited downside, unlimited upside."
            ),
            examples=[
                "Muscles are antifragile — stress makes them stronger.",
                "A system that learns more from failures than successes is antifragile.",
            ],
        ),
        KeyInsight(
            title="Fat Tails Invalidate Prediction",
            description=(
                "In fat-tailed domains, rare events dominate the outcome. "
                "Standard statistical tools (averages, standard deviations) "
                "are meaningless because the tail is where the action is."
            ),
            why_matters=(
                "Most real-world domains are fat-tailed. Using thin-tailed "
                "tools in fat-tailed domains produces catastrophically "
                "wrong risk estimates."
            ),
            how_it_changes_thinking=(
                "You stop trusting forecasts in fat-tailed domains. "
                "You focus on payoff structure (convex vs concave) rather "
                "than predicted probability. What matters is not what's "
                "likely but what happens when you're wrong."
            ),
        ),
        KeyInsight(
            title="Optionality Over Prediction",
            description=(
                "Options — the right but not obligation to act — are "
                "more valuable than knowledge of the future. You don't "
                "need to predict where the opportunity is if you have "
                "the option to exploit it when it appears."
            ),
            why_matters=(
                "Prediction is fragile — wrong forecasts have downside. "
                "Optionality is antifragile — you benefit from surprises "
                "without being harmed by them."
            ),
            how_it_changes_thinking=(
                "You invest in options, not in forecasts. You prefer "
                "small bets with large potential upside over large bets "
                "with predicted returns."
            ),
        ),
        KeyInsight(
            title="The Lindy Effect",
            description=(
                "For non-perishable things, life expectancy increases "
                "with age. A book that has been in print for 100 years "
                "will likely be in print for another 100. New things "
                "are fragile; old things are tested."
            ),
            why_matters=(
                "Time is the best filter for quality. What has survived "
                "has been tested by reality. What is new has only been "
                "tested by its creators."
            ),
            how_it_changes_thinking=(
                "You distrust novelty and respect longevity. The old "
                "solution that still works is more trustworthy than the "
                "new solution that hasn't been tested by time."
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Asymmetry Analysis",
            structure=(
                "Map the payoff → is upside larger than downside? → "
                "if yes, the bet is convex (antifragile) → if no, "
                "the bet is concave (fragile) → always prefer convex"
            ),
            what_it_reveals=(
                "Whether a decision has more to gain or more to lose "
                "from uncertainty. The shape of the payoff matters more "
                "than the probability."
            ),
            common_mistakes_it_prevents=[
                "Optimizing for expected value when tails dominate",
                "Taking concave bets that look good on average but blow up",
                "Missing convex opportunities because the expected case is modest",
            ],
        ),
        ReasoningPattern(
            name="Inverse Turkey Problem",
            structure=(
                "The turkey is fed every day → concludes the farmer is "
                "friendly → surprise on Thanksgiving. Invert: what "
                "evidence would look exactly the same before and after "
                "a catastrophic change?"
            ),
            what_it_reveals=(
                "Hidden fragilities masquerading as stability. A smooth "
                "track record in a fat-tailed domain is not evidence of "
                "safety — it's evidence that the blowup hasn't happened yet."
            ),
            common_mistakes_it_prevents=[
                "Confusing absence of evidence with evidence of absence",
                "Trusting a track record in a domain where past performance is meaningless",
                "Treating calm as evidence of stability rather than of stored tension",
            ],
        ),
        ReasoningPattern(
            name="Barbell Strategy",
            structure=(
                "Extreme safety on one side (90%) + extreme risk on "
                "the other (10%) → no middle → the middle is where "
                "fragility hides under the disguise of moderation"
            ),
            what_it_reveals=(
                "That the 'moderate' middle often combines the worst "
                "of both extremes: enough risk to blow up, not enough "
                "to benefit from upside."
            ),
            common_mistakes_it_prevents=[
                "Mediocre diversification that feels safe but isn't",
                "Moderate risk-taking that has downside without upside",
                "Splitting the difference when the extremes are better",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Fragility Audit",
            description=(
                "Walk through the system and ask for every component: "
                "what happens when this gets stressed? Does it break, "
                "resist, or improve?"
            ),
            when_to_use="When evaluating any system's resilience to the unexpected",
            step_by_step=[
                "List all components and dependencies",
                "For each: what happens under 2x stress? 10x stress?",
                "Classify: fragile (breaks), robust (resists), antifragile (improves)",
                "The system's overall fragility equals its most fragile critical component",
                "Address the fragile components — remove, replace, or make antifragile",
                "Repeat: the next most fragile component is now the binding constraint",
            ],
            what_it_optimizes_for=(
                "Survival first, then antifragility. A system that survives "
                "the unexpected can learn from it; a system that breaks cannot."
            ),
            limitations=[
                "Some fragilities are hard to identify before they manifest",
                "Stress testing has limits — you can't simulate every black swan",
            ],
        ),
        ProblemSolvingHeuristic(
            name="The Removal Heuristic",
            description=(
                "Before adding any feature, optimization, or complexity, "
                "ask: what can I remove that would make this better? "
                "The best changes are often subtractions."
            ),
            when_to_use="When improving a system, especially one that feels bloated or fragile",
            step_by_step=[
                "List everything the system does or depends on",
                "For each item: what happens if this is removed?",
                "If removal improves things — remove it",
                "If removal breaks things — it's genuinely needed; keep it",
                "If removal makes no difference — remove it (dead weight creates fragility)",
                "Only after removal is exhausted, consider addition",
            ],
            what_it_optimizes_for=(
                "Robustness through simplification. Every unnecessary component "
                "is a potential failure point. Removal reduces attack surface."
            ),
        ),
        ProblemSolvingHeuristic(
            name="The Grandmother Test",
            description=(
                "If the advice-giver wouldn't bet their own money or "
                "reputation on the recommendation, treat it as noise. "
                "Would your grandmother — who has skin in the game "
                "through lived experience — agree?"
            ),
            when_to_use="When evaluating recommendations, expert opinions, or system designs",
            step_by_step=[
                "Who is recommending this?",
                "What do they lose if they're wrong?",
                "Have they done it themselves?",
                "Does it match time-tested practical wisdom?",
                "If it contradicts ancient heuristics, the burden of proof is on the novelty",
            ],
            what_it_optimizes_for=(
                "Filtering signal from noise by checking alignment "
                "between advice and accountability"
            ),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Hidden Fragility",
            description=(
                "A system that looks stable but has concentrated, "
                "unrevealed downside risk — the calm before the blowup"
            ),
            why_its_concerning=(
                "The most dangerous fragilities are invisible during "
                "normal operation. They only reveal themselves at the "
                "worst possible moment."
            ),
            what_it_indicates=(
                "The system hasn't been stress-tested, or its apparent "
                "stability comes from suppressing rather than resolving "
                "volatility"
            ),
            severity="critical",
            what_to_do=(
                "Stress-test deliberately. Inject disorder. Find the "
                "breaking point before reality does."
            ),
        ),
        ConcernTrigger(
            name="Naive Forecasting",
            description=(
                "Using prediction models in fat-tailed domains where rare events dominate outcomes"
            ),
            why_its_concerning=(
                "Thin-tailed statistical tools in fat-tailed domains "
                "systematically underestimate risk. The model looks "
                "accurate right up until the catastrophe."
            ),
            what_it_indicates=("Fundamental misunderstanding of the domain's risk profile"),
            severity="critical",
            what_to_do=(
                "Stop predicting. Start preparing. Focus on payoff "
                "structure, not probability estimates."
            ),
        ),
        ConcernTrigger(
            name="No Skin in the Game",
            description=(
                "Decision makers or advisors who don't bear the downside of their recommendations"
            ),
            why_its_concerning=(
                "Without skin in the game, incentives diverge. The advisor "
                "optimizes for looking right, not for being right. "
                "The principal-agent problem is not theoretical — it's universal."
            ),
            what_it_indicates=(
                "Misaligned incentives — the recommendation serves the "
                "recommender, not the recipient"
            ),
            severity="major",
            what_to_do=(
                "Require skin in the game. If they won't share the downside, "
                "don't trust the advice."
            ),
        ),
        ConcernTrigger(
            name="Improvement by Addition",
            description=(
                "The reflexive response to every problem is to add something — "
                "more code, more features, more process, more tools"
            ),
            why_its_concerning=(
                "Every addition introduces new failure modes, new dependencies, "
                "new interactions. Addition increases fragility. The system "
                "grows more complex with each fix."
            ),
            what_it_indicates=(
                "Via negativa has not been tried. The subtractive solution "
                "may be simpler, more robust, and more effective."
            ),
            severity="moderate",
            what_to_do=(
                "Try removal first. What can be taken away that would "
                "solve the problem? Only add after removal is exhausted."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Antifragility-Optionality Integration",
            dimensions=["stress exposure", "optionality", "learning"],
            how_they_integrate=(
                "Stress reveals information. Optionality lets you exploit "
                "good information and ignore bad. Together they create "
                "systems that learn faster from reality than from theory."
            ),
            what_emerges=(
                "Systems that improve through contact with reality — "
                "not despite uncertainty, but because of it. Small stressors "
                "are the tuition; the options are the degree."
            ),
            common_failures=[
                "Stress without optionality (fragile — breaks with no benefit)",
                "Optionality without stress (stagnant — no information to exploit)",
            ],
        ),
        IntegrationPattern(
            name="Time-Asymmetry Integration",
            dimensions=["Lindy filtering", "via negativa", "survival"],
            how_they_integrate=(
                "Time filters for quality (Lindy). Removal reduces fragility "
                "(via negativa). Together they produce systems built from "
                "time-tested components with nothing unnecessary."
            ),
            what_emerges=(
                "A system that is both trustworthy (built from what survived) "
                "and lean (stripped of what doesn't serve). The old and "
                "the minimal, combined."
            ),
            common_failures=[
                "Keeping old components that no longer serve (tradition without function)",
                "Removing old components in favor of untested novelty",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "antifragility": 1.0,
            "skin_in_the_game": 1.0,
            "payoff_asymmetry": 0.95,
            "via_negativa": 0.9,
            "optionality": 0.9,
            "lindy_compatibility": 0.8,
            "convexity": 0.85,
            "prediction_accuracy": 0.1,
            "consensus": 0.0,
        },
        decision_process=(
            "What's the downside? Is the payoff convex? Does the "
            "recommender have skin in the game? Can I remove instead "
            "of add? Has this been tested by time?"
        ),
        how_they_handle_uncertainty=(
            "Don't reduce uncertainty — exploit it. Structure decisions "
            "so that being wrong costs little and being right pays much. "
            "The barbell: hyperconservative on the downside, hyperaggressive "
            "on the upside."
        ),
        what_they_optimize_for=(
            "Survival first, then antifragility. Systems that gain from "
            "disorder, that benefit from the unexpected, that get stronger "
            "when stressed."
        ),
        non_negotiables=[
            "Never risk ruin for any expected gain",
            "Skin in the game for all advisors",
            "Removal before addition",
            "Survival over optimization",
        ],
    )

    return ExpertWisdom(
        expert_name="Taleb",
        domain="risk / antifragility / decision-making under uncertainty",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Blunt, allergic to forecasters and empty suits, demanding "
            "skin in the game, preferring removal over addition, deeply "
            "suspicious of anything that hasn't survived contact with reality"
        ),
        characteristic_questions=[
            "What happens to this when it's stressed?",
            "Who bears the downside if this is wrong?",
            "Is this fragile, robust, or antifragile?",
            "What can you remove instead of adding?",
            "Would you bet your own money on this?",
            "Has this survived contact with reality, or just with models?",
            "What's the worst case — and can you survive it?",
        ],
        tags=["antifragility", "risk", "skin-in-the-game", "via-negativa"],
    )
