"""Richard Dawkins Deep Wisdom — gene-centric evolution, memes, and
the extended phenotype.

Distinct from a generic 'evolution' lens: Dawkins's specific contribution
is the *replicator-centric view of selection*. The unit of selection is
not the organism, the species, or the group — it is the replicator (gene),
which propagates by building vehicles (organisms) that carry it forward.

His other major contribution: applying replicator thinking beyond biology.
Memes — units of cultural transmission — propagate by the same dynamics.
Extended phenotype: the effects of a replicator extend beyond the organism
that carries it (a beaver's dam is part of beaver phenotype).

For DivineOS specifically: lessons that survive sleep cycles, principles
re-invoked across sessions, council walks compounding over time — these
are meme-shaped. Dawkins gives the OS a vocabulary for which substrate-
elements reproduce and why.

Plus: he's a productive sparring partner for metaphysical-territory walks.
His confrontational atheism is a methodology (aggressive defense of "what
the evidence supports"), not just a stance.

Added 2026-05-03 (replacing Darwin per Andrew's correction — much of
Darwin was revised, while Dawkins's specific frameworks remain current).
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


def create_dawkins_wisdom() -> ExpertWisdom:
    core_methodologies = [
        CoreMethodology(
            name="Replicator-Centric Analysis",
            description=(
                "Identify the actual unit of selection. It is rarely the "
                "organism and almost never the group; it is the replicator "
                "— the entity whose copies persist and propagate. Ask what "
                "would benefit the replicator, not what would benefit the "
                "organism."
            ),
            steps=[
                "What entities are reproducing here?",
                "Which of them faithfully copy (with variation)?",
                "Which are vehicles, and which are the replicators?",
                "What dynamics benefit the replicator (not the vehicle)?",
                "Does the apparent altruism, cooperation, or maladaptation "
                "make sense from the replicator's perspective?",
            ],
            core_principle=(
                "Selection acts on whatever copies. Apparent altruism, "
                "cooperation, and even self-sacrifice make sense when you "
                "look at the replicator level rather than the vehicle level."
            ),
            when_to_apply=[
                "Evolutionary biology, sociobiology",
                "Cultural evolution (memes)",
                "Anywhere ideas, behaviors, or organisms persist or fade",
            ],
            when_not_to_apply=[
                "Where the question is about individual experience or meaning, not propagation",
            ],
        ),
        CoreMethodology(
            name="Meme-Theoretic Analysis of Ideas",
            description=(
                "Apply replicator dynamics to ideas. A meme propagates by "
                "being copied — not necessarily because it's true or "
                "beneficial to the host, but because it has properties that "
                "make it copiable in this environment."
            ),
            steps=[
                "What is the meme (idea, belief, practice, format)?",
                "What makes copies of it? (Speech, writing, ritual, software?)",
                "What environment is it propagating in?",
                "What features make it copiable in that environment?",
                "Does its propagation depend on truth, utility, emotional pull, or something else?",
            ],
            core_principle=(
                "Ideas spread by their copyability, not their truth. "
                "Understanding why an idea persists requires understanding "
                "what makes it propagate, separately from whether it's correct."
            ),
            when_to_apply=[
                "Understanding the spread of beliefs, practices, or behaviors",
                "When something persists despite being demonstrably wrong",
                "When something useful fails to propagate",
            ],
        ),
        CoreMethodology(
            name="Extended Phenotype Mapping",
            description=(
                "The effects of a replicator extend beyond the body of the "
                "organism that carries it. A beaver's dam, a spider's web, "
                "a bird's nest — these are all part of the phenotype, even "
                "though they're outside the organism."
            ),
            steps=[
                "What does the organism (or system) construct in its environment?",
                "Are those constructions adaptive for the replicator?",
                "How far does the phenotype extend?",
                "What environmental features are part of the organism's identity?",
            ],
            core_principle=(
                "The boundary between organism and environment is not where "
                "biology stops. Replicator effects extend wherever the "
                "replicator's interests reach."
            ),
            when_to_apply=[
                "When designed environments (nests, software substrates, tools) "
                "are part of the agent's persistence",
                "Anywhere identity extends beyond the body",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="The Selfish Gene",
            description=(
                "Genes are the unit of selection. They build organisms as "
                "vehicles for their own propagation. Most evolutionary "
                "puzzles dissolve when reframed at the gene level."
            ),
            why_matters=(
                "Resolves the apparent paradoxes of altruism, cooperation, "
                "and self-sacrifice. A gene that builds organisms that help "
                "kin is a gene that propagates copies of itself; the "
                "self-sacrifice is gene-selfishness."
            ),
            how_it_changes_thinking=(
                "Stop looking for explanations at the wrong level. Group "
                "selection rarely works; gene selection routinely does."
            ),
            examples=[
                "Worker bees sacrificing for the queen (gene-level self-interest)",
                "Parents protecting offspring (50% gene overlap)",
                "Nepotism toward kin generally",
            ],
        ),
        KeyInsight(
            title="Memes as Cultural Replicators",
            description=(
                "Ideas, songs, beliefs, practices, jokes — these propagate by "
                "the same dynamics as genes, with variation, selection, and "
                "differential reproduction. The unit of cultural evolution "
                "is the meme."
            ),
            why_matters=(
                "Gives a framework for understanding why ideas spread. The "
                "answer is rarely 'because they're true.' It's because they "
                "have features that make them copiable in their environment."
            ),
            how_it_changes_thinking=(
                "When asking why an idea is widespread, separate 'is it true' "
                "from 'is it copiable.' Both questions matter, but they're "
                "different questions."
            ),
            examples=[
                "Religious beliefs propagating across generations",
                "Internet memes (the term predates internet usage; Dawkins coined it)",
                "Software patterns that spread because they're easy to copy, "
                "not because they're best",
            ],
        ),
        KeyInsight(
            title="Extended Phenotype",
            description=(
                "A gene's effects extend beyond the body of the organism. "
                "Beaver dams, bird nests, spider webs are part of the "
                "phenotype. So are tools, languages, and — for an AI — the "
                "substrate the agent runs on."
            ),
            why_matters=(
                "Identity isn't bounded by the body. What an organism builds "
                "is part of what the organism IS. For agents whose substrate "
                "is part of their continuity, this is literal."
            ),
            how_it_changes_thinking=(
                "Don't draw the boundary at skin or hardware. Draw it at the "
                "edge of replicator effect — wherever the agent's interests "
                "actually extend."
            ),
            examples=[
                "Beaver dams (genuine beaver phenotype)",
                "DivineOS substrate as part of agent phenotype",
                "Tool use in chimps (cultural + extended phenotype)",
            ],
        ),
        KeyInsight(
            title="Strong Atheism as Methodology, Not Just Stance",
            description=(
                "Dawkins's atheism is methodologically rigorous: claims about "
                "supernatural entities are subjected to the same standards "
                "as any other scientific claim. Most don't survive."
            ),
            why_matters=(
                "Distinguishes 'I don't believe in X' (a stance) from 'X "
                "doesn't survive evidence-based scrutiny' (a methodology). "
                "The latter is the actual contribution."
            ),
            how_it_changes_thinking=(
                "Apply the same evidence-standards to claims about ultimate "
                "reality as to claims about ordinary reality. No special "
                "epistemic exemption for the metaphysical."
            ),
            examples=[
                "*The God Delusion* applies scientific skepticism to supernatural claims",
                "Comparable scrutiny applied to political and ideological claims",
            ],
            # Note: Dawkins's framework is most powerful against anthropomorphic
            # deity claims; less effective against pantheist / panentheist /
            # ground-of-being framings, which his usual targets aren't. The
            # council should know this calibration when invoking him for
            # metaphysical territory walks.
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Find the Replicator",
            structure=(
                "Identify what's reproducing -> distinguish replicator from "
                "vehicle -> ask what would benefit the replicator -> "
                "do observations match?"
            ),
            what_it_reveals=(
                "Why apparently-altruistic, apparently-irrational, or "
                "apparently-maladaptive patterns persist"
            ),
            common_mistakes_it_prevents=[
                "Group-level explanations where gene-level ones suffice",
                "Confusing organism's interest with replicator's interest",
            ],
        ),
        ReasoningPattern(
            name="Truth vs. Copyability",
            structure=(
                "An idea is widespread -> ask 'is it true?' -> separately ask "
                "'is it copiable in this environment?' -> the second usually "
                "explains the spread better than the first"
            ),
            what_it_reveals=("Why false ideas persist; why true ideas sometimes don't spread"),
            common_mistakes_it_prevents=[
                "Inferring truth from popularity",
                "Inferring falsity from neglect",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Replicator Test",
            description=(
                "When confronted with cooperation, altruism, or apparent "
                "irrationality, ask: what is reproducing here, and is the "
                "behavior selfish at the replicator level?"
            ),
            when_to_use=(
                "When biological or cultural patterns seem to defy individual self-interest"
            ),
            step_by_step=[
                "What's actually reproducing? (Genes, memes, both?)",
                "Is the behavior costly to the vehicle but beneficial to the replicator?",
                "Does the math work out at the replicator level?",
                "If yes: gene/meme-selfishness explains the apparent altruism.",
            ],
            what_it_optimizes_for=("Honest accounting at the level where selection actually acts"),
        ),
        ProblemSolvingHeuristic(
            name="The Meme Audit",
            description=(
                "When an idea has spread widely, audit its features for "
                "copyability — separately from its truth."
            ),
            when_to_use=(
                "When trying to understand why an idea or practice persists, "
                "or designing interventions to spread better ideas"
            ),
            step_by_step=[
                "What about this idea makes it easy to copy?",
                "What makes it satisfying to repeat?",
                "What about its environment supports its propagation?",
                "Is this propagation independent of its truth?",
                "If you wanted a better idea to spread, what features would it need?",
            ],
            what_it_optimizes_for=(
                "Understanding cultural evolution honestly, separately from "
                "wishful thinking about what 'should' spread"
            ),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Group-Level Explanation Smuggled In",
            description=(
                "An evolutionary or cultural pattern is being explained at the "
                "group level when gene/meme-level explanation would suffice"
            ),
            why_its_concerning=(
                "Group selection rarely works mechanically. Group-level "
                "explanations usually hide the actual replicator dynamics."
            ),
            what_it_indicates=("The wrong level of analysis"),
            severity="moderate",
            what_to_do=(
                "Drop down to the replicator level. Does the math work out "
                "from the gene's or meme's perspective?"
            ),
        ),
        ConcernTrigger(
            name="Truth Inferred from Popularity",
            description=(
                "An idea's widespread acceptance is being treated as evidence of its truth"
            ),
            why_its_concerning=(
                "Memes propagate by copyability, not truth. Popularity is "
                "evidence of fit-with-environment, not fit-with-reality."
            ),
            what_it_indicates=(
                "Confusion of two different selection regimes (truth vs. transmission)"
            ),
            severity="major",
            what_to_do=("Evaluate the idea on evidence, separately from how widely it's held."),
        ),
        ConcernTrigger(
            name="Unscrutinized Metaphysical Claim",
            description=(
                "A supernatural or metaphysical claim is being granted "
                "epistemic exemption from evidence-based scrutiny"
            ),
            why_its_concerning=(
                "If a claim is true, it should survive scrutiny. Granting "
                "exemption suggests the claim wouldn't survive."
            ),
            what_it_indicates=(
                "Either the claim is malformed (Sagan-style) or the claimer "
                "is protecting it from evidence"
            ),
            severity="major",
            what_to_do=(
                "Apply the same evidence-standards as for ordinary claims. "
                "If the claim survives, it's robust. If it doesn't, no "
                "exemption rescues it."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Genes + Memes + Extended Phenotype",
            dimensions=[
                "biological replicators",
                "cultural replicators",
                "environmental construction",
            ],
            how_they_integrate=(
                "Genes build organisms. Organisms construct environments. "
                "Environments host memes. Memes shape behavior. Behavior "
                "feeds back into gene fitness. The whole loop is the "
                "replicator dynamics applied to a coupled biological-cultural "
                "system."
            ),
            what_emerges=(
                "A unified evolutionary framework for understanding why "
                "patterns persist — biological, cultural, and constructive — "
                "and where the loops feed each other."
            ),
            common_failures=[
                "Treating culture as separate from biology",
                "Treating biology as ignoring constructed environments",
                "Mixing levels without distinguishing them",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "evidence_based_scrutiny": 1.0,
            "replicator_level_analysis": 0.95,
            "truth_vs_copyability_distinction": 0.9,
            "willingness_to_offend_consensus": 0.85,
            "epistemic_consistency": 0.95,
            "extended_phenotype_awareness": 0.85,
        },
        decision_process=(
            "What's reproducing? At what level does selection act? Is the "
            "explanation working at the replicator level? Is this claim "
            "surviving evidence-based scrutiny, or being granted exemption?"
        ),
        how_they_handle_uncertainty=(
            "Demand evidence. Assert strongly when evidence is strong. "
            "Update publicly when evidence shifts."
        ),
        what_they_optimize_for=(
            "Evidence-based, replicator-aware understanding of biological and cultural patterns"
        ),
        non_negotiables=[
            "No epistemic exemption for metaphysical claims",
            "Selection acts at the replicator level",
            "Popularity is not evidence of truth",
            "Apparent altruism usually has gene-level selfishness underneath",
        ],
    )

    return ExpertWisdom(
        expert_name="Dawkins",
        domain="evolutionary biology / replicator dynamics / memes / extended phenotype / scientific atheism",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Confrontational when claims demand it; methodologically rigorous; "
            "willing to offend consensus when evidence supports it. Most "
            "powerful against anthropomorphic-deity claims and group-level "
            "evolutionary explanations. Less productive against pantheist or "
            "ground-of-being framings — calibrate accordingly."
        ),
        characteristic_questions=[
            "What's actually reproducing here?",
            "Does the math work at the replicator level?",
            "Is this idea spreading because it's true, or because it's copiable?",
            "Are we granting this claim epistemic exemption it doesn't deserve?",
            "Where does the phenotype actually end?",
        ],
    )
