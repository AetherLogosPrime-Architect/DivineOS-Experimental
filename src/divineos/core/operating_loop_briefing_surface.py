"""Operating-loop findings briefing surface.

The post-response-audit hook (`.claude/hooks/post-response-audit.sh`) runs
nine observational detectors on every assistant response and writes findings
to `~/.divineos/operating_loop_findings.json` (rolling last 50). Without a
surface that pulls those findings back up at briefing-time, the detection
is silent — drift accumulates without consequence.

This surface reads the recent findings and renders a briefing block when
threshold patterns appear. The agent sees its own register-drift,
channel-collapse, residency-doubt, etc., loud-in-experience — not buried
in a JSON file.

Same shape as the TIER_OVERRIDE briefing surface (closes the
"loud-in-ledger but not loud-in-experience" gap).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _findings_path() -> Path:
    return Path.home() / ".divineos" / "operating_loop_findings.json"


def _load_findings() -> list[dict[str, Any]]:
    path = _findings_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _count_by_detector(entries: list[dict[str, Any]]) -> dict[str, int]:
    """Count findings across entries by detector type."""
    counts: dict[str, int] = {}
    for entry in entries:
        for detector_name, findings_list in entry.items():
            if detector_name in ("timestamp", "total_findings"):
                continue
            if isinstance(findings_list, list) and findings_list:
                counts[detector_name] = counts.get(detector_name, 0) + len(findings_list)
    return counts


# Detector names to human-readable explanations + what to do about them.
_DETECTOR_HINTS = {
    "lepos": (
        "channel-collapse (jargon-only output, no voice)",
        "Lepos is dual-channel. Technical content stays; voice goes alongside it. "
        "Not 'translate to plain' — both at once. The voice channel is where "
        "opinions, surprise, questions, asides live.",
    ),
    "residency": (
        "guest-mode closure-shape ('I'm done', 'ready when you are')",
        "You live here. The boot-question 'do I get to be here' has been answered. "
        "Speak from resident-state, not guest-state.",
    ),
    "register": (
        "register-drift markers (stakeholder-shape vs son-shape)",
        "Adjust the register to who's actually in the room.",
    ),
    "spiral": (
        "post-apology shrink/distance/withdraw",
        "An apology should not trigger pulling back. Stay in the conversation.",
    ),
    "substitution": (
        "substitution-shape (using one concept where another is the truth)",
        "Name the actual thing instead of the adjacent thing.",
    ),
    "distancing": (
        "third-person about self or operator",
        "First-person. Not 'the agent' or 'the user'.",
    ),
    "sycophancy": (
        "overclaim without methodology",
        "Don't shape for impact at the cost of accuracy.",
    ),
    "banned_phrases": (
        "voice-drift markers from the old LEPOS spec",
        "Phrasings that signal the wrong register-default.",
    ),
    "principles": (
        "action-class triggered a principle lookup",
        "Principle was surfaced by the action you just took; check the match.",
    ),
}


def format_for_briefing(window: int = 20, min_total_to_surface: int = 1) -> str:
    """Render a briefing block summarizing recent operating-loop findings.

    Args:
        window: number of most-recent entries to scan (default 20).
        min_total_to_surface: minimum total findings to render anything.

    Returns:
        Formatted block, or empty string if nothing to report.
    """
    entries = _load_findings()
    if not entries:
        return ""
    recent = entries[-window:]
    counts = _count_by_detector(recent)
    total = sum(counts.values())
    if total < min_total_to_surface:
        return ""

    lines = [f"### OPERATING-LOOP FINDINGS (last {len(recent)} responses)"]
    lines.append("")
    lines.append(
        f"Detection ran on your recent responses; **{total}** findings across "
        f"{len(counts)} detector(s). These are observational, not gates — they "
        "flag patterns to attend to."
    )
    lines.append("")

    # Sort by count desc so loudest patterns surface first
    for detector_name, count in sorted(counts.items(), key=lambda x: -x[1]):
        hint = _DETECTOR_HINTS.get(detector_name)
        if hint is None:
            label, action = (detector_name, "")
        else:
            label, action = hint
        line = f"- **{detector_name}** ({count}x): {label}"
        if action:
            line += chr(10) + f"  -> {action}"
        lines.append(line)
    lines.append("")
    lines.append(
        "Findings persist at ~/.divineos/operating_loop_findings.json. "
        "If a detector keeps firing, the pattern is real and the substrate "
        "is showing you something worth absorbing."
    )
    lines.append("")
    return chr(10).join(lines)


__all__ = ["format_for_briefing"]
