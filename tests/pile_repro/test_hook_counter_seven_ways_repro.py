"""Fixtures (pile round eight): seven ways the fixed hook counter still reads a script wrongly.

The fix on `aria/the-hook-counter-reads-code-not-comments` makes `hook_layer.inventory()` ignore
whole-line comments and read `python -m divineos.x` as a call to the OS. Each fixture below is a tiny
script whose true answer is known by construction, and the test asks the counter for it. Seven are
expected failures; three controls show the counter is alive in both directions. The counter is not
changed. This file lives on a branch cut from the fix's branch, because the fix is not on main.

Five fixtures read ATTACHED when the script does not call the OS (the direction the author chose on
purpose: the fix's own comment says it "errs toward attached"). Two read DETACHED when the script does
call it, which is the direction nobody chose.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from divineos.core import hook_layer as hl


def _count(tmp_path: Path, body: str) -> str:
    hooks = tmp_path / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "h.sh").write_text(body, encoding="utf-8")
    (tmp_path / ".claude" / "settings.json").write_text(json.dumps({"hooks": {}}), encoding="utf-8")
    inv = hl.inventory(tmp_path)
    return "detached" if inv.detached_files else "attached"


def test_control_a_module_call_reads_attached(tmp_path):
    assert _count(tmp_path, '#!/bin/bash\n"$PYTHON_BIN" -m divineos.hooks.x\n') == "attached"


def test_control_a_script_with_no_call_reads_detached(tmp_path):
    assert _count(tmp_path, "#!/bin/bash\necho hello\n") == "detached"


def test_control_a_call_named_only_in_a_whole_line_comment_reads_detached(tmp_path):
    assert _count(tmp_path, "#!/bin/bash\n# run divineos briefing here\necho hello\n") == "detached"


NOT_A_CALL = [
    ("F1_message", '#!/bin/bash\necho "hint: run divineos briefing first"\n', "a printed hint"),
    (
        "F2_block_comment",
        "#!/bin/bash\n: <<'NOTE'\ndivineos briefing is what the old version ran\nNOTE\necho hello\n",
        "a comment written as a here-document to the no-op command",
    ),
    (
        "F3_dead_code",
        "#!/bin/bash\nif false; then\n  divineos briefing\nfi\necho hello\n",
        "a call that can never run (arguable: it is real code that is switched off)",
    ),
    (
        "F4_trailing_comment",
        "#!/bin/bash\necho hello  # divineos briefing\n",
        "a comment after code",
    ),
    (
        "F8_other_program",
        "#!/bin/bash\ngrep -m 1 divineos notes.txt\n",
        "grep searching a file for the word",
    ),
]

IS_A_CALL = [
    (
        "F5_quoted_module",
        '#!/bin/bash\n"$PYTHON_BIN" -m "divineos.hooks.x"\n',
        "a real call with the module name in quotes",
    ),
    (
        "F6_no_space",
        '#!/bin/bash\n"$PYTHON_BIN" -mdivineos.hooks.x\n',
        "a real call with no space after -m",
    ),
]


@pytest.mark.parametrize(
    "body",
    [
        pytest.param(
            body,
            id=name,
            marks=pytest.mark.xfail(strict=True, reason=f"reproduces: {why} reads attached"),
        )
        for name, body, why in NOT_A_CALL
    ],
)
def test_a_script_that_does_not_call_the_os_reads_detached(tmp_path, body):
    assert _count(tmp_path, body) == "detached"


@pytest.mark.parametrize(
    "body",
    [
        pytest.param(
            body,
            id=name,
            marks=pytest.mark.xfail(strict=True, reason=f"reproduces: {why} reads detached"),
        )
        for name, body, why in IS_A_CALL
    ],
)
def test_a_script_that_calls_the_os_reads_attached(tmp_path, body):
    assert _count(tmp_path, body) == "attached"
