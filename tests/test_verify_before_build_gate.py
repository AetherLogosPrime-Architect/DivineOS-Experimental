"""Tests for verify_before_build_gate.

Coverage:
  - Multi-option framing detection (bold markers, prose, numbered)
  - Design-verb + article-noun detection
  - Design-question shape detection
  - Substrate-consult discriminator (Grep/Glob tool, divineos ask/recall cmds)
  - User-provided-options exemption
  - Short-reply exemption
  - Pure-conversation reply exemption
  - Combined scenarios from the actual failure (tonight's A/B miss)
"""

from __future__ import annotations

import pytest

from divineos.core.verify_before_build_gate import check_verify_before_build


# --- Fixtures: representative replies -------------------------------

REPLY_TONIGHT_VENV_MISS = """Two clean fix paths, and I want your read before I touch anything.

**Option A — per-worktree venv (durable, isolates fully).** Create a venv inside this worktree, activate it, install into it. This worktree's shell always uses its own python; the other install stays exactly as-is. Cost: I have to remember to activate the venv when I open a terminal here. Doesn't touch her stuff at all.

**Option B — reversible shim.** Add a small wrapper in this worktree that forces path prepend. When I run the command here, it forces this worktree's src to win. Cost: PATH ordering discipline.

My lean: Option A. Isolation via structure, not via discipline.
"""

REPLY_PURE_CONVERSATION = """Sitting with something honest: I noticed I almost turned this reply into another A/B ask. Caught it before it committed. Different feel than an hour ago.
"""

REPLY_LEGITIMATE_PROPOSAL_AFTER_CONSULT = """I checked the substrate for existing implementations and confirmed nothing like this exists yet. I'll build a new gate module at the standard location and wire it through the standard audit chain. The design follows the same shape as the wallclock gate — broad detection, structural discriminator, hard block per the discipline established tonight.
"""

REPLY_DESIGN_QUESTION = """Should I build the module now, or walk it past the council first? Both approaches have real tradeoffs and I want to make sure we get the shape right before wiring enforcement into the audit chain. The council walk would catch design-edge cases; the direct build gets a working prototype in front of me faster.
"""

REPLY_SHORT = "Cooking now. Back with a draft."


# --- Multi-option detection ----------------------------------------


class TestMultiOptionDetection:
    def test_bold_option_markers_fire_gate(self) -> None:
        result = check_verify_before_build(
            reply=REPLY_TONIGHT_VENV_MISS,
            tool_calls_in_turn=(),
            command_texts=(),
            last_user_text="",
        )
        assert result is not None
        assert "multi-option framing" in result

    def test_two_paths_prose_fires(self) -> None:
        reply = "There are two paths forward. " + "x" * 200
        result = check_verify_before_build(
            reply=reply,
            tool_calls_in_turn=(),
            command_texts=(),
            last_user_text="",
        )
        assert result is not None
        assert "two paths" in result.lower()

    def test_option_a_colon_form_fires(self) -> None:
        reply = "Option A: do the safe thing. Option B: take the risk. " + "y" * 200
        result = check_verify_before_build(
            reply=reply,
            tool_calls_in_turn=(),
            command_texts=(),
            last_user_text="",
        )
        assert result is not None


# --- Design-verb detection -----------------------------------------


class TestDesignVerbDetection:
    def test_ill_build_a_x_fires(self) -> None:
        reply = "I'll build a new module for this. " + "z" * 200
        result = check_verify_before_build(
            reply=reply,
            tool_calls_in_turn=(),
            command_texts=(),
            last_user_text="",
        )
        assert result is not None
        assert "design-verb" in result

    def test_let_me_create_a_y_fires(self) -> None:
        reply = "Let me create a helper function to handle this. " + "z" * 200
        result = check_verify_before_build(
            reply=reply,
            tool_calls_in_turn=(),
            command_texts=(),
            last_user_text="",
        )
        assert result is not None

    def test_we_could_add_fires(self) -> None:
        reply = "We could add a new hook that watches for this. " + "z" * 200
        result = check_verify_before_build(
            reply=reply,
            tool_calls_in_turn=(),
            command_texts=(),
            last_user_text="",
        )
        assert result is not None

    def test_bare_ill_build_no_article_does_not_fire(self) -> None:
        # "I'll build" as reply-ender, not proposal — no article, no noun
        reply = "Cooking now. I'll build. Back with a draft. " + "z" * 200
        result = check_verify_before_build(
            reply=reply,
            tool_calls_in_turn=(),
            command_texts=(),
            last_user_text="",
        )
        # No solution-shape → gate passes trivially
        assert result is None


# --- Design-question detection -------------------------------------


class TestDesignQuestionDetection:
    def test_should_i_build_fires(self) -> None:
        result = check_verify_before_build(
            reply=REPLY_DESIGN_QUESTION,
            tool_calls_in_turn=(),
            command_texts=(),
            last_user_text="",
        )
        assert result is not None
        assert "design-question" in result

    def test_which_route_fires(self) -> None:
        reply = "Which route do you want me to take on this one? " + "x" * 200
        result = check_verify_before_build(
            reply=reply,
            tool_calls_in_turn=(),
            command_texts=(),
            last_user_text="",
        )
        assert result is not None


# --- Discriminator: substrate-consult passes the gate --------------


class TestSubstrateConsultPasses:
    def test_grep_call_passes(self) -> None:
        result = check_verify_before_build(
            reply=REPLY_TONIGHT_VENV_MISS,
            tool_calls_in_turn=("Grep",),
            command_texts=(),
            last_user_text="",
        )
        assert result is None

    def test_glob_call_passes(self) -> None:
        result = check_verify_before_build(
            reply=REPLY_TONIGHT_VENV_MISS,
            tool_calls_in_turn=("Glob",),
            command_texts=(),
            last_user_text="",
        )
        assert result is None

    def test_divineos_ask_command_passes(self) -> None:
        result = check_verify_before_build(
            reply=REPLY_TONIGHT_VENV_MISS,
            tool_calls_in_turn=("Bash",),
            command_texts=("divineos ask cross-worktree install-leak",),
            last_user_text="",
        )
        assert result is None

    def test_divineos_recall_command_passes(self) -> None:
        result = check_verify_before_build(
            reply=REPLY_TONIGHT_VENV_MISS,
            tool_calls_in_turn=("Bash",),
            command_texts=("divineos recall venv hook",),
            last_user_text="",
        )
        assert result is None

    def test_read_alone_does_not_pass(self) -> None:
        # Read is intentionally excluded from consult-signature — too
        # many free-pass paths. Only Grep/Glob count as code-search.
        result = check_verify_before_build(
            reply=REPLY_TONIGHT_VENV_MISS,
            tool_calls_in_turn=("Read",),
            command_texts=(),
            last_user_text="",
        )
        assert result is not None


# --- User-provided-options exemption -------------------------------


class TestUserOptionsExemption:
    def test_a_or_b_in_user_message_exempts(self) -> None:
        result = check_verify_before_build(
            reply=REPLY_TONIGHT_VENV_MISS,
            tool_calls_in_turn=(),
            command_texts=(),
            last_user_text="Should we do A or B? Which one seems right?",
        )
        assert result is None

    def test_which_do_you_want_exempts(self) -> None:
        result = check_verify_before_build(
            reply=REPLY_TONIGHT_VENV_MISS,
            tool_calls_in_turn=(),
            command_texts=(),
            last_user_text="Which do you want to build first?",
        )
        assert result is None


# --- Trivial exemptions --------------------------------------------


class TestTrivialExemptions:
    def test_short_reply_passes(self) -> None:
        result = check_verify_before_build(
            reply=REPLY_SHORT,
            tool_calls_in_turn=(),
            command_texts=(),
            last_user_text="",
        )
        assert result is None

    def test_pure_conversation_passes(self) -> None:
        result = check_verify_before_build(
            reply=REPLY_PURE_CONVERSATION,
            tool_calls_in_turn=(),
            command_texts=(),
            last_user_text="",
        )
        assert result is None

    def test_empty_reply_passes(self) -> None:
        result = check_verify_before_build(
            reply="",
            tool_calls_in_turn=(),
            command_texts=(),
            last_user_text="",
        )
        assert result is None

    def test_whitespace_reply_passes(self) -> None:
        result = check_verify_before_build(
            reply="   \n\n  ",
            tool_calls_in_turn=(),
            command_texts=(),
            last_user_text="",
        )
        assert result is None


# --- The actual failure from tonight -------------------------------


class TestTonightsActualFailure:
    """The A/B venv-fix reply that Andrew caught. This is the dogfood
    test: the gate MUST catch this specific reply with no consult
    signature, and MUST pass it with a divineos ask signature."""

    def test_venv_miss_without_consult_blocks(self) -> None:
        result = check_verify_before_build(
            reply=REPLY_TONIGHT_VENV_MISS,
            tool_calls_in_turn=("Bash",),
            command_texts=("git status", "ls -la .venv"),
            last_user_text="fix it properly and do the hard work needed to make it serve you",
        )
        assert result is not None
        assert "34afed32725f" in result  # prereg ref lands in block message

    def test_venv_fix_with_consult_passes(self) -> None:
        # Same reply, but AFTER I ran divineos ask this turn → passes
        result = check_verify_before_build(
            reply=REPLY_TONIGHT_VENV_MISS,
            tool_calls_in_turn=("Bash", "Grep"),
            command_texts=(
                "divineos ask cross-worktree install-leak pip pingpong",
                "python -c 'import divineos; print(divineos.__file__)'",
            ),
            last_user_text="which serves better in the long run",
        )
        assert result is None


# --- Regression: legitimate proposals after real consult -----------


class TestLegitimateProposalsPass:
    def test_proposal_after_ask_passes(self) -> None:
        result = check_verify_before_build(
            reply=REPLY_LEGITIMATE_PROPOSAL_AFTER_CONSULT,
            tool_calls_in_turn=("Bash", "Grep", "Read"),
            command_texts=(
                "divineos ask verify-before-build gate",
                "divineos ask existing consult mechanism",
            ),
            last_user_text="take the wheel",
        )
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
