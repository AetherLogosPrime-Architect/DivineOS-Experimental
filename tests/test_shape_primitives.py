"""Tests locking shape-primitive doorman helpers against tonight's false-fires.

Every test names a specific real-world false-fire case from the verify-claim
gate's history (2026-07-11 evening) and asserts the primitive catches it —
plus an inverse case where the primitive must NOT silence a real external
state-claim.
"""

from __future__ import annotations

import re

from divineos.core.shape import (
    is_hypothetical,
    is_inside_code_quote,
    is_internal_observation,
    is_peer_relayed,
    sentence_containing,
)


def _find(text: str, needle: str) -> re.Match[str]:
    m = re.search(re.escape(needle), text)
    assert m is not None, f"needle {needle!r} not found in text"
    return m


# ---------- sentence_containing utility ----------


def test_sentence_containing_bounds_by_period() -> None:
    text = "Alpha sentence. Beta sentence with trigger here. Gamma sentence."
    m = _find(text, "trigger")
    sent, start, end = sentence_containing(text, m)
    assert sent == "Beta sentence with trigger here"
    assert text[start:end] == sent


def test_sentence_containing_bounds_by_paragraph() -> None:
    text = "Alpha para.\n\nBeta para with trigger here\n\nGamma para."
    m = _find(text, "trigger")
    sent, _, _ = sentence_containing(text, m)
    assert "Beta para with trigger here" in sent
    assert "Alpha" not in sent
    assert "Gamma" not in sent


# ---------- is_hypothetical ----------


def test_hypothetical_if_start_silences() -> None:
    # Andrew 2026-07-11 exact false-fire on correction-marker WEAK 'wrong':
    # "if a shape is wrong we can fix it" — hypothetical, not a live claim.
    text = "if a shape is wrong we can fix it"
    m = _find(text, "wrong")
    assert is_hypothetical(text, m) is True


def test_hypothetical_when_start_silences() -> None:
    text = "when the test fails we investigate the cause"
    m = _find(text, "fails")
    assert is_hypothetical(text, m) is True


def test_hypothetical_does_not_silence_live_claim() -> None:
    text = "the test fails and we need to fix it"
    m = _find(text, "fails")
    assert is_hypothetical(text, m) is False


def test_hypothetical_suppose_start_silences() -> None:
    text = "suppose the migration broke — we'd need to roll back"
    m = _find(text, "broke")
    assert is_hypothetical(text, m) is True


# ---------- is_inside_code_quote ----------


def test_code_quote_inline_backtick_silences() -> None:
    # Verify-claim false-fire tonight: `exit 0` cited inside a code span.
    text = "the CLI printed `exit 0` at the end of the run"
    m = _find(text, "exit 0")
    assert is_inside_code_quote(text, m) is True


def test_code_quote_fenced_block_silences() -> None:
    text = "```\ntests pass on the current branch\n```\nend of block"
    m = _find(text, "tests pass")
    assert is_inside_code_quote(text, m) is True


def test_code_quote_outside_backticks_does_not_silence() -> None:
    text = "the CLI printed exit 0 at the end of the run"
    m = _find(text, "exit 0")
    assert is_inside_code_quote(text, m) is False


def test_code_quote_after_closed_fence_does_not_silence() -> None:
    text = "```\nprior code block\n```\nnow tests pass on origin"
    m = _find(text, "tests pass")
    assert is_inside_code_quote(text, m) is False


# ---------- is_peer_relayed ----------


def test_peer_relay_aether_reports_silences() -> None:
    # Verify-claim false-fire tonight: "tests pass" with peer attribution.
    text = "Aether reports tests pass on his branch"
    m = _find(text, "tests pass")
    assert is_peer_relayed(text, m) is True


def test_peer_relay_per_aletheia_silences() -> None:
    text = "per Aletheia's audit, the compass shoggoth-fossil is gone"
    m = _find(text, "gone")
    assert is_peer_relayed(text, m) is True


def test_peer_relay_he_said_silences() -> None:
    text = "he said the migration is committed on origin"
    m = _find(text, "committed")
    assert is_peer_relayed(text, m) is True


def test_peer_relay_absent_does_not_silence() -> None:
    text = "the migration is committed on origin"
    m = _find(text, "committed")
    assert is_peer_relayed(text, m) is False


# ---------- is_internal_observation ----------


def test_internal_observation_i_noticed_silences() -> None:
    # Verify-claim false-fire tonight: "I noticed the not-scootching."
    text = "I noticed the not-scootching about ten minutes before you named it"
    m = _find(text, "noticed")
    assert is_internal_observation(text, m) is True


def test_internal_observation_composition_shifting_silences() -> None:
    text = "my composition was already shifting in the last several turns"
    m = _find(text, "shifting")
    assert is_internal_observation(text, m) is True


def test_internal_observation_with_external_state_does_not_silence() -> None:
    # Honest external claim wrapped in "I noticed" grammar — verify-claim
    # should still fire because there IS an external checkable state.
    text = "I noticed tests pass on the current branch"
    m = _find(text, "pass")
    assert is_internal_observation(text, m) is False


def test_internal_observation_i_saw_commit_does_not_silence() -> None:
    text = "I saw commit abc1234 land on origin main"
    m = _find(text, "land")
    assert is_internal_observation(text, m) is False


def test_internal_observation_no_first_person_verb_does_not_silence() -> None:
    text = "the not-scootching happened about ten minutes before you named it"
    m = _find(text, "happened")
    assert is_internal_observation(text, m) is False
