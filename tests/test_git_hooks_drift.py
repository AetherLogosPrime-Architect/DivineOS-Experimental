"""Installed git hooks are compared to setup both ways, and nothing is overwritten.
Draft: docs/drafts/installed_hooks_match_setup_draft_2026-10-04.md."""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core.git_hooks_drift import check_repo, compare, render, setup_hooks

SETUP = """#!/bin/bash
cat > "$HOOKS_DIR/pre-commit" << 'EOF'
#!/bin/bash
echo one
echo two
EOF
cat > "$HOOKS_DIR/commit-msg" << 'EOF'
#!/bin/bash
echo merge-resolution check
EOF
"""


@pytest.fixture
def hooks(tmp_path: Path) -> Path:
    d = tmp_path / "hooks"
    d.mkdir()
    (d / "pre-commit").write_text("#!/bin/bash\necho one\necho two\n")
    (d / "commit-msg").write_text("#!/bin/bash\necho merge-resolution check\n")
    (d / "pre-push.sample").write_text("sample")
    return d


def test_setup_hooks_are_read_by_name():
    assert set(setup_hooks(SETUP)) == {"pre-commit", "commit-msg"}


def test_matching_hooks_say_nothing(hooks):
    assert render(compare(SETUP, hooks)) == ""


def test_both_directions_are_named(hooks):
    # Tonight's real shape: one hook lacks a setup check, the other has a local one.
    (hooks / "commit-msg").write_text("#!/bin/bash\n")
    (hooks / "pre-commit").write_text("#!/bin/bash\necho one\necho two\necho deletion skip\n")
    report = compare(SETUP, hooks)
    by = {h.name: h for h in report.drifted}
    assert by["commit-msg"].only_in_setup == ("echo merge-resolution check",)
    assert by["pre-commit"].only_installed == ("echo deletion skip",)
    text = render(report)
    assert "Nothing was overwritten" in text and "first real run" in text


def test_nothing_is_overwritten(hooks):
    (hooks / "commit-msg").write_text("local\n")
    compare(SETUP, hooks)
    assert (hooks / "commit-msg").read_text() == "local\n"


def test_a_missing_hook_is_missing(hooks):
    (hooks / "commit-msg").unlink()
    assert "commit-msg: MISSING" in render(compare(SETUP, hooks))


def test_hooks_setup_does_not_write_are_named_not_judged(hooks):
    (hooks / "commit-msg.bak-20260807").write_text("old")
    report = compare(SETUP, hooks)
    assert report.not_judged == ("commit-msg.bak-20260807",)


def test_unreadable_setup_is_never_a_match(tmp_path):
    text = render(check_repo(tmp_path))
    assert "could not read" in text and "Not a match" in text


def test_the_real_setup_is_read_whole():
    # The real file, not my picture of it: every hook it installs is found.
    repo = Path(__file__).resolve().parents[1]
    names = set(setup_hooks((repo / "setup" / "setup-hooks.sh").read_text(encoding="utf-8")))
    assert {
        "pre-commit",
        "commit-msg",
        "pre-push",
        "post-commit",
        "prepare-commit-msg",
        "post-merge",
    } <= names
