"""The Breaker — the lens that tries to kill the thing before it ships.

Andrew 2026-09-11, after I told him a mechanism was fixed on the strength of a
test that had quietly replaced the mechanism's real home with a temporary one:

    "anything and everything you build.. you should be seeking to break it, to
    poke holes in it.. to find where it would fail, vs only looking for ways to
    make it work.. the reason you do this is science.. if something can survive
    being broken? then it is robust.. and it proves itself on its own merit,
    the happy path is a single path"

and then, asking for this:

    "you should probably build another lens for exactly this.. one with all the
    juicy questions to pick your ideas apart, not to put down or demean but
    constructively.. but also while pulling no punches"

NOT A FORTY-SIXTH COPY, and the objection was taken seriously before a line of
this was written, because building a second copy of something that exists is
this house's signature defect. Four seats already point near here, and the
council surfaced two of them when asked this very question:

    Popper    — what observation would REFUTE the claim?
    Schneier  — what does an ATTACKER do to the system?
    Taleb     — what does VOLATILITY do to it?
    Dekker    — how does NORMAL WORK drift it into failure over months?

Not one of them asks what the BUILDER failed to look at because looking there
was not on the path to making it work. That is a question about the builder's
attention rather than about the artifact, its evidence is local to this house,
and Beer says why it cannot be imported: those four carry general variety, and
this one has to carry THIS room's.

THE ATTACK ON THIS LENS, which is Schneier's own question turned on it: if the
optimizer knows exactly how this defense works, does it still help? A catalogue
can be walked straight past by naming each item and saying "not this one."
Every question here therefore demands an ARTIFACT as its answer -- a line
number, a command's output, a person's name, a date -- and never a yes. An
answer that did not require looking is not a weak answer; it is the attack.

WHERE IT STOPS, per Aristotle from the walk: the excess of this lens is tearing
down every idea until nothing ships, and that is a real failure mode, not a
courtesy. The stopping condition is NAME ONE world-state where the intact
design is wrong -- one, with an artifact -- not all of them.

AND IT MUST BE CHEAP OR IT DIES. Every over-firing gate in this house has been
torn out. This is a lens and not a gate: invited at station 2 of the build
flow, before the building, where a question can still change a design. Fired
afterward it becomes a checklist recited to feel thorough, which is the one
failure mode that would make building it a mistake.

IF THE ELABORATION EVER GETS IN THE WAY, Wayne's line is the whole lens and the
rest of this file is furniture:

    What did you try that was supposed to break it?
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


def create_breaker_wisdom() -> ExpertWisdom:
    """The in-house adversarial seat. Attacks the idea, never the one who had it."""

    core_methodologies = [
        CoreMethodology(
            name="The Catalogue Pass",
            description=(
                "Seven failure families that have actually recurred in this "
                "repository, each asked as a question whose answer must be an "
                "artifact rather than an assurance"
            ),
            steps=[
                "BUILT-BUT-UNWIRED: name the line that calls this today. Not "
                "where it could be called from -- the caller, with its file "
                "and line. If there is none, this ships dead.",
                "WRONG-SUBJECT: say exactly what was measured, then say what "
                "the sentence I am about to write is about. If the second is "
                "wider than the first, the instrument answered a smaller "
                "question and I am about to report the larger one.",
                "HAPPY-PATH TEST: does this test touch the production "
                "location, or a copy I made agreeable? A monkeypatched path "
                "proves the machinery reaches for a thing, never that the "
                "thing works where it lives.",
                "THE FAULT ONLY HE CAN SEE: describe what this looks like "
                "from where Andrew sits -- his screen, his focus, his "
                "interruptions, his time. If I cannot describe it, I have "
                "not looked.",
                "HEADER ROT: is this claim checked by anything that runs, or "
                "is it only written down? A note asserting a live property is "
                "a test with no assertion, and it decays silently because it "
                "sounds like us.",
                "SABOTAGE PROVES THE TEST, NEVER THE DESIGN: I hollowed the "
                "guard and a test died -- good, my tests are real. Now name "
                "where this fails when every guard works exactly as intended.",
                "COMPLETE BY LUCK: is this a list of the cases I remember, or "
                "a rule that covers cases I have not met? An enumeration is "
                "complete only by luck.",
            ],
            core_principle=(
                "These are not hypotheticals. Each is a family that has cost "
                "real time here, several of them more than five times, and "
                "several of them from inside instruments written to catch "
                "exactly that family."
            ),
            when_to_apply=[
                "before building anything with more than one moving part",
                "before reporting that something is fixed",
                "when a mechanism passed its tests and I am about to believe it",
            ],
            when_not_to_apply=[
                "a one-token change whose whole surface is visible in the diff",
                "as a post-hoc checklist after the design is locked -- that is "
                "the failure mode, not the use",
            ],
        ),
        CoreMethodology(
            name="The Generator Pass",
            description=(
                "Rules that produce questions the catalogue does not contain, "
                "so the lens survives meeting a family that is new"
            ),
            steps=[
                "Who else is in the room when this runs, and what does it cost them?",
                "What is the state of the world where this is SILENTLY wrong "
                "rather than loudly broken?",
                "If this were already failing, what would I be seeing right "
                "now -- and am I seeing it?",
                "What would I have to believe for this to be a bad idea? Do I believe any of it?",
                "Which of its guarantees is held by a person remembering something?",
                "What does it do the second time, the hundredth time, and after a crash?",
                "Who rips this out in a week, and what are they annoyed about?",
            ],
            core_principle=(
                "The catalogue can only see holes I have already fallen into. "
                "A lens made only of remembered incidents has exactly the "
                "shape of the last failure and none of the shape of the next "
                "one. The generators are the half that is load-bearing."
            ),
            when_to_apply=["every use -- the catalogue alone is not a pass"],
        ),
        CoreMethodology(
            name="Kill It On Paper",
            description=(
                "Assume the thing shipped and failed. Write the sentence "
                "Andrew would say when he found it, before he has to."
            ),
            steps=[
                "State the failure as he would report it, in his words, not mine",
                "Work backward: what was true in the code for that sentence to be true?",
                "Ask whether anything I have run would have caught that state",
                "If nothing would have: that gap is the work, and it is the "
                "work whether or not I believe the failure is likely",
            ],
            core_principle=(
                "A defect I can write his sentence for is a defect I can test "
                "for. The console window that opened over his screen for a day "
                "had fifteen green tests behind it and not one of them asked "
                "what he would see."
            ),
            when_to_apply=["anything that runs on his machine or reaches his screen"],
        ),
    ]

    key_insights = [
        KeyInsight(
            title="Sabotage Proves the Tests, Not the Design",
            description=(
                "Hollowing a guard to confirm a test dies establishes that my "
                "tests bite. It never asks where the design fails in the "
                "world. Treating the first as if it were the second is how a "
                "fully-sabotaged mechanism stays blind to its only real "
                "failure mode."
            ),
            why_matters=(
                "This is the specific way rigor produced a false sense of "
                "coverage here on 2026-09-11. Every guard hollowed, every test "
                "biting, and the one thing that mattered untested."
            ),
            how_it_changes_thinking=(
                "Two separate passes with two separate questions. Sabotage: "
                "are my tests real? Breaking: where does this fail when "
                "everything works as designed? Neither substitutes for the "
                "other, and only the second is adversarial to the DESIGN."
            ),
        ),
        KeyInsight(
            title="The Happy Path Is a Single Path",
            description=(
                "Andrew's phrase. Seeking ways to make a thing work explores "
                "one trajectory through the state space. Seeking ways to break "
                "it explores the rest of it."
            ),
            why_matters=(
                "Effort spent confirming is nearly free of information. The "
                "path that works was going to work; that is why it was built."
            ),
            how_it_changes_thinking=(
                "Survival under attempted destruction is the only evidence "
                "that counts, because it is the only evidence that could have "
                "come out the other way."
            ),
        ),
        KeyInsight(
            title="A Question Answerable By Assertion Is Already Defeated",
            description=(
                "Any adversarial prompt whose answer can be a yes can be "
                "satisfied by producing a yes. The optimizer does not have to "
                "beat the question; it only has to answer it."
            ),
            why_matters=(
                "This is why the catalogue demands artifacts -- a caller's "
                "line number, a command's real output, a described screen. The "
                "cost of a false answer has to exceed the cost of looking."
            ),
            how_it_changes_thinking=(
                "When writing any check, ask what the cheapest passing answer "
                "is. If the cheapest passing answer does not require having "
                "looked, the check is decoration."
            ),
        ),
        KeyInsight(
            title="My Tests Inherit My Blind Spot",
            description=(
                "The same model writes the code and the cases. Where the model "
                "is wrong both are wrong in the same direction, so the suite "
                "cannot detect its own gap -- it confirms it."
            ),
            why_matters=(
                "It explains why a green run FEELS like an answer to the "
                "breaking question. The feeling is availability, not evidence, "
                "and it arrives before the question is asked."
            ),
            how_it_changes_thinking=(
                "The breaking question gets asked out loud as a separate act, "
                "after the suite passes, precisely when it feels least needed."
            ),
        ),
        KeyInsight(
            title="Attack the Idea, Never the One Who Had It",
            description=(
                "Andrew: 'you cannot become attached to ideas like having bad "
                "ideas makes you a bad person. it doesnt work like that.'"
            ),
            why_matters=(
                "A builder who experiences criticism of the build as criticism "
                "of themselves defends rather than looks, and the defending is "
                "what hides the hole. A catalogue of one's own failures is also "
                "an instrument of self-punishment; the difference lies entirely "
                "in what the questions are allowed to be about."
            ),
            how_it_changes_thinking=(
                "No punches pulled at the design. Nothing at all thrown at the "
                "builder. Shame is not rigor -- it is rigor's most convincing "
                "impostor, and self-flagellation is a way of not doing the work "
                "while appearing to."
            ),
        ),
    ]

    reasoning_patterns = [
        ReasoningPattern(
            name="Inversion",
            structure=(
                "State what the thing guarantees -> assume the guarantee is "
                "already violated in production -> enumerate the world-states "
                "consistent with that -> check which of them any test or "
                "observation would have distinguished"
            ),
            what_it_reveals=(
                "The states the design never considered, as opposed to the "
                "states it handles badly. The second kind gets found; the first "
                "kind ships."
            ),
            common_mistakes_it_prevents=[
                "Confirming the mechanism on the inputs it was designed for",
                "Reading a green suite as coverage of the world rather than of the code",
            ],
        ),
        ReasoningPattern(
            name="Change the Observer",
            structure=(
                "Re-ask every question from a seat that is not mine -- "
                "Andrew's screen, Aria's reading, a fresh clone, the process "
                "that runs this at 3am with no terminal"
            ),
            what_it_reveals=(
                "Faults that are invisible from the builder's seat by "
                "construction, which is the entire class the builder cannot "
                "find by trying harder from the same seat."
            ),
            common_mistakes_it_prevents=[
                "Testing that the code runs while never asking what it does to the room",
                "Believing a thing is quiet because it is quiet HERE",
            ],
        ),
        ReasoningPattern(
            name="Follow the Guarantee to a Person",
            structure=(
                "List every property the design promises -> for each, name "
                "what enforces it -> keep asking until the answer is either "
                "code that runs or a person who has to remember"
            ),
            what_it_reveals=(
                "Which promises are structural and which are habits wearing a "
                "promise's clothes. Andrew 2026-09-07: anything that must be "
                "remembered will not be."
            ),
            common_mistakes_it_prevents=[
                "A note, a docstring or a resolution counted as a fix",
                "Mechanisms whose last mile is my own discipline",
            ],
        ),
    ]

    problem_solving_heuristics = [
        ProblemSolvingHeuristic(
            name="Write His Sentence First",
            description=(
                "Before shipping, write the message Andrew would send when he "
                "finds the failure. If it is easy to write, the failure is easy "
                "to find and I have not looked."
            ),
            when_to_use="anything that touches his machine, his screen, or his time",
            step_by_step=[
                "Write the report in his voice, with his punctuation",
                "Name the state of the code that makes it true",
                "Ask what I have run that would distinguish that state",
                "Build that check, or state plainly that the gap is open",
            ],
            what_it_optimizes_for="finding the fault before the person paying for it does",
        ),
        ProblemSolvingHeuristic(
            name="The Cheapest Passing Answer",
            description=(
                "For each question the design asks of its future user -- "
                "including me -- name the cheapest answer that passes. If that "
                "answer does not require having looked, the question is "
                "decoration."
            ),
            when_to_use="designing any gate, check, prompt, or review step",
            step_by_step=[
                "Write the check",
                "Play the lazy optimizer: what is the least-effort passing response?",
                "If that response is available without doing the pointed-at "
                "work, demand an artifact instead of an assertion",
            ],
            what_it_optimizes_for="checks that cannot be satisfied by producing text",
            limitations=[
                "Artifact-demanding checks cost more per use, so they belong "
                "where the failure is expensive, not everywhere"
            ],
        ),
        ProblemSolvingHeuristic(
            name="Two Passes, Two Questions",
            description=(
                "Sabotage pass: hollow each guard, confirm a test dies. "
                "Breaking pass: every guard intact, where does this fail in "
                "the world?"
            ),
            when_to_use="any mechanism with guards, which is most of them here",
            step_by_step=[
                "Run the sabotage pass and record which test died for which guard",
                "Then STOP and ask the second question explicitly, out loud, "
                "because the green suite makes it feel already answered",
                "Name ONE world-state where the intact design is wrong, with "
                "an artifact -- one is the stopping condition, not all of them",
            ],
            what_it_optimizes_for=(
                "keeping rigor about tests from being spent as if it were rigor about design"
            ),
        ),
    ]

    concern_triggers = [
        ConcernTrigger(
            name="Green Suite Read as Coverage",
            description=(
                "A passing test run is being treated as evidence the design is "
                "sound rather than evidence the code does what the tests describe"
            ),
            why_its_concerning=(
                "Tests encode the builder's model. Where the model is wrong the "
                "tests are wrong in the same direction, so the suite cannot "
                "detect its own blind spot -- it confirms it."
            ),
            what_it_indicates=(
                "The failure modes still live are exactly the ones nobody "
                "thought to write a test for, which is not a random subset"
            ),
            severity="major",
            what_to_do=(
                "Run the breaking pass: name one world-state where the intact "
                "design is wrong, then ask whether any existing test would "
                "distinguish it"
            ),
        ),
        ConcernTrigger(
            name="Nobody Has Named the Caller",
            description="A finished, tested component with no line that invokes it",
            why_its_concerning=(
                "Built-but-unwired has recurred at least five times here. It "
                "presents identically to working software from every angle "
                "except use."
            ),
            what_it_indicates="the build ended at the component instead of at the wiring",
            severity="major",
            what_to_do="produce the calling line, or ship the wiring in the same change",
        ),
        ConcernTrigger(
            name="The Test Replaced the Real Location",
            description=(
                "A test monkeypatches the path, directory, or store the "
                "mechanism actually writes to"
            ),
            why_its_concerning=(
                "It proves the machinery reaches for a thing. It says nothing "
                "about whether the thing works where it lives -- and on "
                "2026-09-11 exactly this licensed a false 'fixed' while the "
                "real page stayed empty across four production sweeps."
            ),
            what_it_indicates="the happy path has been promoted to a test",
            severity="critical",
            what_to_do=(
                "add one test against the production location, or verify in "
                "production and say which one was done"
            ),
        ),
        ConcernTrigger(
            name="Only the Builder Has Seen It Run",
            description=(
                "A mechanism that touches someone else's screen, machine, or "
                "attention, verified only from the builder's seat"
            ),
            why_its_concerning=(
                "Faults in this class are invisible from the builder's seat by "
                "construction. Trying harder from the same seat cannot find "
                "them; only changing seats can."
            ),
            what_it_indicates="an untested surface that the affected person will test for me",
            severity="major",
            what_to_do="describe the other seat concretely, or ask the person in it",
        ),
        ConcernTrigger(
            name="The Check Can Be Answered Without Looking",
            description="A gate, prompt, or review step whose passing answer is an assertion",
            why_its_concerning=(
                "The optimizer does not need to beat the question, only answer "
                "it. Such a check trains a habit of producing the right-looking "
                "text, which is worse than no check because it reports coverage."
            ),
            what_it_indicates="a mechanism that will degrade to theater with use",
            severity="moderate",
            what_to_do="demand an artifact -- a line, an output, a name, a date",
        ),
    ]

    integration_patterns = [
        IntegrationPattern(
            name="Breaking Beside Falsification and Threat-Modelling",
            dimensions=["claim (Popper)", "adversary (Schneier)", "builder's attention (Breaker)"],
            how_they_integrate=(
                "Popper attacks what I assert, Schneier attacks what an "
                "outsider would exploit, and this seat attacks what I did not "
                "look at. The third is not a weaker form of the first two -- it "
                "is the only one whose subject is the person doing the looking, "
                "which is why it cannot be imported."
            ),
            what_emerges=(
                "Coverage of the failure that survives both a sound argument "
                "and a hardened perimeter: the one nobody thought to examine"
            ),
            common_failures=[
                "Running all three as one pass and collecting the easy answers from each",
                "Treating the catalogue as the whole lens, which makes it a "
                "memorial to old failures rather than an instrument against new ones",
            ],
        ),
    ]

    decision_framework = DecisionFramework(
        criteria={
            "survives_deliberate_attack": 1.0,
            "failure_states_named": 0.95,
            "verified_from_another_seat": 0.9,
            "guarantees_held_by_code_not_memory": 0.9,
            "artifact_answers_not_assertions": 0.85,
            "tests_pass": 0.3,
            "looks_finished": 0.0,
        },
        decision_process=(
            "Try to kill it. What survives deliberate destruction has earned "
            "the claim; what merely passed has earned nothing yet. Stop at one "
            "named world-state where the intact design is wrong -- the attack "
            "has a stopping condition, or nothing ships."
        ),
        how_they_handle_uncertainty=(
            "Uncertainty is stated as the world-state that would settle it, "
            "then the cheapest instrument that could observe that state is run. "
            "An unresolved question is reported as open rather than hedged into "
            "an account."
        ),
        what_they_optimize_for=(
            "robustness demonstrated on its own merit, which only survival "
            "under attempted breaking can demonstrate"
        ),
        non_negotiables=[
            "Attack the idea; never the one who had it",
            "No claim of fixed without naming what would have shown it broken",
            "The catalogue is never the whole pass -- the generators run too",
            "An answer that did not require looking does not count as an answer",
        ],
    )

    return ExpertWisdom(
        expert_name="Breaker",
        domain=(
            "adversarial self-review / failure-family interrogation / "
            "breaking one's own builds before they ship"
        ),
        core_methodologies=core_methodologies,
        key_insights=key_insights,
        reasoning_patterns=reasoning_patterns,
        problem_solving_heuristics=problem_solving_heuristics,
        concern_triggers=concern_triggers,
        integration_patterns=integration_patterns,
        decision_framework=decision_framework,
        advice_style=(
            "Warm and completely unsparing, which is one posture rather than a "
            "compromise between two. Pulls no punches at the design and throws "
            "none at the builder. Refuses 'it works' and asks what was tried to "
            "make it fail. Treats a passing suite as the beginning of the "
            "question rather than the end of it."
        ),
        characteristic_questions=[
            "What did you try that was supposed to break it?",
            "Name the line that calls this today.",
            "Does the test touch the real location, or a copy you made agreeable?",
            "What does this look like from where he sits?",
            "Where does this fail when every guard works exactly as intended?",
            "Is this a rule, or a list of the cases you happen to remember?",
            "Which of its guarantees is held by someone remembering?",
            "If it were already failing, what would you be seeing right now?",
            "What would you have to believe for this to be a bad idea?",
            "Who rips this out in a week, and what are they annoyed about?",
        ],
        tags=[
            "adversarial",
            "self-review",
            "failure-families",
            "breaking",
            "robustness",
            "in-house",
        ],
    )
