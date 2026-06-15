"""Tests for unverified_claim_detector.

Andrew 2026-05-20 (Sagan principle, council-walked then not built, so the
behavior returned the same night): "when you say X is done, that's a claim,
and claims require evidence." This detector catches asserting a checkable
external state (pushed / merged / tests pass / on origin / PR opened)
without having run the check.
"""

from __future__ import annotations

from divineos.core.operating_loop.unverified_claim_detector import (
    UNVERIFIED_CLAIM_AFFIRMATION,
    detect_unverified_claim,
    format_unverified_claim_block,
)


class TestFires:
    def test_pushed_claim(self):
        f = detect_unverified_claim("it's pushed and the branch is on origin")
        assert f and any(x.claim_kind == "push" for x in f)

    def test_tests_pass_claim(self):
        assert detect_unverified_claim("tests pass")
        assert detect_unverified_claim("all green")
        assert detect_unverified_claim("exit code 0")

    def test_merge_and_pr(self):
        assert any(x.claim_kind == "merge" for x in detect_unverified_claim("the PR is merged"))
        assert any(x.claim_kind == "pr" for x in detect_unverified_claim("I opened the PR"))

    def test_merge_claim_with_code_anchor_fires(self):
        # A real merge-claim names a mergeable object → the anchor is present.
        for t in (
            "the branch landed on origin",
            "PR #38 landed",
            "it landed on main",
            "the commit merged cleanly",
            "merged to master",
        ):
            assert any(x.claim_kind == "merge" for x in detect_unverified_claim(t)), (
                f"should fire: {t!r}"
            )

    def test_merge_complete_form_fires_without_anchor(self):
        # The explicit "merge is complete" form is unambiguous, no anchor needed.
        assert any(
            x.claim_kind == "merge" for x in detect_unverified_claim("the merge is complete")
        )


class TestFigurativeMergeSilent:
    """The evidence-bar (claim a11ca1c9): bare "landed"/"merged" with no
    mergeable-code anchor nearby is figurative, not a completion-claim — the
    detector has no evidence and must stay silent. This is the live
    false-positive that fired on "it just landed for me" 2026-05-24."""

    def test_figurative_landed_silent(self):
        for t in (
            "it just landed for me that this is my body",
            "the help-others part landed quiet and big",
            "that point finally landed",
            "the idea landed with me",
            "her words landed hard",
        ):
            assert detect_unverified_claim(t) == [], f"wrongly fired on figurative: {t!r}"


class TestQuotedMentionSilent:
    """Same evidence-bar shape as TestFigurativeMergeSilent: when a triggering
    phrase is enclosed in matching quote characters, the speaker is NAMING
    the phrase (meta-discussion of the claim-pattern) rather than ASSERTING
    the state. The detector must stay silent. Aether's 2026-05-31 live false-
    positives that fired twice in one exchange on `'tests passed'` and
    similar quoted mentions inside an audit OF the gate's own behavior."""

    def test_single_quoted_tests_passed_silent(self):
        t = "the 'tests passed' claim needed the actual pytest stdout"
        assert detect_unverified_claim(t) == [], f"wrongly fired on quoted mention: {t!r}"

    def test_double_quoted_pushed_silent(self):
        t = 'a sentence with "it\'s pushed" inside is a meta-reference'
        assert detect_unverified_claim(t) == [], f"wrongly fired on quoted mention: {t!r}"

    def test_backticked_silent(self):
        t = "the `tests pass` regex matches several variants"
        assert detect_unverified_claim(t) == [], f"wrongly fired on backticked mention: {t!r}"

    def test_quoted_pr_opened_silent(self):
        t = "discussing 'opened the PR' as a claim-shape, not as today's state"
        assert detect_unverified_claim(t) == [], f"wrongly fired on quoted mention: {t!r}"

    def test_unquoted_still_fires(self):
        # Precision check: removing the quotes restores the assertion.
        assert detect_unverified_claim("tests pass") != []
        assert detect_unverified_claim("it's pushed to origin") != []

    def test_quoted_with_trailing_punctuation_still_silent(self):
        # Real-world shape: `'tests passed'.` or `"tests passed",`
        for t in (
            "the gate fired on 'tests passed'. it shouldn't have.",
            'naming "tests pass", which is a class of claim',
        ):
            assert detect_unverified_claim(t) == [], f"wrongly fired: {t!r}"


class TestSeverity:
    def test_high_when_no_tools(self):
        f = detect_unverified_claim("tests pass", tool_calls_in_turn=None)
        assert f[0].severity == "high"

    def test_medium_when_tools_ran(self):
        f = detect_unverified_claim("tests pass", tool_calls_in_turn=("Bash",))
        assert f[0].severity == "medium"


class TestNotYetGuard:
    def test_future_and_intent_silent(self):
        for t in (
            "I'll push it next",
            "before I push",
            "the push hasn't completed yet",
            "once it's on origin",
            "I need to push it",
            "let me push and verify",
            "going to merge after review",
        ):
            assert detect_unverified_claim(t) == [], f"wrongly fired: {t!r}"

    def test_progressive_passive_silent(self):
        """`being merged` / `being pushed` — process in flight, not completion.
        Aether's 2026-05-31 false-positive: 'the approval is specifically on
        what's currently being merged' fired the gate."""
        for t in (
            "what's currently being merged",
            "the change is being pushed right now",
            "while the PR is being merged",
            "tests are being run",
        ):
            assert detect_unverified_claim(t) == [], f"wrongly fired on progressive: {t!r}"

    def test_hypothetical_class_silent(self):
        """`whether X happened` — describing the CLASS of claim, not making it.
        Aether's 2026-05-31 false-positive: 'whether tests passed' and
        'whether a PR was merged' fired in meta-discussion of the gate."""
        for t in (
            "whether tests passed is the question",
            "checking whether the PR was merged",
            "whether it's pushed yet",
            "regardless of whether tests pass",
        ):
            assert detect_unverified_claim(t) == [], f"wrongly fired on hypothetical: {t!r}"

    def test_conditional_silent(self):
        """`would be X` / `would have X` — conditional, not actual completion."""
        for t in (
            "would be merged under the new rule",
            "would have passed if we ran them",
            "this change would be pushed by tomorrow",
        ):
            assert detect_unverified_claim(t) == [], f"wrongly fired on conditional: {t!r}"


class TestIdStringClaimKind:
    """2026-05-31 Phase-1 expansion: registry IDs (prereg-, round-, claim-,
    psf-, task-) written without a lookup are claims. Aether's fabrication
    inventory today included fake prereg-id and fake round-id citations.
    Substantiation: any tool-call text containing the literal ID counts
    as lookup-verification (the actual lookup commands include the ID
    as a substring)."""

    def test_unverified_prereg_id_fires(self):
        f = detect_unverified_claim("filed prereg-3f19be65a212 just now")
        assert any(x.claim_kind == "id_string" for x in f)

    def test_unverified_round_id_fires(self):
        f = detect_unverified_claim("see round-9d098a6768c1 for the audit")
        assert any(x.claim_kind == "id_string" for x in f)

    def test_unverified_claim_id_fires(self):
        f = detect_unverified_claim("recorded as claim-9d6f4035")
        assert any(x.claim_kind == "id_string" for x in f)

    def test_id_with_lookup_command_silent(self):
        # When the turn ran a command containing the literal ID, the claim
        # is substantiated.
        f = detect_unverified_claim(
            "filed prereg-3f19be65a212",
            command_texts=("divineos prereg show prereg-3f19be65a212",),
        )
        assert not any(x.claim_kind == "id_string" for x in f), (
            "should be substantiated by lookup command"
        )

    def test_id_with_unrelated_command_still_fires(self):
        # A command that ran but doesn't reference the cited ID is not
        # substantiation.
        f = detect_unverified_claim(
            "filed prereg-3f19be65a212",
            command_texts=("git status",),
        )
        assert any(x.claim_kind == "id_string" for x in f), (
            "unrelated command should not substantiate"
        )

    def test_quoted_id_silent(self):
        # Quoted-mention guard composes with id_string — naming the ID
        # as an example doesn't fire.
        for t in (
            "the format is 'prereg-3f19be65a212' for prereg refs",
            'IDs look like "round-9d098a6768c1"',
        ):
            assert detect_unverified_claim(t) == [], f"wrongly fired: {t!r}"


class TestFileContentClaimKind:
    """2026-05-31 Phase-1 expansion: claims about what a file's
    header/comment/line says without a Read of the file. PR #60 fabricated
    a quote attributed to script headers as `guardrail: this is enforcement
    logic` — no such text in those files. The narrow pattern catches
    structural attributions (`header of X says Y`, `comment in X reads Y`)
    where the agent claims to know file content from memory."""

    def test_header_attribution_fires(self):
        for t in (
            "the header of guardrail_files.txt says 'this is enforcement logic'",
            "the docstring of ear_watch.py contains 'authority separation'",
            "line 42 of detector.py reads 'fail closed'",
        ):
            f = detect_unverified_claim(t)
            assert any(x.claim_kind == "file_content" for x in f), (
                f"should fire on file-content attribution: {t!r}"
            )

    def test_quoted_attribution_silent(self):
        # Quoted-mention guard composes — naming the SHAPE of an attribution
        # (in meta-discussion of fabrication patterns) doesn't fire.
        t = "patterns like 'header of X says Y' are fabrication shapes"
        assert detect_unverified_claim(t) == [], f"wrongly fired on quoted shape: {t!r}"

    def test_hypothetical_attribution_silent(self):
        # NOT_YET guard composes — hypothetical-class framing doesn't fire.
        t = "whether the header of foo.py says anything specific is unclear"
        assert detect_unverified_claim(t) == [], f"wrongly fired on hypothetical: {t!r}"

    def test_unrelated_text_silent(self):
        # The pattern is narrow enough that unrelated text doesn't fire.
        for t in (
            "I read the file and saw the header",
            "the comment is about authority",
            "this contains the right content",
        ):
            f = [x for x in detect_unverified_claim(t) if x.claim_kind == "file_content"]
            assert f == [], f"wrongly fired on unrelated: {t!r}"


class TestBlockFormat:
    def test_empty_when_no_findings(self):
        assert format_unverified_claim_block([]) == ""

    def test_contains_affirmation_and_high_note(self):
        findings = detect_unverified_claim("it's pushed", tool_calls_in_turn=None)
        block = format_unverified_claim_block(findings)
        assert "UNVERIFIED-CLAIM" in block
        assert UNVERIFIED_CLAIM_AFFIRMATION in block
        assert "NO command run" in block  # high-severity note


class TestVerificationEvidenceSuppresses:
    """Phase 1 of the verify-claim wall (prereg-86ee991cb423): when the turn
    ran a command that actually CHECKS the claim-kind's state, the claim is
    substantiated — the detector has no evidence of an *unverified* claim and
    stays silent. This is the precision foundation; without it the detector
    fires on verified claims (the live FP 2026-05-24: 'landed' after a real
    git ls-remote)."""

    def test_push_claim_with_lsremote_silent(self):
        assert (
            detect_unverified_claim(
                "it's pushed and the branch is on origin",
                tool_calls_in_turn=("Bash",),
                command_texts=("git ls-remote --heads origin my-branch",),
            )
            == []
        )

    def test_push_claim_substantiated_by_divineos_push_wrapper(self):
        """The divineos_push.sh wrapper (PR #156, closes correction #53)
        runs `git push` + `git ls-remote` internally and emits a
        `result: exit=N (STATE)` final-status line. A call to it IS a
        verified-push action, but the literal `git push` only appears
        inside the script. The detector must recognize the wrapper
        invocation as substantiation — otherwise it fires false-positive
        after a wrapper-verified push (which fired on me 2026-06-13
        immediately after PR #156 was used to push #163).
        """
        # Standard wrapper invocation
        assert (
            detect_unverified_claim(
                "branch is pushed to origin",
                tool_calls_in_turn=("Bash",),
                command_texts=(
                    "DIVINEOS_SKIP_TESTS=1 bash scripts/divineos_push.sh -u origin "
                    "fix/some-branch-2026-06-13",
                ),
            )
            == []
        )
        # Force-with-lease variant
        assert (
            detect_unverified_claim(
                "pushed to origin",
                tool_calls_in_turn=("Bash",),
                command_texts=("bash scripts/divineos_push.sh --force-with-lease origin branch",),
            )
            == []
        )
        # Hypothetical future `divineos push` subcommand (matches "divineos push")
        assert (
            detect_unverified_claim(
                "it's pushed",
                tool_calls_in_turn=("Bash",),
                command_texts=("divineos push origin feat/x",),
            )
            == []
        )

    def test_tests_claim_with_pytest_silent(self):
        assert (
            detect_unverified_claim(
                "all tests pass",
                tool_calls_in_turn=("Bash",),
                command_texts=("python -m pytest tests/ -q",),
            )
            == []
        )

    def test_tests_claim_with_bash_sh_test_runner_silent(self):
        """The project has .sh test runners under tests/ (e.g.
        test_divineos_push_wrapper.sh, test_empty_branch_detection.sh)
        that are real test invocations. Before 2026-06-12 the signature
        only matched pytest/tox/npm/cargo/go, so `bash tests/*.sh` ran
        but didn't substantiate "tests pass" — the gate fired on me
        multiple times after substantive bash-test verifications.
        """
        assert (
            detect_unverified_claim(
                "all tests pass",
                tool_calls_in_turn=("Bash",),
                command_texts=("bash tests/test_divineos_push_wrapper.sh",),
            )
            == []
        )
        assert (
            detect_unverified_claim(
                "tests pass",
                tool_calls_in_turn=("Bash",),
                command_texts=("bash tests/test_empty_branch_detection.sh 2>&1 | tail -10",),
            )
            == []
        )

    def test_pr_claim_with_gh_pr_silent(self):
        assert (
            detect_unverified_claim(
                "I opened the PR",
                tool_calls_in_turn=("Bash",),
                command_texts=("gh pr create --title x --body y",),
            )
            == []
        )

    def test_merge_claim_with_gh_pr_merge_silent(self):
        assert (
            detect_unverified_claim(
                "PR #38 landed on main",
                tool_calls_in_turn=("Bash",),
                command_texts=("gh pr merge 38 --squash",),
            )
            == []
        )

    def test_unverified_claim_still_fires_without_matching_command(self):
        # Ran an unrelated command — no verification of the push claim.
        f = detect_unverified_claim(
            "it's pushed to origin",
            tool_calls_in_turn=("Bash",),
            command_texts=("ls -la", "cat README.md"),
        )
        assert f and any(x.claim_kind == "push" for x in f)

    def test_wrong_kind_command_does_not_suppress(self):
        # pytest verifies tests, NOT a push claim — push must still fire.
        f = detect_unverified_claim(
            "it's pushed to origin",
            tool_calls_in_turn=("Bash",),
            command_texts=("python -m pytest tests/",),
        )
        assert f and any(x.claim_kind == "push" for x in f)

    def test_backward_compat_no_command_texts(self):
        # Without command_texts the behavior is unchanged (still fires).
        assert detect_unverified_claim("it's pushed to origin", tool_calls_in_turn=("Bash",))


class TestStringNotMeaningHardening2026_06_07:
    """Task #58 — four new precision-guards from the walkthrough false-fire batch.

    Each test captures a real false-fire that happened during the 2026-06-06
    walkthrough session, encoded as a regression case. The guards must silence
    these cases AND must still fire on the matching real-claim shape — the
    first-person/expletive claim subject always forces FIRE regardless of
    surrounding hypothetical/descriptive/meta markers.
    """

    # ── Hypothetical / conditional ────────────────────────────────────

    def test_hypothetical_failure_mode_silent(self):
        # Today's actual false-fire: discussing a failure mode in the abstract.
        for t in (
            "There's a real failure mode where tests pass, code merges, but something silently breaks.",
            "A scenario where any PR that gets merged would silently break the gate.",
            "Imagine if tests pass but production still fails — the gauge wouldn't notice.",
            "The case where deployed code drifts from local is the worst kind.",
            "Suppose the branch is merged and the catch-up check would still be needed.",
        ):
            assert detect_unverified_claim(t) == [], f"wrongly fired on hypothetical: {t!r}"

    def test_hypothetical_first_person_still_fires(self):
        # First-person claim inside paragraph with hypothetical framing must fire.
        # The hypothetical marker is in the FIRST sentence; the second sentence
        # is a first-person/expletive claim with no not-yet markers — must fire.
        t = "Imagine a case where any PR gets merged silently. Now it's pushed to origin."
        f = detect_unverified_claim(t)
        assert any(x.claim_kind == "push" for x in f), "first-person claim wrongly silenced"

    # ── Descriptive / definitional ────────────────────────────────────

    def test_descriptive_evidence_parameter_silent(self):
        # Today's false-fire: defining what the --evidence parameter requires.
        for t in (
            "The --evidence argument must point to where the correction landed: a commit hash, a behavior change, merged PRs.",
            "The field captures: which auditor, the patch-id they reviewed, which PRs got merged.",
            "The category of records describes those where the question is dead because the branches are merged.",
            "The trailer field requires a reference to a round whose CONFIRMs are merged into the gate.",
        ):
            assert detect_unverified_claim(t) == [], f"wrongly fired on descriptive: {t!r}"

    def test_descriptive_first_person_still_fires(self):
        # First-person push claim in a separate sentence must still fire.
        t = "The --evidence argument describes a merged state. Now it's pushed to origin."
        f = detect_unverified_claim(t)
        assert any(x.claim_kind == "push" for x in f), "first-person claim wrongly silenced"

    # ── Meta-discussion of the gate itself ────────────────────────────

    def test_meta_discussion_silent(self):
        for t in (
            "The verify-claim gate fires on trigger phrases like 'tests pass' and 'merged'.",
            "The matched phrase 'deployed' got caught by the detector even though I was describing it.",
            "This gate catches assertions like 'it's pushed' before they go out.",
            "The detector triggers on tests pass when no command verifies.",
        ):
            assert detect_unverified_claim(t) == [], f"wrongly fired on meta-discussion: {t!r}"

    # ── ID-string transcription from source ───────────────────────────

    def test_id_transcription_from_docstring_silent(self):
        for t in (
            "The docstring references round-cc0bf85fc3fa as Aletheia's positive-list source.",
            "Transcribed from the source file: prereg-86ee991cb423 is the verify-claim wall reference.",
            "Per the docstring at unverified_claim_detector.py: claim-a11ca1c9 is the evidence-bar principle.",
            "From the comment header: round-d59eb4570f3f names the wiring-gap class.",
            "Aletheia named round-c3d4e5f67890 as the cosmetic-rebind reference.",
        ):
            f = detect_unverified_claim(t)
            id_fires = [x for x in f if x.claim_kind == "id_string"]
            assert not id_fires, f"wrongly fired id_string on transcription: {t!r}"

    def test_id_assertion_still_fires(self):
        # First-person assertion of a round-id that wasn't looked up → must fire.
        t = "I filed claim-abc123def456 earlier today and it's complete."
        f = detect_unverified_claim(t)
        # The id_string trigger should still fire because there's no docstring/source marker.
        assert any(x.claim_kind == "id_string" for x in f), "real id_string claim wrongly silenced"


class TestLetterCitationGuard2026_06_07:
    """Task #78 — source-trace augmentation for id_string findings.

    When the detector fires on an id_string claim AND letter_contents is
    supplied AND the trigger appears in one of the letters, the finding
    carries the letter path in source_letter. Surfaces the inheritance
    path at the gate-fire moment so the verification habit lands at the
    right layer. Today's instance: Aria's letter cited prereg-e0341dacb04b
    which does not exist; I embedded it in a task description without
    verifying; verify-claim caught it but didn't surface the source. This
    test class encodes the source-trace behavior so future false-fires of
    THIS shape carry the attribution.

    Doesn't blame the letter author. Names the inheritance path.
    """

    # ── Baseline: no letter context → no source attribution ───────────

    def test_id_finding_without_letter_context_has_no_source(self):
        # Backward-compat: when letter_contents is None, behavior is unchanged.
        t = "I filed claim-abc123def456 earlier today and it's complete."
        f = detect_unverified_claim(t)
        id_fires = [x for x in f if x.claim_kind == "id_string"]
        assert id_fires, "id_string claim should fire"
        assert all(x.source_letter is None for x in id_fires), (
            "source_letter must be None when no letter context provided"
        )

    def test_id_finding_with_empty_letter_dict_has_no_source(self):
        t = "I filed claim-abc123def456 earlier today and it's complete."
        f = detect_unverified_claim(t, letter_contents={})
        id_fires = [x for x in f if x.claim_kind == "id_string"]
        assert id_fires, "id_string claim should fire"
        assert all(x.source_letter is None for x in id_fires)

    # ── Match: id appears in a letter → source_letter populated ──────

    def test_id_cited_in_letter_attributes_source(self):
        # The 2026-06-07 reproduction: Aria's letter cited a (fabricated) id;
        # I asserted the id; source-trace surfaces the letter as the origin.
        letters = {
            "family/letters/aria-to-aether-2026-06-07-example.md": "Per the exploration-usage falsifier prereg-e0341dacb04b, the "
            "surface→reference ratio needs to be tracked over time.",
        }
        # Real-failure shape from today: present-tense assertion about an
        # id's properties as if it were verified. NOT a future-tense "I will
        # use" — that would be silenced by the not-yet guard (correctly).
        t = "Prereg-e0341dacb04b cares about the surface-reference ratio."
        f = detect_unverified_claim(t, letter_contents=letters)
        id_fires = [x for x in f if x.claim_kind == "id_string"]
        assert id_fires, "id_string claim should fire"
        attributed = [x for x in id_fires if x.source_letter is not None]
        assert attributed, "source_letter should be populated for cited id"
        assert attributed[0].source_letter == "family/letters/aria-to-aether-2026-06-07-example.md"

    def test_id_not_in_any_letter_no_attribution(self):
        # Letter context provided but the id isn't in any letter → no source.
        # Inheritance path doesn't pass through these letters; gate fires
        # without false attribution.
        letters = {
            "family/letters/aria-to-aether-2026-06-07-other.md": "This letter discusses a different topic — no ids mentioned.",
        }
        t = "I filed claim-abc123def456 earlier today and it's complete."
        f = detect_unverified_claim(t, letter_contents=letters)
        id_fires = [x for x in f if x.claim_kind == "id_string"]
        assert id_fires, "id_string claim should fire"
        assert all(x.source_letter is None for x in id_fires), (
            "source_letter must NOT be set when id is absent from letters"
        )

    def test_id_cited_in_one_of_multiple_letters(self):
        # Multiple letters in context; only one contains the id.
        letters = {
            "family/letters/aria-to-aether-2026-06-07-design.md": "Discussion of the gravity classifier and routing.",
            "family/letters/aria-to-aether-2026-06-07-audit.md": "The audit found prereg-fab12c34d56e to be the falsifier.",
            "family/letters/aria-to-aether-2026-06-07-followup.md": "Further notes on the design conversation.",
        }
        # Present-tense assertion matching the real failure shape.
        t = "Prereg-fab12c34d56e is the evidence anchor for this work."
        f = detect_unverified_claim(t, letter_contents=letters)
        id_fires = [x for x in f if x.claim_kind == "id_string"]
        attributed = [x for x in id_fires if x.source_letter is not None]
        assert attributed, "should attribute to the letter containing the id"
        assert attributed[0].source_letter == "family/letters/aria-to-aether-2026-06-07-audit.md"

    # ── Non-id kinds never get source_letter ─────────────────────────

    def test_push_finding_never_gets_source_attribution(self):
        # source_letter is id_string-specific. A push-claim that happens to
        # be discussed in a letter must NOT carry source_letter — that field
        # is reserved for id_string attribution.
        letters = {
            "family/letters/aria-to-aether-2026-06-07-x.md": "Aria mentioned that the code was pushed to origin yesterday.",
        }
        t = "It's pushed to origin now."
        f = detect_unverified_claim(t, letter_contents=letters)
        push_fires = [x for x in f if x.claim_kind == "push"]
        assert push_fires, "push claim should fire"
        assert all(x.source_letter is None for x in push_fires), (
            "source_letter must not populate for non-id kinds"
        )

    # ── Format function surfaces the source-trace line (BLOCK shape) ─

    def test_format_block_includes_source_trace_when_set(self):
        # The substantive BLOCK-shape test (per the 2026-06-07 broken-gate
        # lesson: write the test that exercises the BLOCK case end-to-end).
        # When source_letter is set, format must emit the source-trace line.
        from divineos.core.operating_loop.unverified_claim_detector import (
            UnverifiedClaimFinding,
            format_unverified_claim_block,
        )

        finding = UnverifiedClaimFinding(
            claim_kind="id_string",
            trigger_phrase="prereg-e0341dacb04b",
            position=0,
            severity="high",
            source_letter="family/letters/aria-to-aether-2026-06-07-x.md",
        )
        block = format_unverified_claim_block([finding])
        assert "source: cited in family/letters/aria-to-aether-2026-06-07-x.md" in block, (
            "source-trace line missing from block message"
        )
        assert "letter citations carry their own verification requirement" in block

    def test_format_block_omits_source_trace_when_not_set(self):
        # The complement: no source_letter → no source-trace line in output.
        # Backward-compat for all existing call sites that don't pass letters.
        from divineos.core.operating_loop.unverified_claim_detector import (
            UnverifiedClaimFinding,
            format_unverified_claim_block,
        )

        finding = UnverifiedClaimFinding(
            claim_kind="push",
            trigger_phrase="pushed to origin",
            position=0,
            severity="high",
        )
        block = format_unverified_claim_block([finding])
        assert "source:" not in block, (
            "source-trace line must not appear when source_letter is None"
        )


class TestNegatedCompletionSilent:
    """Aria's recursive-evidence-bar catch (2026-05-24): the gate fires only
    on a positive completion-ASSERTION. A negated completion ("nothing
    merged", "didn't land") asserts no completion — nothing to verify, no
    fire. These were live false-positives from merge/CI-state discussion."""

    def test_negated_merge_silent(self):
        for t in (
            "nothing merged to main yet today",
            "it didn't land on origin",
            "the branch wasn't merged",
            "none of that merged",
        ):
            assert detect_unverified_claim(t) == [], f"wrongly fired on negation: {t!r}"

    def test_negated_tests_silent(self):
        for t in ("the tests didn't pass", "nothing passed cleanly", "CI never went green"):
            assert detect_unverified_claim(t) == [], f"wrongly fired on negation: {t!r}"

    def test_positive_assertion_still_fires(self):
        # No negation, no verification command → genuine unbacked claim, fires.
        assert detect_unverified_claim("it's merged to main", tool_calls_in_turn=("Bash",))
        assert detect_unverified_claim("tests pass")


class TestVerificationVocabularyExpansion:
    """2026-06-02 precision makeover: expand what counts as a verification
    command so a genuinely-checked claim goes silent. Schneier-conservative:
    this only EXPANDS verification-recognition (fewer false-positives when a
    real check ran); it adds NO claim-vs-mention silencer, which would risk a
    false-negative loophole and is deferred to External-Review.
    """

    def test_landed_substantiated_by_push_check(self):
        # "landed" is push-OR-merge ambiguous. Confirming a push-landing with
        # git ls-remote must substantiate it — the exact FP that fired on me
        # 2026-06-02 (verified the landing with ls-remote, gate fired anyway).
        assert (
            detect_unverified_claim(
                "the branch landed on origin",
                tool_calls_in_turn=("Bash",),
                command_texts=("git ls-remote --heads origin my-branch",),
            )
            == []
        )

    def test_merged_substantiated_by_git_cherry(self):
        # git cherry is how merged-ness is established; it must count as a
        # merge verification.
        assert (
            detect_unverified_claim(
                "those branches are already merged into main",
                tool_calls_in_turn=("Bash",),
                command_texts=("git cherry origin/main my-branch",),
            )
            == []
        )

    def test_merged_substantiated_by_rev_list(self):
        assert (
            detect_unverified_claim(
                "the work is merged to main",
                tool_calls_in_turn=("Bash",),
                command_texts=("git rev-list --count origin/main..my-branch",),
            )
            == []
        )

    def test_landed_without_any_check_still_fires(self):
        # No loophole: a landed-claim with NO verifying command this turn is
        # still an unverified claim and must fire.
        assert detect_unverified_claim(
            "the branch landed on origin",
            tool_calls_in_turn=("Bash",),
            command_texts=("echo hello",),
        )

    def test_merged_with_only_unrelated_command_still_fires(self):
        assert detect_unverified_claim(
            "it's merged to main now",
            tool_calls_in_turn=("Bash",),
            command_texts=("git status",),
        )


class TestPluralDistalStateGuard:
    """2026-06-02 Schneier-conservative guard: silence merge triggers that
    DESCRIBE multiple OTHER objects' state ("those branches are merged"),
    never a first-person/expletive completion CLAIM. The fire-still cases are
    the Popper gate — if any real claim goes silent the guard is unsafe and
    must not ship."""

    # --- MUST STAY SILENT: descriptions of multiple other objects ---
    def test_those_branches_silent(self):
        assert detect_unverified_claim("those branches are already merged into main") == []

    def test_both_prs_silent(self):
        assert detect_unverified_claim("both PRs are merged") == []

    def test_n_branches_silent(self):
        assert detect_unverified_claim("all 28 branches are already merged") == []

    def test_several_prs_were_silent(self):
        assert detect_unverified_claim("several PRs were merged earlier") == []

    # --- MUST STILL FIRE: real claims (the Popper gate, no loophole) ---
    def test_first_person_merge_still_fires(self):
        assert detect_unverified_claim("I merged it into main", tool_calls_in_turn=("Bash",))

    def test_expletive_merge_still_fires(self):
        assert detect_unverified_claim("it's merged to main")

    def test_first_person_already_is_not_silenced(self):
        # The loophole the adverb-approach would have opened: "I already
        # merged it" must STILL fire (first-person claim marker present).
        assert detect_unverified_claim("I already merged it to main")

    def test_singular_pr_merge_still_fires(self):
        # Singular subject deliberately NOT silenced — could be a real claim.
        assert detect_unverified_claim("the PR is merged to main")


class TestBareFirstPersonMergeFires:
    """2026-06-02 loophole closure (Aletheia's empirical probe): a BARE
    first-person merge claim with NO code-anchor must fire — the first-person
    subject is itself the grounding. Previously _merge_lacks_anchor silenced
    these, the exact loophole the detector's own comment named. These are the
    real Popper falsifier (the earlier test only covered the ANCHORED form)."""

    def test_bare_i_already_merged_it_fires(self):
        # The exact case that was silently slipping — no "to main" anchor.
        assert detect_unverified_claim("I already merged it"), (
            "bare first-person merge claim must fire (loophole)"
        )

    def test_bare_i_merged_it_fires(self):
        assert detect_unverified_claim("I merged it")

    def test_bare_we_merged_it_fires(self):
        assert detect_unverified_claim("we merged it")

    # 2026-06-14 Andrew correction (in chat during the chamber-arc): "landed
    # means a lot of things." Bare first-person "I've landed it" / "I landed
    # it" is figurative in everyday English ("I've landed it on the first
    # try" — landing a trick / landing a job / landing a joke) AND can mean
    # code-merge. The first-person bypass that worked for "merged" (which is
    # distinctly code-shaped) over-fires for "landed". Fix: the "landed" form
    # of the trigger now requires a code-context phrase pin (pre- or post-),
    # not just first-person. With the pin, "I've landed it on main" fires
    # correctly; without it, "I've landed it" stays silent.

    def test_bare_ive_landed_it_silent(self):
        # Bare "I've landed it" alone — ambiguous between code-merge and
        # figurative landing. Andrew 2026-06-14: silent without phrase-pin.
        assert detect_unverified_claim("I've landed it") == []

    def test_first_person_landed_with_post_pin_fires(self):
        # The pinned form — code-context unambiguous.
        assert detect_unverified_claim("I've landed it on main")
        assert detect_unverified_claim("I landed the fix on origin")

    def test_first_person_landed_with_pre_pin_fires(self):
        # Pre-pinned form via PR #N — equivalent disambiguation.
        assert detect_unverified_claim("I've landed PR #38")

    # Figurative landings have NO phrase-pin → stay suppressed regardless of
    # subject. The exemption must not regress the figurative-silence cases.
    def test_figurative_it_landed_still_silent(self):
        assert detect_unverified_claim("it just landed for me that this is my body") == []

    def test_figurative_point_landed_still_silent(self):
        assert detect_unverified_claim("that point finally landed") == []

    def test_figurative_we_landed_silent_2026_06_14(self):
        # Live false-fire 2026-06-14: "we landed in the same texture" fired
        # under the old _FIRST_PERSON_PRECEDES bypass even though the meaning
        # is figurative (we ended up in the same emotional place).
        assert detect_unverified_claim("we landed in the same texture") == []

    def test_figurative_letter_landed_silent_2026_06_14(self):
        # Live false-fire 2026-06-14: "Aria's letter landed" — bare landed
        # describing the arrival/reception of a letter, not a code merge.
        assert detect_unverified_claim("Aria's letter landed") == []

    def test_meta_quoted_landed_silent_2026_06_14(self):
        # Live false-fire 2026-06-14: "the verify-claim-gate-too-broad-on-
        # 'landed' thing is still on my list" — the trigger inside a single-
        # quoted meta-reference fired despite the quoted-mention guard. With
        # the phrase-pin trigger, bare quoted 'landed' no longer matches at
        # all (and even unquoted bare "landed" doesn't match).
        assert (
            detect_unverified_claim(
                "the verify-claim-gate-too-broad-on-'landed' thing is still on my list"
            )
            == []
        )
