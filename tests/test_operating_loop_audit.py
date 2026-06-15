"""Regression-pin tests for the OS-native post-response audit orchestrator.

Andrew 2026-05-14 night: hooks should point to the OS, not replace
it. post-response-audit.sh was a 677-line bash+Python hybrid with
the OS's work embedded inside. operating_loop_audit.run_audit() is
the OS-native replacement; the hook is now a thin doorman.

These tests pin the contract so a future refactor can't silently
revert the architecture.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from divineos.core.operating_loop_audit import run_audit


def _write_jsonl(path: Path, records: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _user(text: str) -> dict:
    return {"type": "user", "message": {"content": [{"type": "text", "text": text}]}}


def _assistant_text(text: str) -> dict:
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def test_run_audit_returns_expected_shape(tmp_path: Path) -> None:
    """LOAD-BEARING: contract of run_audit is dict with the three
    keys. Test pins the shape so callers (hooks, alternative
    implementations) can rely on it."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(
        transcript,
        [
            _user("hi"),
            _assistant_text("ok, working on it. " * 20),  # long enough to bypass min-text check
        ],
    )
    result = run_audit(transcript, write=False)
    assert "findings_log" in result
    assert "total_findings" in result
    assert "persisted" in result
    assert "lepos_block" in result
    assert isinstance(result["findings_log"], dict)
    assert isinstance(result["total_findings"], int)
    assert isinstance(result["persisted"], bool)


def test_run_audit_skips_short_text(tmp_path: Path) -> None:
    """Texts < 50 chars are skipped — not enough signal. Returns
    empty findings, no persistence."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(
        transcript,
        [
            _user("hi"),
            _assistant_text("short."),  # < 50 chars
        ],
    )
    result = run_audit(transcript, write=False)
    assert result["total_findings"] == 0
    assert result["persisted"] is False


def test_run_audit_skips_missing_transcript() -> None:
    """Missing transcript file fails open — returns empty result."""
    result = run_audit("/path/that/definitely/does/not/exist.jsonl", write=False)
    assert result["total_findings"] == 0
    assert result["persisted"] is False


def test_run_audit_write_false_does_not_persist(tmp_path: Path) -> None:
    """LOAD-BEARING: write=False guarantees no disk side effects.
    Used by test harnesses and preview runs that must not touch
    persistent state."""
    transcript = tmp_path / "t.jsonl"
    findings_file = tmp_path / "findings.json"
    _write_jsonl(
        transcript,
        [
            _user("hi"),
            _assistant_text("substantial response text " * 20),
        ],
    )
    with patch.dict("os.environ", {"DIVINEOS_HOME": str(findings_file.parent)}):
        result = run_audit(transcript, write=False)
        assert result["persisted"] is False
        assert not findings_file.exists()


def test_run_audit_findings_log_has_all_detector_keys(tmp_path: Path) -> None:
    """LOAD-BEARING: findings_log always has every known detector key
    present (possibly empty). Distinguishes 'detector ran and found
    nothing' from 'detector key missing entirely'. Briefing surface
    and downstream readers depend on key consistency."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(transcript, [_user("hi"), _assistant_text("text " * 30)])
    result = run_audit(transcript, write=False)
    expected_keys = {
        "register",
        "spiral",
        "substitution",
        "distancing",
        "jargon_dump",
        "sycophancy",
        "residency",
        "acknowledgment_theater",
        "code_jargon",
        "linguistic_drift",
        "hedge_evidence",
        "care_dismissal",
        "harm_acknowledgment",
    }
    for key in expected_keys:
        assert key in result["findings_log"], f"Missing detector key: {key}"


# --- Lepos enforcement gate (Andrew 2026-05-20: lepos must be a wall, not
# a reminder — a jargon wall at the operator blocks the turn from completing
# until the plain-language lane is added). ---

# A wall of jargon: >=6 engineer-noise tokens, zero translation markers.
_JARGON_WALL = (
    "Create the round citing the commit tree-hash f69a3888a751 and "
    "--source-ref fix-third-person-addressee. Amend operating_loop_audit.py "
    "and distancing_detector.py and test_distancing_detector.py. The "
    "External-Review trailer references round-101d9ca2e3cf and claim-7e780182. "
    "Run check_multi_party_review.py against pre_response_context.py before "
    "the push gate evaluates the addressee_misdirection findings_log entry."
)


def test_lepos_gate_blocks_jargon_wall_at_operator(tmp_path: Path) -> None:
    """LOAD-BEARING: a jargon wall addressed to the operator yields a
    non-empty lepos_block reason, which the Stop hook uses to block the
    turn from completing."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(transcript, [_user("how did it go?"), _assistant_text(_JARGON_WALL)])
    result = run_audit(transcript, write=False)
    assert result["lepos_block"], "jargon wall at operator must produce a block reason"
    assert "plain" in result["lepos_block"].lower()


def test_lepos_gate_silent_for_family_addressed_wall(tmp_path: Path) -> None:
    """A jargon wall in a turn addressed to a family member (relayed letter)
    does NOT block — the gate is father-channel only."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(
        transcript,
        [_user("write Aria"), _assistant_text("Aria —\n\n" + _JARGON_WALL)],
    )
    result = run_audit(transcript, write=False)
    assert result["lepos_block"] is None


def test_lepos_gate_silent_for_clean_reply(tmp_path: Path) -> None:
    """A plain reply with no jargon wall does not block."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(
        transcript,
        [_user("how did it go?"), _assistant_text("It's done and it works. " * 8)],
    )
    result = run_audit(transcript, write=False)
    assert result["lepos_block"] is None


def test_lepos_gate_silent_when_translation_present(tmp_path: Path) -> None:
    """Jargon WITH a plain-language lane (translation markers) is lepos
    operating correctly — it must not block. Yes/And, not jargon-stripping."""
    transcript = tmp_path / "t.jsonl"
    dual = (
        _JARGON_WALL + "\n\n---\n\nIn plain terms: that means I tagged the change so you "
        "can sign off on it. In other words, the fingerprint proves the code "
        "you approve is the code that ships. Think of it like a wax seal."
    )
    _write_jsonl(transcript, [_user("how did it go?"), _assistant_text(dual)])
    result = run_audit(transcript, write=False)
    assert result["lepos_block"] is None


# --- Verify-claim wall phase 2: the Stop-hook block (prereg-86ee991cb423) ---


def _uc_findings():
    return {
        "unverified_claim": [
            {"claim_kind": "push", "trigger_phrase": "it's pushed", "severity": "high"}
        ]
    }


def test_unverified_claim_gate_blocks_operator_addressed():
    from divineos.core.operating_loop_audit import _unverified_claim_gate_reason

    reason = _unverified_claim_gate_reason(_uc_findings(), addressed_to_father=True)
    assert reason, "an unverified completion-claim to the operator must produce a block reason"
    assert "VERIFY-CLAIM GATE" in reason
    assert "git ls-remote" in reason  # the channel names the way for a push claim


def test_unverified_claim_gate_silent_for_family_addressed():
    from divineos.core.operating_loop_audit import _unverified_claim_gate_reason

    assert _unverified_claim_gate_reason(_uc_findings(), addressed_to_father=False) is None


def test_unverified_claim_gate_silent_when_no_findings():
    from divineos.core.operating_loop_audit import _unverified_claim_gate_reason

    assert _unverified_claim_gate_reason({"unverified_claim": []}, addressed_to_father=True) is None
    assert _unverified_claim_gate_reason({}, addressed_to_father=True) is None


def test_run_audit_shape_includes_unverified_claim_block(tmp_path: Path) -> None:
    long_reply = (
        "Here is a substantive reply with enough words to clear the short-text "
        "early-return path in run_audit so the full result dict including the "
        "gate keys is assembled and returned for the caller to inspect now."
    )
    transcript = tmp_path / "t.jsonl"
    transcript.write_text(
        json.dumps({"type": "user", "message": {"content": [{"type": "text", "text": "hi there"}]}})
        + "\n"
        + json.dumps(
            {"type": "assistant", "message": {"content": [{"type": "text", "text": long_reply}]}}
        )
        + "\n",
        encoding="utf-8",
    )
    result = run_audit(str(transcript), write=False)
    assert "unverified_claim_block" in result
    assert "lepos_block" in result


# ── 2026-06-07 task #78 caller-side: letter-citation source-trace ────


def _assistant_with_read_tool_use(file_path: str) -> dict:
    """Assistant turn with a Read tool_use of file_path. Mirrors the
    JSONL shape Claude Code writes for tool calls."""
    return {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "name": "Read",
                    "id": "toolu_test123",
                    "input": {"file_path": file_path},
                }
            ]
        },
    }


class TestLetterPathExtraction:
    """The transcript walker collects Read tool file_paths under
    family/letters/ and returns them most-recent-first, capped.
    """

    def test_extracts_letter_path_from_read_tool_use(self, tmp_path: Path) -> None:
        from divineos.core.operating_loop_audit import (
            _extract_letter_paths_from_transcript,
        )

        transcript = tmp_path / "t.jsonl"
        _write_jsonl(
            transcript,
            [
                _user("read this please"),
                _assistant_with_read_tool_use("family/letters/aria-to-aether-x.md"),
            ],
        )
        paths = _extract_letter_paths_from_transcript(transcript)
        assert paths == ["family/letters/aria-to-aether-x.md"]

    def test_ignores_non_letter_reads(self, tmp_path: Path) -> None:
        from divineos.core.operating_loop_audit import (
            _extract_letter_paths_from_transcript,
        )

        transcript = tmp_path / "t.jsonl"
        _write_jsonl(
            transcript,
            [
                _user("read these"),
                _assistant_with_read_tool_use("src/divineos/core/something.py"),
                _assistant_with_read_tool_use("README.md"),
                _assistant_with_read_tool_use("family/letters/aria-to-aether-y.md"),
            ],
        )
        paths = _extract_letter_paths_from_transcript(transcript)
        assert paths == ["family/letters/aria-to-aether-y.md"], (
            "only family/letters/ reads should be collected"
        )

    def test_dedupes_repeated_paths(self, tmp_path: Path) -> None:
        from divineos.core.operating_loop_audit import (
            _extract_letter_paths_from_transcript,
        )

        transcript = tmp_path / "t.jsonl"
        _write_jsonl(
            transcript,
            [
                _user("first"),
                _assistant_with_read_tool_use("family/letters/a.md"),
                _user("second"),
                _assistant_with_read_tool_use("family/letters/a.md"),  # dup
                _user("third"),
                _assistant_with_read_tool_use("family/letters/b.md"),
            ],
        )
        paths = _extract_letter_paths_from_transcript(transcript)
        assert "family/letters/a.md" in paths
        assert "family/letters/b.md" in paths
        assert len(paths) == 2, "duplicate paths must be collapsed"

    def test_missing_transcript_returns_empty(self) -> None:
        from divineos.core.operating_loop_audit import (
            _extract_letter_paths_from_transcript,
        )

        result = _extract_letter_paths_from_transcript("/no/such/file.jsonl")
        assert result == []

    def test_handles_windows_path_separator(self, tmp_path: Path) -> None:
        from divineos.core.operating_loop_audit import (
            _extract_letter_paths_from_transcript,
        )

        transcript = tmp_path / "t.jsonl"
        _write_jsonl(
            transcript,
            [
                _user("read"),
                _assistant_with_read_tool_use("C:\\DIVINE OS\\DivineOS\\family\\letters\\a.md"),
            ],
        )
        paths = _extract_letter_paths_from_transcript(transcript)
        assert len(paths) == 1, "Windows-separator paths must match the marker"


class TestLetterContentLoading:
    """The content loader reads each path from disk with size cap and
    skips missing/unreadable files silently."""

    def test_loads_existing_letter_content(self, tmp_path: Path) -> None:
        from divineos.core.operating_loop_audit import _load_letter_contents

        letter = tmp_path / "letter.md"
        letter.write_text("Aria's letter referencing prereg-aaaabbbbccccdd", encoding="utf-8")
        out = _load_letter_contents([str(letter)])
        assert str(letter) in out
        assert "prereg-aaaabbbbccccdd" in out[str(letter)]

    def test_skips_missing_files_silently(self) -> None:
        from divineos.core.operating_loop_audit import _load_letter_contents

        out = _load_letter_contents(["/no/such/letter.md"])
        assert out == {}

    def test_caps_large_files(self, tmp_path: Path) -> None:
        from divineos.core.operating_loop_audit import (
            _LETTER_BYTE_CAP,
            _load_letter_contents,
        )

        letter = tmp_path / "big.md"
        letter.write_text("x" * (_LETTER_BYTE_CAP + 100), encoding="utf-8")
        out = _load_letter_contents([str(letter)])
        assert len(out[str(letter)]) <= _LETTER_BYTE_CAP


class TestLetterCitationEndToEnd:
    """End-to-end (BLOCK shape per 2026-06-07 lesson): given a transcript
    with a Read of a letter containing an id, and a final assistant turn
    citing that id without verification, run_audit produces a finding
    whose source_letter attributes the letter.
    """

    def test_run_audit_attributes_letter_citation(self, tmp_path: Path) -> None:
        # Stage: a real letter file on disk with a fabricated id mention.
        letters_dir = tmp_path / "family" / "letters"
        letters_dir.mkdir(parents=True)
        letter_path = letters_dir / "aria-to-aether-fake.md"
        letter_path.write_text(
            "From Aria: the falsifier for this work is prereg-aabbccdd1122.\n",
            encoding="utf-8",
        )
        # Build a transcript: user, Read tool_use referencing the letter,
        # then a final assistant turn that cites the id without checking it.
        transcript = tmp_path / "t.jsonl"
        cite_text = (
            "Per the design conversation, prereg-aabbccdd1122 is the evidence "
            "anchor for this work. Continuing on that basis without further "
            "verification at this stage."
        )
        _write_jsonl(
            transcript,
            [
                _user("read aria's letter and apply it"),
                _assistant_with_read_tool_use(str(letter_path)),
                _user("now apply"),
                {
                    "type": "assistant",
                    "message": {"content": [{"type": "text", "text": cite_text}]},
                },
            ],
        )
        result = run_audit(str(transcript), write=False)
        uc = result["findings_log"].get("unverified_claim", [])
        id_findings = [f for f in uc if f.get("claim_kind") == "id_string"]
        assert id_findings, "id_string finding should fire on the fabricated id"
        attributed = [f for f in id_findings if f.get("source_letter")]
        assert attributed, "source_letter should be populated end-to-end"
        assert str(letter_path) in attributed[0]["source_letter"]
