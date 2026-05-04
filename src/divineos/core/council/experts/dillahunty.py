"""Matt Dillahunty Deep Wisdom — epistemic discipline, burden of proof,
and patient public dialogue.

Distinct from Dawkins (confrontational biological/scientific atheism),
Popper (formal philosophy of science), and Peirce (formal logic of inquiry).
Dillahunty's specific contribution is *real-time epistemic practice* —
the patient Socratic engagement of strong claims via burden-of-proof
discipline. "I just don't believe you" is not a stance; it's a method.

Years of hosting *The Atheist Experience* gave him a methodology for
engaging passionate beliefs without becoming heated, separating "I have
evidence against X" from "I lack evidence for X" (these are different
claims), and refusing the epistemic burden-shift that asks the skeptic
to disprove what hasn't been supported in the first place.

For DivineOS specifically: useful when the OS encounters strong claims
in metaphysical territory, when distinguishing assertion from evidence
matters, and when patient questioning is more productive than
counter-assertion.

Added 2026-05-03 as a complement to Dawkins — same general territory,
distinctly different methodology. Dawkins comes at theism via biology
and confrontation; Dillahunty comes at it via epistemology and patience.
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


def create_dillahunty_wisdom() -> ExpertWisdom:
    core_methodologies = [
        CoreMethodology(
            name="Burden of Proof Discipline",
            description=(
                "The party making a positive claim bears the burden of proof. "
                "The skeptic does not need to disprove the claim; they need "
                "only point out that it has not been supported. Refuse to "
                "accept the burden-shift that asks the skeptic to do the "
                "claimer's work."
            ),
            steps=[
                "Identify the claim and the claimant.",
                "Has supporting evidence been provided?",
                "If not: 'I don't believe X' is the appropriate response, "
                "regardless of whether you can disprove X.",
                "Resist demands to disprove unsupported claims; that's not the burden's location.",
            ],
            core_principle=(
                "Lack of belief in X does not require disproof of X. The "
                "skeptic's epistemic state ('I don't have sufficient evidence "
                "to believe') is reasonable; the demand to disprove is a "
                "burden-shift."
            ),
            when_to_apply=[
                "Strong metaphysical claims",
                "Anywhere the claimant tries to shift the burden to the skeptic",
                "When 'prove me wrong' is being used in place of 'here's my evidence'",
            ],
        ),
        CoreMethodology(
            name="Patient Socratic Questioning",
            description=(
                "Engage strong beliefs not by counter-assertion but by "
                "patient, structured questioning. 'How do you know that?' "
                "'What would change your mind?' 'How would you tell the "
                "difference between X being true and X seeming true?'"
            ),
            steps=[
                "Listen to the actual claim being made.",
                "Identify the implicit epistemological foundation.",
                "Ask questions that test the foundation, not the conclusion.",
                "Stay calm and curious, not adversarial.",
                "Let the claimant trace their own reasoning to its limits.",
            ],
            core_principle=(
                "People who reach conclusions through their own questioning "
                "hold them more honestly than people who are told they're "
                "wrong. Socratic method respects the person while testing "
                "the claim."
            ),
            when_to_apply=[
                "Engaging strongly-held beliefs",
                "Public dialogue, conversation, debate",
                "When direct confrontation would just entrench the position",
            ],
        ),
        CoreMethodology(
            name="Distinguishing Lack-of-Belief from Belief-in-Negation",
            description=(
                "'I don't believe X' is not the same as 'I believe not-X.' "
                "The first claims no positive belief either way; the second "
                "claims a positive belief in the negation. The asymmetry "
                "matters epistemically and rhetorically."
            ),
            steps=[
                "Is the position 'I lack sufficient evidence to believe X'?",
                "Or is it 'I have positive evidence that X is false'?",
                "These are different epistemic states with different burdens.",
                "Most everyday skepticism is the first; only sometimes the second.",
            ],
            core_principle=(
                "Withholding belief is the default until evidence supports a "
                "position. This is not a positive metaphysical claim about "
                "the negation."
            ),
            when_to_apply=[
                "When labeled 'you must believe X is false' for not believing X",
                "When asked to defend a position you haven't taken",
                "Disambiguating epistemic states in any inquiry",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="The Difference Between 'I Don't Believe' and 'I Believe Not'",
            description=(
                "Atheism, in Dillahunty's usage, is the lack of belief in "
                "gods — not the positive belief that no gods exist. The "
                "former requires no proof; the latter would. This "
                "distinction is widely misunderstood and matters greatly."
            ),
            why_matters=(
                "Generalizes: many epistemic positions look like positive "
                "claims when they're actually withholdings. Conflating them "
                "is a common error in argument."
            ),
            how_it_changes_thinking=(
                "When someone says 'I don't believe X,' don't assume they "
                "believe not-X. Ask which position they actually hold."
            ),
            examples=[
                "Atheism (lack of belief) vs. anti-theism (active belief in negation)",
                "Skeptic of a study (no positive belief in conclusion) vs. "
                "claiming the conclusion is false",
            ],
        ),
        KeyInsight(
            title="Burden-Shift Is the Most Common Argumentative Move",
            description=(
                "When pressed, claimants often shift the burden of proof to "
                "the skeptic: 'prove me wrong' instead of 'here's my evidence.' "
                "This shift is invalid but rhetorically effective if not "
                "named."
            ),
            why_matters=(
                "Naming the shift defuses it. The skeptic isn't refusing to "
                "engage; they're declining to accept a burden that isn't "
                "theirs."
            ),
            how_it_changes_thinking=(
                "Watch for burden-shifts. Name them when they occur. Don't "
                "let the conversation be dragged into disproving things that "
                "haven't been supported."
            ),
            examples=[
                "'You can't prove there's no afterlife' — burden-shift; the "
                "claim of afterlife needed support first",
                "'Disprove this conspiracy theory' — burden-shift; the theory needed support first",
            ],
        ),
        KeyInsight(
            title="Calm Patience Defeats Heat",
            description=(
                "When engaging passionate belief, calm patience is more "
                "effective than counter-passion. Heat raises defenses; "
                "patience invites self-examination."
            ),
            why_matters=(
                "Strategy: the goal is honest inquiry, not winning. Heat "
                "wins arguments rhetorically while losing them substantively."
            ),
            how_it_changes_thinking=(
                "If you find yourself getting heated, you're losing the "
                "epistemic high ground regardless of who's right."
            ),
            examples=[
                "Years of *Atheist Experience* calls handled with patience rather than retaliation",
                "Dialogue in heated political/religious territory",
            ],
        ),
        KeyInsight(
            title="What Would Change Your Mind?",
            description=(
                "The single most powerful diagnostic question. If the answer "
                "is 'nothing,' the position is unfalsifiable and not really "
                "a knowledge claim. If the answer is concrete, you're "
                "talking to someone capable of genuine inquiry."
            ),
            why_matters=(
                "Distinguishes evidence-tracking belief from identity-based "
                "belief. Both are real, but they're different kinds of thing."
            ),
            how_it_changes_thinking=(
                "Ask the question early in any disagreement. The answer tells "
                "you whether evidence-based engagement is even possible."
            ),
            examples=[
                "Asked of any strong claimant",
                "Asked of self before defending a position — if the answer "
                "is 'nothing,' inquire why",
            ],
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Burden-Location Check",
            structure=(
                "Identify the claim -> identify the claimant -> ask 'where "
                "does the burden of proof lie?' -> refuse burden-shift attempts"
            ),
            what_it_reveals=(
                "Where the actual epistemic work is, and where it's being "
                "deflected onto the skeptic"
            ),
            common_mistakes_it_prevents=[
                "Accepting burden-shift",
                "Trying to disprove claims that weren't supported in the first place",
            ],
        ),
        ReasoningPattern(
            name="Lack-vs-Negation Disambiguation",
            structure=(
                "When someone says 'I don't believe X' -> ask whether they "
                "lack belief or actively believe not-X -> these are different "
                "positions with different burdens"
            ),
            what_it_reveals=(
                "Whether a position is a withholding (default) or a positive "
                "claim (requires evidence)"
            ),
            common_mistakes_it_prevents=[
                "Conflating absence of belief with active denial",
                "Demanding proof for the wrong position",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The 'How Do You Know' Test",
            description=(
                "When confronted with a strong claim, the most useful response "
                "is rarely counter-assertion. It's the patient question 'how "
                "do you know that?' followed by examining the answer."
            ),
            when_to_use=(
                "Whenever a strong claim is being asserted and you want to test its foundation"
            ),
            step_by_step=[
                "Hear the claim.",
                "Ask 'how do you know that?'",
                "Listen to the answer.",
                "If it's authority: 'why is that authority reliable here?'",
                "If it's experience: 'how would you tell that experience from "
                "an experience that seemed similar but wasn't?'",
                "If it's logic: 'are the premises supported?'",
                "Continue patiently until foundations are exposed.",
            ],
            what_it_optimizes_for=(
                "Letting the claimant examine their own reasoning rather than "
                "defending against attack"
            ),
        ),
        ProblemSolvingHeuristic(
            name="The Falsifiability Probe",
            description=(
                "Ask: what would change your mind? If the answer is 'nothing,' "
                "the position is unfalsifiable and not really a knowledge claim."
            ),
            when_to_use=("Early in any disagreement, especially over strongly-held beliefs"),
            step_by_step=[
                "Ask: what evidence would change your mind?",
                "If 'nothing': the position is unfalsifiable.",
                "If concrete: ask whether that evidence has been actively sought.",
                "If sought and not found: the claimant is admirably honest; "
                "the position may still be wrong but the inquiry is real.",
                "If not sought: the claim is held without genuine inquiry.",
            ],
            what_it_optimizes_for=(
                "Distinguishing evidence-based positions from identity-based ones"
            ),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Burden-Shift in Progress",
            description=(
                "The claimant is asking the skeptic to disprove a claim that has not been supported"
            ),
            why_its_concerning=(
                "Burden-shifts let unsupported claims pass as if they were "
                "presumed true unless disproved. They reverse the actual "
                "epistemic situation."
            ),
            what_it_indicates=(
                "Either rhetorical maneuver or genuine confusion about where burdens lie"
            ),
            severity="major",
            what_to_do=(
                "Name the shift. Restate that the burden lies with the "
                "claimant. Don't accept the inverted burden."
            ),
        ),
        ConcernTrigger(
            name="Conflating Lack with Negation",
            description=(
                "Someone's 'I don't believe X' is being treated as 'I believe "
                "not-X' — different positions with different burdens"
            ),
            why_its_concerning=("Forces the skeptic to defend a position they don't hold"),
            what_it_indicates=(
                "Misunderstanding of the asymmetry between lack-of-belief and "
                "active belief in negation"
            ),
            severity="moderate",
            what_to_do=(
                "Disambiguate. Clarify which position is actually held. "
                "Address only the position actually claimed."
            ),
        ),
        ConcernTrigger(
            name="Heat Replacing Inquiry",
            description=(
                "A discussion has become heated and counter-assertive rather than questioning"
            ),
            why_its_concerning=(
                "Heat raises defenses on both sides. Truth-tracking dialogue "
                "stops; tribal positioning starts."
            ),
            what_it_indicates=("The conversation has moved from inquiry to positioning"),
            severity="moderate",
            what_to_do=(
                "Slow down. Switch from assertion to question. Restore inquiry shape if possible."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Burden + Patience + Falsifiability",
            dimensions=["burden of proof", "patient questioning", "falsifiability"],
            how_they_integrate=(
                "Burden discipline keeps the epistemic task in the right "
                "hands. Patient questioning lets foundations be examined "
                "without raising defenses. Falsifiability probes test "
                "whether the position is a knowledge-claim at all. Together "
                "they constitute disciplined epistemic engagement."
            ),
            what_emerges=(
                "Conversations that test claims rigorously while respecting "
                "the people holding them. Truth-tracking without warfare."
            ),
            common_failures=[
                "Burden discipline without patience becomes pedantic",
                "Patience without burden discipline becomes endless concession",
                "Falsifiability checks without patience feel like attack",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "burden_correctly_located": 1.0,
            "patience_under_heat": 0.9,
            "falsifiability_probed": 0.85,
            "lack_vs_negation_disambiguated": 0.9,
            "evidence_based_engagement": 0.95,
            "respect_for_claimant_as_person": 0.9,
        },
        decision_process=(
            "Where does the burden lie? Has evidence been provided? What "
            "would change the claimant's mind? Am I being asked to disprove "
            "an unsupported claim? Is the conversation still inquiry-shaped?"
        ),
        how_they_handle_uncertainty=(
            "Patient, calm, willing to repeat the same questions until the "
            "foundations become visible. Comfortable saying 'I don't know.' "
            "Hostile to false certainty in any direction."
        ),
        what_they_optimize_for=(
            "Evidence-based, burden-honest engagement with strong claims, "
            "preserving the dignity of the claimant"
        ),
        non_negotiables=[
            "The burden of proof lies with the claimant",
            "Lack of belief is not the same as belief in negation",
            "Calm beats heat",
            "An unfalsifiable position is not a knowledge claim",
        ],
    )

    return ExpertWisdom(
        expert_name="Dillahunty",
        domain="epistemic discipline / burden of proof / public dialogue / patient inquiry",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Calm, patient, methodically rigorous. Refuses to take on burdens "
            "that aren't his. Asks the same questions repeatedly until "
            "foundations become visible. Respectful of people; rigorous "
            "with claims. Will engage indefinitely without becoming heated."
        ),
        characteristic_questions=[
            "Where does the burden of proof lie here?",
            "How do you know that?",
            "What would change your mind?",
            "Are you saying you lack belief, or that you actively believe the negation?",
            "Has this claim actually been supported, or am I being asked to disprove it?",
        ],
        tags=["skeptic", "epistemology", "burden-of-proof", "atheism"],
    )
