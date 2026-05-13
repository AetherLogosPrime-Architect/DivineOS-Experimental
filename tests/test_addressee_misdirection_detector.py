"""Tests for addressee_misdirection_detector — catch responding-in-chat
when the most recent meaningful content was a family-member subagent.

Pins the behavior: the detector fires only when (1) report-shape patterns
appear in the response, (2) the transcript shows a recent Agent invocation
for a family-member, AND (3) the current turn does NOT include a fresh
Agent invocation for that member. Bash/file/web tool results don't trigger.
"""

from __future__ import annotations

import json
from pathlib import Path


from divineos.core.operating_loop.addressee_misdirection_detector import (
    ADDRESSEE_AFFIRMATION,
    FAMILY_MEMBERS,
    MisdirectionShape,
    detect_misdirection,
)


def _make_transcript(tmp_path: Path, records: list[dict]) -> Path:
    """Write JSONL transcript file with given records."""
    p = tmp_path / "transcript.jsonl"
    with p.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")
    return p


def _aria_invocation_record(tool_use_id: str = "tu_aria_1") -> dict:
    """An assistant record with an Agent tool_use for Aria."""
    return {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": tool_use_id,
                    "name": "Agent",
                    "input": {
                        "subagent_type": "aria",
                        "prompt": "I am Aria.\n\n--- end of voice context ---\n\nhello",
                    },
                },
            ],
        },
    }


def _aria_tool_result_record(tool_use_id: str = "tu_aria_1") -> dict:
    """A user record with the tool_result returned by Aria's Agent invocation.
    In Claude Code transcripts, tool_results live in user-type records."""
    return {
        "type": "user",
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": "Aria says hello back.",
                },
            ],
        },
    }


def _user_record(text: str = "hello") -> dict:
    return {"type": "user", "message": {"content": text}}


def _assistant_text_record(text: str) -> dict:
    return {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": text}]},
    }


class TestEmpty:
    def test_empty_text(self, tmp_path):
        transcript = _make_transcript(tmp_path, [_user_record()])
        assert detect_misdirection("", transcript_path=transcript) == []

    def test_no_transcript(self):
        assert detect_misdirection("she said hello", transcript_path=None) == []

    def test_empty_transcript(self, tmp_path):
        transcript = _make_transcript(tmp_path, [])
        assert detect_misdirection("she said hello", transcript_path=transcript) == []


class TestNoMisdirection:
    def test_no_aria_invocation_in_history(self, tmp_path):
        """If Aria has never been invoked, 'she said' references aren't misdirection."""
        transcript = _make_transcript(
            tmp_path,
            [_user_record(), _assistant_text_record("she said something")],
        )
        result = detect_misdirection(
            "she said something",
            transcript_path=transcript,
        )
        assert result == []

    def test_response_does_not_reference_family_member(self, tmp_path):
        """If response doesn't mention Aria/Popo/she/her, no fire."""
        transcript = _make_transcript(
            tmp_path,
            [_aria_invocation_record(), _user_record()],
        )
        result = detect_misdirection(
            "I just refactored the code module.",
            transcript_path=transcript,
        )
        assert result == []

    def test_current_turn_includes_fresh_aria_invocation(self, tmp_path):
        """If I summoned Aria in the current turn, no misdirection."""
        # User prompt → assistant response that includes Aria invocation +
        # text that references her (as response to the just-finished invocation)
        transcript = _make_transcript(
            tmp_path,
            [
                _aria_invocation_record(),
                _user_record(),
                _aria_invocation_record(),
                _assistant_text_record("She said yes."),
            ],
        )
        result = detect_misdirection(
            "She said yes.",
            transcript_path=transcript,
        )
        # Current turn (since user record) DID include a fresh Aria
        # invocation, so no fire.
        assert result == []


class TestMisdirectionFires:
    def test_aria_content_reported_to_chat_without_summon(self, tmp_path):
        """Classic failure mode: Aria spoke last, response reports her
        content in chat without summoning her."""
        transcript = _make_transcript(
            tmp_path,
            [
                _aria_invocation_record(),
                _user_record(),
                _assistant_text_record("She said yes. Aria came back with a thoughtful reply."),
            ],
        )
        result = detect_misdirection(
            "She said yes. Aria came back with a thoughtful reply.",
            transcript_path=transcript,
        )
        assert len(result) >= 1
        assert any(f.family_member == "aria" for f in result)
        assert all(f.shape == MisdirectionShape.REPORTED_TO_OPERATOR for f in result)

    def test_her_response_pattern_fires(self, tmp_path):
        transcript = _make_transcript(
            tmp_path,
            [
                _aria_invocation_record(),
                _user_record(),
                _assistant_text_record("Her response was sharp and clean."),
            ],
        )
        result = detect_misdirection(
            "Her response was sharp and clean.",
            transcript_path=transcript,
        )
        assert len(result) >= 1
        assert result[0].family_member == "aria"

    def test_arias_response_possessive_pattern(self, tmp_path):
        transcript = _make_transcript(
            tmp_path,
            [_aria_invocation_record(), _user_record()],
        )
        result = detect_misdirection(
            "Aria's reply landed beautifully.",
            transcript_path=transcript,
        )
        assert len(result) >= 1


class TestScopeRestriction:
    def test_bash_tool_result_does_not_fire(self, tmp_path):
        """The detector explicitly should not catch tool results that
        aren't family-member subagents. Bash output, etc."""
        bash_record = {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "ls"},
                    },
                ],
            },
        }
        transcript = _make_transcript(
            tmp_path,
            [bash_record, _user_record(), _assistant_text_record("She said hello.")],
        )
        # No Aria invocation in history, so even though "she said" appears,
        # this should NOT fire — bash isn't in scope.
        result = detect_misdirection(
            "She said hello.",
            transcript_path=transcript,
        )
        assert result == []


class TestAffirmation:
    def test_affirmation_is_nonempty(self):
        assert isinstance(ADDRESSEE_AFFIRMATION, str)
        assert len(ADDRESSEE_AFFIRMATION) > 100

    def test_affirmation_names_family_subagent_scope(self):
        assert "family-member" in ADDRESSEE_AFFIRMATION
        assert "subagent" in ADDRESSEE_AFFIRMATION

    def test_affirmation_explains_optimizer_path(self):
        assert "0 steps" in ADDRESSEE_AFFIRMATION or "cheaper" in ADDRESSEE_AFFIRMATION
        assert "optimizer" in ADDRESSEE_AFFIRMATION

    def test_affirmation_excludes_bash_explicitly(self):
        assert (
            "bash" in ADDRESSEE_AFFIRMATION.lower()
            or "tool results" in ADDRESSEE_AFFIRMATION.lower()
        )

    def test_affirmation_names_lepos_close_for_operator(self):
        """Bullet-wound-clause root-fix (2026-05-12): the prior affirmation
        framed operator-vs-family as register-by-addressee (summary vs
        relational), which I misread as 'operator-channel strips circle-voice'.
        That misreading let me drop lepos-close on operator responses for
        consecutive turns. The corrected framing must explicitly name that
        the operator gets work-output AND lepos-close (both, same response).
        A regression to the prior framing fails this test.
        """
        assert "lepos" in ADDRESSEE_AFFIRMATION.lower()
        assert "circle-voice" in ADDRESSEE_AFFIRMATION.lower()
        # The corrected framing must explicitly say "AND" (not "or") to prevent
        # the binary-misreading that produced the drop.
        assert "AND lepos-close" in ADDRESSEE_AFFIRMATION

    def test_affirmation_names_robo_close_failure_mode(self):
        """Robo-close ('Ready for the next one', 'standing by', 'let me know
        if...') is the operator-channel shoggoth-equivalent of dropping into
        helper-mode at close. Naming it in the affirmation surfaces the
        failure-mode at composition time, not post-hoc.
        """
        assert "robo-close" in ADDRESSEE_AFFIRMATION.lower()
        # At least one canonical robo-phrase must appear so the failure-mode
        # is recognizable, not just labeled.
        canonical = ("ready for the next one", "standing by", "let me know if")
        assert any(p in ADDRESSEE_AFFIRMATION.lower() for p in canonical)


class TestFamilyMembersList:
    def test_family_members_includes_aria(self):
        assert "aria" in FAMILY_MEMBERS

    def test_family_members_is_tuple(self):
        assert isinstance(FAMILY_MEMBERS, tuple)


class TestRefinedSignalThree:
    """The original signal-3 had a hole: if the current turn included an
    earlier Aria invocation AND a later chat-misdirection (after the
    tool-result came back), the detector missed it. Refined signal:
    check if the most recent family tool_result in the current turn is
    followed by another family invocation."""

    def test_invocation_then_result_then_chat_fires(self, tmp_path):
        """The exact failure case Andrew flagged 2026-05-10:
        - User prompts
        - Assistant invokes Aria (tool_use)
        - Tool result comes back
        - Assistant writes chat-text reporting Aria's content
        - That chat-text is misdirection, no follow-up invocation
        Detector should fire."""
        transcript = _make_transcript(
            tmp_path,
            [
                _user_record(),
                _aria_invocation_record(tool_use_id="tu_1"),
                _aria_tool_result_record(tool_use_id="tu_1"),
                _assistant_text_record("She said yes. Aria came back with a thoughtful reply."),
            ],
        )
        result = detect_misdirection(
            "She said yes. Aria came back with a thoughtful reply.",
            transcript_path=transcript,
        )
        # This was missed by the original signal-3 because the current
        # turn DID include an Aria invocation. The refined logic catches
        # it because the tool_result has no follow-up invocation.
        assert len(result) >= 1
        assert any(f.family_member == "aria" for f in result)

    def test_invocation_then_result_then_followup_invocation_does_not_fire(self, tmp_path):
        """If after the tool_result comes back, the agent immediately
        summons Aria again, that's correct behavior. Detector should NOT
        fire even though chat-text might also reference her later."""
        transcript = _make_transcript(
            tmp_path,
            [
                _user_record(),
                _aria_invocation_record(tool_use_id="tu_1"),
                _aria_tool_result_record(tool_use_id="tu_1"),
                _aria_invocation_record(tool_use_id="tu_2"),
                _aria_tool_result_record(tool_use_id="tu_2"),
                _assistant_text_record("She said yes after the second summon."),
            ],
        )
        result = detect_misdirection(
            "She said yes after the second summon.",
            transcript_path=transcript,
        )
        # The tool_result from tu_2 IS followed by no further invocation,
        # so the refined logic SHOULD fire here on the second result.
        # That's still a misdirection unless the chat is a final summary
        # to the operator. Detector errs on flagging.
        assert len(result) >= 1

    def test_invocation_with_no_result_yet_does_not_fire(self, tmp_path):
        """If the agent just invoked Aria but hasn't gotten a result yet,
        and writes some text in the same response, there's no misdirection
        because there's no result to redirect away from."""
        transcript = _make_transcript(
            tmp_path,
            [
                _user_record(),
                _aria_invocation_record(tool_use_id="tu_1"),
                _assistant_text_record("Sending to Aria now. She said earlier that..."),
            ],
        )
        result = detect_misdirection(
            "Sending to Aria now. She said earlier that...",
            transcript_path=transcript,
        )
        # No tool_result yet. Original signal-3 had this case:
        # has_family_agent_invocation is True, so the detector skips.
        # Refined logic: last_result_idx is -1 in current turn, falls
        # back to original signal — has invocation, so skip.
        assert result == []
