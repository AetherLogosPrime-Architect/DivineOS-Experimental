"""Smoke tests for the four stragglers from the completion_check audit.

After parametrized expert + CLI test files closed the bulk of the
coverage gap (120 -> 4), these four remained:

  - core/memory_types/skill_index.py
  - core/operating_loop_briefing_surface.py
  - core/resonant_truth.py
  - .claude/hooks/pre-tool-context.sh

Each gets a smoke test that exercises the public surface without
asserting deep behavior — enough to catch import errors, signature
drift, and "the module loads but its main function crashes on
empty input" failures.

Built 2026-05-14 in the coverage-gap-close batch.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


# --- skill_index ------------------------------------------------------


def test_skill_index_load_returns_list() -> None:
    """skill_index.load_skills returns a list (empty or populated)
    without raising on a normal repo state."""
    from divineos.core.memory_types.skill_index import load_skills

    out = load_skills()
    assert isinstance(out, list)


def test_skill_index_rank_handles_empty_query() -> None:
    """rank_skills with an empty query returns a list without raising."""
    from divineos.core.memory_types.skill_index import load_skills, rank_skills

    skills = load_skills()
    ranked = rank_skills(query="", skills=skills)
    assert isinstance(ranked, list)


# --- operating_loop_briefing_surface ----------------------------------


def test_operating_loop_briefing_surface_format_returns_str() -> None:
    """format_for_briefing returns a string (possibly empty if no
    findings recorded yet)."""
    from divineos.core.operating_loop_briefing_surface import format_for_briefing

    out = format_for_briefing()
    assert isinstance(out, str)


def test_operating_loop_briefing_surface_respects_min_threshold() -> None:
    """With min_total_to_surface high, output is empty (suppressed)."""
    from divineos.core.operating_loop_briefing_surface import format_for_briefing

    out = format_for_briefing(min_total_to_surface=10**9)
    assert out == ""


# --- resonant_truth ---------------------------------------------------


def test_resonant_truth_is_rt_loaded_returns_bool() -> None:
    """is_rt_loaded returns a bool — fundamental contract."""
    from divineos.core.resonant_truth import is_rt_loaded

    assert isinstance(is_rt_loaded(), bool)


def test_resonant_truth_load_protocol_returns_str() -> None:
    """load_protocol returns a string. Empty is OK if protocol file
    isn't present, but the function must not crash."""
    from divineos.core.resonant_truth import load_protocol

    out = load_protocol()
    assert isinstance(out, str)


# --- pre-tool-context.sh ----------------------------------------------


def test_pre_tool_context_hook_syntax_valid(tmp_path: Path) -> None:
    """The pre-tool-context.sh hook must pass `bash -n` syntax check.
    Catches quoting/grammar errors that would silently break the hook
    at runtime. Skipped on systems without bash (Windows native python
    where the WSL bash bridge isn't available)."""
    import shutil

    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash not available on this system")
    repo_root = Path(__file__).parent.parent
    hook_path = repo_root / ".claude" / "hooks" / "pre-tool-context.sh"
    if not hook_path.exists():
        pytest.skip(f"hook not present: {hook_path}")
    try:
        result = subprocess.run(
            [bash, "-n", str(hook_path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        pytest.skip("bash invocation failed in this environment")
    assert result.returncode == 0, f"bash -n failed: {result.stderr}"
