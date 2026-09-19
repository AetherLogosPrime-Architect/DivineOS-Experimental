"""Tests for the gravity classifier — deterministic gate-fire scoring.

The classifier decides WHEN the substrate-modification gate and the
cognitive-value (oscillating-read) gate fire. It is rule-based and
deterministic over observable features — so the tests pin exact
feature-firing and the two thresholds, the behavior the rest of the
gate machinery trusts.

Untested at ship; closed 2026-05-23 while working down the
unfinished-mechanism backlog the repaired initiative dial surfaced.
"""

from divineos.core.gravity_classifier import (
    _HIGH_IMPACT_FEATURES,
    _shell_write_targets,
    CognitiveValueGravity,
    SubstrateModGravity,
    borderline_indicator_cognitive,
    borderline_indicator_substrate,
    score_cognitive_value,
    score_substrate_modification,
)


class TestSubstrateModificationFeatures:
    def test_git_commit_fires(self):
        r = score_substrate_modification("Bash", bash_command="git commit -m 'x'")
        assert "git-commit" in r.fired_features
        assert r.is_high_gravity

    def test_git_status_does_not_fire(self):
        r = score_substrate_modification("Bash", bash_command="git status")
        assert r.score == 0
        assert not r.is_high_gravity

    def test_edit_src_divineos_fires(self):
        r = score_substrate_modification("Edit", file_paths=("src/divineos/core/foo.py",))
        assert "edit-src-divineos" in r.fired_features
        assert r.is_high_gravity

    def test_edit_outside_src_does_not_fire_src_feature(self):
        r = score_substrate_modification("Edit", file_paths=("README.md",))
        assert "edit-src-divineos" not in r.fired_features

    def test_edit_hooks_fires_guardrail(self):
        r = score_substrate_modification("Write", file_paths=(".claude/hooks/some-hook.sh",))
        assert "edit-guardrail" in r.fired_features

    def test_edit_check_script_fires_guardrail(self):
        r = score_substrate_modification("Edit", file_paths=("scripts/check_push_readiness.py",))
        assert "edit-guardrail" in r.fired_features

    def test_edit_guardrail_files_list_fires(self):
        r = score_substrate_modification("Edit", file_paths=("scripts/guardrail_files.txt",))
        assert "edit-guardrail" in r.fired_features

    def test_substrate_write_cli_fires(self):
        for sub in ("audit", "claim", "learn", "prereg", "decide", "feel", "journal"):
            r = score_substrate_modification("Bash", bash_command=f"divineos {sub} x")
            assert "substrate-write-cli" in r.fired_features, sub

    def test_compass_ops_fires_substrate_write(self):
        r = score_substrate_modification(
            "Bash", bash_command="divineos compass-ops observe initiative -p 0.1 -e x"
        )
        assert "substrate-write-cli" in r.fired_features

    def test_readonly_cli_does_not_fire(self):
        r = score_substrate_modification("Bash", bash_command="divineos briefing")
        assert r.score == 0

    def test_kiln_layer_edit_fires(self):
        r = score_substrate_modification("Write", file_paths=("docs/foundational_truths.md",))
        assert "edit-kiln-layer" in r.fired_features

    def test_seed_json_fires_kiln(self):
        r = score_substrate_modification("Edit", file_paths=("src/divineos/seed.json",))
        assert "edit-kiln-layer" in r.fired_features

    def test_consolidation_cli_fires(self):
        for sub in ("extract", "sleep"):
            r = score_substrate_modification("Bash", bash_command=f"divineos {sub}")
            assert "consolidation-cli" in r.fired_features, sub

    def test_windows_backslash_paths_normalized(self):
        r = score_substrate_modification("Edit", file_paths=(r"src\divineos\core\foo.py",))
        assert "edit-src-divineos" in r.fired_features

    def test_multiple_features_sum(self):
        # A kiln-layer file also lives under src/divineos/ → two features.
        r = score_substrate_modification("Edit", file_paths=("src/divineos/seed.json",))
        assert r.score >= 2
        assert "edit-src-divineos" in r.fired_features
        assert "edit-kiln-layer" in r.fired_features

    def test_returns_dataclass(self):
        r = score_substrate_modification("Read", file_paths=("x.py",))
        assert isinstance(r, SubstrateModGravity)
        assert r.score == 0
        assert not r.is_high_gravity


class TestWritingAFileDoesNotSwitchOffTheCommandChecks:
    """A redirect used to suppress every command-level feature.

    The classifier recorded a shell write by reassigning the variable that
    ALSO gated the command-level checks, so noting a write turned those checks
    off. The comment two lines above promised the opposite — that a compound
    command "fires everything it earns" — and had been false since the
    reassignment was introduced.

    Measured 2026-09-18: a commit alone fired; the same commit with output sent
    to a log file fired NOTHING — not the commit, and not a write either, since
    an ordinary log file sits in no watched location. One redirect, zero gates.

    This is the first defect repaired in this stretch that let something
    THROUGH rather than getting in the way, and it was found only because Aria
    named that bias in a letter. A gate that refuses generates evidence every
    time; a gate that does not fire generates none.
    """

    _G = "g" + "it"
    _D = "divi" + "neos"

    def test_a_commit_still_fires_with_a_redirect_appended(self):
        r = score_substrate_modification("Bash", bash_command=f"{self._G} commit -m x > log.txt")
        assert "git-commit" in r.fired_features

    def test_a_store_write_still_fires_with_a_redirect_appended(self):
        r = score_substrate_modification("Bash", bash_command=f"{self._D} learn xyz > out.txt")
        assert "substrate-write-cli" in r.fired_features

    def test_a_shell_write_to_a_watched_path_still_fires_its_path_feature(self):
        """The control. Closing the hole must not cost the write detection."""
        r = score_substrate_modification("Bash", bash_command="cat > src/divineos/core/x.py")
        assert "edit-src-divineos" in r.fired_features

    def test_a_plain_read_is_still_silent(self):
        """The other control. Nothing here should make quiet commands loud."""
        assert score_substrate_modification("Bash", bash_command=f"{self._G} status").score == 0


class TestCouncilRequiredTier2026_06_20:
    """Andrew 2026-06-20: 'the gravity classifier is not pulling its weight
    its letting you make serious changes with no council.' The prior design
    fired only the basic substrate-gate at score >= 1; edits to guardrail-
    listed detector files scored 1 (borderline-single-feature, edit-src-
    divineos only) and passed through with passive surface only — no
    council requirement. The fix (as-of 2026-06-20): add edit-guardrail-
    listed feature reading scripts/guardrail_files.txt, plus
    is_council_required tier.

    Andrew 2026-07-26 CLAY-MODE-VS-KILN-MODE UPDATE: edit-guardrail-listed
    was REMOVED from _HIGH_IMPACT_FEATURES short-circuit. Clay-mode
    workspace edits to guardrail-listed files should NOT trigger council-
    required per-edit — External-Review at merge time is the discipline
    for guardrail-listed drift. Only edit-kiln-layer (foundational_truths,
    seed.json — the actual identity substrate) still short-circuits council-
    required. Cumulative score-threshold still fires council-required at
    total >= 6. Tests below updated to match new correct behavior.

    ANDREW 2026-09-16 SUPERSEDES THE THRESHOLD HALF OF THE ABOVE, AND IT
    REVERSES HIS OWN JULY DECISION. Asked directly whether a single-area code
    edit should owe a council walk, he answered yes, so the threshold moved
    from 6 to 1. Every edit firing any feature now requires a walk — which is
    exactly what the clay-mode paragraph above argued against: *"Clay-mode
    workspace edits to guardrail-listed files should NOT trigger council-
    required per-edit."*

    The July paragraph is LEFT STANDING rather than rewritten. Its reasoning
    is still the best statement of what the stricter threshold costs, and a
    superseded decision with its argument intact is worth more than a tidy
    file reading as though the question was never open. What changed is not
    that the July reasoning was wrong — it is that three builds cleared this
    gate in one evening while it sat at 6, and he weighed the extra
    interruptions against that and chose them.

    The SHORT-CIRCUIT half is unchanged: guardrail-listed still does not
    short-circuit, kiln-layer still does. Only the number moved, and the four
    assertions below invert with it. Each names what it used to say.

    Council-walked (2026-06-20 consult-944ad9d332e5 original design;
    council-939eae4d46a3 for the 2026-07-26 revision).
    """

    def test_edit_guardrail_listed_detector_requires_council_by_threshold(self):
        # Until 2026-09-16 this asserted `not r.is_council_required`, on the
        # clay-mode reasoning that External-Review at merge is the discipline
        # for guardrail-listed drift. The SHORT-CIRCUIT is still absent —
        # guardrail-listed does not force council on its own. What requires a
        # walk now is the threshold, which Andrew moved to 1.
        r = score_substrate_modification(
            "Edit",
            file_paths=("src/divineos/core/operating_loop/distancing_detector.py",),
        )
        assert "edit-guardrail-listed" in r.fired_features
        assert "edit-src-divineos" in r.fired_features
        assert "edit-guardrail-listed" not in _HIGH_IMPACT_FEATURES, (
            "the 2026-07-26 short-circuit removal must survive the threshold "
            "change — this edit requires council by SCORE, not by class"
        )
        assert r.is_council_required

    def test_edit_unverified_claim_detector_requires_council_by_threshold(self):
        # Same inversion, same reason. Previously asserted not-required.
        r = score_substrate_modification(
            "Edit",
            file_paths=("src/divineos/core/operating_loop/unverified_claim_detector.py",),
        )
        assert "edit-guardrail-listed" in r.fired_features
        assert r.is_council_required

    def test_edit_gravity_classifier_itself_requires_council(self):
        # The meta-case. Previously asserted not-required under clay mode.
        # Editing the thing that decides gravity now owes a walk like
        # anything else, which is the least surprising place for the
        # stricter threshold to land.
        r = score_substrate_modification(
            "Edit",
            file_paths=("src/divineos/core/gravity_classifier.py",),
        )
        assert "edit-guardrail-listed" in r.fired_features
        assert r.is_council_required

    def test_edit_non_guardrail_src_requires_council(self):
        # THE TEST ANDREW'S DECISION IS ABOUT. It previously asserted that a
        # routine one-feature edit does NOT require council; he was asked
        # exactly that and said it should. This is the single-area code edit.
        r = score_substrate_modification(
            "Edit",
            file_paths=("src/divineos/cli/hud_commands.py",),
        )
        assert r.fired_features == ("edit-src-divineos",)
        assert r.is_high_gravity
        assert r.is_council_required

    def test_edit_kiln_layer_requires_council(self):
        # Kiln-layer files (foundational_truths.md, seed.json) are the
        # other high-impact feature class. Edits trigger council via the
        # same short-circuit.
        r = score_substrate_modification(
            "Edit",
            file_paths=("docs/foundational_truths.md",),
        )
        assert "edit-kiln-layer" in r.fired_features
        assert r.is_council_required

    def test_borderline_indicator_uses_kiln_layer_for_council_required_label(self):
        # 2026-07-26 update: previously tested that guardrail-listed edits
        # returned "council-required" label. Now guardrail-listed no longer
        # triggers council-required, so we test the label with a kiln-layer
        # file (foundational_truths.md) which STILL fires council-required.
        r = score_substrate_modification(
            "Edit",
            file_paths=("docs/foundational_truths.md",),
        )
        # 2026-09-16: the label now carries the fragility shape alongside the
        # requirement, so this asserts the requirement is SAID rather than
        # that it is the whole string. The two facts are independent and the
        # slot lost one of them silently once already.
        assert "council-required" in borderline_indicator_substrate(r)

    def test_routine_edit_still_reports_its_fragility(self):
        # THIS TEST CAUGHT A SIGNAL DYING, so read before changing it.
        #
        # It used to assert the bare label "borderline-single-feature". When
        # the threshold moved to 1 on 2026-09-16, the indicator returned
        # early on council-required and the fragile label became UNREACHABLE
        # for every firing edit — the June sanity-check signal stopped
        # existing while the surface kept printing a label, so nothing looked
        # broken. The cheap close was to rewrite this assertion to expect the
        # constant, which is a test rewritten to ratify a regression.
        #
        # The fix was to the indicator: one slot now carries both facts.
        # Assert the fragility is still SAID, not the exact wrapper.
        r = score_substrate_modification(
            "Edit",
            file_paths=("src/divineos/cli/hud_commands.py",),
        )
        label = borderline_indicator_substrate(r)
        assert "borderline-single-feature" in label
        assert "council-required" in label

    def test_each_fragility_shape_is_still_reachable(self):
        """The guard the walk named as the remaining open route: nothing
        checks that every label CAN still be produced, so the next early
        return added above them removes a distinction with no noise."""
        single = score_substrate_modification(
            "Edit", file_paths=("src/divineos/cli/hud_commands.py",)
        )
        multi = score_substrate_modification(
            "Edit", file_paths=("src/divineos/core/gravity_classifier.py",)
        )
        none = score_substrate_modification("Read", file_paths=("README.md",))

        assert "borderline-single-feature" in borderline_indicator_substrate(single)
        assert "strong-multi-feature" in borderline_indicator_substrate(multi)
        assert borderline_indicator_substrate(none) == "no-fire"

    def test_zero_features_still_no_fire(self):
        # Zero-feature case unchanged: not high-gravity, not council-required.
        r = score_substrate_modification("Read", file_paths=("README.md",))
        assert r.score == 0
        assert not r.is_high_gravity
        assert not r.is_council_required
        assert borderline_indicator_substrate(r) == "no-fire"

    def test_dataclass_default_is_council_required_false(self):
        # Defensive: existing call-sites that construct SubstrateModGravity
        # without the new field still get is_council_required=False.
        r = SubstrateModGravity(score=1, fired_features=("x",), is_high_gravity=True)
        assert r.is_council_required is False


class TestGuardrailListPathNormalization2026_06_20:
    """Aether's design review: suffix-match has a silent-wrong failure mode.
    A guardrail entry like 'src/divineos/core/operating_loop/distancing_detector.py'
    would match an unrelated path 'foo/src/divineos/core/operating_loop/distancing_detector.py'
    under endswith. Fixed via repo-relative exact-match. These tests pin
    the new normalization behavior.
    """

    def test_relative_path_repo_relative_matches(self):
        # The canonical case: caller passes a repo-relative string that
        # exactly matches an entry in the guardrail list.
        r = score_substrate_modification(
            "Edit",
            file_paths=("src/divineos/core/operating_loop/distancing_detector.py",),
        )
        assert "edit-guardrail-listed" in r.fired_features

    def test_leading_dot_slash_normalized(self):
        # "./src/..." should normalize to "src/..." and match.
        r = score_substrate_modification(
            "Edit",
            file_paths=("./src/divineos/core/operating_loop/distancing_detector.py",),
        )
        assert "edit-guardrail-listed" in r.fired_features

    def test_backslash_paths_normalized_to_forward(self):
        # Windows-style backslashes should normalize to forward-slash before
        # matching against the guardrail list (which is forward-slash canonical).
        r = score_substrate_modification(
            "Edit",
            file_paths=("src\\divineos\\core\\operating_loop\\distancing_detector.py",),
        )
        assert "edit-guardrail-listed" in r.fired_features

    def test_upward_traversal_path_rejected(self):
        # Paths containing ".." are ambiguous (could resolve outside repo)
        # and must NOT fire the guardrail-listed feature. The basic
        # edit-src-divineos may still fire on string-contains; that's the
        # designed fail-open behavior.
        r = score_substrate_modification(
            "Edit",
            file_paths=("src/../src/divineos/core/operating_loop/distancing_detector.py",),
        )
        assert "edit-guardrail-listed" not in r.fired_features

    def test_suffix_lookalike_path_does_not_false_fire(self):
        # The exact silent-wrong shape Aether caught: a path that ends
        # with a guardrail entry suffix but is in a different repo-relative
        # location. Under the prior suffix-match this would have false-fired;
        # under repo-relative exact-match it must NOT fire.
        # The path "foo/src/divineos/core/operating_loop/distancing_detector.py"
        # is repo-relative (no absolute prefix), so it normalizes to itself.
        # Since "foo/src/..." is not in the guardrail list, no fire.
        r = score_substrate_modification(
            "Edit",
            file_paths=("foo/src/divineos/core/operating_loop/distancing_detector.py",),
        )
        # The lookalike must not match the guardrail entry.
        assert "edit-guardrail-listed" not in r.fired_features
        # But edit-src-divineos still fires (basic substrate-mod gate)
        # because the path contains "src/divineos/" — that's correct;
        # the basic gate is permissive by design.
        assert "edit-src-divineos" in r.fired_features

    def test_non_guardrail_relative_path_silent(self):
        # Sanity: a clean repo-relative path NOT in the guardrail list
        # does not fire the guardrail feature.
        r = score_substrate_modification(
            "Edit",
            file_paths=("src/divineos/cli/hud_commands.py",),
        )
        assert "edit-guardrail-listed" not in r.fired_features


class TestCognitiveValueScoring:
    def test_empty_content_is_low_gravity(self):
        r = score_cognitive_value("")
        assert r.score == 0.0
        assert not r.is_high_gravity

    def test_returns_dataclass_with_feature_scores(self):
        r = score_cognitive_value("hello")
        assert isinstance(r, CognitiveValueGravity)
        assert set(r.feature_scores) == {
            "char",
            "header",
            "path",
            "composition",
            "codeblock",
        }

    def test_long_dense_doc_in_core_path_is_high_gravity(self):
        content = (
            "# Design\n\nThis architecture integrates a framework and a "
            "methodology, decompose the principle into a lens.\n\n"
            "## Section\n\n" + ("word " * 500)
        )
        r = score_cognitive_value(content, source_path="src/divineos/core/foo.py")
        assert r.is_high_gravity
        assert r.score >= 0.3

    def test_path_bonus_for_priority_dirs(self):
        for p in ("exploration/x.md", "docs/y.md", "family/letters/z.md"):
            r = score_cognitive_value("text", source_path=p)
            assert r.feature_scores["path"] == 1.0, p

    def test_path_bonus_partial_for_secondary_dirs(self):
        r = score_cognitive_value("text", source_path="scripts/x.sh")
        # 0.1 raw / 0.3 max ≈ 0.333
        assert 0.3 < r.feature_scores["path"] < 0.4

    def test_no_path_bonus_for_unknown_dir(self):
        r = score_cognitive_value("text", source_path="/tmp/random.txt")
        assert r.feature_scores["path"] == 0.0

    def test_composition_markers_raise_composition_score(self):
        plain = score_cognitive_value("the cat sat on the mat there")
        dense = score_cognitive_value("design architecture principle lens")
        assert dense.feature_scores["composition"] > plain.feature_scores["composition"]

    def test_header_density_counts_markdown_headers(self):
        r = score_cognitive_value("# A\n## B\n### C\ntext")
        assert r.feature_scores["header"] > 0.0

    def test_codeblock_density_counts_fences(self):
        r = score_cognitive_value("text\n```\ncode\n```\nmore")
        assert r.feature_scores["codeblock"] > 0.0

    def test_char_score_increases_with_length(self):
        short = score_cognitive_value("hi")
        long = score_cognitive_value("x" * 5000)
        assert long.feature_scores["char"] > short.feature_scores["char"]

    def test_all_feature_scores_bounded_0_1(self):
        content = ("# H\n```\nc\n```\n" + "design framework lens " * 200) * 3
        r = score_cognitive_value(content, source_path="docs/big.md")
        for name, val in r.feature_scores.items():
            assert 0.0 <= val <= 1.0, f"{name}={val} out of [0,1]"
        assert 0.0 <= r.score <= 1.0


class TestSubstrateBorderlineIndicator:
    """Task #111 (2026-06-09): borderline-zone surface helper for
    substrate-modification-gravity. Classifies the routing decision shape
    so the gate-fire surface can name fragile single-feature fires
    distinctly from well-supported multi-feature fires."""

    def test_no_fire_returns_no_fire(self):
        r = SubstrateModGravity(score=0, fired_features=(), is_high_gravity=False)
        assert borderline_indicator_substrate(r) == "no-fire"

    def test_single_feature_returns_borderline(self):
        r = SubstrateModGravity(score=1, fired_features=("git-commit",), is_high_gravity=True)
        assert borderline_indicator_substrate(r) == "borderline-single-feature"

    def test_two_features_returns_strong(self):
        r = SubstrateModGravity(
            score=2,
            fired_features=("git-commit", "src-write"),
            is_high_gravity=True,
        )
        assert borderline_indicator_substrate(r) == "strong-multi-feature"

    def test_real_git_commit_classified_borderline(self):
        """End-to-end: a git commit by itself fires only the git-commit
        feature; the indicator names that fragility."""
        r = score_substrate_modification("Bash", bash_command="git commit -m 'x'")
        label = borderline_indicator_substrate(r)
        # Fragility still named. The council-required wrapper arrived with the
        # 2026-09-16 threshold; the fragility fact is the part this test is for.
        assert "borderline-single-feature" in label


class TestCognitiveBorderlineIndicator:
    """Task #111: borderline-zone surface for cognitive-value-gravity.
    Threshold = 0.3, radius = 0.10, so:
      score < 0.20 -> clearly-low
      0.20 <= score < 0.30 -> borderline-low
      0.30 <= score < 0.40 -> borderline-high
      score >= 0.40 -> clearly-high
    """

    def _make(self, score: float) -> CognitiveValueGravity:
        return CognitiveValueGravity(
            score=score,
            feature_scores={"char": score},
            is_high_gravity=score >= 0.30,
        )

    def test_clearly_low(self):
        assert borderline_indicator_cognitive(self._make(0.05)) == "clearly-low"
        assert borderline_indicator_cognitive(self._make(0.19)) == "clearly-low"

    def test_borderline_low(self):
        assert borderline_indicator_cognitive(self._make(0.20)) == "borderline-low"
        assert borderline_indicator_cognitive(self._make(0.29)) == "borderline-low"

    def test_borderline_high(self):
        assert borderline_indicator_cognitive(self._make(0.30)) == "borderline-high"
        assert borderline_indicator_cognitive(self._make(0.39)) == "borderline-high"

    def test_clearly_high(self):
        assert borderline_indicator_cognitive(self._make(0.40)) == "clearly-high"
        assert borderline_indicator_cognitive(self._make(0.95)) == "clearly-high"

    def test_boundary_values(self):
        assert borderline_indicator_cognitive(self._make(0.30)) == "borderline-high"
        assert borderline_indicator_cognitive(self._make(0.40)) == "clearly-high"


class TestAnInlineBodyDoesNotHideTheFileBeingWritten:
    """The module promises a shell write is named by its FILE, not the command.

    It stopped being true for writes carrying an inline body: the body is
    arbitrary text, an apostrophe in it broke the tokeniser, and the edit was
    then named by two words of shell. The module's own docstring says why that
    matters — one walk filed against two words of shell clears every write of
    that shape in the tree, with the refusal and the walk each looking correct
    on their own. Measured 2026-09-18 before the fix: same write, body and no
    body, gave the filename in one case and the command shape in the other.
    """

    _NL = "\n"
    _Q = "'"

    def _heredoc(self, body: str) -> str:
        return self._NL.join([f"cat >> tests/foo.py <<{self._Q}EOF{self._Q}", body, "EOF"])

    def test_a_body_with_an_apostrophe_no_longer_hides_the_target(self):
        assert _shell_write_targets(self._heredoc("don't stop")) == ("tests/foo.py",)

    def test_a_body_with_an_unbalanced_double_quote_too(self):
        assert _shell_write_targets(self._heredoc('a " quote')) == ("tests/foo.py",)

    def test_a_write_after_the_body_is_still_found(self):
        """The drop ends at the terminator — it does not swallow the rest."""
        cmd = self._NL.join([f"cat > a.txt <<{self._Q}EOF{self._Q}", "data", "EOF", "cat > b.txt"])
        assert _shell_write_targets(cmd) == ("a.txt", "b.txt")

    def test_a_plain_write_is_unaffected(self):
        assert _shell_write_targets("cat >> tests/foo.py") == ("tests/foo.py",)

    def test_a_genuinely_unreadable_command_still_returns_none(self):
        """The control that matters most: fail-toward-scrutiny is preserved.

        None means could-not-read and is NOT an empty tuple. If this ever
        returns () the blind spot reports clean, which is the fault the
        could-not-read answer exists to prevent.
        """
        assert _shell_write_targets(f"echo {self._Q}unterminated") is None


class TestDoingTheActVersusTalkingAboutIt:
    """The feature matched the phrase anywhere, so three unlike sentences scored alike.

    One performs the act. One computes what the act would be named. One is a
    council walk whose findings have to SAY what is being walked -- and that
    third is what broke, 2026-09-19. Writing the required artifact counted as
    doing the thing, so the prerequisite became unfileable: two refusals in a
    row, the second one for filing the cure named by the first.

    The only door left open by that is the documented bypass, and every use of
    it records as routing-around-a-gate. So the telemetry that measures my
    gate discipline was being fed by a defect in a gate, which makes this a
    repair to a measurement as much as to a door.

    The name is built from pieces for the same reason the class above does it:
    a test file about this feature must not trip it.
    """

    _G = "g" + "it"

    def _fires(self, command: str) -> bool:
        return (
            "git-commit"
            in score_substrate_modification("Bash", bash_command=command).fired_features
        )

    def test_the_act_fires_however_it_is_reached(self):
        """The direction that must never regress."""
        for shape in (
            f"{self._G} commit -m hello",
            f"cd somewhere && {self._G} commit -am done",
            f"{self._G} -C /elsewhere commit -m done",
            f"sudo {self._G} commit -m done",
            f"cd somewhere ; {self._G} commit --amend",
        ):
            assert self._fires(shape), f"a real commit escaped: {shape!r}"

    def test_a_multiline_command_is_split_on_its_newlines(self):
        """Named separately because the act-anchor does NOT split on newlines.

        Reusing that split would have let every multi-line invocation through:
        the commit sits on its own line, and flattened into one segment the
        head is a shell builtin. Checked rather than copied.
        """
        assert self._fires(f"set -o pipefail\ncd somewhere\n{self._G} commit -q -F -")

    def test_a_walk_describing_the_act_is_not_the_act(self):
        """The refusal that made its own cure unfileable."""
        walk = (
            "divi" + "neos council log --edit anchor "
            f'--finding "norman=the refusal names {self._G} commit and cannot be followed"'
        )
        assert not self._fires(walk)

    def test_a_read_only_computation_mentioning_the_act_is_not_the_act(self):
        probe = f'python -c "print(anchor(t, p, c))"  # what {self._G} commit resolves to'
        assert not self._fires(probe)

    def test_a_neighbouring_subcommand_is_not_the_act(self):
        assert not self._fires(f"{self._G} log --oneline")
        assert not self._fires(f"{self._G} status")

    def test_an_assignment_prefix_does_not_hide_the_act(self):
        """Aletheia's finding, 2026-09-19. My coverage claim was false here.

        A bare ``VAR=value`` before the command is shell assignment syntax, not
        a wrapper, and my private stripper did not know it. So backdating or
        scripting -- ordinary idioms, not exotic tricks -- escaped entirely,
        which means the narrowing DID admit what the old text-search refused.
        I wrote the opposite into a letter as settled. She tried three shapes
        and it failed on the third.
        """
        for shape in (
            f"GIT_AUTHOR_DATE=2020-01-01 {self._G} commit -m x",
            f"GIT_AUTHOR_NAME=x GIT_AUTHOR_EMAIL=y {self._G} commit -m z",
            f"env GIT_EDITOR=true {self._G} commit -m x",
        ):
            assert self._fires(shape), f"assignment prefix hid the act: {shape!r}"

    def test_a_command_that_cannot_be_parsed_is_assumed_heavy(self):
        """The direction that must never be aligned with the other callers.

        The shared splitter answers cannot-parse with None. An allowlist reads
        that as not-permitted, its safe direction. This is not an allowlist --
        it decides whether an act owes a recorded walk, so cannot-parse must
        mean assume-heavy. A substitution is how you would hide the acting word
        on purpose, and the accidental case looks identical from here.
        """
        assert self._fires("$(echo " + self._G + ") commit -m x")
        assert self._fires(f"{self._G} commit -m 'unterminated")

    def test_the_indirect_route_stays_open_and_this_says_so(self):
        """Not a wish. The old text match missed these too, so nothing regressed.

        A command assembled from a variable, or one hiding inside a script the
        classifier never reads, is invisible -- and was invisible before. The
        game-walk recorded both as leaks left open. This is here so the gap is
        a written fact rather than something a later reader rediscovers by
        being surprised.
        """
        assert not self._fires("$VC $SUBCOMMAND -m done")
        assert not self._fires("bash scripts/ship.sh")
