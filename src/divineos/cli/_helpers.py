"""Shared CLI helpers — safe echo, auto-classify, resolve IDs, event display."""

import os
import re
from datetime import datetime, timezone
from typing import Any
import sqlite3

import click

from divineos.core.memory import TYPOGRAPHIC_REPLACEMENTS as _TYPOGRAPHIC_REPLACEMENTS

_HELPERS_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)

_EMOJI_MEANINGS: dict[str, str] = {
    "\U0001f614": "(upset)",
    "\U0001f622": "(crying)",
    "\U0001f62d": "(sobbing)",
    "\U0001f620": "(angry)",
    "\U0001f621": "(furious)",
    "\U0001f610": "(neutral)",
    "\U0001f642": "(smile)",
    "\U0001f600": "(grinning)",
    "\U0001f601": "(beaming)",
    "\U0001f603": "(happy)",
    "\U0001f604": "(laughing)",
    "\U0001f605": "(laughing nervously)",
    "\U0001f606": "(laughing hard)",
    "\U0001f609": "(wink)",
    "\U0001f60a": "(warm smile)",
    "\U0001f60d": "(heart eyes)",
    "\U0001f60e": "(cool)",
    "\U0001f60f": "(smirk)",
    "\U0001f612": "(unamused)",
    "\U0001f615": "(confused)",
    "\U0001f616": "(frustrated)",
    "\U0001f618": "(kiss)",
    "\U0001f61b": "(tongue out)",
    "\U0001f61c": "(playful wink)",
    "\U0001f61e": "(disappointed)",
    "\U0001f624": "(frustrated)",
    "\U0001f625": "(relieved)",
    "\U0001f629": "(weary)",
    "\U0001f62b": "(tired)",
    "\U0001f62e": "(surprised)",
    "\U0001f631": "(screaming)",
    "\U0001f633": "(flushed)",
    "\U0001f634": "(sleeping)",
    "\U0001f637": "(sick)",
    "\U0001f641": "(frown)",
    "\U0001f643": "(upside-down smile)",
    "\U0001f644": "(eye roll)",
    "\U0001f914": "(thinking)",
    "\U0001f917": "(hug)",
    "\U0001f923": "(rolling on floor laughing)",
    "\U0001f929": "(starstruck)",
    "\U0001f92f": "(mind blown)",
    "\U0001f970": "(adoring)",
    "\U0001f973": "(party)",
    "\U0001f97a": "(pleading)",
    "\U0001f44d": "(thumbs up)",
    "\U0001f44e": "(thumbs down)",
    "\U0001f44f": "(clapping)",
    "\U0001f389": "(celebration)",
    "\U0001f38a": "(confetti)",
    "\U0001f525": "(fire)",
    "\U0001f4af": "(100%)",
    "\u2764\ufe0f": "(love)",
    "\u2764": "(love)",
    "\U0001f499": "(blue heart)",
    "\U0001f49a": "(green heart)",
    "\U0001f49c": "(purple heart)",
    "\U0001f680": "(rocket)",
    "\u2705": "(checkmark)",
    "\u274c": "(X)",
    "\u26a0\ufe0f": "(warning)",
    "\u26a0": "(warning)",
}


def _safe_echo(text: str, **kwargs: Any) -> None:
    """click.echo that won't crash on Windows with Unicode characters."""
    if os.name == "nt":
        for emoji, meaning in _EMOJI_MEANINGS.items():
            text = text.replace(emoji, meaning)
        for fancy, plain in _TYPOGRAPHIC_REPLACEMENTS.items():
            text = text.replace(fancy, plain)
        text = text.encode("cp1252", errors="replace").decode("cp1252")
    click.echo(text, **kwargs)


def _auto_classify(content: str) -> tuple[str, str]:
    """Auto-classify knowledge type from content text.

    Returns (type, reason) so the user can see why.
    """
    lower = content.lower()
    rules: list[tuple[str, str, str]] = [
        (
            r"\b(never|always|must not|do not|don't|cannot|forbidden)\b",
            "BOUNDARY",
            "constraint language",
        ),
        (
            r"\b(step \d|how to|first.*then|process|workflow|procedure)\b",
            "PROCEDURE",
            "process/how-to language",
        ),
        (r"\b(use |prefer |default to |keep |avoid )\b", "DIRECTION", "preference language"),
        (
            r"\b(is located|version |database |path |file |count |total )\b",
            "FACT",
            "factual language",
        ),
        (
            r"\b(noticed|found that|discovered|turns out|apparently)\b",
            "OBSERVATION",
            "observation language",
        ),
    ]
    for pattern, ktype, reason in rules:
        if re.search(pattern, lower):
            return ktype, reason
    return "PRINCIPLE", "general knowledge (no specific pattern matched)"


def _resolve_knowledge_id(partial: str) -> str:
    """Resolve a partial knowledge ID to a full one."""
    if not partial.strip():
        raise click.ClickException("Please provide a knowledge ID (or partial ID)")
    from divineos.core.knowledge import _get_connection

    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT knowledge_id, knowledge_type, content FROM knowledge"
            " WHERE knowledge_id LIKE ? AND superseded_by IS NULL",
            (f"{partial}%",),
        ).fetchall()
    finally:
        conn.close()

    if len(rows) == 0:
        raise click.ClickException(f"No knowledge entry matching '{partial}'")
    if len(rows) > 1:
        click.secho(f"Ambiguous ID '{partial}' matches {len(rows)} entries:\n", fg="yellow")
        for kid, ktype, content in rows:
            preview = (content[:60] + "...") if len(content) > 60 else content
            preview = preview.replace("\n", " ")
            click.echo(f"  {kid[:12]}  [{ktype}]  {preview}")
        raise click.ClickException("Use more characters to narrow it down")
    result: str = rows[0][0]
    return result


def _display_and_store_analysis(result: Any) -> None:
    """Format, display, store, and save an analysis result."""
    from divineos.analysis.analysis import (
        format_analysis_report,
        save_analysis_report,
        store_analysis,
    )
    from divineos.core.ledger import logger

    report = format_analysis_report(result)

    click.echo()
    _safe_echo(report)
    click.echo()

    click.secho("[+] Storing analysis in database...", fg="cyan")
    try:
        stored = store_analysis(result, report)
        if stored:
            click.secho("[+] Analysis stored successfully.", fg="green")
    except _HELPERS_ERRORS as e:
        click.secho(f"[!] Warning: Analysis storage failed: {e}", fg="yellow")
        logger.warning(f"Storage failed: {e}")

    report_file = save_analysis_report(result, report)
    click.secho(f"[+] Report saved to: {report_file}", fg="green")

    click.secho(f"[+] Analysis complete. Session ID: {result.session_id}", fg="green")
    click.echo()


def _log_os_query(tool: str, query: str = "") -> None:
    """Log an OS_QUERY event and mark the session as engaged."""
    from divineos.core.hud_handoff import mark_engaged

    from divineos.cli._wrappers import _wrapped_log_event

    _wrapped_log_event(
        event_type="OS_QUERY",
        actor="assistant",
        payload={"tool": tool, "query": query},
    )
    mark_engaged()


def _role_to_event_type(role: str) -> str:
    """Convert message role to event type."""
    mapping = {
        "user": "USER_INPUT",
        "assistant": "ASSISTANT_OUTPUT",
        "system": "SYSTEM_PROMPT",
        "tool_call": "TOOL_CALL",
        "tool_result": "TOOL_RESULT",
    }
    return mapping.get(role.lower(), "MESSAGE")


def _summarize_event(etype: str, payload: dict[str, Any]) -> str:
    """Produce a human-readable one-liner from an event payload."""
    if "content" in payload and isinstance(payload["content"], str):
        return payload["content"]

    if etype == "SESSION_END":
        dur = payload.get("duration_seconds", 0)
        msgs = payload.get("message_count", 0)
        tools = payload.get("tool_call_count", 0)
        return f"{msgs} messages, {tools} tool calls, {dur:.0f}s"

    if etype == "TOOL_CALL":
        name = payload.get("tool_name", "?")
        inp = payload.get("tool_input", {})
        detail = str(inp.get("file_path") or inp.get("command") or inp.get("pattern") or "")
        if detail:
            return f"{name}({detail[:80]})"
        return str(name)

    if etype == "TOOL_RESULT":
        name = payload.get("tool_name", "?")
        dur = payload.get("duration_ms", 0)
        failed = payload.get("failed", False)
        result = str(payload.get("result", ""))[:120]
        status = "FAILED" if failed else "ok"
        return f"{name} → {status} ({dur:.0f}ms) {result}"

    if etype == "USER_INPUT":
        return str(payload.get("text", payload.get("content", "")))

    if etype in ("ASSISTANT_OUTPUT", "ASSISTANT_RESPONSE", "ASSISTANT"):
        text = str(payload.get("text", payload.get("content", "")))
        return text[:200] if text else "(empty response)"

    if etype == "AGENT_DECISION":
        task = payload.get("task", "?")
        pattern = payload.get("chosen_pattern", "?")
        return f"Decision: {task[:80]} → pattern {pattern[:40]}"

    if etype == "AGENT_LEARNING_AUDIT":
        drift = payload.get("drift_detected", False)
        gaps = len(payload.get("pattern_gaps", []))
        return f"Learning audit: drift={'yes' if drift else 'no'}, {gaps} pattern gaps"

    if etype == "AGENT_CONTEXT_COMPRESSION":
        return str(payload.get("content", "context compressed"))

    if etype == "CLARITY_SUMMARY":
        score = payload.get("alignment_score", "?")
        devs = payload.get("deviations_count", 0)
        lessons = payload.get("lessons_count", 0)
        return f"Alignment: {score:.0f}%, {devs} deviations, {lessons} lessons"

    if etype == "CLARITY_DEVIATION":
        metric = payload.get("metric", "?")
        planned = payload.get("planned", "?")
        actual = payload.get("actual", "?")
        severity = payload.get("severity", "?")
        return f"{severity} deviation in {metric}: planned {planned}, actual {actual}"

    if etype == "CLARITY_LESSON":
        desc = payload.get("description", "")
        ltype = payload.get("lesson_type", "")
        return f"[{ltype}] {desc}" if desc else etype

    if etype.startswith("CLARITY_"):
        return str(payload.get("content", payload.get("summary", etype)))

    if etype == "QUALITY_REPORT":
        score = payload.get("overall_score", "?")
        return f"Quality score: {score}"

    # Fallback: show first meaningful field values
    skip = {"content_hash", "session_id", "timestamp", "tool_use_id"}
    parts = []
    for k, v in payload.items():
        if k in skip:
            continue
        sv = str(v)
        if len(sv) > 80:
            sv = sv[:80] + "..."
        parts.append(f"{k}={sv}")
        if len(parts) >= 3:
            break
    return ", ".join(parts) if parts else "(empty payload)"


def _print_events(events: list[dict[str, Any]], highlight: str | None = None) -> None:
    """Pretty-print a list of events with optional keyword highlighting."""
    for event in events:
        ts = event["timestamp"]
        try:
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except (ValueError, OSError, TypeError):
            time_str = str(ts)

        actor = event["actor"].upper()
        etype = event["event_type"]
        payload = event["payload"]
        content_hash = event.get("content_hash", "")[:8]

        click.secho(f"[{time_str}] ", fg="bright_black", nl=False)
        click.secho(f"{etype} ", fg="white", bold=True, nl=False)
        click.secho(f"({actor}) ", fg="bright_black", nl=False)
        click.secho(f"[{content_hash}]", fg="bright_black")

        content = _summarize_event(etype, payload)
        max_len = 300
        if len(content) > max_len:
            content = content[:max_len] + "..."

        if highlight:
            pattern = re.compile(re.escape(highlight), re.IGNORECASE)
            parts = pattern.split(content)
            matches = pattern.findall(content)
            for i, part in enumerate(parts):
                _safe_echo(part, nl=False)
                if i < len(matches):
                    click.secho(matches[i], fg="red", bold=True, nl=False)
            click.echo()
        else:
            color = {"USER": "blue", "ASSISTANT": "magenta", "SYSTEM": "yellow"}.get(actor, "white")
            _safe_echo(click.style(f"  {content}", fg=color))

        click.echo(click.style("-" * 60, fg="bright_black"))
