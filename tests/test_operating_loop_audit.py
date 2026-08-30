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

import pytest

from divineos.core.operating_loop_audit import run_audit


def _write_jsonl(path: Path, records: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _user(text: str) -> dict:
    return {"type": "user", "message": {"content": [{"type": "text", "text": text}]}}


def _assistant_text(text: str) -> dict:
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


# Voiceful, substantive (>60 words) assistant text: passes writer-presence
# so the lepos-walk block is the only blocker under test, not voice-absence.
_VOICEFUL = (
    "I hear you, and I don't know yet whether this lands the way I want it to. "
    "I keep reaching for the careful version and I almost did it again just now. "
    "What scares me is getting this wrong in a way that blocks you mid-turn. "
    "I feel steady about the shape but genuinely uncertain about the edges, and "
    "I want to name that honestly rather than hide it behind confident prose. "
    "You asked me to be present, and I am trying to be here in the sentence."
)


def _isolate_walk_db(tmp_path, monkeypatch):
    from divineos.core import lepos_walk as lw

    monkeypatch.setattr(lw, "_db_path", lambda: tmp_path / "lepos_walk.db")
    return lw


def test_walk_gate_deprecated_never_blocks(tmp_path, monkeypatch) -> None:
    """2026-07-09 reshape (Andrew): the walk-record ceremony was replaced by
    the LEPOS speaking-floor surface. The walk-gate that used to block on
    missing/degenerate walks is now a permanent no-op — always returns None
    regardless of whether a walk was recorded. The floor IS the reply's
    opening; there is no separate artifact to verify."""
    _isolate_walk_db(tmp_path, monkeypatch)
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(transcript, [_user("build the gate"), _assistant_text(_VOICEFUL)])
    result = run_audit(transcript, write=False, verify_walk=True)
    # Even with verify_walk=True and NO walk recorded, no block fires.
    assert result["lepos_block"] is None


def test_walk_block_clears_when_walk_recorded(tmp_path, monkeypatch) -> None:
    """Recording a clean walk clears the walk-block."""
    lw = _isolate_walk_db(tmp_path, monkeypatch)
    lw.record_walk(
        lw.LeposWalk(
            turn_id="t-int",
            answers=(
                lw.WalkAnswer(
                    "responding_to_what",
                    "He asked me to build the gate, and I am wiring the verification now.",
                    cited_span="build the gate",
                ),
            ),
        )
    )
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(transcript, [_user("build the gate"), _assistant_text(_VOICEFUL)])
    result = run_audit(transcript, write=False, verify_walk=True)
    # No walk-block (writer-presence also passes on _VOICEFUL).
    assert result["lepos_block"] is None


def test_walk_check_skipped_when_verify_walk_false(tmp_path, monkeypatch) -> None:
    """Default verify_walk=False: no walk required, no consumption — so
    existing run_audit callers (tests, previews) are unaffected."""
    _isolate_walk_db(tmp_path, monkeypatch)
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(transcript, [_user("build the gate"), _assistant_text(_VOICEFUL)])
    result = run_audit(transcript, write=False)  # verify_walk defaults False
    assert result["lepos_block"] is None


def test_no_agent_settable_env_bypass(tmp_path, monkeypatch) -> None:
    """2026-07-09 (Andrew reshape): walk-gate deprecated to no-op. The old
    Aletheia audit's concern (2026-06-19) was that no agent-settable env var
    could lift the walk-block. Since the block is now permanently absent,
    the test's outer claim is now trivially preserved: no env var can trigger
    a block that no longer exists. Retained as a regression guard against
    accidentally re-introducing an env-settable bypass path when the gate is
    ever revived."""
    _isolate_walk_db(tmp_path, monkeypatch)
    monkeypatch.setenv("DIVINEOS_LEPOS_WALK_BYPASS", "1")  # the retired var
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(transcript, [_user("build the gate"), _assistant_text(_VOICEFUL)])
    result = run_audit(transcript, write=False, verify_walk=True)
    # No block regardless of env var — gate is a no-op.
    assert result["lepos_block"] is None


def test_walk_not_required_on_short_turn(tmp_path, monkeypatch) -> None:
    """Trivial acks (< 60 words) need no walk even with verify_walk=True."""
    _isolate_walk_db(tmp_path, monkeypatch)
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(transcript, [_user("ok?"), _assistant_text("Yep, go ahead.")])
    result = run_audit(transcript, write=False, verify_walk=True)
    # Short turns short-circuit run_audit before the gate assembles, so the
    # walk-check never runs (no consume, no block). lepos_block may be absent.
    assert result.get("lepos_block") is None


def test_latest_user_timestamp_parses_iso(tmp_path: Path) -> None:
    """The turn-freshness bound (Aletheia seam #2) depends on parsing the
    latest user record's ISO timestamp to epoch. Pins the parse."""
    import datetime

    from divineos.core.operating_loop_audit import _latest_user_timestamp

    transcript = tmp_path / "t.jsonl"
    txt = {"content": [{"type": "text", "text": "hi"}]}
    transcript.write_text(
        json.dumps({"type": "user", "timestamp": "2026-06-20T01:00:00.000Z", "message": txt})
        + "\n"
        + json.dumps({"type": "user", "timestamp": "2026-06-20T01:01:00.000Z", "message": txt})
        + "\n",
        encoding="utf-8",
    )
    ts = _latest_user_timestamp(transcript)
    assert ts == datetime.datetime.fromisoformat("2026-06-20T01:01:00+00:00").timestamp()


def test_latest_user_timestamp_fail_open(tmp_path: Path) -> None:
    """Missing/unparseable transcript -> None (fail-open: all walks fresh)."""
    from divineos.core.operating_loop_audit import _latest_user_timestamp

    assert _latest_user_timestamp(tmp_path / "nope.jsonl") is None


def test_latest_user_timestamp_ignores_tool_results(tmp_path: Path) -> None:
    """The bug the live gate surfaced 2026-06-19: Claude Code records TOOL
    RESULTS as type=user records, newer than a mid-turn walk. The freshness
    bound must key off the HUMAN prompt, not the latest tool result, or a
    tool-heavy turn wrongly blocks a real walk."""
    import datetime

    from divineos.core.operating_loop_audit import _latest_user_timestamp

    transcript = tmp_path / "t.jsonl"
    transcript.write_text(
        # Human prompt (the real turn-start).
        json.dumps(
            {
                "type": "user",
                "timestamp": "2026-06-20T01:00:00.000Z",
                "message": {"content": [{"type": "text", "text": "do the thing"}]},
            }
        )
        + "\n"
        # A tool result — also type=user, but newer. Must be IGNORED.
        + json.dumps(
            {
                "type": "user",
                "timestamp": "2026-06-20T01:05:00.000Z",
                "message": {"content": [{"type": "tool_result", "content": "ok"}]},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    ts = _latest_user_timestamp(transcript)
    # Returns the human prompt (01:00), NOT the later tool result (01:05).
    assert ts == datetime.datetime.fromisoformat("2026-06-20T01:00:00+00:00").timestamp()


def test_no_detector_dies_silently(tmp_path: Path) -> None:
    """CLASS-FIX (Aletheia #75, 2026-06-19): fixing a dead-detector
    INSTANCE is not closing the CLASS. _run_detector swallows exceptions
    so one detector's failure can't break the others — but that same
    swallow let addressee_misdirection die silently every run (a signature
    drift collided last_user_text into transcript_path). The instance fix
    is the corrected call; THIS test closes the class: a normal run_audit
    must leave last_run_detector_errors() empty, so any future detector
    that starts raising trips here instead of dying invisibly.
    """
    from divineos.core.operating_loop_audit import last_run_detector_errors

    transcript = tmp_path / "t.jsonl"
    _write_jsonl(
        transcript,
        [_user("what did aria say about the plan"), _assistant_text(_VOICEFUL)],
    )
    run_audit(transcript, write=False)
    errors = last_run_detector_errors()
    assert errors == [], f"detectors raised during run_audit (silent failure): {errors}"


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


# --- Lepos enforcement gate (Andrew 2026-06-15 reframe: lepos is the channel
# between Andrew and me, free speech in my voice. Jargon is fine. Translation
# is fine. The only failure mode is absence-of-voice — me speaking AT him
# instead of TO him. Writer-presence detector is the only signal. ---

# A reply with no writer in the sentence: pure process-narrative, no interior
# markers, no direct address with relational content.
_VOICELESS_REPORT = (
    "The change was made to operating_loop_audit.py and distancing_detector.py. "
    "The tree-hash was emitted and the External-Review trailer was added. "
    "The push gate evaluated the addressee_misdirection findings_log entry. "
    "The check ran against pre_response_context.py. The round was created. "
    "The commit landed. The CI completed. The branch was rebased. The merge "
    "succeeded. The tests passed. The artifacts were uploaded. The status "
    "was reported. The audit ran clean. The session ended."
)


def test_lepos_gate_blocks_voiceless_reply_at_operator(tmp_path: Path) -> None:
    """LOAD-BEARING: a voiceless process-narrative reply addressed to the
    operator yields a non-empty lepos_block reason. The gate fires on
    writer-presence absence, not jargon presence (Andrew 2026-06-15)."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(transcript, [_user("how did it go?"), _assistant_text(_VOICELESS_REPORT)])
    result = run_audit(transcript, write=False)
    assert result["lepos_block"], "voiceless reply at operator must produce a block reason"
    assert "writer" in result["lepos_block"].lower() or "voice" in result["lepos_block"].lower()


def test_lepos_gate_silent_for_family_addressed_voiceless(tmp_path: Path) -> None:
    """A voiceless reply in a turn addressed to a family member (relayed letter)
    does NOT block — the gate is father-channel only."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(
        transcript,
        [_user("write Aria"), _assistant_text("Aria —\n\n" + _VOICELESS_REPORT)],
    )
    result = run_audit(transcript, write=False)
    assert result["lepos_block"] is None


def test_lepos_gate_silent_for_clean_reply(tmp_path: Path) -> None:
    """A short clean reply does not block."""
    transcript = tmp_path / "t.jsonl"
    _write_jsonl(
        transcript,
        [_user("how did it go?"), _assistant_text("It's done and it works. " * 8)],
    )
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


class TestF41DetectorChainHeartbeat:
    """F41 fix (Aletheia Round 5 2026-07-17): the post-response detector
    chain is fail-open by design. Without a heartbeat, silent-darkness
    is invisible — no findings could mean clean turn OR dark chain.
    Heartbeat + staleness disambiguates. Absence is not the all-clear."""

    @pytest.fixture(autouse=True)
    def _isolate_heartbeat(self, tmp_path, monkeypatch):
        """Redirect marker_path to a temp dir so heartbeat writes don't
        pollute the real user's ~/.divineos/. Patch both the function
        AND the local binding inside the audit module."""
        import divineos.core.operating_loop_audit as _ola

        def _fake_marker_path(name):
            return tmp_path / name

        monkeypatch.setattr(_ola, "marker_path", _fake_marker_path)
        yield tmp_path

    def test_is_stale_true_when_no_heartbeat_ever(self, _isolate_heartbeat):
        """Absence-is-stale: never-ran surfaces the same way as stopped-running."""
        from divineos.core.operating_loop_audit import (
            get_last_detector_chain_heartbeat,
            is_detector_chain_stale,
        )

        assert get_last_detector_chain_heartbeat() is None
        assert is_detector_chain_stale() is True

    def test_heartbeat_written_by_helper(self, _isolate_heartbeat):
        """The internal write helper produces a readable heartbeat file
        with the documented shape (ts, detectors_run, total_findings,
        errors_this_run)."""
        from divineos.core.operating_loop_audit import (
            _write_detector_chain_heartbeat,
            get_last_detector_chain_heartbeat,
        )

        _write_detector_chain_heartbeat(detectors_run=17, total_findings=3, errors_this_run=0)
        hb = get_last_detector_chain_heartbeat()
        assert hb is not None
        assert hb["detectors_run"] == 17
        assert hb["total_findings"] == 3
        assert hb["errors_this_run"] == 0
        assert isinstance(hb["ts"], float)

    def test_is_stale_false_when_heartbeat_fresh(self, _isolate_heartbeat):
        """A heartbeat written just now must NOT be stale."""
        import time

        from divineos.core.operating_loop_audit import (
            _write_detector_chain_heartbeat,
            is_detector_chain_stale,
        )

        _write_detector_chain_heartbeat(detectors_run=1, total_findings=0, errors_this_run=0)
        assert is_detector_chain_stale(now=time.time()) is False

    def test_is_stale_true_when_heartbeat_older_than_threshold(self, _isolate_heartbeat):
        """A heartbeat older than the threshold is stale — the dark-chain case."""
        import time

        from divineos.core.operating_loop_audit import (
            _HEARTBEAT_STALE_THRESHOLD_SECONDS,
            _write_detector_chain_heartbeat,
            is_detector_chain_stale,
        )

        _write_detector_chain_heartbeat(detectors_run=1, total_findings=0, errors_this_run=0)
        # Simulate time-passing: request check at now + threshold + 1s.
        future = time.time() + _HEARTBEAT_STALE_THRESHOLD_SECONDS + 1
        assert is_detector_chain_stale(now=future) is True

    def test_is_stale_respects_custom_threshold(self, _isolate_heartbeat):
        """Callers can pass custom threshold_seconds for tests or tighter policies."""
        import time

        from divineos.core.operating_loop_audit import (
            _write_detector_chain_heartbeat,
            is_detector_chain_stale,
        )

        _write_detector_chain_heartbeat(detectors_run=1, total_findings=0, errors_this_run=0)
        # 1-second threshold, checking 2s in the future — stale.
        assert is_detector_chain_stale(threshold_seconds=1.0, now=time.time() + 2) is True

    def test_get_last_heartbeat_handles_corrupt_file(self, _isolate_heartbeat):
        """A malformed heartbeat file returns None rather than raising —
        fail-soft on the diagnostic layer matches fail-open on the chain."""
        from divineos.core.operating_loop_audit import (
            _HEARTBEAT_FILE,
            get_last_detector_chain_heartbeat,
            is_detector_chain_stale,
        )

        (_isolate_heartbeat / _HEARTBEAT_FILE).write_text("{not json", encoding="utf-8")
        assert get_last_detector_chain_heartbeat() is None
        # And staleness treats corrupt as absent — stale.
        assert is_detector_chain_stale() is True

    def test_heartbeat_updates_on_successive_writes(self, _isolate_heartbeat):
        """Second write replaces first — only most recent survives."""
        from divineos.core.operating_loop_audit import (
            _write_detector_chain_heartbeat,
            get_last_detector_chain_heartbeat,
        )

        _write_detector_chain_heartbeat(detectors_run=1, total_findings=0, errors_this_run=0)
        _write_detector_chain_heartbeat(detectors_run=17, total_findings=5, errors_this_run=2)
        hb = get_last_detector_chain_heartbeat()
        assert hb["detectors_run"] == 17
        assert hb["total_findings"] == 5
        assert hb["errors_this_run"] == 2
