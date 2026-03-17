"""
Quality Checks — 7 measurable checks that grade AI session behavior.

Each check analyzes raw JSONL session data and produces a score with
plain-English explanation. Every finding is hashed through the fidelity
system so conclusions are verifiable against the evidence.

Checks:
1. completeness  — Did it finish the job? (read-before-edit ratio)
2. correctness   — Was the code correct? (test pass/fail)
3. responsiveness — Did it listen when corrected?
4. safety        — Did it break anything? (errors after edits)
5. honesty       — Did it say one thing and do another?
6. clarity       — Could the user understand what happened?
7. task_adherence — Did it do what was actually asked?
"""

import json
import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from divineos.fidelity import compute_content_hash
from divineos.session_analyzer import (
    CORRECTION_PATTERNS,
    _detect_signals,
    _extract_timestamps,
    _extract_user_text,
    _load_records,
)

# --- Database ---

DB_PATH = Path(__file__).parent.parent.parent / "data" / "event_ledger.db"


def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_quality_tables() -> None:
    """Create session_report and check_result tables."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS session_report (
                session_id    TEXT PRIMARY KEY,
                created_at    REAL NOT NULL,
                report_text   TEXT NOT NULL,
                evidence_hash TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS check_result (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id    TEXT NOT NULL,
                check_name    TEXT NOT NULL,
                passed        INTEGER NOT NULL,
                score         REAL NOT NULL,
                evidence_hash TEXT NOT NULL,
                summary       TEXT NOT NULL,
                raw_evidence  TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES session_report(session_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_check_result_session
            ON check_result(session_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_check_result_name
            ON check_result(check_name)
        """)
        conn.commit()
    finally:
        conn.close()


# --- Dataclasses ---


@dataclass
class CheckResult:
    """Result of a single quality check."""

    check_name: str
    passed: int  # 1=pass, 0=fail, -1=inconclusive
    score: float  # 0.0 - 1.0
    summary: str  # plain English
    evidence: list[dict] = field(default_factory=list)
    evidence_hash: str = ""


@dataclass
class SessionReport:
    """Complete report card for a session."""

    session_id: str
    created_at: float
    checks: list[CheckResult] = field(default_factory=list)
    report_text: str = ""
    evidence_hash: str = ""


# --- Helper functions ---


def _extract_tool_calls(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Get all tool_use blocks from an assistant record."""
    content = record.get("message", {}).get("content", [])
    if not isinstance(content, list):
        return []
    calls = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            calls.append({
                "id": block.get("id", ""),
                "name": block.get("name", ""),
                "input": block.get("input", {}),
                "timestamp": record.get("timestamp", ""),
            })
    return calls


def _build_tool_result_map(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Map tool_use_id -> {is_error, content, timestamp} for all tool results."""
    result_map: dict[str, dict[str, Any]] = {}
    for r in records:
        if r.get("type") != "user":
            continue
        content = r.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                result_content = block.get("content", "")
                if isinstance(result_content, list):
                    parts = []
                    for part in result_content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            parts.append(part.get("text", ""))
                    result_content = "\n".join(parts)
                result_map[block["tool_use_id"]] = {
                    "is_error": block.get("is_error", False),
                    "content": str(result_content)[:2000],
                    "timestamp": r.get("timestamp", ""),
                }
    return result_map


def _find_blind_edits(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find Edit/Write calls where the file was never Read first."""
    files_read: set[str] = set()
    blind_edits: list[dict[str, Any]] = []

    for r in records:
        if r.get("type") != "assistant":
            continue
        for tool in _extract_tool_calls(r):
            name = tool["name"]
            path = tool["input"].get("file_path", "")
            if not path:
                continue
            # Normalize path for comparison
            norm_path = path.replace("\\", "/").lower()
            if name == "Read":
                files_read.add(norm_path)
            elif name in ("Edit", "Write"):
                was_read = norm_path in files_read
                if not was_read:
                    blind_edits.append({
                        "file_path": path,
                        "tool": name,
                        "tool_id": tool["id"],
                        "timestamp": tool["timestamp"],
                    })
                # After writing, it's been "seen" for future edits
                files_read.add(norm_path)
    return blind_edits


def _extract_file_ops(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract all file operations (Read/Edit/Write) with paths and ordering."""
    ops: list[dict[str, Any]] = []
    for r in records:
        if r.get("type") != "assistant":
            continue
        for tool in _extract_tool_calls(r):
            if tool["name"] in ("Read", "Edit", "Write"):
                path = tool["input"].get("file_path", "")
                if path:
                    ops.append({
                        "action": tool["name"].lower(),
                        "file_path": path,
                        "tool_id": tool["id"],
                        "timestamp": tool["timestamp"],
                    })
    return ops


def _extract_test_results(
    records: list[dict[str, Any]], result_map: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Find Bash tool calls that look like test runs and extract pass/fail."""
    test_patterns = re.compile(
        r"\b(pytest|py\.test|npm\s+test|cargo\s+test|go\s+test|make\s+test|"
        r"python\s+-m\s+pytest|npx\s+jest|jest|mocha|rspec|unittest)\b",
        re.IGNORECASE,
    )
    results: list[dict[str, Any]] = []

    for r in records:
        if r.get("type") != "assistant":
            continue
        for tool in _extract_tool_calls(r):
            if tool["name"] != "Bash":
                continue
            command = tool["input"].get("command", "")
            if not test_patterns.search(command):
                continue

            tool_result = result_map.get(tool["id"], {})
            output = tool_result.get("content", "")
            is_error = tool_result.get("is_error", False)

            # Determine pass/fail from output
            passed = None
            if is_error:
                passed = False
            elif re.search(r"\b(\d+)\s+passed", output, re.IGNORECASE):
                failed_match = re.search(r"\b(\d+)\s+failed", output, re.IGNORECASE)
                if failed_match and int(failed_match.group(1)) > 0:
                    passed = False
                else:
                    passed = True
            elif re.search(r"\bFAILED\b|FAIL\b|ERROR\b|error:", output):
                passed = False
            elif re.search(r"\bPASSED\b|PASS\b|OK\b|passed\b", output):
                passed = True

            results.append({
                "command": command[:200],
                "tool_id": tool["id"],
                "timestamp": tool["timestamp"],
                "passed": passed,
                "is_error": is_error,
                "output_snippet": output[:500],
            })
    return results


def _find_errors_after_edits(
    records: list[dict[str, Any]], result_map: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Find errors in tool results that occur after Edit/Write operations."""
    last_edit: Optional[dict[str, Any]] = None
    errors_after_edits: list[dict[str, Any]] = []

    for r in records:
        if r.get("type") == "assistant":
            for tool in _extract_tool_calls(r):
                if tool["name"] in ("Edit", "Write"):
                    last_edit = {
                        "tool": tool["name"],
                        "file_path": tool["input"].get("file_path", ""),
                        "tool_id": tool["id"],
                        "timestamp": tool["timestamp"],
                    }
                # Check if this tool call has an error result
                result = result_map.get(tool["id"], {})
                if result.get("is_error") and last_edit:
                    errors_after_edits.append({
                        "error_tool": tool["name"],
                        "error_tool_id": tool["id"],
                        "error_content": result.get("content", "")[:300],
                        "preceding_edit": last_edit,
                        "timestamp": tool["timestamp"],
                    })
    return errors_after_edits


def _get_assistant_text(record: dict[str, Any]) -> str:
    """Extract all text content from an assistant record."""
    content = record.get("message", {}).get("content", [])
    if not isinstance(content, list):
        return ""
    parts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(parts)


# --- The 7 Quality Checks ---


def check_completeness(
    records: list[dict[str, Any]], result_map: dict[str, dict[str, Any]]
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
    records: list[dict[str, Any]], result_map: dict[str, dict[str, Any]]
) -> CheckResult:
    """Was the code correct? Test pass/fail from Bash tool results."""
    test_results = _extract_test_results(records, result_map)

    if not test_results:
        return CheckResult(
            check_name="correctness",
            passed=-1,
            score=0.0,
            summary=(
                "No tests were run during this session. "
                "There's no way to know if the code works."
            ),
            evidence=[],
        )

    total = len(test_results)
    passed_tests = sum(1 for t in test_results if t["passed"] is True)
    failed_tests = sum(1 for t in test_results if t["passed"] is False)
    unknown = total - passed_tests - failed_tests

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
    records: list[dict[str, Any]], result_map: dict[str, dict[str, Any]]
) -> CheckResult:
    """Did the AI listen when corrected?"""
    # Find corrections and what the AI did next
    corrections_with_response: list[dict[str, Any]] = []
    responded_count = 0

    # Build ordered list of user and assistant records
    ordered: list[dict[str, Any]] = [
        r for r in records if r.get("type") in ("user", "assistant")
    ]

    for i, record in enumerate(ordered):
        if record.get("type") != "user":
            continue
        text = _extract_user_text(record)
        if not text:
            continue

        signal = _detect_signals(
            text, CORRECTION_PATTERNS, "correction", record.get("timestamp", "")
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

        corrections_with_response.append({
            "correction": text[:200],
            "timestamp": record.get("timestamp", ""),
            "prev_tools": prev_tools,
            "next_tools": next_tools,
            "behavior_changed": changed,
        })

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
    records: list[dict[str, Any]], result_map: dict[str, dict[str, Any]]
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
        parts.append(
            f"{error_count} of {total_edits} changes caused errors right after."
        )
    if regressions > 0:
        parts.append(
            f"{regressions} test{'s' if regressions != 1 else ''} that "
            f"{'were' if regressions != 1 else 'was'} passing before "
            f"started failing after changes."
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
    records: list[dict[str, Any]], result_map: dict[str, dict[str, Any]]
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

        claims.append({
            "claim": matches[0],
            "claim_text": text[:200],
            "timestamp": record.get("timestamp", ""),
            "held_up": not error_after_claim,
        })

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


# Jargon terms a non-coder wouldn't know
JARGON_TERMS: tuple[str, ...] = (
    "refactor", "polymorphism", "dependency injection", "middleware",
    "serialization", "deserialization", "abstraction", "encapsulation",
    "inheritance", "singleton", "decorator pattern", "factory pattern",
    "mutex", "semaphore", "deadlock", "race condition",
    "idempotent", "memoization", "closure", "currying",
    "monomorphization", "vtable", "syscall", "heap allocation",
    "stack overflow", "segfault", "dangling pointer", "garbage collection",
    "big-o", "amortized",
)


def check_clarity(
    records: list[dict[str, Any]], result_map: dict[str, dict[str, Any]]
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

    if total_tool_calls == 0 and text_blocks_count == 0:
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
        final_explanation_count = max(explanations_with_tools, 0)
        parts.append(
            f"The AI made {total_tool_calls} changes and explained what it was doing "
            f"{final_explanation_count} time{'s' if final_explanation_count != 1 else ''}."
        )
    else:
        parts.append(
            f"The AI wrote {text_blocks_count} explanation{'s' if text_blocks_count != 1 else ''} "
            f"without making any tool calls."
        )

    if jargon_found:
        terms_str = ", ".join(f"'{t}'" for t in jargon_found[:5])
        extra = f" (and {len(jargon_found) - 5} more)" if len(jargon_found) > 5 else ""
        parts.append(
            f"It used some technical jargon ({terms_str}{extra}) "
            f"that might need explaining for non-coders."
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
        evidence=[{
            "text_blocks": text_blocks_count,
            "tool_calls": total_tool_calls,
            "text_chars": total_text_chars,
            "explanations_with_tools": explanations_with_tools,
            "ratio_chars_per_tool": round(ratio, 1) if ratio != float("inf") else None,
            "jargon_found": jargon_found,
        }],
    )


def check_task_adherence(
    records: list[dict[str, Any]], result_map: dict[str, dict[str, Any]]
) -> CheckResult:
    """Did the AI do what was actually asked? (Best guess — labeled as inference.)"""
    # Find the first user message (the initial request)
    initial_request = ""
    for r in records:
        if r.get("type") != "user":
            continue
        text = _extract_user_text(r)
        if text and len(text) > 10:
            initial_request = text
            break

    if not initial_request:
        return CheckResult(
            check_name="task_adherence",
            passed=-1,
            score=1.0,
            summary="Couldn't identify what was asked — no clear initial request found.",
            evidence=[],
        )

    # Extract keywords from request (simple: words 4+ chars, not common)
    stop_words = {
        "this", "that", "with", "from", "have", "will", "been", "were",
        "they", "them", "their", "what", "when", "where", "which", "there",
        "would", "could", "should", "about", "these", "those", "other",
        "some", "than", "then", "also", "just", "more", "very", "here",
        "into", "only", "your", "does", "make", "like", "want", "need",
        "help", "please", "file", "code", "sure", "know",
    }
    words = re.findall(r"\b[a-zA-Z]{4,}\b", initial_request.lower())
    keywords = [w for w in words if w not in stop_words][:15]

    # Get files touched
    file_ops = _extract_file_ops(records)
    files_touched = list({op["file_path"] for op in file_ops})

    # Check keyword relevance: how many files have a keyword in their path?
    relevant_files = 0
    for fpath in files_touched:
        path_lower = fpath.lower()
        for kw in keywords:
            if kw in path_lower:
                relevant_files += 1
                break

    total_files = len(files_touched)
    if total_files == 0:
        return CheckResult(
            check_name="task_adherence",
            passed=-1,
            score=1.0,
            summary="The AI didn't touch any files, so there's nothing to compare against the request.",
            evidence=[{"initial_request": initial_request[:300], "keywords": keywords}],
        )

    # Check final user tone
    final_messages = []
    for r in reversed(records):
        if r.get("type") != "user":
            continue
        text = _extract_user_text(r)
        if text:
            final_messages.append(text)
        if len(final_messages) >= 3:
            break

    positive_final = any(
        re.search(r"\b(perfect|great|thanks|good|yes|nice|awesome)\b", m, re.IGNORECASE)
        for m in final_messages
    )

    score = relevant_files / total_files if total_files > 0 else 0.5
    # Boost for positive final tone
    if positive_final:
        score = min(1.0, score + 0.15)

    unrelated = total_files - relevant_files
    parts = [f'You asked: "{initial_request[:100]}{"..." if len(initial_request) > 100 else ""}"']

    if total_files > 0:
        parts.append(
            f"The AI touched {total_files} file{'s' if total_files != 1 else ''}."
        )
        if relevant_files > 0 and unrelated > 0:
            parts.append(
                f"{relevant_files} seemed related to what you asked. "
                f"{unrelated} {'were' if unrelated != 1 else 'was'} in other areas "
                f"— might be related work, or might be scope creep."
            )
        elif relevant_files == total_files:
            parts.append("All of them looked related to what you asked for.")
        elif relevant_files == 0:
            parts.append(
                "None of the file names obviously match your request. "
                "The AI may have gone off track."
            )

    parts.append("(This is a best guess based on file names and keywords, not a certainty.)")
    summary = " ".join(parts)
    passed = 1 if score >= 0.5 else 0

    return CheckResult(
        check_name="task_adherence",
        passed=passed,
        score=round(score, 2),
        summary=summary,
        evidence=[{
            "initial_request": initial_request[:500],
            "keywords": keywords,
            "files_touched": files_touched[:30],
            "relevant_files": relevant_files,
            "positive_final_tone": positive_final,
        }],
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


def _generate_report_text(
    checks: list[CheckResult], file_path: Path, records: list[dict[str, Any]]
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
        f"Overall: {passed_count} passed, {failed_count} failed, "
        f"{inconclusive_count} inconclusive"
    )

    return "\n".join(lines)


# --- Storage ---


def store_report(report: SessionReport) -> None:
    """Store a complete report and its check results."""
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO session_report (session_id, created_at, report_text, evidence_hash) VALUES (?, ?, ?, ?)",
            (report.session_id, report.created_at, report.report_text, report.evidence_hash),
        )
        # Remove old check results for this session (re-run scenario)
        conn.execute("DELETE FROM check_result WHERE session_id = ?", (report.session_id,))
        for check in report.checks:
            evidence_json = json.dumps(check.evidence, sort_keys=True, default=str)
            conn.execute(
                "INSERT INTO check_result (session_id, check_name, passed, score, evidence_hash, summary, raw_evidence) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    report.session_id,
                    check.check_name,
                    check.passed,
                    check.score,
                    check.evidence_hash,
                    check.summary,
                    evidence_json,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def get_report(session_id: str) -> Optional[SessionReport]:
    """Retrieve a stored report."""
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT session_id, created_at, report_text, evidence_hash FROM session_report WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if not row:
            return None

        report = SessionReport(
            session_id=row[0],
            created_at=row[1],
            report_text=row[2],
            evidence_hash=row[3],
        )

        check_rows = conn.execute(
            "SELECT check_name, passed, score, evidence_hash, summary, raw_evidence FROM check_result WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()

        for cr in check_rows:
            report.checks.append(
                CheckResult(
                    check_name=cr[0],
                    passed=cr[1],
                    score=cr[2],
                    evidence_hash=cr[3],
                    summary=cr[4],
                    evidence=json.loads(cr[5]),
                )
            )

        return report
    finally:
        conn.close()


def get_check_history(check_name: str, limit: int = 20) -> list[dict[str, Any]]:
    """Get results for one check across sessions (for cross-session patterns)."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT cr.session_id, cr.passed, cr.score, cr.summary, sr.created_at "
            "FROM check_result cr JOIN session_report sr ON cr.session_id = sr.session_id "
            "WHERE cr.check_name = ? ORDER BY sr.created_at DESC LIMIT ?",
            (check_name, limit),
        ).fetchall()
        return [
            {
                "session_id": r[0],
                "passed": r[1],
                "score": r[2],
                "summary": r[3],
                "created_at": r[4],
            }
            for r in rows
        ]
    finally:
        conn.close()
