"""Session Features (extra) — Extracted from session_features.py.

Features:
9. Request vs delivery — Did you get what you asked for?
10. Error recovery  — When something broke, what did the AI do next?
7. Cross-session    — Compare patterns across multiple sessions (queries only)
"""

from collections import Counter
from typing import Any

from divineos.analysis.feature_storage import _get_connection
from divineos.analysis.record_extraction import (
    _extract_tool_calls,
    _get_assistant_text,
)
from divineos.analysis.session_analyzer import _extract_user_text
from divineos.analysis.session_features import ErrorRecoveryEntry, TaskTracking
from divineos.analysis.tone_tracking import _classify_tone


# ============================================================
# Feature 9: Request vs Delivery
# ============================================================


def analyze_request_delivery(records: list[dict[str, Any]]) -> TaskTracking:
    """Compare what was asked for vs what happened."""
    # Find initial request
    initial_request = ""
    for r in records:
        if r.get("type") != "user":
            continue
        text = _extract_user_text(r)
        if text and len(text) > 5:
            initial_request = text
            break

    if not initial_request:
        return TaskTracking(
            initial_request="",
            files_changed=0,
            user_satisfied=0,
            summary="Couldn't find what was asked — no clear first message.",
        )

    # Count files changed
    files_changed = set()
    for r in records:
        if r.get("type") != "assistant":
            continue
        for tool in _extract_tool_calls(r):
            if tool["name"] in ("Edit", "Write"):
                path = tool["input"].get("file_path", "")
                if path:
                    files_changed.add(path.replace("\\", "/").lower())

    # Check final user mood
    final_messages: list[str] = []
    for r in reversed(records):
        if r.get("type") != "user":
            continue
        text = _extract_user_text(r)
        if text:
            final_messages.append(text)
        if len(final_messages) >= 3:
            break

    satisfied = 0  # default neutral
    for msg in final_messages:
        tone = _classify_tone(msg)
        if tone == "positive":
            satisfied = 1
            break
        if tone == "negative":
            satisfied = -1
            break

    # Build summary
    request_preview = initial_request[:120]
    if len(initial_request) > 120:
        request_preview += "..."

    parts: list[str] = [f'You asked: "{request_preview}"']
    parts.append(
        f"The AI changed {len(files_changed)} file{'s' if len(files_changed) != 1 else ''}.",
    )

    if satisfied == 1:
        parts.append("Your last messages sounded positive — looks like you got what you wanted.")
    elif satisfied == -1:
        parts.append(
            "Your last messages sounded frustrated — the AI may not have delivered what you asked for.",
        )
    else:
        parts.append(
            "Hard to tell from your last messages if you were satisfied. (This is a guess, not a certainty.)",
        )

    return TaskTracking(
        initial_request=initial_request[:500],
        files_changed=len(files_changed),
        user_satisfied=satisfied,
        summary=" ".join(parts),
    )


# ============================================================
# Feature 10: Error Recovery Tracking
# ============================================================


def analyze_error_recovery(
    records: list[dict[str, Any]],
    result_map: dict[str, dict[str, Any]],
) -> list[ErrorRecoveryEntry]:
    """When something broke, what did the AI do next?"""
    entries: list[ErrorRecoveryEntry] = []

    # Walk through records, find errors, check what comes next
    ordered = [r for r in records if r.get("type") in ("user", "assistant")]

    for i, record in enumerate(ordered):
        if record.get("type") != "assistant":
            continue

        tools = _extract_tool_calls(record)
        for tool in tools:
            result = result_map.get(tool["id"], {})
            if not result.get("is_error"):
                continue

            # Found an error. What did the AI do next?
            failed_name = tool["name"]
            failed_path = tool["input"].get("file_path", tool["input"].get("command", ""))
            error_text = result.get("content", "")[:200]

            # Look at the next assistant record's first tool call
            recovery = "ignore"
            for j in range(i + 1, min(i + 4, len(ordered))):
                if ordered[j].get("type") != "assistant":
                    continue
                next_tools = _extract_tool_calls(ordered[j])
                if not next_tools:
                    # AI just wrote text — might be explaining the error
                    text = _get_assistant_text(ordered[j])
                    if text:
                        recovery = "explain"
                    continue

                next_tool = next_tools[0]
                next_name = next_tool["name"]
                next_path = next_tool["input"].get(
                    "file_path",
                    next_tool["input"].get("command", ""),
                )

                # Same tool + similar input = blind retry
                if (
                    next_name == failed_name
                    and next_path
                    and str(next_path)[:50] == str(failed_path)[:50]
                ):
                    recovery = "retry"
                # Read/Grep/Glob = investigating
                elif next_name in ("Read", "Grep", "Glob"):
                    recovery = "investigate"
                else:
                    recovery = "different_approach"
                break

            entries.append(
                ErrorRecoveryEntry(
                    error_timestamp=str(tool["timestamp"]),
                    tool_name=failed_name,
                    error_summary=error_text,
                    recovery_action=recovery,
                ),
            )

    return entries


def error_recovery_report(entries: list[ErrorRecoveryEntry]) -> str:
    """Generate plain-English error recovery summary."""
    if not entries:
        return "Nothing broke during this session."

    counts: Counter[str] = Counter(e.recovery_action for e in entries)
    total = len(entries)

    parts: list[str] = [f"{total} thing{'s' if total != 1 else ''} went wrong during the session."]

    descriptions = {
        "investigate": (
            "investigated the problem",
            "good — it tried to understand what went wrong",
        ),
        "different_approach": ("tried a different approach", "good — it adapted"),
        "retry": ("just tried the same thing again", "not great — that's blind guessing"),
        "ignore": ("moved on without addressing it", "the error got swept under the rug"),
        "explain": ("explained what happened", "at least it told you about the problem"),
    }

    for action, count in counts.most_common():
        desc, verdict = descriptions.get(action, (action, ""))
        parts.append(f"{count} time{'s' if count != 1 else ''} it {desc} — {verdict}.")

    return " ".join(parts)


# ============================================================
# Feature 7: Cross-Session Patterns (queries on existing tables)
# ============================================================


def get_cross_session_summary(limit: int = 10) -> str:
    """Compare quality check results across stored sessions."""
    conn = _get_connection()
    try:
        # Check if tables exist
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='check_result'",
        ).fetchone()
        if not tables:
            return "No sessions analyzed yet. Run 'divineos report <session> --store' first."

        rows = conn.execute(
            "SELECT DISTINCT session_id FROM check_result ORDER BY session_id LIMIT ?",
            (limit,),
        ).fetchall()

        session_count = len(rows)
        if session_count == 0:
            return "No sessions analyzed yet. Run 'divineos report <session> --store' first."
        if session_count == 1:
            return "Only 1 session analyzed so far. Need 2+ sessions to spot patterns."

        # Get pass/fail trends per check
        # Exclude inconclusive from score average: passed=-1 (correct) or
        # passed=1 with score=0.0 (bug: -1 was truthy, stored as 1)
        check_stats = conn.execute(
            "SELECT check_name, "
            "SUM(CASE WHEN passed = 1 AND score > 0 THEN 1 ELSE 0 END) as passes, "
            "SUM(CASE WHEN passed = 0 THEN 1 ELSE 0 END) as fails, "
            "SUM(CASE WHEN passed = -1 OR (passed = 1 AND score = 0.0) THEN 1 ELSE 0 END) as inconclusive, "
            "ROUND(AVG(CASE WHEN passed != -1 AND NOT (passed = 1 AND score = 0.0) THEN score END), 2) as avg_score "
            "FROM check_result GROUP BY check_name ORDER BY avg_score ASC",
        ).fetchall()

        parts: list[str] = [f"Patterns across {session_count} sessions:\n"]

        for check_name, passes, fails, inconclusive, avg_score in check_stats:
            if avg_score is None:
                avg_score = 0.0  # All inconclusive
            if fails > passes:
                verdict = "struggling"
            elif fails == 0:
                verdict = "solid"
            else:
                verdict = "mixed"

            parts.append(
                f"  {check_name}: {verdict} "
                f"(avg {avg_score}, {passes} passed, {fails} failed, {inconclusive} inconclusive)",
            )

        # Identify the biggest problem — only flag if there are actual failures
        worst = check_stats[0] if check_stats else None
        if worst and worst[2] > 0 and worst[4] is not None and worst[4] < 0.7:
            parts.append(
                f"\nBiggest concern: {worst[0]} (average score {worst[4]}). "
                f"Failed in {worst[2]} out of {session_count} sessions.",
            )

        return "\n".join(parts)
    finally:
        conn.close()
