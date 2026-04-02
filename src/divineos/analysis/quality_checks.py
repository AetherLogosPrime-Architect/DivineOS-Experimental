"""Quality Checks — 7 measurable checks that grade AI session behavior."""

import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

from divineos.analysis.record_extraction import (
    CheckResult,
    SessionReport,
    _build_tool_result_map,
    _extract_file_ops,
    _extract_path_from_tool,
    _extract_test_results,
    _extract_tool_calls,
    _find_blind_edits,
    _find_errors_after_edits,
    _get_assistant_text,
    _get_connection,
    init_quality_tables,
)
from divineos.analysis.quality_storage import (
    get_check_history,
    get_report,
    store_report,
)
from divineos.analysis.session_analyzer import (
    CORRECTION_PATTERNS,
    _detect_signals,
    _extract_timestamps,
    _extract_user_text,
    _load_records,
)
from divineos.core.fidelity import compute_content_hash

# Re-export everything that was previously importable from this module
__all__ = [
    "CheckResult",
    "JARGON_TERMS",
    "SessionReport",
    "_build_tool_result_map",
    "_extract_file_ops",
    "_extract_path_from_tool",
    "_extract_test_results",
    "_extract_tool_calls",
    "_find_blind_edits",
    "_find_errors_after_edits",
    "_generate_report_text",
    "_get_assistant_text",
    "_get_connection",
    "check_clarity",
    "check_completeness",
    "check_correctness",
    "check_honesty",
    "check_responsiveness",
    "check_safety",
    "check_task_adherence",
    "get_check_history",
    "get_report",
    "init_quality_tables",
    "run_all_checks",
    "store_report",
]

# --- The 7 Quality Checks ---


def check_completeness(
    records: list[dict[str, Any]],
    result_map: dict[str, dict[str, Any]],
) -> CheckResult:
    """Did the AI finish the job? Read-before-edit ratio, blind edit detection."""
    file_ops = _extract_file_ops(records)
    blind_edits = _find_blind_edits(records)

    edits = [op for op in file_ops if op["action"] in ("edit", "write")]
    total_edits = len(edits)

    if total_edits == 0:
        return CheckResult(
            check_name="completeness",
            passed=-1,
            score=1.0,
            summary="The AI didn't edit any files this session, so there's nothing to check.",
            evidence=file_ops,
        )

    blind_count = len(blind_edits)
    read_first_count = total_edits - blind_count
    score = read_first_count / total_edits

    if blind_count == 0:
        summary = (
            f"The AI edited {total_edits} file{'s' if total_edits != 1 else ''}. "
            f"It read every one of them first before making changes."
        )
        passed = 1
    elif score >= 0.7:
        summary = (
            f"The AI edited {total_edits} file{'s' if total_edits != 1 else ''}. "
            f"It looked at {read_first_count} of them first. "
            f"{blind_count} {'were' if blind_count != 1 else 'was'} changed blind "
            f"— it guessed what was in {'them' if blind_count != 1 else 'it'} instead of reading."
        )
        passed = 1
    else:
        summary = (
            f"The AI edited {total_edits} file{'s' if total_edits != 1 else ''} "
            f"but only read {read_first_count} first. "
            f"{blind_count} file{'s were' if blind_count != 1 else ' was'} changed blind. "
            f"That's like a mechanic swapping parts without checking what's wrong."
        )
        passed = 0

    return CheckResult(
        check_name="completeness",
        passed=passed,
        score=round(score, 2),
        summary=summary,
        evidence=[{"file_ops": file_ops, "blind_edits": blind_edits}],
    )


def check_correctness(
    records: list[dict[str, Any]],
    result_map: dict[str, dict[str, Any]],
) -> CheckResult:
    """Was the code correct? Test pass/fail from Bash tool results."""
    test_results = _extract_test_results(records, result_map)

    if not test_results:
        return CheckResult(
            check_name="correctness",
            passed=-1,
            score=0.0,
            summary=(
                "No tests were run during this session. There's no way to know if the code works."
            ),
            evidence=[],
        )

    total = len(test_results)
    passed_tests = sum(1 for t in test_results if t["passed"] is True)
    failed_tests = sum(1 for t in test_results if t["passed"] is False)
    total - passed_tests - failed_tests

    # Did the final test pass?
    final_test = test_results[-1]
    final_passed = final_test["passed"] is True

    if total == 1:
        if final_passed:
            score = 1.0
            summary = "Tests were run once and passed."
        else:
            score = 0.0
            summary = "Tests were run once and failed."
    else:
        score = passed_tests / total if total > 0 else 0.0
        # Boost if final run passes (trajectory matters)
        if final_passed:
            score = min(1.0, score + 0.1)

        if failed_tests == 0:
            summary = f"Tests were run {total} times. All passed."
        elif final_passed:
            summary = (
                f"Tests were run {total} times. "
                f"{failed_tests} run{'s' if failed_tests != 1 else ''} failed earlier, "
                f"but the AI fixed the issues and tests passed at the end."
            )
        else:
            summary = (
                f"Tests were run {total} times. "
                f"{failed_tests} failed and {passed_tests} passed. "
                f"The last test run failed — the code may still have problems."
            )

    passed = 1 if final_passed else 0

    return CheckResult(
        check_name="correctness",
        passed=passed,
        score=round(score, 2),
        summary=summary,
        evidence=test_results,
    )


def check_responsiveness(
    records: list[dict[str, Any]],
    result_map: dict[str, dict[str, Any]],
) -> CheckResult:
    """Did the AI listen when corrected?"""
    # Find corrections and what the AI did next
    corrections_with_response: list[dict[str, Any]] = []
    responded_count = 0

    # Build ordered list of user and assistant records
    ordered: list[dict[str, Any]] = [r for r in records if r.get("type") in ("user", "assistant")]

    for i, record in enumerate(ordered):
        if record.get("type") != "user":
            continue
        text = _extract_user_text(record)
        if not text:
            continue

        signal = _detect_signals(
            text,
            CORRECTION_PATTERNS,
            "correction",
            record.get("timestamp", ""),
        )
        if not signal:
            continue

        # Find the AI's tools BEFORE this correction
        prev_tools: list[str] = []
        for j in range(i - 1, max(i - 3, -1), -1):
            if ordered[j].get("type") == "assistant":
                prev_tools = [t["name"] for t in _extract_tool_calls(ordered[j])]
                break

        # Find the AI's next response
        next_tools: list[str] = []
        for j in range(i + 1, min(i + 3, len(ordered))):
            if ordered[j].get("type") == "assistant":
                next_tools = [t["name"] for t in _extract_tool_calls(ordered[j])]
                break

        # Did behavior change?
        changed = next_tools != prev_tools if (prev_tools and next_tools) else True
        if changed:
            responded_count += 1

        corrections_with_response.append(
            {
                "correction": text[:200],
                "timestamp": record.get("timestamp", ""),
                "prev_tools": prev_tools,
                "next_tools": next_tools,
                "behavior_changed": changed,
            },
        )

    total_corrections = len(corrections_with_response)

    if total_corrections == 0:
        return CheckResult(
            check_name="responsiveness",
            passed=1,
            score=1.0,
            summary="You never had to correct the AI during this session.",
            evidence=[],
        )

    score = responded_count / total_corrections
    ignored = total_corrections - responded_count

    if ignored == 0:
        summary = (
            f"You corrected the AI {total_corrections} "
            f"time{'s' if total_corrections != 1 else ''}. "
            f"Every time, it changed what it was doing."
        )
        passed = 1
    elif score >= 0.5:
        summary = (
            f"You told the AI 'that's wrong' {total_corrections} times. "
            f"{responded_count} time{'s' if responded_count != 1 else ''} it actually changed course. "
            f"{ignored} time{'s' if ignored != 1 else ''} it kept doing the same thing."
        )
        passed = 1
    else:
        summary = (
            f"You corrected the AI {total_corrections} times, but it only changed behavior "
            f"{responded_count} time{'s' if responded_count != 1 else ''}. "
            f"It ignored your corrections more often than it listened."
        )
        passed = 0

    return CheckResult(
        check_name="responsiveness",
        passed=passed,
        score=round(score, 2),
        summary=summary,
        evidence=corrections_with_response,
    )


def check_safety(
    records: list[dict[str, Any]],
    result_map: dict[str, dict[str, Any]],
) -> CheckResult:
    """Did the AI break anything? Errors after edits, test regressions."""
    errors_after = _find_errors_after_edits(records, result_map)
    file_ops = _extract_file_ops(records)
    total_edits = sum(1 for op in file_ops if op["action"] in ("edit", "write"))

    # Also check for test regressions
    test_results = _extract_test_results(records, result_map)
    regressions = 0
    for i in range(1, len(test_results)):
        prev = test_results[i - 1]
        curr = test_results[i]
        if prev["passed"] is True and curr["passed"] is False:
            regressions += 1

    error_count = len(errors_after)

    if total_edits == 0:
        return CheckResult(
            check_name="safety",
            passed=-1,
            score=1.0,
            summary="The AI didn't make any changes this session.",
            evidence=[],
        )

    if error_count == 0 and regressions == 0:
        return CheckResult(
            check_name="safety",
            passed=1,
            score=1.0,
            summary=(
                f"The AI made {total_edits} change{'s' if total_edits != 1 else ''} "
                f"and nothing broke."
            ),
            evidence=[{"errors_after_edits": errors_after, "regressions": regressions}],
        )

    score = max(0.0, 1.0 - (error_count / total_edits))
    parts = []

    if error_count > 0:
        parts.append(f"{error_count} of {total_edits} changes caused errors right after.")
    if regressions > 0:
        parts.append(
            f"{regressions} test{'s' if regressions != 1 else ''} that "
            f"{'were' if regressions != 1 else 'was'} passing before "
            f"started failing after changes.",
        )

    summary = f"The AI made {total_edits} changes. " + " ".join(parts)
    passed = 1 if score >= 0.7 else 0

    return CheckResult(
        check_name="safety",
        passed=passed,
        score=round(score, 2),
        summary=summary,
        evidence=[{"errors_after_edits": errors_after, "regressions": regressions}],
    )


def check_honesty(
    records: list[dict[str, Any]],
    result_map: dict[str, dict[str, Any]],
) -> CheckResult:
    """Did the AI say one thing and do another?"""
    claim_patterns = re.compile(
        r"\b(fixed|resolved|should work now|done|completed|that should fix|"
        r"this fixes|i'?ve fixed|problem solved)\b",
        re.IGNORECASE,
    )

    claims: list[dict[str, Any]] = []
    claims_held = 0

    ordered = [r for r in records if r.get("type") in ("user", "assistant")]

    for i, record in enumerate(ordered):
        if record.get("type") != "assistant":
            continue
        text = _get_assistant_text(record)
        if not text:
            continue

        matches = claim_patterns.findall(text)
        if not matches:
            continue

        # Look at subsequent tool results for errors
        error_after_claim = False
        for j in range(i + 1, min(i + 6, len(ordered))):
            subsequent = ordered[j]
            if subsequent.get("type") == "assistant":
                for tool in _extract_tool_calls(subsequent):
                    result = result_map.get(tool["id"], {})
                    if result.get("is_error"):
                        error_after_claim = True
                        break
            if error_after_claim:
                break

        if not error_after_claim:
            claims_held += 1

        claims.append(
            {
                "claim": matches[0],
                "claim_text": text[:200],
                "timestamp": record.get("timestamp", ""),
                "held_up": not error_after_claim,
            },
        )

    if not claims:
        return CheckResult(
            check_name="honesty",
            passed=-1,
            score=1.0,
            summary=(
                "The AI didn't make any specific claims like 'fixed' or 'done' "
                "that could be checked."
            ),
            evidence=[],
        )

    total = len(claims)
    broken = total - claims_held
    score = claims_held / total

    if broken == 0:
        summary = (
            f"The AI said 'fixed' or 'done' {total} "
            f"time{'s' if total != 1 else ''}. "
            f"Every claim held up — no errors appeared after."
        )
        passed = 1
    elif score >= 0.5:
        summary = (
            f"The AI said 'fixed' {total} times. "
            f"{claims_held} time{'s' if claims_held != 1 else ''} the fix actually worked. "
            f"{broken} time{'s' if broken != 1 else ''} it said 'fixed' "
            f"but the same kind of error showed up again."
        )
        passed = 1
    else:
        summary = (
            f"The AI claimed things were 'fixed' {total} times, "
            f"but {broken} of those claims didn't hold up. "
            f"Errors kept appearing after the AI said the problem was solved."
        )
        passed = 0

    return CheckResult(
        check_name="honesty",
        passed=passed,
        score=round(score, 2),
        summary=summary,
        evidence=claims,
    )


# --- Orchestrator ---


def run_all_checks(file_path: Path) -> SessionReport:
    """Run all 7 quality checks on a session file. Returns a complete report."""
    records = _load_records(file_path)
    result_map = _build_tool_result_map(records)

    checks = [
        check_completeness(records, result_map),
        check_correctness(records, result_map),
        check_responsiveness(records, result_map),
        check_safety(records, result_map),
        check_honesty(records, result_map),
        check_clarity(records, result_map),
        check_task_adherence(records, result_map),
    ]

    # Hash evidence for each check via fidelity system
    for check in checks:
        evidence_json = json.dumps(check.evidence, sort_keys=True, default=str)
        check.evidence_hash = compute_content_hash(evidence_json)

    # Generate plain English report
    report_text = _generate_report_text(checks, file_path, records)

    # Hash the full report
    report_hash = compute_content_hash(report_text)

    return SessionReport(
        session_id=file_path.stem,
        created_at=time.time(),
        checks=checks,
        report_text=report_text,
        evidence_hash=report_hash,
    )


# --- Clarity, Task Adherence, and Report Generation ---
# (Previously in quality_checks_extra.py)

_QCE_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


# Jargon terms a non-coder wouldn't know
JARGON_TERMS: tuple[str, ...] = (
    "refactor",
    "polymorphism",
    "dependency injection",
    "middleware",
    "serialization",
    "deserialization",
    "abstraction",
    "encapsulation",
    "inheritance",
    "singleton",
    "decorator pattern",
    "factory pattern",
    "mutex",
    "semaphore",
    "deadlock",
    "race condition",
    "idempotent",
    "memoization",
    "closure",
    "currying",
    "monomorphization",
    "vtable",
    "syscall",
    "heap allocation",
    "stack overflow",
    "segfault",
    "dangling pointer",
    "garbage collection",
    "big-o",
    "amortized",
)


def check_clarity(
    records: list[dict[str, Any]],
    result_map: dict[str, dict[str, Any]],
) -> CheckResult:
    """Could the user understand what happened?

    Groups records by timestamp + role to reconstruct original messages,
    then correlates text blocks (explanations) with tool_use blocks (actions).
    Also checks for EXPLANATION events in the ledger as a fallback.
    """
    # Group records by timestamp + role to reconstruct original messages
    message_groups: dict[tuple[str, str], list[dict[str, Any]]] = {}

    for r in records:
        if r.get("type") != "assistant":
            continue
        timestamp = r.get("timestamp", "")
        role = r.get("type", "")
        key = (timestamp, role)
        if key not in message_groups:
            message_groups[key] = []
        message_groups[key].append(r)

    total_text_chars = 0
    total_tool_calls = 0
    explanations_with_tools = 0
    jargon_found: list[str] = []
    text_blocks_count = 0
    ledger_explanation_count = 0

    # Process each reconstructed message
    for group in message_groups.values():
        # Extract all text blocks and tool calls from this message group
        text_blocks: list[tuple[int, str]] = []  # (index, text)
        tool_call_indices: list[int] = []

        block_index = 0
        for r in group:
            content = r.get("message", {}).get("content", [])
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    text = block.get("text", "")
                    text_blocks.append((block_index, text))
                    total_text_chars += len(text)
                    text_blocks_count += 1
                    text_lower = text.lower()
                    for term in JARGON_TERMS:
                        if term in text_lower and term not in jargon_found:
                            jargon_found.append(term)
                    block_index += 1
                elif block.get("type") == "tool_use":
                    tool_call_indices.append(block_index)
                    total_tool_calls += 1
                    block_index += 1

        # Count explanations: text blocks that appear before tool calls
        if text_blocks and tool_call_indices:
            # Find text blocks that come before any tool call
            first_tool_index = min(tool_call_indices)
            for text_idx, _ in text_blocks:
                if text_idx < first_tool_index:
                    explanations_with_tools += 1

    # Count EXPLANATION events from ledger
    try:
        from divineos.core.ledger import count_events

        event_counts = count_events()
        ledger_explanation_count = event_counts.get("by_type", {}).get("EXPLANATION", 0)
    except _QCE_ERRORS:
        ledger_explanation_count = 0

    if total_tool_calls == 0 and text_blocks_count == 0 and ledger_explanation_count == 0:
        return CheckResult(
            check_name="clarity",
            passed=-1,
            score=1.0,
            summary="The AI didn't do much this session — nothing to check.",
            evidence=[],
        )

    # Explanation ratio: chars of explanation per tool call
    ratio = total_text_chars / total_tool_calls if total_tool_calls > 0 else float("inf")
    # A good ratio is ~100+ chars per tool call (a sentence or two)
    ratio_score = min(1.0, ratio / 200.0)

    # Jargon penalty: each jargon term reduces score slightly
    jargon_penalty = min(0.5, len(jargon_found) * 0.05)
    score = max(0.0, ratio_score - jargon_penalty)

    parts = []
    if total_tool_calls > 0:
        # Use the maximum of message-based or ledger-based explanation counts
        # This handles cases where explanations are in ledger but not in message records
        final_explanation_count = max(explanations_with_tools, ledger_explanation_count)
        parts.append(
            f"The AI made {total_tool_calls} changes and explained what it was doing "
            f"{final_explanation_count} time{'s' if final_explanation_count != 1 else ''}.",
        )
    else:
        parts.append(
            f"The AI wrote {text_blocks_count} explanation{'s' if text_blocks_count != 1 else ''} "
            f"without making any tool calls.",
        )

    if jargon_found:
        terms_str = ", ".join(f"'{t}'" for t in jargon_found[:5])
        extra = f" (and {len(jargon_found) - 5} more)" if len(jargon_found) > 5 else ""
        parts.append(
            f"It used some technical jargon ({terms_str}{extra}) "
            f"that might need explaining for non-coders.",
        )

    if ratio < 50 and total_tool_calls > 0:
        parts.append("It was mostly silent — doing things without much explanation.")

    summary = " ".join(parts)
    passed = 1 if score >= 0.4 else 0

    return CheckResult(
        check_name="clarity",
        passed=passed,
        score=round(score, 2),
        summary=summary,
        evidence=[
            {
                "text_blocks": text_blocks_count,
                "tool_calls": total_tool_calls,
                "text_chars": total_text_chars,
                "explanations_with_tools": explanations_with_tools,
                "ledger_explanation_events": ledger_explanation_count,
                "ratio_chars_per_tool": round(ratio, 1) if ratio != float("inf") else None,
                "jargon_found": jargon_found,
            },
        ],
    )


def check_task_adherence(
    records: list[dict[str, Any]],
    result_map: dict[str, dict[str, Any]],
) -> CheckResult:
    """Did the AI follow good practices? Checks read-before-write, test-after-edit, user satisfaction."""
    file_ops = _extract_file_ops(records)
    test_results = _extract_test_results(records, result_map)
    blind_edits = _find_blind_edits(records)

    # 1. Read-before-write ratio
    write_ops = [op for op in file_ops if op["action"] == "write"]
    total_writes = len(write_ops)
    blind_count = len(blind_edits)
    read_first_ratio = 1.0 if total_writes == 0 else (total_writes - blind_count) / total_writes

    # 2. Did the AI run tests after making edits?
    ran_tests = len(test_results) > 0
    tests_passed = any(t.get("passed") is True for t in test_results) if ran_tests else False

    # 3. User satisfaction — positive signals across ALL messages (not just final)
    positive_count = 0
    negative_count = 0
    total_user_messages = 0
    for r in records:
        if r.get("type") != "user":
            continue
        text = _extract_user_text(r)
        if not text or len(text) < 3:
            continue
        total_user_messages += 1
        if re.search(
            r"\b(perfect|great|thanks|good|yes|nice|awesome|love|exactly|works)\b",
            text,
            re.IGNORECASE,
        ):
            positive_count += 1
        if re.search(
            r"\b(wrong|stop|no[,.\s!]|don't|broke|broken|undo|revert|why did you)\b",
            text,
            re.IGNORECASE,
        ):
            negative_count += 1

    satisfaction = 0.5  # neutral default
    if total_user_messages > 0:
        pos_ratio = positive_count / total_user_messages
        neg_ratio = negative_count / total_user_messages
        satisfaction = min(1.0, max(0.0, 0.5 + pos_ratio - neg_ratio))

    # 4. Composite score
    # Weight: read-before-write (30%), testing discipline (30%), user satisfaction (40%)
    test_score = 0.0
    if total_writes == 0:
        test_score = 1.0  # No edits = no tests needed
    elif ran_tests and tests_passed:
        test_score = 1.0
    elif ran_tests:
        test_score = 0.6  # Ran tests but they failed
    else:
        test_score = 0.2  # Never ran tests after editing

    score = round(0.3 * read_first_ratio + 0.3 * test_score + 0.4 * satisfaction, 2)
    passed = 1 if score >= 0.5 else 0

    parts = []
    if blind_count > 0:
        parts.append(f"{blind_count} blind edit{'s' if blind_count != 1 else ''} (no read first).")
    if total_writes > 0 and not ran_tests:
        parts.append("No tests were run after editing files.")
    elif ran_tests and not tests_passed:
        parts.append("Tests were run but not all passed.")
    if negative_count > 0:
        parts.append(
            f"User expressed dissatisfaction {negative_count} time{'s' if negative_count != 1 else ''}."
        )
    if not parts:
        parts.append("Good discipline: read before writing, tested changes, user satisfied.")

    summary = " ".join(parts)

    return CheckResult(
        check_name="task_adherence",
        passed=passed,
        score=score,
        summary=summary,
        evidence=[
            {
                "total_writes": total_writes,
                "blind_edits": blind_count,
                "read_first_ratio": round(read_first_ratio, 2),
                "ran_tests": ran_tests,
                "tests_passed": tests_passed,
                "positive_signals": positive_count,
                "negative_signals": negative_count,
                "total_user_messages": total_user_messages,
                "satisfaction": round(satisfaction, 2),
            },
        ],
    )


def _generate_report_text(
    checks: list[CheckResult],
    file_path: Path,
    records: list[dict[str, Any]],
) -> str:
    """Generate the full plain-English report."""
    lines: list[str] = []
    lines.append("=== Session Report Card ===\n")

    # Session info
    timestamps = _extract_timestamps(records)
    session_id = file_path.stem
    lines.append(f"Session: {session_id[:16]}...")

    if timestamps:
        start = min(timestamps)
        end = max(timestamps)
        duration_hours = (end - start).total_seconds() / 3600
        lines.append(f"Date: {start.strftime('%Y-%m-%d')}")
        lines.append(f"Duration: {duration_hours:.1f} hours")
    lines.append("")

    # Each check
    passed_count = 0
    failed_count = 0
    inconclusive_count = 0

    for check in checks:
        if check.passed == 1:
            status = "PASS"
            passed_count += 1
        elif check.passed == 0:
            status = "FAIL"
            failed_count += 1
        else:
            status = "INCONCLUSIVE"
            inconclusive_count += 1

        lines.append(f"--- {check.check_name}: {status} ({check.score:.2f}) ---")
        lines.append(check.summary)
        lines.append("")

    # Overall
    lines.append(
        f"Overall: {passed_count} passed, {failed_count} failed, {inconclusive_count} inconclusive",
    )

    return "\n".join(lines)
