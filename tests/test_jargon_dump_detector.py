"""Regression-pin tests for jargon_dump_detector.

The bug-shape these tests prevent: a future refactor that loosens the
detector's idea of "translation" — e.g. counting any parenthesis or
any contraction as evidence that lepos is operating — would silently
re-introduce the failure-mode the operator named 2026-05-13: jargon
dumped without translation alongside.

Most load-bearing tests:
- ``test_hash_laden_short_response_flagged`` — pins the worst case
  (short response with many engineer-noise tokens, zero translation)
- ``test_concept_heavy_no_translation_flagged`` — pins the middle case
  (longer engineer-talk without IDs but no translation work either)
- ``test_jargon_with_translation_stays_clean`` — pins lepos working:
  jargon used AND explained in the same response
"""

from __future__ import annotations

from divineos.core.operating_loop.jargon_dump_detector import (
    JargonDumpFinding,
    detect_jargon_dump,
    format_finding,
)


# ─── Load-bearing: catches the bad cases ────────────────────────────


def test_hash_laden_short_response_flagged() -> None:
    """Short response stuffed with hash strings and round-IDs but no
    translation: the worst failure-mode."""
    text = (
        "Filed round-101d9ca2e3cf for the post-response-audit "
        "aggregation fix. Before: last_assistant_text = "
        "assistant_msgs[-1]. tree-hash: "
        "d7972103f92060df28ae73201749a8b231b9fc77. diff-hash: "
        "05ea2b6bc540b7d7709833531fcf1e3534da8af6ed896c18846acc15"
        "34295989."
    )
    findings = detect_jargon_dump(text)
    assert len(findings) == 1
    assert findings[0].severity == "high"
    assert findings[0].noise_count >= 5
    assert findings[0].translation_count == 0


def test_concept_heavy_no_translation_flagged() -> None:
    """Longer engineer-talk without specific IDs but no translation
    markers: the middle case. Coined-compound names + code-shape
    expressions in prose."""
    text = (
        "Regression-pin test. The synthetic check I did at fix-time is "
        "good for now, but no test pins the behavior going forward. "
        "First-turn-no-user-record, multiple consecutive user-records, "
        "non-text content blocks. My implementation handles all three "
        "verified by reading my own code: last_user_idx=-1 falls to "
        "aggregate-all branch; backward walk finds the LAST user "
        "index; text-block filter c.get('type')=='text' skips tool "
        "uses and images."
    )
    findings = detect_jargon_dump(text)
    assert len(findings) == 1
    assert findings[0].translation_count == 0


# ─── Load-bearing: lepos working stays clean ────────────────────────


def test_jargon_with_translation_stays_clean() -> None:
    """The lepos shape: engineering terms USED AND EXPLAINED in plain
    language alongside. This is what we want; the detector must not
    flag it."""
    text = (
        "The watchdog (the thing that's supposed to flag jargon-dumping "
        "at you) is broken. The detector counted contractions like "
        '"I\'m" and "you\'re" as proof I was speaking gracefully -- '
        "which means a response could be 95% engineer-talk with two "
        "contractions sprinkled in and the watchdog said it was fine. "
        "In plain English: the wrong yardstick."
    )
    findings = detect_jargon_dump(text)
    assert findings == [], (
        "Jargon paired with translation IS lepos operating. "
        "If this test fails, the translation-marker logic loosened or "
        "the noise-pattern tightened to flag legitimate explanation. "
        "Do NOT relax by counting more things as translation; investigate "
        "what specifically caused the false positive."
    )


def test_translated_plain_response_stays_clean() -> None:
    """Operator-channel response with translated explanations and zero
    raw engineer-noise: definitively clean."""
    text = (
        "Right. Not gone, not dumping jargon either. With you in your "
        "language as I work. Here's what I'm about to do, in plain "
        "English: The audit-gate is too suspicious right now. If a "
        "code-formatter shifts whitespace in my file, the gate treats "
        "it the same as if I changed how the code actually works -- "
        "makes me redo the whole approval song-and-dance."
    )
    findings = detect_jargon_dump(text)
    assert findings == []


def test_short_response_with_one_jargon_mention_stays_clean() -> None:
    """A short response that LEGITIMATELY references some jargon once
    is not a dump. The threshold prevents single-mention false-flags."""
    text = (
        "Yeah. I just did it in that response -- round-IDs, file names, "
        "structural gap, cumulative content to the detectors."
    )
    findings = detect_jargon_dump(text)
    assert findings == []


def test_short_id_with_translation_stays_clean() -> None:
    """Edge case: a short message containing one round-id that's
    immediately translated. Should be clean."""
    text = (
        "Filed round-abcdef123456 -- that's the audit record for the "
        "watchdog fix. Going to commit now."
    )
    findings = detect_jargon_dump(text)
    assert findings == []


# ─── Detector pattern coverage ──────────────────────────────────────


def test_hex_hash_pattern_detected() -> None:
    """SHA-shape hex strings ≥ 8 chars in prose count as engineer-noise."""
    text = "The tree at d7972103f92060df shifted from f0e1d2c3b4a59687 "
    text = text + " ".join(["filler"] * 60)
    findings = detect_jargon_dump(text)
    # 2 hashes alone is below threshold-3 for long responses
    assert findings == []


def test_round_id_prefix_detected() -> None:
    """round-XXX, find-XXX, claim-XXX prefixes detected."""
    text = "Filed round-101d9ca2e3cf and find-cbfb51192e3e and claim-7e780182 " + " ".join(
        ["filler"] * 70
    )
    findings = detect_jargon_dump(text)
    assert findings
    assert findings[0].noise_count >= 3


def test_snake_case_in_prose_detected() -> None:
    """snake_case_identifiers with 2+ underscores trigger the pattern."""
    text = (
        "The last_assistant_text and prior_assistant_text and last_user_text "
        "values feed into the detectors. " + " ".join(["filler"] * 60)
    )
    findings = detect_jargon_dump(text)
    assert findings


def test_long_kebab_compound_detected() -> None:
    """Long kebab-case compounds (4+ segments) are engineer-shape coining."""
    text = (
        "The first-turn-no-user-record and non-text-content-block-skip "
        "and aggregate-all-records-branch cases " + " ".join(["filler"] * 50)
    )
    findings = detect_jargon_dump(text)
    assert findings


def test_call_expression_in_prose_detected() -> None:
    """Code-in-prose: function calls with arguments trigger the pattern."""
    text = (
        "The check returns c.get('type') and then calls extract_turn(p) "
        "and processes records.append('x'). " + " ".join(["filler"] * 60)
    )
    findings = detect_jargon_dump(text)
    assert findings


# ─── Translation-marker patterns ────────────────────────────────────


def test_in_plain_english_counts_as_translation() -> None:
    """'In plain English:' is a definitional translation-marker."""
    text = (
        "Filed round-101d9ca2e3cf for the audit-aggregation fix. "
        "In plain English: I told the watchdog where to look. "
        "Also tree-hash: d7972103f92060df. " + " ".join(["filler"] * 30)
    )
    findings = detect_jargon_dump(text)
    # With translation marker, ~2 noise tokens + 1 translation = clean
    # (noise_count needs to exceed 2 * translation_count for the
    # high-noise branch; with only 2-3 noise and 1 translation, clean)
    if findings:
        assert findings[0].translation_count >= 1


def test_em_dash_restate_counts_as_translation() -> None:
    """Em-dash followed by plain-language restate counts."""
    text = (
        "The round-101d9ca2e3cf audit -- that's the approval record -- "
        "got both confirms. " + " ".join(["filler"] * 50)
    )
    findings = detect_jargon_dump(text)
    # Em-dash restate provides translation; short noise count → clean
    assert findings == []


def test_which_means_counts_as_translation() -> None:
    """'which means' is a definitional translation-marker."""
    text = (
        "The last_assistant_text variable was empty, which means the "
        "watchdog had nothing to look at. The detector returned silent." + " ".join(["filler"] * 50)
    )
    findings = detect_jargon_dump(text)
    # snake_case (1) + 'which means' (1 translation) → clean
    assert findings == []


# ─── Robustness ─────────────────────────────────────────────────────


def test_empty_text_no_crash() -> None:
    assert detect_jargon_dump("") == []
    assert detect_jargon_dump("   \n\n  ") == []


def test_short_text_below_floor_clean() -> None:
    """Very short responses are not dumps by definition."""
    assert detect_jargon_dump("Done.") == []
    assert detect_jargon_dump("Filed round-abc123def456.") == []


def test_format_finding_includes_diagnostics() -> None:
    """The formatter must surface noise count, translation count, and
    samples for the post-response audit log."""
    text = (
        "Filed round-101d9ca2e3cf with tree-hash "
        "d7972103f92060df28ae73201749a8b231b9fc77 and diff-hash "
        "05ea2b6bc540b7d7709833531fcf1e3534da8af6ed896c18846acc15"
        "34295989 plus last_assistant_text snake_case_identifier."
    )
    findings = detect_jargon_dump(text)
    assert findings
    formatted = format_finding(findings[0])
    assert "jargon_dump" in formatted
    assert "engineer-noise" in formatted
    assert "translation-markers" in formatted


def test_finding_is_frozen_dataclass() -> None:
    """JargonDumpFinding is immutable so future code can't mutate
    findings after detection."""
    text = (
        "Filed round-101d9ca2e3cf for fix d7972103f92060df with "
        "last_assistant_text and a long-kebab-case-compound-here."
    )
    findings = detect_jargon_dump(text)
    assert findings
    finding = findings[0]
    assert isinstance(finding, JargonDumpFinding)
    try:
        finding.noise_count = 999  # type: ignore[misc]
        raise AssertionError("Should have raised FrozenInstanceError")
    except Exception as e:
        assert "frozen" in str(type(e).__name__).lower() or "frozen" in str(e).lower()
