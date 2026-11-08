"""The link that listens to our own words: its wiring, its settings, and one door for every lane.

Design: docs/drafts/the_link_listens_to_our_own_words_design_note_aether_2026-11-08.md (tests 1 to 3 of ten).
Written first and failing: nothing here exists yet.

Dad, 2026-11-08: "if you and Aria can get everything linked up.. it will change everything". The failure these three
tests close is the quiet one: a listener that is built and passes its own tests and is called by nothing, or a lane the
retriever gained that has no way to be cleared, so a hit in it could be shown and never answered.
"""

import json
from pathlib import Path

import pytest

from divineos.core.memory_linkage_retriever import _SOURCE_THRESHOLDS
from divineos.core import own_words_link_settings as settings

REPO = Path(__file__).resolve().parent.parent
SETTINGS_JSON = REPO / ".claude" / "settings.json"
HOOK_FILE = REPO / ".claude" / "hooks" / "own-words-link.sh"


# -- test 1: built-but-unwired ---------------------------------------------------------------


def _post_tool_commands() -> list[str]:
    cfg = json.loads(SETTINGS_JSON.read_text(encoding="utf-8"))
    out: list[str] = []
    for block in cfg.get("hooks", {}).get("PostToolUse", []):
        for hook in block.get("hooks", []):
            out.append(hook.get("command", ""))
    return out


def test_the_hook_has_a_named_caller_in_the_real_settings_json():
    assert any("own-words-link.sh" in c for c in _post_tool_commands()), (
        "own-words-link.sh is called by nothing: a listener nobody calls is a note, not a mechanism"
    )


def test_the_caller_says_so_when_the_file_is_gone_and_the_file_exists():
    callers = [c for c in _post_tool_commands() if "own-words-link.sh" in c]
    assert callers and HOOK_FILE.exists()
    assert all("NOT RUNNING" in c and "127" in c for c in callers), (
        "a missing hook must print NOT RUNNING and exit 127"
    )


# -- test 2: the settings are valid or the build fails loudly ---------------------------------


def test_the_shipped_settings_load_and_are_valid():
    cfg = settings.load()
    assert cfg["mode"] in ("off", "log", "block")
    assert cfg["chunk_rule"] in ("first", "last", "per_paragraph")
    assert isinstance(cfg["chunk_tokens"], int) and 32 <= cfg["chunk_tokens"] <= 512


@pytest.mark.parametrize(
    "bad",
    [
        {"mode": "on"},
        {"mode": ""},
        {"chunk_rule": "middle"},
        {"chunk_tokens": 8},
        {"chunk_tokens": "256"},
    ],
)
def test_a_bad_value_fails_loudly_instead_of_falling_back(bad):
    cfg = settings.load()
    cfg.update(bad)
    with pytest.raises(settings.SettingsError):
        settings.validate(cfg)


def test_the_live_default_is_off_and_the_copy_default_is_log_is_not_decided_here():
    # Design point 10: off in the live house until the note is walked. The shipped file must not be 'block'.
    assert settings.load()["mode"] != "block"


# -- test 3: every lane has a door ------------------------------------------------------------


def test_every_retriever_lane_has_a_defined_clear():
    cfg = settings.load()
    missing = sorted(set(_SOURCE_THRESHOLDS) - set(cfg["lane_clears"]))
    assert not missing, f"lanes the retriever has but the settings give no clear for: {missing}"


def test_a_lane_added_to_the_retriever_fails_the_build_until_it_has_a_clear():
    cfg = settings.load()
    cfg["lane_clears"] = {k: v for k, v in cfg["lane_clears"].items() if k != "letter"}
    with pytest.raises(settings.SettingsError, match="letter"):
        settings.validate(cfg, lanes=set(_SOURCE_THRESHOLDS))


def test_a_clear_is_a_real_kind():
    for lane, clear in settings.load()["lane_clears"].items():
        assert clear["kind"] in ("read_file", "show_command", "undefined_placeholder"), lane


def test_a_placeholder_clear_fails_loudly_so_nothing_passes_on_a_guess():
    """The show commands for the corrections and knowledge lanes belong to Aria to name. Until she does, those lanes
    carry an explicit placeholder, and a placeholder must make the strict check fail: no lane may be silently open."""
    cfg = settings.load()
    placeholders = sorted(
        lane for lane, c in cfg["lane_clears"].items() if c["kind"] == "undefined_placeholder"
    )
    with pytest.raises(settings.SettingsError):
        settings.validate(cfg, lanes=set(_SOURCE_THRESHOLDS), strict=True)
    # and the non-strict load (log-only mode) still works, naming which lanes are placeholders
    assert settings.validate(cfg, lanes=set(_SOURCE_THRESHOLDS)) == placeholders
