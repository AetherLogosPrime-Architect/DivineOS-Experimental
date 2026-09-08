"""The hook layer is measured, not remembered.

Andrew 2026-09-08: *"i dont want an OS made of external hooks through the IDE,
the hooks should just be pointing to the logic in the OS itself."*

These pinned a ratchet on the layer's SIZE until he rejected the idea outright
— *"why would you build something that can only shrink and never grow?"* — so
what remains is the instrument that earned its place by finding a duplicate my
own hands had missed.

Every assertion that something is absent is paired with its control. A bare
``== []`` passes with the module blanked, which is how six of seven tests
survived sabotage earlier the same day.
"""

from __future__ import annotations

import json
from pathlib import Path

from divineos.core import hook_layer as hl


def _tree(tmp_path: Path, registrations: dict[str, list[str]], files: dict[str, str]) -> Path:
    hooks = tmp_path / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    for name, body in files.items():
        (hooks / name).write_text(body, encoding="utf-8")
    settings = {
        "hooks": {
            event: [{"hooks": [{"command": f"bash .claude/hooks/{n}"} for n in names]}]
            for event, names in registrations.items()
        }
    }
    (tmp_path / ".claude" / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
    (tmp_path / "docs").mkdir()
    return tmp_path


_ONE = {"a.sh": "#!/bin/bash\nexit 0\n"}


def test_inventory_counts_what_is_registered_not_what_exists(tmp_path):
    root = _tree(
        tmp_path,
        {"Stop": ["a.sh"]},
        {"a.sh": "#!/bin/bash\nexit 0\n", "unwired.sh": "#!/bin/bash\nexit 0\n"},
    )
    inv = hl.inventory(root)
    assert inv.total == 1
    assert inv.shell_files == 2  # the file on disk is counted; the registration is not


def test_every_door_without_a_bell_is_named(tmp_path):
    """Five of the seven doors had no doorbell when this was written, which is
    the fact the whole consolidation turns on."""
    root = _tree(tmp_path, {"Stop": ["a.sh"]}, _ONE)
    inv = hl.inventory(root)
    assert "Stop" not in inv.doors_without_a_bell
    assert "UserPromptSubmit" in inv.doors_without_a_bell
    assert len(inv.doors_without_a_bell) == len(hl.EVENTS) - 1


def test_a_script_registered_twice_on_one_event_is_caught(tmp_path):
    """The finding that justified building this at all: one hook had been
    running twice on every tool call, and hand-searching missed it."""
    clean = hl.inventory(_tree(tmp_path / "clean", {"Stop": ["a.sh"]}, _ONE))
    assert clean.duplicates == []
    dupe = hl.inventory(_tree(tmp_path / "dupe", {"Stop": ["a.sh", "a.sh"]}, _ONE))
    assert dupe.duplicates == [("Stop", "a.sh")]


def test_the_same_script_on_two_different_events_is_not_a_duplicate(tmp_path):
    root = _tree(tmp_path, {"Stop": ["a.sh"], "PreToolUse": ["a.sh"]}, _ONE)
    assert hl.inventory(root).duplicates == []


def test_a_registration_with_no_file_behind_it_is_named(tmp_path):
    root = _tree(tmp_path, {"Stop": ["a.sh", "ghost.sh"]}, _ONE)
    assert hl.inventory(root).phantom == ["ghost.sh"]
    clean = hl.inventory(_tree(tmp_path / "clean", {"Stop": ["a.sh"]}, _ONE))
    assert clean.phantom == []


def test_shell_that_never_touches_the_os_is_counted_apart(tmp_path):
    root = _tree(
        tmp_path,
        {"Stop": ["a.sh", "b.sh", "c.sh"]},
        {
            "a.sh": "#!/bin/bash\necho hi\n",
            "b.sh": "#!/bin/bash\nfrom divineos.core import x\n",
            "c.sh": "#!/bin/bash\ndivineos briefing\n",
        },
    )
    assert hl.inventory(root).detached_files == 1  # only a.sh; the others reach the OS


def test_embedded_python_is_counted_as_judgment_in_the_shell(tmp_path):
    root = _tree(
        tmp_path,
        {"Stop": ["a.sh", "b.sh"]},
        {"a.sh": "#!/bin/bash\necho hi\n", "b.sh": '#!/bin/bash\npython3 -c "print(1)"\n'},
    )
    assert hl.inventory(root).inline_python_files == 1


def test_registered_names_span_every_event(tmp_path):
    root = _tree(tmp_path, {"Stop": ["a.sh"], "PreToolUse": ["b.sh"]}, {**_ONE, "b.sh": "x"})
    assert hl.inventory(root).registered_names == {"a.sh", "b.sh"}


def test_the_report_says_plainly_that_it_is_not_a_limit(tmp_path):
    """The correction, kept where a reader will hit it. He killed a ceiling on
    this layer and the instrument must not imply one survived."""
    root = _tree(tmp_path, {"Stop": ["a.sh", "a.sh"]}, _ONE)
    text = hl.format_inventory(hl.inventory(root))
    assert "not a limit" in text
    assert "may grow as much as is" in text
    assert "REGISTERED MORE THAN ONCE" in text  # and it still reports the real defect


def test_a_malformed_settings_file_raises_rather_than_reporting_zero(tmp_path):
    root = _tree(tmp_path, {"Stop": ["a.sh"]}, _ONE)
    assert hl.inventory(root).total == 1  # control: it really does read a good file

    (root / ".claude" / "settings.json").write_text("{not json", encoding="utf-8")
    try:
        hl.inventory(root)
    except ValueError:
        return
    raise AssertionError("a settings file it could not parse must not report a count")


def test_the_event_list_is_the_routers_and_not_a_second_copy():
    """SURVIVES HOLLOWING, and that is correct rather than a hole.

    This asserts a module-level identity, so blanking every function cannot
    affect it. Recorded because the sabotage run reports it as the lone
    survivor, and an unexplained survivor is what a hollow test looks like from
    outside. Its control is direct: a copy fails it.
    """
    from divineos.core.hook_router import EVENTS as ROUTER_EVENTS

    assert hl.EVENTS is ROUTER_EVENTS
    # tuple(t) and t[:] both RETURN t for a tuple, so the copy is forced
    # through a list. Caught by this control failing on the first attempt.
    assert hl.EVENTS is not tuple(list(ROUTER_EVENTS))


def test_the_live_repository_is_readable_by_this_module():
    """The instrument proved against the real tree, not only fixtures.

    Andrew 2026-09-07: one instrument asked once is not a measurement, and an
    empty result from a single probe is most often a broken probe.
    """
    inv = hl.inventory(Path(__file__).resolve().parents[1])
    assert inv.total > 0
    assert inv.shell_files > 0
    assert inv.per_event["UserPromptSubmit"] > 0
