"""Auto-goal derivation from user prompts.

Memory-expansion mechanism (Andrew 2026-07-24): the goal-doorman keeps
firing because I keep forgetting to set a goal before substrate-work.
The forgetting isn't an optimizer issue, it's a memory issue. Automation
solves memory by not requiring me to remember.

This module derives a plausible goal-text from the user's most recent
prompt when work-shape intent is detected, so the goal exists by the
time the PreToolUse gate checks for it. My cognition stops spending
attention on the meta-question "did I remember to set the goal" and
becomes free for the actual work.

Design:
    - Detect work-shape intent via verb-presence in the prompt
    - If detected AND no session-fresh goal exists, derive a goal-text
    - Call the existing add_goal() machinery to persist it

Non-goals:
    - This is not a classifier for what KIND of goal it is
    - This does not attempt to be smart about multi-intent prompts
    - This does not override an existing goal (dedup handled by add_goal)

Escape hatch: any error in derivation returns None silently. If the
auto-derive fails, the doorman surface still fires and the manual
'divineos goal add' path stays open. Never blocks the composer.
"""

from __future__ import annotations

import re

# Work-shape verbs and phrases that suggest the prompt is asking me to
# do substrate-touching work. Kept small and conservative — false-positives
# here mean auto-setting a goal on conversation-only turns, which is
# minor noise but not harmful (goals dedupe and don't block).
_WORK_INTENT_VERBS: frozenset[str] = frozenset(
    {
        "add",
        "build",
        "check",
        "commit",
        "configure",
        "create",
        "debug",
        "delete",
        "design",
        "disable",
        "edit",
        "enable",
        "extend",
        "fix",
        "go",
        "implement",
        "install",
        "integrate",
        "investigate",
        "look",
        "merge",
        "migrate",
        "push",
        "read",
        "redesign",
        "refactor",
        "remove",
        "replace",
        "research",
        "restructure",
        "review",
        "run",
        "ship",
        "test",
        "update",
        "verify",
        "walk",
        "write",
    }
)

_INTENT_RE = re.compile(
    r"\b(" + "|".join(re.escape(v) for v in _WORK_INTENT_VERBS) + r")\b",
    re.IGNORECASE,
)


def is_work_shape_prompt(prompt: str) -> bool:
    """Return True if the prompt contains a work-shape verb.

    Empty or whitespace-only prompts return False. Very short prompts
    (< 4 chars) return False — they can't contain a verb.
    """
    if not prompt or len(prompt.strip()) < 4:
        return False
    return bool(_INTENT_RE.search(prompt))


def derive_goal_text(prompt: str, max_chars: int = 120) -> str:
    """Derive a short goal-text string from a user prompt.

    Takes the first sentence-ish chunk of the prompt (split on period /
    newline) and trims to max_chars. If the whole prompt is shorter than
    max_chars, returns the whole prompt.

    Returns empty string if the prompt is empty. Never raises.
    """
    if not prompt:
        return ""
    cleaned = prompt.strip()
    if not cleaned:
        return ""

    # Prefer the first sentence-ish chunk. Split on period, newline, or
    # question mark — keep everything before the first such break.
    first_chunk = re.split(r"[.\n?!]", cleaned, maxsplit=1)[0].strip()
    if not first_chunk:
        first_chunk = cleaned

    # Collapse internal whitespace so multi-line prompts produce a
    # readable single-line goal.
    first_chunk = re.sub(r"\s+", " ", first_chunk)

    if len(first_chunk) <= max_chars:
        return first_chunk
    # Trim at last word boundary before max_chars to avoid mid-word cut.
    trimmed = first_chunk[:max_chars]
    last_space = trimmed.rfind(" ")
    if last_space > max_chars // 2:
        trimmed = trimmed[:last_space]
    return trimmed.rstrip() + "..."


def derive_and_set_goal_from_prompt(prompt: str) -> str | None:
    """Derive a goal from prompt and set it if no session-fresh goal exists.

    Returns the goal-text that was set, or None if no goal was set
    (either because the prompt wasn't work-shape, a session-fresh goal
    already exists, or derivation/persistence failed).

    Fail-soft at every step: errors return None silently rather than
    raising. The composer should never be blocked by auto-goal failure —
    the existing manual 'divineos goal add' path always remains available.
    """
    if not is_work_shape_prompt(prompt):
        return None

    try:
        from divineos.core.hud_state import add_goal, has_session_fresh_goal
    except Exception:
        return None

    try:
        if has_session_fresh_goal():
            return None
    except Exception:
        return None

    goal_text = derive_goal_text(prompt)
    if not goal_text:
        return None

    try:
        add_goal(goal_text, original_words=prompt[:500])
    except Exception:
        return None

    return goal_text
