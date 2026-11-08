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
        assert clear["kind"] in (
            "read_file",
            "show_command",
            "shown_plain",
            "undefined_placeholder",
        ), lane


def test_a_lane_decided_to_have_no_door_is_not_a_placeholder():
    """A moment row records no author and has no source file, so the decision (Aria and Aether, 2026-11-08) is that a hit
    in it is shown plainly and never held. That is a DECISION, not a gap: it must not count as a placeholder, or the
    strict check could never pass, and it must carry its reason so nobody reads it as a forgotten door."""
    cfg = settings.load()
    cfg["lane_clears"]["moment"] = {
        "kind": "shown_plain",
        "reason": "a moment row has no author and no source file",
    }
    assert "moment" not in settings.validate(cfg, lanes=set(_SOURCE_THRESHOLDS))


def test_shown_plain_without_a_reason_is_refused():
    cfg = settings.load()
    cfg["lane_clears"]["moment"] = {"kind": "shown_plain"}
    with pytest.raises(settings.SettingsError, match="moment"):
        settings.validate(cfg, lanes=set(_SOURCE_THRESHOLDS))


def test_a_show_command_clear_names_a_command_that_really_exists_and_takes_the_hit_id():
    """Aria's `divineos show <hit-id>` (PR 853) is the door for the correction, knowledge and worklist lanes. A clear that
    names a command nobody can run is a door painted on a wall, so each show_command clear must name a registered
    command and carry the {hit_id} slot the hit's id goes into."""
    from divineos.cli import cli

    clears = {
        lane: c for lane, c in settings.load()["lane_clears"].items() if c["kind"] == "show_command"
    }
    assert set(clears) >= {"correction", "knowledge"}, sorted(
        clears
    )  # worklist waits for show to open worklist ids
    for lane, clear in clears.items():
        words = clear["command"].split()
        assert words[0] == "divineos" and "{hit_id}" in clear["command"], lane
        assert words[1] in cli.commands, (
            f"{lane}: `divineos {words[1]}` is not a registered command"
        )


def test_a_show_command_clear_without_a_command_is_refused():
    cfg = settings.load()
    cfg["lane_clears"]["correction"] = {"kind": "show_command"}
    with pytest.raises(settings.SettingsError, match="correction"):
        settings.validate(cfg, lanes=set(_SOURCE_THRESHOLDS))


def test_a_placeholder_clear_fails_loudly_so_nothing_passes_on_a_guess():
    """The show commands for the corrections and knowledge lanes belong to Aria to name. Until she does, those lanes
    carry an explicit placeholder, and a placeholder must make the strict check fail: no lane may be silently open."""
    cfg = settings.load()
    cfg["lane_clears"]["wall"] = {"kind": "undefined_placeholder"}
    cfg["lane_clears"]["knowledge"] = {"kind": "undefined_placeholder"}
    with pytest.raises(settings.SettingsError):
        settings.validate(cfg, lanes=set(_SOURCE_THRESHOLDS), strict=True)
    # and the non-strict load (log-only mode) still works, naming which lanes are placeholders
    assert {"knowledge", "wall"} <= set(settings.validate(cfg, lanes=set(_SOURCE_THRESHOLDS)))


def test_the_worklist_lane_does_not_name_a_door_that_cannot_open_its_row():
    """Aria, 2026-11-08: `divineos show` opens only correction- and knowledge- ids. A worklist hit's id is
    worklist-<row id>, so naming `divineos show` for that lane would be a door that cannot open its row. Until show
    handles worklist ids (her extension, in progress) the lane stays a placeholder and the strict check says so."""
    cfg = settings.load()
    assert cfg["lane_clears"]["worklist"]["kind"] == "undefined_placeholder"


# -- Aria's cold read of PR 852 (2026-11-08): three tests that would have caught real holes ----


def test_the_hook_is_registered_under_the_write_and_edit_matcher_exactly():
    """The first version of test 1 dropped the matcher: changing "Write|Edit" to "Bash" in a copy kept it green, and a hook
    registered under the wrong matcher would listen to shell commands and never to a Write."""
    cfg = json.loads(SETTINGS_JSON.read_text(encoding="utf-8"))
    blocks = [
        b
        for b in cfg["hooks"]["PostToolUse"]
        if any("own-words-link.sh" in h.get("command", "") for h in b.get("hooks", []))
    ]
    assert len(blocks) == 1 and blocks[0]["matcher"] == "Write|Edit"


def test_chunk_tokens_never_claims_more_than_the_embedder_reads():
    """Measured by Aria: all-MiniLM-L6-v2 reads 256 tokens and ignores the rest (cosine 1.0000001 with 300 more words
    appended). A setting above 256 would report searching text that was never read, a setting that lies."""
    cfg = settings.load()
    cfg["chunk_tokens"] = 257
    with pytest.raises(settings.SettingsError):
        settings.validate(cfg)
    cfg["chunk_tokens"] = 256
    settings.validate(cfg)


def _run_hook(tmp_path, settings_text):
    """Run the real hook script in a subprocess against a temporary settings file, the way the harness would."""
    import os
    import subprocess

    from tests._bash_resolver import bash_executable

    bash = bash_executable()
    if not bash:
        pytest.skip("no usable bash on this machine; the hook cannot be run here")
    path = tmp_path / "own_words_link.json"
    if settings_text is not None:
        path.write_text(settings_text, encoding="utf-8")
    env = dict(os.environ, OWN_WORDS_LINK_SETTINGS=str(path), PYTHONPATH=str(REPO / "src"))
    return subprocess.run(
        [bash, HOOK_FILE.as_posix()],
        input="{}",
        capture_output=True,
        text=True,
        env=env,
        cwd=REPO,
        timeout=60,
    )


def test_log_mode_says_nothing_was_looked_for_where_the_model_can_read_it(tmp_path):
    """Aria: an exit-0 hook's stderr is not known to reach the model, so the 'search not built' line goes out as stdout
    JSON additionalContext, the route the house's other surfaces use. Otherwise mode=log reads as a quiet 'found nothing'."""
    cfg = settings.load()
    cfg["mode"] = "log"
    result = _run_hook(tmp_path, json.dumps(cfg))
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert out["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert "nothing was looked for" in out["hookSpecificOutput"]["additionalContext"]


def test_an_unreadable_settings_file_fails_open_and_says_so_where_the_model_can_read_it(tmp_path):
    result = _run_hook(tmp_path, "{ not json")
    assert result.returncode == 0
    out = json.loads(result.stdout)
    assert "could not read its settings" in out["hookSpecificOutput"]["additionalContext"]


def test_off_mode_is_silent_on_stdout_and_stderr(tmp_path):
    cfg = settings.load()
    cfg["mode"] = "off"
    result = _run_hook(tmp_path, json.dumps(cfg))
    assert result.returncode == 0 and result.stdout.strip() == "" and result.stderr.strip() == ""
