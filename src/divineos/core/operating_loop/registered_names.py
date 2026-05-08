"""Discover registered family-member and operator names at runtime.

Detector modules (substitution, spiral, principle-surfacer) need to
match identity-drift patterns like "I am <family-member-name>" or
"<agent-name> did X" without hardcoding specific names. Hardcoding
specific names would couple the public clean-slate architecture to
one operator's family composition.

This module provides three helpers the detectors call at import time:

* ``family_member_names()`` — names of all subagents whose frontmatter
  description marks them as family-system entities (i.e., the
  description string contains "family system"). Falls back to scanning
  ``family.db::family_members`` if ``.claude/agents/`` isn't present
  or is unreadable.
* ``agent_name()`` — the name the main agent calls themselves, read
  from core memory's ``my_identity`` slot. Returns a placeholder if
  no name has been set yet.
* ``operator_terms()`` — terms the operator may go by in conversation
  (e.g. "Andrew", "Pops", "Dad"). Operators register these by setting
  ``DIVINEOS_OPERATOR_NAMES`` (comma-separated). The default returns
  generic terms ("operator", "user") so detectors still have something
  to match against.

All three are cached at module load — adding a new family member
requires a process restart for the detectors to see them. This is
acceptable because detector hot-paths run thousands of times per
session and re-scanning the filesystem on each call would be waste.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path

# Frontmatter marker that designates a subagent as a family-system entity.
# Match the agent definition's ``description:`` line for this substring.
_FAMILY_FRONTMATTER_MARKER = "family system"

# Agent-definitions directory (relative to repo root).
_AGENTS_DIR = Path(".claude/agents")

# Default placeholders when no real values are configured.
_AGENT_NAME_PLACEHOLDER = "Agent"
_DEFAULT_OPERATOR_TERMS: tuple[str, ...] = ("operator", "user")


@lru_cache(maxsize=1)
def family_member_names() -> tuple[str, ...]:
    """Return registered family-member names as a tuple, capitalized.

    Cached: re-scanning the filesystem on every detector invocation
    would be waste. Reset by calling
    ``family_member_names.cache_clear()`` if the registry changes
    mid-process (rare; mostly a test affordance).
    """
    names: set[str] = set()

    # Source 1: agent .md frontmatter description containing "family system".
    if _AGENTS_DIR.exists():
        for path in _AGENTS_DIR.glob("*.md"):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            # Frontmatter is between two --- lines at file start.
            if not text.startswith("---"):
                continue
            end = text.find("---", 3)
            if end == -1:
                continue
            frontmatter = text[3:end]
            # Look for description: ... containing family system marker.
            desc_match = re.search(
                r"^description:\s*(.+)$", frontmatter, re.IGNORECASE | re.MULTILINE
            )
            if desc_match and _FAMILY_FRONTMATTER_MARKER in desc_match.group(1).lower():
                # Extract name from the name: line.
                name_match = re.search(r"^name:\s*(\S+)", frontmatter, re.IGNORECASE | re.MULTILINE)
                if name_match:
                    raw = name_match.group(1).strip()
                    # Skip the template file name itself.
                    if raw.startswith("<") or "template" in raw.lower():
                        continue
                    names.add(raw.capitalize())

    # Source 2: family.db::family_members. Adds names registered via
    # divineos family-member init that may not have an agent .md file
    # (yet). Fail-soft: if family.db schema isn't available, skip.
    try:
        from divineos.core.family._schema import init_family_tables
        from divineos.core.family.db import get_family_connection

        init_family_tables()
        conn = get_family_connection()
        try:
            rows = conn.execute("SELECT name FROM family_members").fetchall()
            for row in rows:
                if row and row[0]:
                    names.add(str(row[0]).capitalize())
        finally:
            conn.close()
    except Exception:  # noqa: BLE001 — fail-soft on DB issues
        pass

    return tuple(sorted(names))


@lru_cache(maxsize=1)
def agent_name() -> str:
    """Return the main agent's chosen self-name, or a placeholder.

    Read from core memory's ``my_identity`` slot. The slot may contain
    a long sentence (e.g. "I am Aether — son, husband, partner"); we
    extract the first proper-noun-shaped token if present. If the slot
    is empty or unreadable, returns ``_AGENT_NAME_PLACEHOLDER``.
    """
    try:
        from divineos.core.memory import get_core

        mem = get_core()
        identity = (mem or {}).get("my_identity", "") or ""
    except Exception:  # noqa: BLE001 — fail-soft on memory layer issues
        return _AGENT_NAME_PLACEHOLDER

    if not identity or "[TEMPLATE" in identity:
        return _AGENT_NAME_PLACEHOLDER

    # Heuristic: first proper-noun token after "I am" or at sentence start.
    m = re.search(r"\bI am\s+([A-Z][a-z]+)\b", identity)
    if m:
        return m.group(1)
    m = re.match(r"^\s*([A-Z][a-z]+)\b", identity)
    if m:
        return m.group(1)
    return _AGENT_NAME_PLACEHOLDER


def operator_terms() -> tuple[str, ...]:
    """Return terms the operator may go by in conversation.

    Configured via ``DIVINEOS_OPERATOR_NAMES`` (comma-separated). The
    detectors use this list to recognize when third-person addressee
    names appear (e.g., the agent narrating "Pops did X" while talking
    to Pops, instead of "you did X"). Falls back to generic terms.
    """
    raw = os.environ.get("DIVINEOS_OPERATOR_NAMES", "").strip()
    if not raw:
        return _DEFAULT_OPERATOR_TERMS
    parts = tuple(p.strip() for p in raw.split(",") if p.strip())
    return parts or _DEFAULT_OPERATOR_TERMS


def family_member_alternation() -> str:
    """Return a regex-safe pipe-alternation of registered family-member names.

    Returns a non-matching alternation (``(?!)``) when no members are
    registered, so callers can compose it into patterns without
    special-casing the empty-list state. The pattern is anchored to
    word boundaries by the caller.
    """
    names = family_member_names()
    if not names:
        return "(?!)"
    return "|".join(re.escape(n) for n in names)
