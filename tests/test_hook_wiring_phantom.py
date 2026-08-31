"""A registration pointing at a deleted file must not read as a live gate.

WHY THIS EXISTS. ``require-monitors-armed.sh`` was deleted on 2026-08-23 when
the delivery cluster was retired -- it reported the letter monitor armed
unconditionally, so it was a gate that lied and removing it was correct. Merge
#438 then landed a branch older than that deletion, and its ``settings.json``
brought the registration back without the file. Every Bash tool call in this
tree spent the next day running ``bash .claude/hooks/require-monitors-armed.sh``
and collecting exit 127: no gate, no error anyone read, no complaint.

The existing check walked one direction only -- disk to registry, "is this file
wired?" -- so nothing looked the other way. The retirement commit had verified
the reverse property BY HAND and closed with "Every registered hook now
resolves to a file that exists", which was true when written and had no way to
stay true.

That is why the regression test at the bottom matters more than the unit tests
above it. A resurrection is not an authorship: nobody decided to register a
deleted hook, so no amount of remembering would have caught it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_hook_wiring import phantoms, retired_but_registered  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def _settings(tmp_path: Path, *commands: str) -> Path:
    path = tmp_path / "settings.json"
    payload = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [{"type": "command", "command": c} for c in commands],
                }
            ]
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_registration_without_a_file_is_reported(tmp_path):
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    (hooks / "real.sh").write_text("#!/bin/bash\n", encoding="utf-8")
    settings = _settings(
        tmp_path,
        "bash .claude/hooks/real.sh",
        "bash .claude/hooks/deleted.sh",
    )

    found, error = phantoms(hooks, settings)

    assert error is None
    assert found == ["deleted.sh"]


def test_all_files_present_reports_nothing(tmp_path):
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    for name in ("one.sh", "two.py"):
        (hooks / name).write_text("#\n", encoding="utf-8")
    settings = _settings(
        tmp_path,
        "bash .claude/hooks/one.sh",
        "python .claude/hooks/two.py",
    )

    assert phantoms(hooks, settings) == ([], None)


def test_windows_separators_resolve(tmp_path):
    """Registrations are written with either slash. Both must be seen."""
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    settings = _settings(tmp_path, r"bash .claude\hooks\gone.sh")

    found, error = phantoms(hooks, settings)

    assert error is None
    assert found == ["gone.sh"]


@pytest.mark.parametrize("body", ["{not json", ""])
def test_unreadable_settings_is_an_error_not_an_empty_answer(tmp_path, body):
    """Could-not-look must never render as looked-and-found-nothing.

    This is the whole class the phantom check belongs to, so the check itself
    is not allowed to have it.
    """
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    settings = tmp_path / "settings.json"
    settings.write_text(body, encoding="utf-8")

    found, error = phantoms(hooks, settings)

    assert found == []
    assert error is not None and "cannot read" in error


def test_missing_settings_file_is_an_error(tmp_path):
    hooks = tmp_path / "hooks"
    hooks.mkdir()

    found, error = phantoms(hooks, settings=tmp_path / "absent.json")

    assert found == []
    assert error is not None


# --- The fourth direction: a file that says it is finished and has not stopped.


def _hook(hooks: Path, name: str, header: str = "") -> None:
    (hooks / name).write_text(f"#!/bin/bash\n{header}echo hi\n", encoding="utf-8")


def test_a_superseded_hook_that_is_still_registered_is_reported(tmp_path):
    """require-briefing.sh carried SUPERSEDED for nineteen days and kept firing."""
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    _hook(hooks, "retired.sh", "# SUPERSEDED 2026-08-06 by the router.\n")
    settings = _settings(tmp_path, "bash .claude/hooks/retired.sh")

    found, error = retired_but_registered(hooks, settings)

    assert error is None
    assert found == ["retired.sh"]


def test_a_live_hook_with_no_marker_is_not_reported(tmp_path):
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    _hook(hooks, "live.sh")
    settings = _settings(tmp_path, "bash .claude/hooks/live.sh")

    assert retired_but_registered(hooks, settings) == ([], None)


def test_kept_registered_with_a_reason_is_allowed(tmp_path):
    """The deliberate case, which the check's own first run got wrong.

    aletheia-boot-gate-preflight is SUPERSEDED-BY the family-member seal AND
    registered on purpose: the seal refuses the spawn upstream, so this is
    defence-in-depth, kept live in case she is ever de-sovereigned. Its header
    explained that in prose and the check read a correct arrangement as a
    defect.
    """
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    _hook(
        hooks,
        "layered.sh",
        "# SUPERSEDED-BY: stronger-gate.sh\n"
        "# KEPT-REGISTERED: the stronger gate stands in front and refuses upstream, "
        "so this is defence-in-depth rather than a duplicate\n",
    )
    settings = _settings(tmp_path, "bash .claude/hooks/layered.sh")

    assert retired_but_registered(hooks, settings) == ([], None)


def test_a_thin_reason_does_not_buy_the_exemption(tmp_path):
    """Otherwise the marker becomes the way to quiet the check."""
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    _hook(hooks, "lazy.sh", "# SUPERSEDED by something\n# KEPT-REGISTERED: fine\n")
    settings = _settings(tmp_path, "bash .claude/hooks/lazy.sh")

    found, _ = retired_but_registered(hooks, settings)

    assert found == ["lazy.sh"]


def test_unreadable_settings_is_an_error_for_this_direction_too(tmp_path):
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    settings = tmp_path / "settings.json"
    settings.write_text("{not json", encoding="utf-8")

    found, error = retired_but_registered(hooks, settings)

    assert found == []
    assert error is not None


def test_this_checkout_has_no_retired_but_registered_hooks():
    """The regression guard for the nineteen-day instance."""
    found, error = retired_but_registered(
        REPO / ".claude" / "hooks", REPO / ".claude" / "settings.json"
    )

    assert error is None, error
    assert found == [], (
        f"declared retired and still registered: {found}. Each fires beside whatever "
        "replaced it, with its own silent-swallow live underneath the fix for it. "
        "Unregister it, or drop the marker if the retirement was abandoned."
    )


def test_this_checkout_has_no_phantom_registrations():
    """The regression guard. This is the one that would have caught #438."""
    found, error = phantoms(REPO / ".claude" / "hooks", REPO / ".claude" / "settings.json")

    assert error is None, error
    assert found == [], (
        f"registered with no file on disk: {found}. Every matching tool call runs "
        "bash against a path that does not exist and collects exit 127 -- no gate "
        "runs and nothing says so. Remove the registration, or restore the file if "
        "the deletion was the mistake."
    )
