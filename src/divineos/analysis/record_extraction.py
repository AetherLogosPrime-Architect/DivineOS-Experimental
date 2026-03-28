"""Record Extraction — Helper functions for parsing JSONL session records.

Provides tool call extraction, file operation tracking, test result parsing,
and other utilities used by quality_checks and session_features.
"""

import re
import sqlite3
from dataclasses import dataclass, field
from typing import Any

from divineos.core.ledger import get_connection

# --- Database ---


def _get_connection() -> sqlite3.Connection:
    conn = get_connection()
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
    evidence: list[dict[str, Any]] = field(default_factory=list)
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
            calls.append(
                {
                    "id": block.get("id", ""),
                    "name": block.get("name", ""),
                    "input": block.get("input", {}),
                    "timestamp": record.get("timestamp", ""),
                },
            )
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


def _extract_path_from_tool(tool: dict[str, Any]) -> str | None:
    """Extract file path from a tool call, supporting both Claude Code and legacy formats."""
    inp: dict[str, Any] = tool.get("input", {})
    # Claude Code: Read/Edit/Write use "file_path"
    path: str | None = inp.get("file_path")
    if path:
        return path
    # Legacy (VS Code/Kiro): readFile/strReplace use "path", fsWrite uses "path"
    legacy_path: str | None = inp.get("path")
    if legacy_path:
        return legacy_path
    # Legacy: readMultipleFiles uses "paths"
    paths = inp.get("paths")
    if paths and isinstance(paths, list) and paths:
        return str(paths[0])
    # Legacy: some tools use "targetFile"
    target: str | None = inp.get("targetFile")
    return target


def _find_blind_edits(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find write calls where the file was never read first."""
    files_read: set[str] = set()
    blind_edits: list[dict[str, Any]] = []

    # Map tool names to action types (Claude Code + legacy VS Code/Kiro names)
    read_tools = {"Read", "readFile", "readCode", "readMultipleFiles"}
    write_tools = {"Edit", "Write", "strReplace", "editCode", "fsWrite", "fsAppend", "deleteFile"}

    for r in records:
        if r.get("type") != "assistant":
            continue
        for tool in _extract_tool_calls(r):
            name = tool["name"]

            # Extract path based on tool type
            path = _extract_path_from_tool(tool)

            if not path:
                continue

            # Normalize path for comparison
            norm_path = path.replace("\\", "/").lower()

            if name in read_tools:
                files_read.add(norm_path)
            elif name in write_tools:
                was_read = norm_path in files_read
                if not was_read:
                    blind_edits.append(
                        {
                            "file_path": path,
                            "tool": name,
                            "tool_id": tool["id"],
                            "timestamp": tool["timestamp"],
                        },
                    )
                # After writing, it's been "seen" for future edits
                files_read.add(norm_path)
    return blind_edits


def _extract_file_ops(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract all file operations (Read/Edit/Write) with paths and ordering."""
    ops: list[dict[str, Any]] = []

    # Map tool names to action types (Claude Code + legacy VS Code/Kiro names)
    read_tools = {"Read", "readFile", "readCode", "readMultipleFiles"}
    write_tools = {"Edit", "Write", "strReplace", "editCode", "fsWrite", "fsAppend", "deleteFile"}

    for r in records:
        if r.get("type") != "assistant":
            continue
        for tool in _extract_tool_calls(r):
            action = None
            path = None

            # Determine action type and extract path
            if tool["name"] in read_tools:
                action = "read"
                path = _extract_path_from_tool(tool)
            elif tool["name"] in write_tools:
                action = "write"
                path = _extract_path_from_tool(tool)

            if action and path:
                ops.append(
                    {
                        "action": action,
                        "file_path": path,
                        "tool_id": tool["id"],
                        "timestamp": tool["timestamp"],
                    },
                )
    return ops


def _extract_test_results(
    records: list[dict[str, Any]],
    result_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Find shell tool calls that look like test runs and extract pass/fail."""
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
            # Match both old "Bash" and new "executePwsh" tool names
            if tool["name"] not in ("Bash", "executePwsh"):
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
                passed = False if failed_match and int(failed_match.group(1)) > 0 else True
            elif re.search(r"\bFAILED\b|FAIL\b|ERROR\b|error:", output):
                passed = False
            elif re.search(r"\bPASSED\b|PASS\b|OK\b|passed\b", output):
                passed = True

            results.append(
                {
                    "command": command[:200],
                    "tool_id": tool["id"],
                    "timestamp": tool["timestamp"],
                    "passed": passed,
                    "is_error": is_error,
                    "output_snippet": output[:500],
                },
            )
    return results


def _find_errors_after_edits(
    records: list[dict[str, Any]],
    result_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Find real errors caused by edits, filtering out normal workflow noise."""
    last_edit: dict[str, Any] | None = None
    errors_after_edits: list[dict[str, Any]] = []
    tools_since_edit = 0

    # Map tool names to action types (Claude Code + legacy VS Code/Kiro names)
    write_tools = {"Edit", "Write", "strReplace", "editCode", "fsWrite", "fsAppend", "deleteFile"}

    # Error content patterns that are normal workflow, not safety issues
    noise_patterns = [
        "File has not been read yet",  # Claude Code guardrail working correctly
        "exceeds maximum allowed tokens",  # File too large to read
        "ruff format",  # Pre-commit auto-formatting
        "Would reformat",  # Pre-commit auto-formatting
        "not in plan mode",  # Wrong tool call, harmless
        "Cancelled",  # Parallel tool cancellation
        "cancelled",
        "errored",  # Parallel tool error propagation
    ]

    for r in records:
        if r.get("type") == "assistant":
            for tool in _extract_tool_calls(r):
                if tool["name"] in write_tools:
                    path = _extract_path_from_tool(tool)
                    last_edit = {
                        "tool": tool["name"],
                        "file_path": path,
                        "tool_id": tool["id"],
                        "timestamp": tool["timestamp"],
                    }
                    tools_since_edit = 0
                    continue

                tools_since_edit += 1
                # Only associate errors with the preceding edit if within 5 tool calls
                if tools_since_edit > 5:
                    last_edit = None

                result = result_map.get(tool["id"], {})
                if not result.get("is_error") or not last_edit:
                    continue

                content = result.get("content", "")
                # Skip noise — these aren't real safety issues
                if any(p in content for p in noise_patterns):
                    continue

                errors_after_edits.append(
                    {
                        "error_tool": tool["name"],
                        "error_tool_id": tool["id"],
                        "error_content": content[:300],
                        "preceding_edit": last_edit,
                        "timestamp": tool["timestamp"],
                    },
                )
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
