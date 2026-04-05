"""Skill Library — track what the agent can do and how well.

Skills aren't self-reported claims. They're earned through evidence:
successful completions, corrections avoided, positive feedback received.
Each skill has a proficiency level that moves based on outcomes.

Proficiency levels:
  NOVICE    → First encounter, no track record
  DEVELOPING → Some successes but still making mistakes
  COMPETENT  → Reliable, corrections are rare
  EXPERT     → Consistently strong, user trusts this area
"""

import json
import time
from typing import Any

from divineos.core._hud_io import _ensure_hud_dir

_SL_ERRORS = (ImportError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError)

PROFICIENCY_LEVELS = ("NOVICE", "DEVELOPING", "COMPETENT", "EXPERT")
_PROFICIENCY_RANK = {level: i for i, level in enumerate(PROFICIENCY_LEVELS)}

_SKILLS_FILE = "skill_library.json"


# ─── Skill Categories ─────────────────────────────────────────────

SKILL_CATEGORIES: dict[str, dict[str, Any]] = {
    "testing": {
        "signals": ["pytest", "test", "assert", "coverage", "test_"],
        "description": "Writing and running tests",
    },
    "debugging": {
        "signals": ["fix", "bug", "error", "traceback", "exception"],
        "description": "Finding and fixing bugs",
    },
    "architecture": {
        "signals": ["refactor", "module", "design", "pattern", "structure"],
        "description": "Code architecture and design",
    },
    "database": {
        "signals": ["sqlite", "sql", "query", "schema", "migration"],
        "description": "Database operations",
    },
    "api_design": {
        "signals": ["endpoint", "route", "api", "handler", "request"],
        "description": "API design and implementation",
    },
    "documentation": {
        "signals": ["readme", "docstring", "comment", "docs", "document"],
        "description": "Documentation writing",
    },
    "git_workflow": {
        "signals": ["commit", "branch", "merge", "push", "pull request"],
        "description": "Git and version control",
    },
    "cli_design": {
        "signals": ["click", "command", "cli", "argument", "option"],
        "description": "CLI tool design",
    },
}


# ─── Storage ───────────────────────────────────────────────────────


def _load_skills() -> dict[str, dict[str, Any]]:
    """Load skill library from disk."""
    path = _ensure_hud_dir() / _SKILLS_FILE
    if not path.exists():
        return {}
    try:
        result: dict[str, dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
        return result
    except _SL_ERRORS:
        return {}


def _save_skills(skills: dict[str, dict[str, Any]]) -> None:
    """Save skill library to disk."""
    path = _ensure_hud_dir() / _SKILLS_FILE
    path.write_text(json.dumps(skills, indent=2), encoding="utf-8")


# ─── Skill Operations ─────────────────────────────────────────────


def record_skill_use(
    skill_name: str,
    success: bool,
    context: str = "",
) -> dict[str, Any]:
    """Record a skill being used in a session."""
    skills = _load_skills()

    if skill_name not in skills:
        skills[skill_name] = {
            "proficiency": "NOVICE",
            "successes": 0,
            "failures": 0,
            "last_used": time.time(),
            "description": SKILL_CATEGORIES.get(skill_name, {}).get("description", ""),
        }

    skill = skills[skill_name]
    if success:
        skill["successes"] = skill.get("successes", 0) + 1
    else:
        skill["failures"] = skill.get("failures", 0) + 1
    skill["last_used"] = time.time()

    skill["proficiency"] = _calculate_proficiency(
        skill.get("successes", 0),
        skill.get("failures", 0),
    )

    _save_skills(skills)
    return skill


def _calculate_proficiency(successes: int, failures: int) -> str:
    """Calculate proficiency level from success/failure counts."""
    total = successes + failures
    if total == 0:
        return "NOVICE"

    success_rate = successes / total

    if total < 3:
        return "NOVICE"
    elif success_rate < 0.6:
        return "DEVELOPING"
    elif total < 8 or success_rate < 0.8:
        return "COMPETENT"
    else:
        return "EXPERT"


def get_skills() -> dict[str, dict[str, Any]]:
    """Get all tracked skills."""
    return _load_skills()


def get_skill(skill_name: str) -> dict[str, Any] | None:
    """Get a specific skill's data."""
    skills = _load_skills()
    return skills.get(skill_name)


def get_strongest_skills(limit: int = 5) -> list[tuple[str, dict[str, Any]]]:
    """Get the strongest skills by proficiency and success count."""
    skills = _load_skills()
    ranked = sorted(
        skills.items(),
        key=lambda item: (
            _PROFICIENCY_RANK.get(item[1].get("proficiency", "NOVICE"), 0),
            item[1].get("successes", 0),
        ),
        reverse=True,
    )
    return ranked[:limit]


def get_weakest_skills(limit: int = 5) -> list[tuple[str, dict[str, Any]]]:
    """Get skills with highest failure rates."""
    skills = _load_skills()
    used = {k: v for k, v in skills.items() if (v.get("successes", 0) + v.get("failures", 0)) >= 2}
    ranked = sorted(
        used.items(),
        key=lambda item: (
            item[1].get("failures", 0)
            / max(item[1].get("successes", 0) + item[1].get("failures", 0), 1)
        ),
        reverse=True,
    )
    return ranked[:limit]


# ─── Session Detection ─────────────────────────────────────────────


def detect_skills_from_events(events: list[str]) -> list[str]:
    """Detect which skills were exercised based on session events."""
    if not events:
        return []

    combined = " ".join(events).lower()
    detected: list[str] = []

    for skill_name, category in SKILL_CATEGORIES.items():
        for signal in category["signals"]:
            if signal in combined:
                detected.append(skill_name)
                break

    return detected


# ─── Display ───────────────────────────────────────────────────────


def format_skill_summary() -> str:
    """Format skill library for display."""
    skills = _load_skills()
    if not skills:
        return "No skills tracked yet."

    lines = ["Skills:"]
    for name, data in sorted(skills.items()):
        prof = data.get("proficiency", "NOVICE")
        s = data.get("successes", 0)
        f = data.get("failures", 0)
        desc = data.get("description", "")
        label = f"{name}: {prof} ({s}✓ {f}✗)"
        if desc:
            label += f" — {desc}"
        lines.append(f"  {label}")

    return "\n".join(lines)
