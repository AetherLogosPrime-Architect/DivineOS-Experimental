"""A gate's remedy is a remedy however the program is typed.

2026-10-04: from every workbench I type divineos with its path, the only way to
reach that workbench's install, and both the build gate's private reader and the
shared remedy list compared the raw first word, so every other gate's exit read
as building. Draft: docs/drafts/a_remedy_is_a_remedy_however_it_is_typed_draft_2026-10-04.md.
Spelling only: membership and the every-segment rule are unchanged (Aria's read).
"""

from __future__ import annotations

import pathlib

import pytest

from divineos.core.command_parsing import program_name
from divineos.core.remedy_allowlist import is_remedy

REPO = pathlib.Path(__file__).resolve().parents[1]
HOOK = REPO / ".claude" / "hooks" / "check-council-required.sh"
NL = chr(10)
_END = "return all(' '.join(seg).startswith(_ARTIFACT_FILING_COMMANDS) for seg in acts)"
EXE = '"C:/DIVINE OS/DivineOS-Experimental/.venv/Scripts/divineos.exe"'


@pytest.fixture(scope="module")
def is_filing():
    """The real build-gate function, lifted from the hook, never copied."""
    src = HOOK.read_text(encoding="utf-8")
    start = src.rindex(NL, 0, src.index("_ARTIFACT_FILING_COMMANDS = ("))
    end = src.index(_END) + len(_END)
    ns: dict = {}
    exec(src[start:end].replace(chr(92) * 2, chr(92)), ns)
    return ns["_is_artifact_filing"]


@pytest.mark.parametrize(
    "token,name",
    [
        ("divineos", "divineos"),
        (".venv/Scripts/divineos.exe", "divineos"),
        ("C:\\x\\divineos.EXE", "divineos"),
        ("/usr/bin/git", "git"),
        ("rm", "rm"),
    ],
)
def test_the_program_is_read_by_name(token, name):
    assert program_name(token) == name


@pytest.mark.parametrize(
    "spelling",
    ["divineos", ".venv/Scripts/divineos.exe", EXE, "PYTHONPATH=C:/w/src divineos"],
)
def test_the_build_gate_lets_a_remedy_through_however_it_is_typed(is_filing, spelling):
    assert is_filing(f"{spelling} prereg assess prereg-x --outcome INCONCLUSIVE --notes n")
    assert is_filing(f"cd C:/w && {spelling} game-walk file --mechanism m --route r --edit e")


@pytest.mark.parametrize("spelling", ["divineos", ".venv/Scripts/divineos.exe", EXE])
def test_the_shared_list_lets_a_remedy_through_however_it_is_typed(spelling):
    assert is_remedy(f"{spelling} prereg assess prereg-x --outcome INCONCLUSIVE --notes n")


@pytest.mark.parametrize(
    "command",
    [
        # Aria: a chain is many commands, and every one must pass.
        "cd x && rm -rf y && divineos prereg assess p",
        f"{EXE} prereg assess p && git push",
        "/usr/bin/git commit -m x",
        "PYTHONPATH=x .venv/Scripts/divineos.exe council log --edit e ; git commit -m y",
    ],
)
def test_anything_else_in_the_chain_is_still_refused(is_filing, command):
    assert not is_filing(command)
    assert not is_remedy(command)


def test_the_one_refusal_this_week_it_now_lets_through_is_a_remedy(is_filing):
    # Run over all 800 commands refused in the 2026-10-04 session, exactly one
    # newly passes: council walks behind a bare folder assignment. Judged a
    # remedy; every other refusal is unchanged in both lists.
    assert is_filing(
        'cd "C:/x" && S="C:/s" && divineos council walk --edit e --lens Popper --problem p'
        ' < "$S/a.txt" && divineos council walk --edit e --lens Norman --problem p < "$S/b.txt"'
    )
