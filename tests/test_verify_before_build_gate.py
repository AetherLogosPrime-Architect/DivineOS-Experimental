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

from divineos.core.verify_before_build_gate import (
    check_thread_walk_required,
    check_verify_before_build,
)


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


# --- Thread-walk requirement (council-62c1bcc6dc3a, 2026-07-23) ------


class TestThreadWalkRequired:
    """The thread-walk block fires on the same solution-shape triggers as
    check_verify_before_build but requires a recent decision_journal entry
    with populated tension/almost fields matching the choice being
    presented. Complementary to substrate-consult check."""

    def test_solution_shape_without_walk_blocks(self) -> None:
        result = check_thread_walk_required(
            reply=REPLY_TONIGHT_VENV_MISS,
            last_user_text="fix it properly",
        )
        # No walk-record filed with matching content → blocks
        # (unless a prior test happened to file one; the fuzzy content-
        # match on 'option' / 'venv' should be specific enough that
        # unrelated recent decisions don't clear it)
        assert result is not None
        assert "walking the thread" in result
        assert "tension" in result and "almost" in result

    def test_user_provided_options_exempt(self) -> None:
        result = check_thread_walk_required(
            reply=REPLY_TONIGHT_VENV_MISS,
            last_user_text="should we do option A or option B?",
        )
        # User handed the options — no walk required
        assert result is None

    def test_pure_conversation_passes(self) -> None:
        result = check_thread_walk_required(
            reply=REPLY_PURE_CONVERSATION,
            last_user_text="",
        )
        # No solution-shape → gate doesn't fire
        assert result is None

    def test_short_reply_passes(self) -> None:
        result = check_thread_walk_required(
            reply=REPLY_SHORT,
            last_user_text="",
        )
        assert result is None

    def test_empty_reply_passes(self) -> None:
        result = check_thread_walk_required(
            reply="",
            last_user_text="",
        )
        assert result is None

    def test_walk_with_matching_content_clears_block(self, tmp_path, monkeypatch) -> None:
        """When a recent decision_journal entry exists with populated
        tension AND almost fields whose content matches the choice-phrase,
        the block clears."""
        # Point the decision_journal at a fresh test DB
        from divineos.core import decision_journal as dj

        test_db = tmp_path / "test_dj.db"
        monkeypatch.setattr(
            dj, "_get_connection", lambda: __import__("sqlite3").connect(str(test_db))
        )
        dj.init_decision_journal()
        # File a decision with content matching the venv reply's phrases,
        # substantive tension and almost fields
        dj.record_decision(
            content="build a venv per-worktree option to isolate this install-leak",
            tension=(
                "want to fix the install-leak durably vs want to avoid disruption to "
                "the working state; isolation via structure is more durable than "
                "isolation via discipline over time"
            ),
            almost=(
                "almost proposed the reversible shim as equal alternative but the "
                "PATH-ordering discipline route fails silently when I forget; the "
                "durable path is the venv even if it costs more upfront"
            ),
        )
        result = check_thread_walk_required(
            reply=REPLY_TONIGHT_VENV_MISS,
            last_user_text="fix it properly",
        )
        assert result is None

    def test_walk_with_empty_tension_blocks(self, tmp_path, monkeypatch) -> None:
        """A decision_journal entry with tension field but no almost (or
        vice versa) does NOT clear the block — both required."""
        from divineos.core import decision_journal as dj

        test_db = tmp_path / "test_dj.db"
        monkeypatch.setattr(
            dj, "_get_connection", lambda: __import__("sqlite3").connect(str(test_db))
        )
        dj.init_decision_journal()
        dj.record_decision(
            content="build a venv per-worktree option",
            tension="want to fix this properly and durably without breaking the working state again",
            almost="",  # empty — should not clear
        )
        result = check_thread_walk_required(
            reply=REPLY_TONIGHT_VENV_MISS,
            last_user_text="fix it properly",
        )
        assert result is not None

    def test_walk_with_unrelated_content_blocks(self, tmp_path, monkeypatch) -> None:
        """Popper break-case two: a decision_journal entry with populated
        fields but content unrelated to the current choice does NOT clear
        the block. The check is fuzzy-content-match, not just field-
        presence."""
        from divineos.core import decision_journal as dj

        test_db = tmp_path / "test_dj.db"
        monkeypatch.setattr(
            dj, "_get_connection", lambda: __import__("sqlite3").connect(str(test_db))
        )
        dj.init_decision_journal()
        # Populated but about family, not about venv/options
        dj.record_decision(
            content="reach out to Aletheia about the audit round timing question",
            tension=(
                "want to give her space to work vs want to unblock the review before "
                "session compaction runs and freshness fades"
            ),
            almost=(
                "almost sent a second follow-up but the first was clear enough and a "
                "second would read as pressure not care"
            ),
        )
        result = check_thread_walk_required(
            reply=REPLY_TONIGHT_VENV_MISS,
            last_user_text="fix it properly",
        )
        # No token overlap between "aletheia audit round" and
        # "option venv worktree" → block should still fire
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
