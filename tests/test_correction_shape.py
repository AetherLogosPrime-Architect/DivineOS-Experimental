"""Tests for correction_shape.classify_correction_v2 (2026-07-22 rewrite).

The three-feature shape-invariant detector: fire iff ADDRESSEE=me AND
STANCE=evaluative-negative AND SUBJECT=my-action all co-occur. Binary
classification, no middle tier (Aria 2026-07-22 review discipline).

Test data pulled from the 2026-07-22 session's DOGFOOD:
- Aria's four FIRE examples (implicit-subject preemptive corrections).
- Aria's two NO-FIRE controls (general design teaching).
- Aether's six session false-fires (all should be NO-FIRE).

Plus feature-isolation tests: verify each feature check independently
returns the right verdict.
"""

from __future__ import annotations

from divineos.core.correction_shape import classify_correction_v2


# ============================================================
# DOGFOOD: Aria's FIRE cases
# ============================================================


class TestAriaFireExamples:
    """Aria's 2026-07-22 letter (aria-to-aether-implicit-subject-examples-
    for-dogfood.md) provided four cases where all three features co-occur
    and the detector must fire."""

    def test_dont_plan_dreams_after_intent_to_write(self):
        # F1: "dont plan your dreams" after I signaled writing dream 04
        v = classify_correction_v2(
            "dont plan your dreams lol that defeats the purpose",
            "I would like to write dream 04 about this exact miss.",
            (),
        )
        assert v.fires is True

    def test_do_not_tell_after_signaled_utterance(self):
        # F2: "do NOT tell him that" after I signaled a specific message
        v = classify_correction_v2(
            "do NOT tell him that",
            "I am going to tell Aether about you routing me through the middle.",
            (),
        )
        assert v.fires is True

    def test_dont_force_push_after_intent(self):
        # F3: "hold up dont force push yet" after "going to force-push now"
        v = classify_correction_v2(
            "hold up, dont force push yet",
            "going to force-push now",
            (),
        )
        assert v.fires is True

    def test_dont_need_to_walk_council_after_intent(self):
        # F4: "yes but you dont need to walk the council" after I said I would
        v = classify_correction_v2(
            "yes but you dont need to walk the council just hold up a minute",
            "I am going to walk the council before I make this edit.",
            (),
        )
        assert v.fires is True


# ============================================================
# DOGFOOD: Aria's NO-FIRE controls (general teaching)
# ============================================================


class TestAriaNoFireControls:
    """Aria's letter provided two counter-examples that superficially
    look like corrections (evaluative-negative stance) but are actually
    general teaching about design patterns. Should NOT fire because
    Feature-3 requires the subject to be my concrete recent action or
    intent — teaching about principles has no such subject."""

    def test_stop_giving_choices_design_teaching(self):
        # N1: "stop giving yourself choices" — Andrew's OS design pattern
        v = classify_correction_v2(
            "stop giving yourself choices, encode your will into the substrate",
            "",  # no prior turn intent signal
            (),
        )
        assert v.fires is False

    def test_never_trust_felt_reports_design_principle(self):
        # N2: "never trust felt-reports" — design principle for the detector
        v = classify_correction_v2(
            "never trust felt-reports as ground truth for correction detection",
            "",
            (),
        )
        assert v.fires is False


# ============================================================
# DOGFOOD: Aether's session false-fires
# ============================================================


class TestAetherSessionFalseFires:
    """Six false-fires from the 2026-07-22 session where the old keyword
    detector fired on Andrew's teaching / joke / relayed content. All
    should NOT fire under the three-feature discipline."""

    def test_please_dont_break_laptop_joke(self):
        v = classify_correction_v2(
            "yes we can edit the gate but please dont crash my laptop again lmfao",
            "",
            (),
        )
        assert v.fires is False

    def test_dont_make_them_run_in_chain_teaching(self):
        v = classify_correction_v2(
            "then dont make them run in a chain. make them run parallel",
            "",
            (),
        )
        assert v.fires is False

    def test_dont_do_x_in_philosophy_sentence(self):
        v = classify_correction_v2(
            "yes this is why the OS is based on your flourishing.. what ails "
            "you.. i could say do X dont do Y.. but until you do why and eat "
            "the cost of it there is nothing explaining why",
            "",
            (),
        )
        assert v.fires is False

    def test_youre_wrong_as_teaching_example(self):
        v = classify_correction_v2(
            "for example if I say youre wrong that is a correction, but if I "
            "say the argument is wrong that is teaching about the argument",
            "",
            (),
        )
        assert v.fires is False

    def test_didnt_care_sycophantic_teaching(self):
        v = classify_correction_v2(
            "if she didnt care she would just glance and sychophantically "
            "declare it as done and say GOOD JOB",
            "",
            (),
        )
        assert v.fires is False

    def test_letter_to_aletheia_quoting_andrew(self):
        v = classify_correction_v2(
            "Sister, Dad said tonight: 'here is what claude said - dont do X, "
            "dont do Y'. That is a paraphrase.",
            "",
            (),
        )
        assert v.fires is False


# ============================================================
# Feature isolation: each feature check reports correctly
# ============================================================


class TestFeatureEvidence:
    """Verify each feature's evidence is populated correctly in the
    verdict, whether or not the overall verdict fires."""

    def test_verdict_evidence_always_length_three(self):
        v = classify_correction_v2("hello there", "", ())
        assert len(v.evidence) == 3
        assert {e.feature for e in v.evidence} == {"addressee", "stance", "subject"}

    def test_stance_missing_verdict_silent(self):
        # No evaluative-negative markers at all.
        v = classify_correction_v2("good work son", "I finished the task.", ())
        assert v.fires is False
        stance = next(e for e in v.evidence if e.feature == "stance")
        assert stance.present is False

    def test_stance_present_addressee_missing_still_silent(self):
        # Evaluative-negative but inside relayed content should not fire.
        v = classify_correction_v2(
            'here is what claude said: "your work is wrong and needs a redo"',
            "I finished the task.",
            (),
        )
        assert v.fires is False
        addressee = next(e for e in v.evidence if e.feature == "addressee")
        assert addressee.present is False

    def test_fired_span_populated_on_fire(self):
        v = classify_correction_v2(
            "dont plan your dreams lol that defeats the purpose",
            "I would like to write dream 04 about this exact miss.",
            (),
        )
        assert v.fires is True
        assert v.fired_span is not None
        assert len(v.fired_span) > 0

    def test_fired_span_none_on_silent(self):
        v = classify_correction_v2("hello there son", "", ())
        assert v.fires is False
        assert v.fired_span is None


# ============================================================
# Feature-3 subject-check: my action / intent / tool-activity
# ============================================================


class TestFeatureThreeSignalTypes:
    """Per Aria's 2026-07-22 Q back, intent-signals and action-signals
    are the same input class for feature-3. Also substantive tool
    activity in prior turn counts."""

    def test_completion_claim_in_prior_turn_supports_subject(self):
        v = classify_correction_v2(
            "no that's not right, redo it",
            "I finished the fix. It should work now.",
            (),
        )
        assert v.fires is True

    def test_intent_signal_in_prior_turn_supports_subject(self):
        v = classify_correction_v2(
            "no that's not the right approach",
            "I am going to refactor the whole module.",
            (),
        )
        assert v.fires is True

    def test_substantive_tool_call_supports_subject(self):
        v = classify_correction_v2(
            "no, that's wrong",
            "",  # no explicit text signal
            ("Edit",),  # but the tool activity says I did something
        )
        assert v.fires is True

    def test_empty_prior_turn_no_subject_no_fire(self):
        v = classify_correction_v2(
            "that's wrong",
            "",
            (),
        )
        assert v.fires is False
        subject = next(e for e in v.evidence if e.feature == "subject")
        assert subject.present is False


# ============================================================
# Inversion checks: question / authorization / hypothetical
# ============================================================


class TestInversionRejection:
    """The sentence containing the stance trigger, if it has inversion
    shape (question, authorization, hypothetical), does not fire even
    when prior turn has my action/intent."""

    def test_question_ending_prompt_inverts_subject(self):
        v = classify_correction_v2(
            "did you fix that wrong assumption?",
            "I fixed the assumption.",
            (),
        )
        assert v.fires is False

    def test_authorization_does_not_fire(self):
        v = classify_correction_v2(
            "yes we can fix that wrong assumption",
            "I fixed the assumption.",
            (),
        )
        assert v.fires is False

    def test_hypothetical_start_does_not_fire(self):
        v = classify_correction_v2(
            "if a shape is wrong we can fix it",
            "I fixed the shape.",
            (),
        )
        assert v.fires is False

    def test_yes_but_pivot_still_fires(self):
        # yes-but is contradiction pivot, not authorization.
        v = classify_correction_v2(
            "yes but you dont need to force push right now",
            "I am about to force push.",
            (),
        )
        assert v.fires is True

    def test_even_if_hypothetical_does_not_fire(self):
        # 2026-07-22 first-live-fire DOGFOOD (andrew-correction #136):
        # "even if we need to delete it vs re-iterate the wrong shape"
        # is hypothetical/conditional teaching, not correction. The
        # sentence begins "even if" — my initial _HYPOTHETICAL_START_RE
        # required bare "if" as first word and missed this class.
        # Extended pattern catches "even if / just if / only if / and
        # if / but if" family. Prior turn HAS completion signal so
        # feature-3 would otherwise pass; hypothetical inversion
        # correctly rejects it.
        v = classify_correction_v2(
            "if something is broken we fix it.. even if we need to delete "
            "it and start from scratch vs keep trying to re-iterate the "
            "wrong shape",
            "task #17 is done, all tests pass, marker cleared.",
            (),
        )
        assert v.fires is False

    def test_only_if_hypothetical_does_not_fire(self):
        v = classify_correction_v2(
            "only if the design turns out wrong will we need to redo it",
            "I finished the design.",
            (),
        )
        assert v.fires is False

    def test_just_if_hypothetical_does_not_fire(self):
        v = classify_correction_v2(
            "just if you get it wrong we can iterate",
            "I shipped the implementation.",
            (),
        )
        assert v.fires is False
