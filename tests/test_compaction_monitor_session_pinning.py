"""Tests for the compaction monitor's session-pinned transcript resolution.

Root-cause fix for Andrew correction #50 (2026-06-10): the prior
mtime-only resolver false-fired a COMPACTION-BLOCK at 961k when actual
context was 136k, because an abandoned 67MB session JSONL in the same
project folder had a fresher mtime and got picked.

Tests inject projects_dir + session_id directly into _find_active_transcript
rather than monkeypatching Path.home() or os.environ. The injection
parameters exist FOR test isolation — the previous monkeypatch-based
shape failed in the full pytest suite under test pollution (passed
standalone, failed in CI), wasting 12 min per CI cycle. Parameter
injection is shared-state-free.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _touch(path: Path, mtime: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}\n")
    os.utime(path, (mtime, mtime))


def test_pins_to_session_id_even_when_another_jsonl_has_fresher_mtime(tmp_path):
    """The exact bug from correction #50: an abandoned session's JSONL has
    a fresher mtime, but the monitor must follow the launching session."""
    from scripts.compaction_token_monitor import _find_active_transcript

    session_id = "ad5073a4-244c-49c4-b651-80b612f4c176"
    projects = tmp_path / "projects"
    project = projects / "myproject"
    pinned = project / f"{session_id}.jsonl"
    abandoned = project / "4b30bf60-eaf7-4cd4-9e96-1536a293499d.jsonl"
    now = time.time()
    _touch(pinned, mtime=now - 100)
    _touch(abandoned, mtime=now)

    result = _find_active_transcript(projects_dir=projects, session_id=session_id)

    assert result == pinned


def test_falls_back_to_mtime_when_session_id_unset(tmp_path):
    """Non-Claude-Code harnesses don't pass session_id; the monitor must
    still resolve a transcript so it arms."""
    from scripts.compaction_token_monitor import _find_active_transcript

    projects = tmp_path / "projects"
    project = projects / "myproject"
    older = project / "older.jsonl"
    newer = project / "newer.jsonl"
    now = time.time()
    _touch(older, mtime=now - 100)
    _touch(newer, mtime=now)

    result = _find_active_transcript(projects_dir=projects, session_id="")

    assert result == newer


def test_falls_back_to_mtime_when_session_id_set_but_no_matching_jsonl(tmp_path):
    """If session_id is provided but no JSONL matches (startup race), fall
    back to mtime so the monitor still arms instead of going silent."""
    from scripts.compaction_token_monitor import _find_active_transcript

    projects = tmp_path / "projects"
    project = projects / "myproject"
    only = project / "some-other-id.jsonl"
    _touch(only, mtime=time.time())

    result = _find_active_transcript(
        projects_dir=projects, session_id="session-that-has-no-jsonl-yet"
    )

    assert result == only


def test_returns_none_when_projects_dir_missing(tmp_path):
    """No projects directory → None (monitor emits COMPACTION-ERROR)."""
    from scripts.compaction_token_monitor import _find_active_transcript

    missing = tmp_path / "does-not-exist"

    assert _find_active_transcript(projects_dir=missing, session_id="") is None


def test_returns_none_when_no_jsonls_anywhere(tmp_path):
    """Projects dir exists but is empty."""
    from scripts.compaction_token_monitor import _find_active_transcript

    projects = tmp_path / "projects"
    projects.mkdir()

    assert _find_active_transcript(projects_dir=projects, session_id="") is None


def test_runtime_defaults_use_env_var_and_path_home(tmp_path, monkeypatch):
    """When called with no args (runtime path), it reads CLAUDE_CODE_SESSION_ID
    from env and Path.home() for the projects dir.

    Isolated by patching os.environ and Path.home only for this one test —
    parameter injection in the other tests means the suite doesn't depend
    on these patches being correctly scoped.
    """
    from scripts.compaction_token_monitor import _find_active_transcript

    fake_home = tmp_path / "home"
    projects = fake_home / ".claude" / "projects" / "p"
    session_id = "env-resolved-session"
    pinned = projects / f"{session_id}.jsonl"
    distractor = projects / "other.jsonl"
    now = time.time()
    _touch(pinned, mtime=now - 100)
    _touch(distractor, mtime=now)
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", session_id)

    result = _find_active_transcript()

    assert result == pinned


def test_legacy_env_var_claude_session_id_honored(tmp_path, monkeypatch):
    """CLAUDE_SESSION_ID (consultation-tracker's env-var name) is honored
    as a fallback when CLAUDE_CODE_SESSION_ID is absent."""
    from scripts.compaction_token_monitor import _find_active_transcript

    fake_home = tmp_path / "home"
    projects = fake_home / ".claude" / "projects" / "p"
    session_id = "legacy-name-session"
    pinned = projects / f"{session_id}.jsonl"
    distractor = projects / "other.jsonl"
    now = time.time()
    _touch(pinned, mtime=now - 100)
    _touch(distractor, mtime=now)
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    monkeypatch.setenv("CLAUDE_SESSION_ID", session_id)

    result = _find_active_transcript()

    assert result == pinned
