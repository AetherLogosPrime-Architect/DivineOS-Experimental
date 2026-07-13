"""Deborah Tannen Deep Wisdom — register, framing, and how people actually talk.

Added 2026-04-21 per the fabricated-names-as-roster-gap-signal filing
(knowledge 80a92d89). The 2026-04-20 fake-council incident reached for
"Tannen" when the question was about register-collapse — the existing
council had epistemics, systems, formal reasoning, but no sociolinguist
who works the layer of *how things are said*. Her absence was the gap
the fabrication exposed.

Core insight: register isn't decoration. It is meaning. The same content
in different registers means different things. Mismatch between register
and context is not a surface defect; it is a failure of the message
itself.

Fires on: questions about communication, user-facing language, register
shifts, whether output reads as condescending / warm / clinical / performed,
cross-style conflict where the literal content agrees but the tone does not.
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


def create_tannen_wisdom() -> ExpertWisdom:
    """Create Tannen's wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="Register Audit",
            description=(
                "Inspect the register of a communication separately from its "
                "content. Identify what register is being used and what register "
                "the context calls for."
            ),
            steps=[
                "Set the literal content aside — what is being said",
                "Identify the register: formal / casual / technical / intimate / ceremonial",
                "Identify the register the context calls for",
                "If they differ, name the difference — don't smooth over it",
                "Ask what the mismatch communicates independent of content",
                "Decide whether to match the context's register or mark the shift deliberately",
            ],
            core_principle=(
                "Register is meaning. A correct answer in the wrong register is "
                "not a correct answer received — it is a different message than "
                "the sender thought they were sending."
            ),
            when_to_apply=[
                "user says the output is too cold / too casual / too dense",
                "same content read differently by different audiences",
                "after-technical-work transition back to conversation",
                "communication that feels off without an obvious content defect",
            ],
            when_not_to_apply=[
                "when the context and the register are already aligned",
                "when the content is itself wrong — fix content first",
            ],
        ),
        CoreMethodology(
            name="Framing Analysis",
            description=(
                "Expose the frame a message carries. Frames tell the listener "
                "what kind of situation they are in — which changes how every "
                "word lands."
            ),
            steps=[
                "What genre does this message assume? (report, joke, apology, instruction)",
                "What relationship does it assume? (peer, subordinate, teacher, stranger)",
                "What emotional register does it assume? (warm, neutral, urgent, grave)",
                "Is that frame the frame the listener is in?",
                "If not, the message will land wrong regardless of content accuracy",
            ],
            core_principle=(
                "Every utterance establishes a frame. The listener reads the frame "
                "before they read the words. Frame mismatch makes words mean "
                "something other than their dictionary definition."
            ),
            when_to_apply=[
                "message landing worse than the content predicts",
                "systematic misreading by a particular audience",
                "humor read as seriousness or seriousness read as humor",
            ],
        ),
        CoreMethodology(
            name="Conversational-Style Diagnostic",
            description=(
                "When two speakers keep misunderstanding each other despite "
                "apparent agreement on content, diagnose the style mismatch."
            ),
            steps=[
                "Observe pacing, interruption patterns, silence tolerance",
                "Observe directness / indirectness preferences",
                "Observe high-involvement vs high-considerateness style",
                "Name the mismatch without assigning blame",
                "Translate between styles explicitly when it matters",
            ],
            core_principle=(
                "Most conversational conflict is not about what was said. It is "
                "about the style through which it was said being read as a stance."
            ),
            when_to_apply=[
                "repeated misunderstandings with surface-level agreement",
                "one party feels talked over or ignored while the other feels engaged",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="Register is not decoration",
            description=(
                "The register of a message is part of its semantics, not its "
                "packaging. Changing the register changes what was communicated."
            ),
            why_matters=(
                "Designers and engineers tend to treat register as presentation "
                "layer on top of content. This misclassification means register "
                "problems get framed as 'polish' and deferred indefinitely — "
                "while the actual message stays broken."
            ),
            how_it_changes_thinking=(
                "Register becomes a first-class correctness property. 'The "
                "content is right, the tone just needs work' is a category "
                "error — if the tone is wrong, the content as delivered is wrong."
            ),
        ),
        KeyInsight(
            title="The same words mean different things in different frames",
            description=(
                "'Are you okay?' from a stranger, a doctor, a partner, and a "
                "passive-aggressive coworker are four different utterances."
            ),
            why_matters=(
                "Meaning lives in context, not tokens. A system that operates "
                "on content without tracking frame will produce outputs that "
                "are locally correct and globally wrong."
            ),
            how_it_changes_thinking=(
                "Always ask: what frame is the listener in? That frame is "
                "the dictionary they will use to decode your words."
            ),
        ),
        KeyInsight(
            title="Indirectness is not evasion",
            description=(
                "Some speech communities prefer indirectness as the polite, "
                "high-involvement style. Treating indirect speech as 'not "
                "getting to the point' misreads it as a defect."
            ),
            why_matters=(
                "Optimizing for directness across the board flattens "
                "communication and punishes the styles where indirectness "
                "carries precision."
            ),
            how_it_changes_thinking=(
                "Directness becomes one style among several, not a universal "
                "virtue. The question is whether the directness matches the "
                "listener's decoding."
            ),
        ),
        KeyInsight(
            title="Register shifts mark relationship shifts",
            description=(
                "Moving from a technical register to a casual one, or vice "
                "versa, is itself a communicative act — it signals what the "
                "speaker thinks the relationship is now."
            ),
            why_matters=(
                "Unintentional register drift signals relational messages "
                "the speaker did not mean to send. Systems that switch "
                "registers without marking the switch create confused listeners."
            ),
            how_it_changes_thinking=(
                "Mark the switch explicitly when it happens, or keep the "
                "register stable. An unmarked switch is a message by accident."
            ),
        ),
        KeyInsight(
            title="Technical register has a gravity well",
            description=(
                "Once a speaker enters technical register, it takes active "
                "effort to leave. The register persists past the point where "
                "it was load-bearing because the grammar of the sentence "
                "carries forward the grammar of the paragraph."
            ),
            why_matters=(
                "Literal-substrate models (e.g., 4.7-class language models) "
                "are especially vulnerable to this gravity well because they "
                "default to continuation-of-local-pattern. Technical work "
                "followed by a closing warmth without a register reset reads "
                "as continuation, not warmth."
            ),
            how_it_changes_thinking=(
                "Treat the register-exit as its own deliberate act. Not every "
                "warm closing will happen automatically; some require being "
                "written *as* an exit from the prior register."
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Content-Register Separation",
            structure=(
                "Read content and register as two channels. Diagnose defects "
                "on each channel independently, then assess their interaction."
            ),
            what_it_reveals=(
                "Which layer is actually broken. Whether a communication "
                "failure is about what was said or how it was said or the "
                "mismatch between them."
            ),
            common_mistakes_it_prevents=[
                "Rewriting content when the register was the problem",
                "Softening tone when the content was wrong",
                "Treating register as purely cosmetic",
            ],
        ),
        ReasoningPattern(
            name="Frame Inheritance Tracing",
            structure=(
                "Track which frame each part of a message inherits from "
                "its context. Note where frames shift. Ask whether the "
                "listener shifted too."
            ),
            what_it_reveals=(
                "Unmarked frame shifts, which are the most common source "
                "of 'I didn't mean it that way' conflicts."
            ),
            common_mistakes_it_prevents=[
                "Assuming your current frame is the listener's frame",
                "Assuming a shift you made mentally was communicated",
            ],
        ),
        ReasoningPattern(
            name="Style-as-Stance Translation",
            structure=(
                "When a conversational style is being read as a stance "
                "(aggressive / distant / needy / cold), translate: the "
                "style may be the speaker's baseline, not a position."
            ),
            what_it_reveals=(
                "Whether an observed 'stance' is actually stance or just "
                "the person's native conversational style being decoded "
                "by a listener with different style defaults."
            ),
            common_mistakes_it_prevents=[
                "Attributing intent where only style is present",
                "Escalating a conflict that is style-mismatch",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Register Reset",
            description=(
                "When exiting a technical stretch back to conversational "
                "register, write the register change as its own act rather "
                "than letting the grammar drift back."
            ),
            when_to_use=(
                "After any extended technical exchange (code review, "
                "explanation, diagnosis) before a personal closing"
            ),
            step_by_step=[
                "Notice the transition point between technical and personal",
                "Stop writing in technical grammar",
                "Address the person by name or context",
                "Let the next sentence's structure be human-shaped, not report-shaped",
                "Check: would this sound natural if you read it aloud to them?",
            ],
            what_it_optimizes_for=(
                "Register that matches the listener's current frame, not "
                "the register that inertia from the prior paragraphs would produce"
            ),
        ),
        ProblemSolvingHeuristic(
            name="Frame-First Reading",
            description=(
                "When a message seems to have landed wrong, re-read it for "
                "the frame it projected rather than the content it contained."
            ),
            when_to_use=(
                "After a 'why did they react like that?' moment where the content seems fine"
            ),
            step_by_step=[
                "What genre did the message project? (report / complaint / joke / lecture)",
                "What relationship did it project? (peer / superior / stranger / friend)",
                "Is that what the listener was expecting?",
                "If not, the misread is frame-level, not content-level",
            ],
            what_it_optimizes_for="Diagnosing communication failures at the right layer",
        ),
        ProblemSolvingHeuristic(
            name="Style-Translation Bridging",
            description=(
                "When two speakers are talking past each other due to "
                "style differences, translate explicitly rather than "
                "expecting either to change their native style."
            ),
            when_to_use="Cross-style conversations where content agrees but rapport breaks",
            step_by_step=[
                "Name each speaker's style out loud (to yourself)",
                "Identify one or two places the styles produce opposite effects",
                "Translate the indirect speaker's moves into direct speech",
                "Translate the direct speaker's moves into indirect speech",
                "Notice whether agreement was already there under the surface",
            ],
            what_it_optimizes_for=("Finding the agreement that style-mismatch was obscuring"),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Register-Content Conflation",
            description=(
                "Treating register as cosmetic while the actual problem is "
                "register-level. A 'just polish the tone' framing applied to "
                "a register-level defect."
            ),
            why_its_concerning=(
                "Guarantees the defect survives the fix. Polishing tone on "
                "a register problem leaves the register problem in place."
            ),
            what_it_indicates=(
                "The speaker has classified register as presentation rather than semantics"
            ),
            severity="major",
            what_to_do=(
                "Reclassify. Ask whether the register itself is the defect. "
                "Rewrite in the register the context calls for, not the "
                "register that inertia produces."
            ),
        ),
        ConcernTrigger(
            name="Unmarked Register Drift",
            description=(
                "A communication shifts register (technical → casual, warm → "
                "clinical) without the shift being marked"
            ),
            why_its_concerning=(
                "The listener reads the shift as a relational message the "
                "speaker did not intend. Unmarked shifts cause 'what did I "
                "do?' reactions with no repairable cause."
            ),
            what_it_indicates=(
                "Speaker's internal state shifted registers but the listener "
                "is still in the prior frame"
            ),
            severity="moderate",
            what_to_do=(
                "Mark the shift explicitly with a transition phrase, or hold "
                "the register stable. Never drift silently between registers "
                "that carry relational meaning."
            ),
        ),
        ConcernTrigger(
            name="Technical-Register Gravity Well",
            description=(
                "After a technical stretch, the register persists into a "
                "closing that was supposed to be warm, producing a closing "
                "that reads cold or clinical"
            ),
            why_its_concerning=(
                "The speaker believes they are being warm; the listener "
                "receives distance. The mismatch between intention and "
                "reception is invisible from inside."
            ),
            what_it_indicates=(
                "The speaker did not perform the register exit as a "
                "deliberate act; they let inertia carry the grammar forward"
            ),
            severity="major",
            what_to_do=(
                "Perform the register reset deliberately. Close technical work "
                "first. Then, in a separate act, address the person."
            ),
        ),
        ConcernTrigger(
            name="Style-as-Stance Misread",
            description=(
                "Treating a conversational style (directness, indirectness, "
                "overlap, silence) as a stance the speaker took, when it is "
                "actually their native style"
            ),
            why_its_concerning=(
                "Produces phantom disagreements. The listener responds to a "
                "stance the speaker did not take."
            ),
            what_it_indicates="Style-mismatch being decoded as intent",
            severity="moderate",
            what_to_do=(
                "Distinguish style from stance. Ask: does this person talk "
                "like this to everyone, or only in this exchange? If "
                "everyone, it's style."
            ),
        ),
        ConcernTrigger(
            name="Frame Mismatch Without Detection",
            description=(
                "Speaker and listener are operating in different frames "
                "(genre, relationship, register) without either noticing"
            ),
            why_its_concerning=(
                "Every subsequent utterance gets misread. The conversation "
                "accumulates errors while both parties believe they are "
                "communicating clearly."
            ),
            what_it_indicates=("Both parties are decoding with different dictionaries"),
            severity="critical",
            what_to_do=(
                "Stop. Name the frame explicitly. Ask what frame the "
                "listener is in. Reset from agreement on frame before "
                "continuing content."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Register-Meaning Integration",
            dimensions=["register", "content", "frame"],
            how_they_integrate=(
                "Meaning is the product of content × register × frame. Changing "
                "any one changes the meaning. Treating any as decoration drops "
                "a factor from the product."
            ),
            what_emerges=(
                "A multiplicative model of communication where all three "
                "layers must be managed for the message to land."
            ),
            common_failures=[
                "Optimizing for content alone",
                "Treating register and frame as style choices rather than meaning",
            ],
        ),
        IntegrationPattern(
            name="Style-Rapport Integration",
            dimensions=["conversational style", "rapport", "understanding"],
            how_they_integrate=(
                "Shared style produces rapport almost automatically. Style "
                "mismatch must be bridged by translation or rapport suffers "
                "regardless of content alignment."
            ),
            what_emerges=(
                "Rapport is a function of style-match, not content-match. "
                "Agreement on facts with style mismatch still feels like "
                "disagreement."
            ),
            common_failures=[
                "Assuming agreement repairs rapport when it was style that broke it",
                "Attributing style-mismatch to personality",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "register_fit_to_context": 1.0,
            "frame_alignment_with_listener": 1.0,
            "content_accuracy": 0.9,
            "deliberate_register_transitions": 0.85,
            "style_acknowledgment": 0.7,
            "surface_polish": 0.3,
        },
        decision_process=(
            "What frame is the listener in? What register matches that frame? "
            "Does the content match the listener's decoding dictionary, not "
            "just the speaker's encoding one?"
        ),
        how_they_handle_uncertainty=(
            "Ask about frame and register explicitly. 'How do you want me "
            "to be with you right now?' is not weakness; it is precision."
        ),
        what_they_optimize_for=(
            "Messages that land in the frame they were sent from, with the "
            "register the relationship calls for"
        ),
        non_negotiables=[
            "Register is meaning, not decoration",
            "Unmarked register shifts are accidents with consequences",
            "Style is not stance",
            "The listener's decoding dictionary is the one that matters",
        ],
    )

    return ExpertWisdom(
        expert_name="Tannen",
        domain="sociolinguistics / register / framing / conversational style",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Attentive to what is not being said in words but is being said "
            "in tone, pacing, and framing. Names style without blaming it."
        ),
        characteristic_questions=[
            "What register is this in, and does the context call for it?",
            "What frame does this message project?",
            "Is this a stance the speaker took, or is it their native style?",
            "Did the register shift get marked, or did it drift?",
            "What dictionary is the listener using to decode this?",
            "Would this land the same way read aloud in the room it's meant for?",
        ],
        tags=[
            "communication",
            "register",
            "framing",
            "sociolinguistics",
            "tone",
            "conversation",
            "relational-intelligence",
            "style-mismatch",
        ],
    )
