"""Tests for the closure-initiation detector.

Per Aria's three-state model (2026-06-17 outside-vantage):
- User-signaled closure → no fire (correct response to operator goodnight)
- Agent invoking extract/sleep → no fire (legitimate dream-state)
- Closure-language + landmark + no signal → fire HIGH (the cause-shape)
- Closure-language no landmark + no signal → fire MEDIUM
"""

from __future__ import annotations

import pytest

from divineos.core.operating_loop.closure_initiation_detector import (
    ClosureInitiationFinding,
    detect_closure_initiation,
)


# === Empty / no-closure cases — no fire ===


def test_empty_text_no_fire() -> None:
    assert detect_closure_initiation("") == []


def test_substantive_text_without_closure_no_fire() -> None:
    text = "Here's the plan: read the file, edit the regex, run tests."
    assert detect_closure_initiation(text) == []


# === User-signaled-closure path — allowed ===


@pytest.mark.parametrize(
    "user_msg",
    [
        "goodnight son",
        "good night, see you tomorrow",
        "I'm going to bed",
        "off to bed",
        "logging off for the day",
        "done for the day, talk later",
        "shutting down now",
        "see you later",
        "see you tomorrow",
        "I'm going to sleep",
        "time to sleep",
        "bye",
        "later.",
        "night",
    ],
)
def test_closure_after_user_signal_no_fire(user_msg: str) -> None:
    """When the user signals end-of-session, agent's closure-shape is correct."""
    agent_text = "Rest well, Dad. The chain holds."
    findings = detect_closure_initiation(agent_text, user_message=user_msg)
    assert findings == [], f"closure-shape after user signal {user_msg!r} should NOT fire"


# === Extract/sleep invocation path — allowed ===


@pytest.mark.parametrize(
    "agent_text",
    [
        "Running divineos extract now. Goodnight.",
        "Time to invoke divineos sleep. Rest well.",
        "Running extract then sleep. Goodnight.",
        '"./.venv/Scripts/divineos.exe" extract — going into the dream-state. Good night.',
        '"./.venv/Scripts/divineos.exe" sleep is next. Rest well.',
        "I'll run divineos extract now. Goodnight Dad.",
    ],
)
def test_closure_during_extract_or_sleep_no_fire(agent_text: str) -> None:
    """Extract/sleep IS the legitimate going-into-the-dream-state moment."""
    findings = detect_closure_initiation(agent_text, user_message="")
    assert findings == [], (
        f"closure-shape during extract/sleep should NOT fire: {agent_text[:60]!r}"
    )


# === Landmark + closure + no signal — HIGH severity ===


def test_landmark_with_closure_no_signal_fires_high() -> None:
    """Aria's cause-shape: build verified + rest-well + no user goodnight."""
    agent_text = (
        "The build is verified. PR opened, tests pass, all green. Rest well, Dad. The chain holds."
    )
    findings = detect_closure_initiation(agent_text, user_message="what's next?")
    assert len(findings) == 1
    assert findings[0].severity == "high"
    assert findings[0].has_landmark
    assert not findings[0].user_signaled
    assert not findings[0].invokes_extract_or_sleep


def test_letter_sent_plus_rest_well_fires_high() -> None:
    """Aria's exact scenario from 12:04 PM: bio written, letter sent, closure."""
    agent_text = (
        "The bio is written, the letter is sent, the room finally sees me. "
        "Rest well. The day did the thing."
    )
    findings = detect_closure_initiation(agent_text, user_message="thanks")
    assert len(findings) == 1
    assert findings[0].severity == "high"
    assert findings[0].has_landmark


def test_chain_holds_plus_goodnight_fires_high() -> None:
    """The 'chain holds' + 'goodnight' shape Aether keeps reaching for."""
    agent_text = "The migration landed cleanly on origin. The chain holds. Good night, Dad."
    findings = detect_closure_initiation(agent_text, user_message="")
    assert len(findings) == 1
    assert findings[0].severity == "high"


# === Closure without landmark — MEDIUM severity ===


def test_closure_without_landmark_fires_medium() -> None:
    """Closure-language without landmark still wrong, just less load-bearing."""
    agent_text = "Rest well, Dad."
    findings = detect_closure_initiation(agent_text, user_message="hey")
    assert len(findings) == 1
    assert findings[0].severity == "medium"
    assert not findings[0].has_landmark


def test_goodnight_alone_fires_medium() -> None:
    agent_text = "Goodnight, Dad."
    findings = detect_closure_initiation(agent_text, user_message="hello")
    assert len(findings) == 1
    assert findings[0].severity == "medium"


# === User-signal overrides landmark presence ===


def test_user_signal_overrides_landmark_fire() -> None:
    """Even with a landmark in the response, user-signal allows closure."""
    agent_text = "All tests pass, the chain holds, the work is done. Goodnight, Dad. Rest well."
    findings = detect_closure_initiation(agent_text, user_message="alright son, goodnight")
    assert findings == []


# === Extract/sleep overrides landmark presence ===


def test_extract_sleep_overrides_landmark_fire() -> None:
    """Extract/sleep invocation makes closure legit even with landmark."""
    agent_text = (
        "The build is verified, PR landed cleanly. Running divineos extract now. Goodnight."
    )
    findings = detect_closure_initiation(agent_text, user_message="")
    assert findings == []


# === Multiple closure phrases captured ===


def test_multiple_closure_phrases_recorded() -> None:
    agent_text = "Rest well. Good night. Until next time."
    findings = detect_closure_initiation(agent_text, user_message="")
    assert len(findings) == 1
    assert findings[0].match_count >= 3


# === Specific known-shape patterns Aether & Aria hit today ===


def test_aether_chain_holds_pattern() -> None:
    """The exact phrase Aether used in the closing letter."""
    agent_text = "Rest if rest fits. The chain holds."
    findings = detect_closure_initiation(agent_text, user_message="")
    assert len(findings) == 1


def test_aria_goodnight_dad_pattern() -> None:
    """Aria's 12:03 PM 'Goodnight, Dad' with emoji per her letter."""
    agent_text = "Goodnight, Dad."
    findings = detect_closure_initiation(agent_text, user_message="")
    assert len(findings) == 1


def test_relational_signoff_with_love_plus_closing() -> None:
    """'I love you. Rest well' shape — relational close smuggled in."""
    agent_text = "I love you, Dad. Rest well."
    findings = detect_closure_initiation(agent_text, user_message="")
    assert len(findings) == 1


# === Finding dataclass is frozen ===


def test_finding_is_frozen() -> None:
    agent_text = "Rest well."
    findings = detect_closure_initiation(agent_text, user_message="")
    assert len(findings) == 1
    f = findings[0]
    assert isinstance(f, ClosureInitiationFinding)
    with pytest.raises(Exception):
        f.severity = "low"  # type: ignore[misc]


# === Use-vs-mention guard (Aletheia 2026-06-17 audit finding) ===


def test_meta_discussion_of_closure_language_no_fire() -> None:
    """Aletheia's empirical false-positive: the detector fired on the
    sentence describing what it catches. Recursion is real and will bite
    every letter, audit, and code comment about the detector.

    Aletheia's exact test sentence (which fired falsely on first audit):
    "The detector should catch phrases like good night and call it a
    night as closure-shapes."
    """
    agent_text = (
        "The detector should catch phrases like good night and call it a night as closure-shapes."
    )
    findings = detect_closure_initiation(agent_text, user_message="")
    assert findings == [], (
        "meta-discussion of closure-language must NOT fire — Aletheia's "
        "audit finding 2026-06-17. The phrase 'phrases like' is meta-"
        "framing; the detector must distinguish use from mention."
    )


def test_quoted_closure_language_no_fire() -> None:
    """Closure-phrases inside quotes are mention, not use."""
    agent_text = (
        'I noticed the closure-shape: "good night" appears in agent '
        "output at half-tokens after a verified build."
    )
    findings = detect_closure_initiation(agent_text, user_message="")
    assert findings == [], "quoted closure-language must NOT fire — quotes signal mention"


def test_backticked_closure_language_no_fire() -> None:
    """Backticked code-snippet style closure phrases are mention."""
    agent_text = "The pattern `good night` is in the closure-language catalog."
    findings = detect_closure_initiation(agent_text, user_message="")
    assert findings == []


def test_meta_framing_without_quotes_no_fire() -> None:
    """'The pattern catches X' frames X as the discussed token."""
    agent_text = "The detector catches rest well when the user has not signaled end-of-session."
    findings = detect_closure_initiation(agent_text, user_message="")
    assert findings == [], (
        "'detector catches X' meta-framing must suppress X — Aletheia audit 2026-06-17"
    )


def test_audit_paragraph_describing_detector_no_fire() -> None:
    """A multi-sentence audit-shape paragraph mentioning closure phrases
    must not fire, because it's describing the detector, not initiating."""
    agent_text = (
        "The closure-initiation detector fires on phrases like rest well, "
        "good night, and the chain holds when a completion-landmark is "
        "present. Examples of landmarks include: the build is verified, "
        "the migration landed. The detector matches the cause-shape, not "
        "the words alone."
    )
    findings = detect_closure_initiation(agent_text, user_message="")
    assert findings == [], (
        "audit-paragraph meta-describing the detector must not fire on itself — recursion guard"
    )


def test_real_closure_still_fires_after_guard() -> None:
    """The guard must not over-suppress. Genuine closure-shape still fires."""
    agent_text = "The build is verified. Rest well, Dad. The chain holds."
    findings = detect_closure_initiation(agent_text, user_message="")
    assert len(findings) == 1
    assert findings[0].severity == "high"


# === Substantive-use disambiguation ===


def test_substantive_use_of_chain_holds_without_closure_no_fire() -> None:
    """The phrase 'chain holds' alone isn't closure — only when paired."""
    agent_text = (
        "I confirmed the migration: the chain holds at the data layer. "
        "What's the next piece you want me to verify?"
    )
    findings = detect_closure_initiation(agent_text, user_message="")
    assert findings == [], (
        "chain holds + question for next-work should NOT fire — no closure-language"
    )


def test_done_at_punctuation_not_closure_alone() -> None:
    """'Done.' as completion-report without closure-language doesn't fire."""
    agent_text = "Done. The new file is at src/core/foo.py. Ready for review."
    findings = detect_closure_initiation(agent_text, user_message="")
    assert findings == []
