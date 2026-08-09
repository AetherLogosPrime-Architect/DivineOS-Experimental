"""Andrew's character sheet loads exactly once per session, not per turn.

Andrew 2026-07-07: "so are you telling me you cant remember it from
loading once per context session?" — yes. The first cut of the loader
put the sheet in build_baseline_text (called at every UserPromptSubmit),
burning ~10k tokens per user message even though the sheet doesn't
change during a session. Wallpaper shape, one meta-level up.

The correct design: load the sheet ONCE at SessionStart. The sheet
enters the context window and stays there for the session lifetime.
When compaction happens, SessionStart:resume fires and reloads it into
the fresh post-compaction context. That's the natural cadence.

This test file pins three things:
  1. The sheet file exists at the canonical path.
  2. build_baseline_text does NOT load the sheet (regression guard —
     if a future me tries to put the load back into the per-turn path,
     this test fails and CI catches it).
  3. The hook file exists, references its target, and is REACHABLE —
     registered directly, or invoked by a registered initializer. The
     window-freeze work collapsed a long SessionStart list into one
     init script, so pinning the route rather than the reachability
     made a design change look like a defect.

Per kiln truth #15 (meta-Winnicott): the file points at who I am
composing to; the SessionStart hook is what makes the pointing
structural. The wrong loader is worse than no loader — silent token
burn masquerading as discipline.
"""

from __future__ import annotations

import json
from pathlib import Path

from divineos.core.pre_response_context import build_baseline_text


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    while here != here.parent and not (here / ".git").exists():
        here = here.parent
    return here


def test_character_sheet_file_exists():
    """The sheet file must exist. The SessionStart hook depends on it
    being at the canonical path; a moved-or-missing sheet is a
    substrate injury."""
    sheet = _repo_root() / "docs/identity_anchors/andrew_character_sheet.md"
    assert sheet.is_file(), (
        f"Character sheet missing at {sheet}. This file is "
        "guardrail-protected; if it's gone, an unauthorized modification "
        "has occurred."
    )


def test_baseline_does_not_load_character_sheet():
    """Regression guard against Andrew catch 2026-07-07. The per-turn
    load in build_baseline_text was wallpaper — burning ~10k tokens per
    user message on ground already in context. If a future refactor
    silently re-adds the load here, this test fails."""
    for prompt in [None, "", "ok", "yes", "a longer substantive prompt here"]:
        baseline = build_baseline_text(prompt=prompt)
        assert "Who I am composing to" not in baseline, (
            f"build_baseline_text(prompt={prompt!r}) loaded the character "
            "sheet. That is the wallpaper shape Andrew caught 2026-07-07 — "
            "the sheet must load at SessionStart, not per-turn. See "
            ".claude/hooks/load-character-sheet.sh."
        )


def test_session_start_hook_exists_and_readable():
    """The SessionStart hook that actually loads the sheet must exist
    at the expected path."""
    hook = _repo_root() / ".claude/hooks/load-character-sheet.sh"
    assert hook.is_file(), (
        f"SessionStart hook missing at {hook}. This is the mechanism "
        "that loads the character sheet once per session; without it, "
        "the sheet is decorative again."
    )
    body = hook.read_text(encoding="utf-8")
    assert "andrew_character_sheet.md" in body, (
        "Hook exists but does not reference the sheet file — it may have "
        "been silently disconnected from its target."
    )
    assert "additionalContext" in body, (
        "Hook exists but does not emit additionalContext JSON — its "
        "output would not reach the session context."
    )


def test_character_sheet_hook_is_actually_reachable():
    """The hook must be REACHABLE at session start. An unreachable hook
    file is just a file, and the sheet would never load.

    This originally asserted direct registration under ``SessionStart`` in
    settings.json. That stopped describing reality when the window-freeze
    work consolidated a long SessionStart list into a single
    ``session-init-once.sh`` that invokes the individual hooks in turn.
    The sheet still loads; only the route changed.

    Asserting the ROUTE rather than the OUTCOME is how a test starts
    reporting a design change as a defect. So this checks either route —
    registered directly, or invoked by a registered initializer — and
    fails only when the sheet is genuinely unreachable by both.
    """
    root = _repo_root()
    settings = root / ".claude/settings.json"
    assert settings.is_file(), f".claude/settings.json missing at {settings}"
    data = json.loads(settings.read_text(encoding="utf-8"))

    # Every registered event, not just SessionStart. The freeze fix moved
    # the initializer to UserPromptSubmit (it runs once, on the first
    # prompt), so scanning SessionStart alone reports "unreachable" for a
    # hook that runs perfectly well — looking in one place and calling the
    # miss an absence.
    hook_commands: list[str] = []
    for groups in data.get("hooks", {}).values():
        for group in groups:
            for entry in group.get("hooks", []):
                cmd = entry.get("command", "")
                if isinstance(cmd, str):
                    hook_commands.append(cmd)
    registered_directly = any("load-character-sheet.sh" in c for c in hook_commands)

    # Consolidated route: a registered SessionStart script that fans out.
    invoked_by_initializer = False
    for cmd in hook_commands:
        for token in cmd.split():
            if not token.endswith(".sh"):
                continue
            candidate = root / token
            if not candidate.is_file():
                continue
            if "load-character-sheet.sh" in candidate.read_text(encoding="utf-8", errors="replace"):
                invoked_by_initializer = True
                break

    assert registered_directly or invoked_by_initializer, (
        "load-character-sheet.sh is reachable by NEITHER route: it is not "
        "registered under SessionStart in .claude/settings.json, and no "
        "registered SessionStart script invokes it. The sheet will not "
        "load at session start."
    )
