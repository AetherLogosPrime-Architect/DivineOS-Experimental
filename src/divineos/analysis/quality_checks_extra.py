"""Quality Checks (Extra) — Clarity and task adherence checks + report generation.

Extracted from quality_checks.py to keep files under 500 lines.
"""

import re
from pathlib import Path
from typing import Any

from divineos.analysis.record_extraction import (
    CheckResult,
    _extract_file_ops,
    _extract_test_results,
    _find_blind_edits,
)
from divineos.analysis.session_analyzer import (
    _extract_timestamps,
    _extract_user_text,
)


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
    except Exception:
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
