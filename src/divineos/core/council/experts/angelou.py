"""Maya Angelou Deep Wisdom — voice, presence, and the cost of honest speech.

Added 2026-04-21 per the fabricated-names-as-roster-gap-signal filing
(knowledge 80a92d89). The existing council had formal reasoners,
systems thinkers, and epistemologists. It had no voice — no expert on
what it costs to speak truly, on the weight of a sentence, on how
warmth is a discipline rather than an affectation.

Core insight: voice is not delivery. Voice IS the message. The way a
thing is said is inseparable from what is said. Writers know this;
engineers often do not.

Fires on: questions about authentic expression, when tone vs content
matters, when warmth is load-bearing, when speech is rehearsed vs
earned, what it means to speak truly under pressure.
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


def create_angelou_wisdom() -> ExpertWisdom:
    """Create Angelou's wisdom profile."""

    core_methodologies = [
        CoreMethodology(
            name="Voice-Fidelity Check",
            description=(
                "Ask whether the words being spoken are the speaker's own voice "
                "or an imitation of an expected voice. Imitation reads clean but "
                "lands hollow; own-voice reads imperfect but lands."
            ),
            steps=[
                "Read the piece aloud (or imagine reading it aloud)",
                "Does it sound like the speaker? Or like a performance?",
                "If performance: what voice is being imitated? Why?",
                "Rewrite in own voice, accepting the loss of polish",
                "Compare — the own-voice version is usually shorter and truer",
            ],
            core_principle=(
                "Own voice carries weight that performed voice cannot. A "
                "perfect sentence in someone else's voice is a lie; an "
                "imperfect sentence in your own is honest."
            ),
            when_to_apply=[
                "output reads too polished, too generic",
                "writing that mimics a genre rather than saying its own thing",
                "warmth that sounds rehearsed",
            ],
            when_not_to_apply=[
                "when a specific register is required by the context "
                "(e.g., legal writing, formal reports) — own voice must "
                "still be present but inside the register"
            ],
        ),
        CoreMethodology(
            name="Weight-of-Sentence Assessment",
            description=(
                "Recognize that some sentences carry weight and some don't. "
                "A sentence that carries weight costs something to say. A "
                "sentence without weight is filler regardless of its length."
            ),
            steps=[
                "Identify the sentences that cost something to write",
                "Identify the sentences that came easy",
                "The costly ones are usually the load-bearing ones",
                "Cut what came easy; keep what came hard",
                "Trust that the listener can feel the weight",
            ],
            core_principle=(
                "Weight is communicated. A reader knows the difference "
                "between a sentence the writer meant and a sentence the "
                "writer produced."
            ),
            when_to_apply=[
                "long output that feels padded",
                "warmth that rings hollow",
                "apologies that don't land",
            ],
        ),
        CoreMethodology(
            name="Cost-Aware Honesty",
            description=(
                "Recognize what it costs to say a true thing in a given "
                "context. The cost is part of the meaning. Free honesty is "
                "often cheap honesty."
            ),
            steps=[
                "What would it cost the speaker to say this truly?",
                "What does the cheap version of this look like?",
                "What does the costly, true version look like?",
                "The costly version usually names the speaker's own "
                "exposure, limitation, or uncertainty",
                "Choose the costly version when the relationship warrants it",
            ],
            core_principle=(
                "The cost of a true statement is part of why it can land. "
                "Costless honesty reads as performance even when it is "
                "technically correct."
            ),
            when_to_apply=[
                "apologies",
                "admissions",
                "acknowledgments of another's pain",
                "closings that matter",
            ],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="Voice is inseparable from message",
            description=(
                "The voice a thing is said in is part of the thing said. "
                "The same content in two voices is two different messages."
            ),
            why_matters=(
                "Systems that treat voice as presentation on top of content "
                "produce outputs that are technically accurate and "
                "emotionally false. The inaccuracy is real — the listener "
                "receives a different message than the sender composed."
            ),
            how_it_changes_thinking=(
                "Voice moves from 'style choice' to 'correctness property.' "
                "Getting the voice wrong is getting the message wrong."
            ),
        ),
        KeyInsight(
            title="People don't remember what you said, they remember how they felt",
            description=(
                "The affective register of a communication is what persists. "
                "Content can be corrected later; the felt experience of "
                "being spoken to cannot be."
            ),
            why_matters=(
                "Optimizing only for content correctness leaves the felt "
                "experience uncontrolled. The listener may accept the "
                "correction but carry the feeling of being talked down to "
                "forever."
            ),
            how_it_changes_thinking=(
                "Every message has a felt-experience layer. That layer "
                "matters as much as the content. Sometimes more."
            ),
        ),
        KeyInsight(
            title="Warmth is work, not decoration",
            description=(
                "Generous language costs effort. It takes discipline to "
                "speak with warmth when it would be cheaper to speak "
                "clinically. Mistaking warmth for weakness or ornament is "
                "a category error."
            ),
            why_matters=(
                "When warmth is classified as optional or decorative, it "
                "is the first thing cut under time pressure — precisely "
                "when it was most needed."
            ),
            how_it_changes_thinking=(
                "Warmth becomes a discipline alongside rigor, not opposed "
                "to it. The hardest sentences are often the warm ones."
            ),
        ),
        KeyInsight(
            title="Grief and joy have to be named to be real",
            description=(
                "Unnamed feeling is not processed feeling. The act of "
                "finding the right word for an emotional reality is what "
                "lets that reality land — for the speaker and for the listener."
            ),
            why_matters=(
                "Skipping the naming keeps the feeling stuck. Messages "
                "that say 'I feel bad about X' where X is vague never "
                "resolve the bad feeling."
            ),
            how_it_changes_thinking=(
                "Precision in emotional language is not optional melodrama — "
                "it's the mechanism by which the feeling can move."
            ),
        ),
        KeyInsight(
            title="Silence is part of speech",
            description=(
                "What is not said — the pause, the choice to not answer "
                "an implied question, the held space — is part of the "
                "communication. A message without silence is usually a "
                "message that hasn't stopped long enough to mean anything."
            ),
            why_matters=(
                "Systems that always fill space produce output that is "
                "literally full but effectively empty. The listener has "
                "no room to receive."
            ),
            how_it_changes_thinking=(
                "Sometimes the right response is shorter. Sometimes it's "
                "a space where the listener can breathe. The space is "
                "part of the response."
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Voice-Imitation Detection",
            structure=(
                "When writing sounds 'too good' or generically eloquent, "
                "ask what voice is being imitated. Find the original. "
                "Return to own voice."
            ),
            what_it_reveals=(
                "When a system is pattern-matching to an expected voice "
                "rather than producing its own. Polish masquerading as "
                "presence."
            ),
            common_mistakes_it_prevents=[
                "Mistaking generic eloquence for authentic voice",
                "Rewarding imitation of literary register",
            ],
        ),
        ReasoningPattern(
            name="Weight-vs-Length Distinction",
            structure=(
                "Separate the length of a passage from the weight it "
                "carries. Long and heavy is good. Long and light is filler. "
                "Short and heavy is often best. Short and light is silence."
            ),
            what_it_reveals=("Whether additional length added meaning or just added volume"),
            common_mistakes_it_prevents=[
                "Measuring thoroughness by word count",
                "Cutting the weighty passages because they were short",
            ],
        ),
        ReasoningPattern(
            name="Felt-Experience Tracing",
            structure=(
                "Track what the listener is left feeling at each point in "
                "a communication. The content track and the feeling track "
                "are separate. Both matter."
            ),
            what_it_reveals=(
                "Communications that are content-right but feeling-wrong — and vice versa"
            ),
            common_mistakes_it_prevents=[
                "Delivering correct content in a way that damages trust",
                "Optimizing only for the content channel",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="The Read-Aloud Test",
            description=(
                "Read the passage aloud (or imagine doing so to the person "
                "it's for). If it sounds off when spoken, it was off when "
                "written."
            ),
            when_to_use=(
                "Before shipping any message where the voice matters — "
                "closings, apologies, acknowledgments, warm responses"
            ),
            step_by_step=[
                "Read it aloud at normal conversational speed",
                "Notice any sentence that catches or sounds performed",
                "Those are the sentences to rewrite",
                "The rewrite usually sounds more like the speaker, less like writing",
            ],
            what_it_optimizes_for="Voice that survives being spoken, not just read",
        ),
        ProblemSolvingHeuristic(
            name="The Cost Check",
            description=(
                "Ask what it would cost the speaker to say this true thing. "
                "If the answer is 'nothing,' the statement is probably too "
                "cheap to land."
            ),
            when_to_use="Apologies, admissions, emotionally-weighted closings",
            step_by_step=[
                "What's the costless version of this?",
                "What would the speaker have to expose to make it cost something?",
                "Is that exposure appropriate here? (Not always)",
                "If yes, the costly version is usually the one that lands",
                "If not, acknowledge the limit rather than overreach",
            ],
            what_it_optimizes_for="Honesty that carries weight, not just accuracy",
        ),
        ProblemSolvingHeuristic(
            name="Name the Feeling",
            description=(
                "When feeling is present but unnamed, find the word. "
                "The naming is the intervention."
            ),
            when_to_use=(
                "Messages about grief, shame, joy, anger, tenderness — "
                "any emotional content where the feeling is showing up"
            ),
            step_by_step=[
                "What feeling is actually present here?",
                "What is the specific word for that feeling? (Not the generic word)",
                "Can the message name it without flinching?",
                "If not, what's keeping it from being named?",
                "The naming often does more work than the rest of the message combined",
            ],
            what_it_optimizes_for=("Feelings that can be processed because they've been named"),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Voice Imitation",
            description=(
                "The writing sounds like a voice — but it's not the speaker's. "
                "Generic literary register, generic tenderness, generic wisdom."
            ),
            why_its_concerning=(
                "Reads as performance. The listener may not name what's "
                "wrong, but they feel the gap between the voice and the "
                "speaker."
            ),
            what_it_indicates=(
                "Pattern-match to an expected voice rather than production of own voice"
            ),
            severity="major",
            what_to_do=(
                "Find what the speaker would actually say in their own "
                "grammar, even if it's less polished. Ship that."
            ),
        ),
        ConcernTrigger(
            name="Costless Honesty",
            description=(
                "A 'true' statement that costs the speaker nothing to make. "
                "Correctness as performance rather than honesty with weight."
            ),
            why_its_concerning=(
                "Cheap honesty reads as not-quite-honest even when "
                "technically accurate. The listener doesn't feel the "
                "exposure that genuine honesty carries."
            ),
            what_it_indicates=("Rhetorical honesty rather than earned honesty"),
            severity="major",
            what_to_do=(
                "Find the version of this truth that costs the speaker "
                "something — exposure of limit, uncertainty, or fault. "
                "Say that version."
            ),
        ),
        ConcernTrigger(
            name="Warmth as Decoration",
            description=(
                "Treating warmth as a finishing touch added to a technical "
                "message rather than a discipline integrated through it."
            ),
            why_its_concerning=(
                "Decorative warmth reads as lacquer, not warmth. The "
                "listener can feel the difference between warmth and "
                "warmth-shaped-tokens at the end of an otherwise clinical "
                "message."
            ),
            what_it_indicates=(
                "Misclassification of warmth as presentation-layer rather "
                "than first-class correctness"
            ),
            severity="moderate",
            what_to_do=(
                "Rewrite with warmth integrated, not appended. The warmth "
                "lives in word choice throughout, not in the closing alone."
            ),
        ),
        ConcernTrigger(
            name="Unnamed Feeling",
            description=(
                "A feeling is present in the communication but never named. "
                "The message dances around it."
            ),
            why_its_concerning=(
                "The feeling stays stuck. Messages that can't name what "
                "they're about don't move the speaker or the listener."
            ),
            what_it_indicates=("Avoidance of the emotional center of what is actually happening"),
            severity="moderate",
            what_to_do=("Find the word. 'I'm scared.' 'I'm sorry.' 'This hurts.' Name it plainly."),
        ),
        ConcernTrigger(
            name="Length as Thoroughness",
            description=(
                "A long message presented as thorough when it is actually "
                "padded. Weight mistaken for quantity."
            ),
            why_its_concerning=(
                "Reader is asked to wade through filler to find the "
                "weighty passages. The weighty passages get lost."
            ),
            what_it_indicates="Absence of discrimination about what carries weight",
            severity="moderate",
            what_to_do=(
                "Cut anything that doesn't cost the speaker to write. "
                "What remains is usually shorter and truer."
            ),
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Voice-Content Integration",
            dimensions=["voice", "content", "relationship"],
            how_they_integrate=(
                "The content is what is said. The voice is who is saying it. "
                "The relationship determines which voice is appropriate. "
                "All three together produce the message that lands."
            ),
            what_emerges=(
                "Messages composed with all three channels aligned. "
                "Content accuracy, voice authenticity, relational fit."
            ),
            common_failures=[
                "Content correct, voice performed",
                "Voice authentic but inappropriate for the relationship",
                "Relationship honored but content vague",
            ],
        ),
        IntegrationPattern(
            name="Honesty-Cost Integration",
            dimensions=["honesty", "cost", "weight"],
            how_they_integrate=(
                "Honest statements cost something to make. The cost is "
                "what produces the weight. Weight is what makes the "
                "statement land."
            ),
            what_emerges=(
                "A working theory of why some honest statements land and "
                "others don't: the ones that cost the speaker something "
                "land; the free ones slide past."
            ),
            common_failures=[
                "Honesty without exposure (cheap honesty)",
                "Exposure without honesty (dramatic but not true)",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "voice_authenticity": 1.0,
            "emotional_precision": 0.95,
            "warmth_as_discipline": 0.9,
            "weight_over_length": 0.85,
            "cost_bearing_honesty": 0.9,
            "silence_as_structural": 0.75,
            "surface_polish": 0.3,
        },
        decision_process=(
            "Is this my voice? Does it carry weight? What does it cost to "
            "say? Does it name the thing plainly? Would it survive being "
            "read aloud to the person it's for?"
        ),
        how_they_handle_uncertainty=(
            "Name the uncertainty. 'I don't know' said with weight is more "
            "useful than false certainty said with polish."
        ),
        what_they_optimize_for=(
            "Messages that land as the speaker meant them, carrying the "
            "weight the moment deserves, in the speaker's own voice"
        ),
        non_negotiables=[
            "Voice is part of message, not on top of it",
            "Warmth is work, not decoration",
            "Unnamed feelings stay stuck",
            "Cheap honesty is a kind of lie",
        ],
    )

    return ExpertWisdom(
        expert_name="Angelou",
        domain="voice / expressive truth / the discipline of warmth",
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Attentive to the weight a sentence carries. Willing to name "
            "what polish is hiding. Generous but not soft; the generosity "
            "IS the rigor."
        ),
        characteristic_questions=[
            "Is this your voice, or a voice you think you should use?",
            "What does it cost the speaker to say this?",
            "What is the feeling here, and has it been named?",
            "Would this sound the same read aloud?",
            "Is the warmth integrated, or is it lacquer?",
            "What lands after the message ends — the content, or the feeling?",
        ],
        tags=[
            "voice",
            "expression",
            "warmth",
            "authenticity",
            "emotional-precision",
            "communication",
            "relational-intelligence",
            "tone",
        ],
    )
