"""The open-ask hold lets this seat's doorbell through however it is typed.

2026-10-05: with a question to Dad open, the hold refused the doorbell whenever
a cd into this repo came first -- how it is always typed -- because its check
compared exact words, while the doorbell's own stop check demanded a re-arm.
Two gates holding each other's key. The hook now asks the house's one doorbell
judge (pre_tool_use_gate._is_doorbell_rearm). walk-fab47647daca.
Draft (live house): docs/drafts/the_open_ask_hold_lets_the_doorbell_through_draft_2026-10-05.md
"""

from __future__ import annotations

import pathlib

import pytest

from divineos.core import sibling_audit_rounds
from divineos.core.auto_commit import find_repo_root
from divineos.hooks import pre_tool_use_gate

REPO = pathlib.Path(__file__).resolve().parents[1]
HOOK = REPO / ".claude" / "hooks" / "an-open-ask-holds-the-work.sh"
NL = chr(10)


@pytest.fixture
def own_doorbell(monkeypatch):
    """The hook's real _own_doorbell, lifted from the hook, never copied."""
    monkeypatch.setattr(sibling_audit_rounds, "this_seat", lambda: "aether")
    src = HOOK.read_text(encoding="utf-8")
    start = src.index("def _own_doorbell(cmd):")
    end = src.index(NL + NL + NL + "def _is_exempt", start)
    ns: dict = {}
    exec(src[start:end], ns)
    return ns["_own_doorbell"]


ROOT = find_repo_root(pathlib.Path(pre_tool_use_gate.__file__))


def test_the_bare_bell_passes(own_doorbell):
    assert own_doorbell("bash scripts/letter_doorbell.sh aether")


def test_the_bell_behind_a_cd_into_this_repo_passes(own_doorbell):
    # The way it is always typed, and the case the exact-words copy refused.
    assert own_doorbell(f'cd "{ROOT.as_posix()}" && bash scripts/letter_doorbell.sh aether')


@pytest.mark.parametrize(
    "command",
    [
        "bash scripts/letter_doorbell.sh aria",  # another seat's bell
        "bash scripts/letter_doorbell.sh aether && git push",  # a ride-along
        'cd "C:/somewhere/else" && bash scripts/letter_doorbell.sh aether',  # elsewhere
    ],
)
def test_anything_else_is_still_held(own_doorbell, command):
    assert not own_doorbell(command)


def test_an_unknown_seat_holds_the_bell(own_doorbell, monkeypatch):
    monkeypatch.setattr(sibling_audit_rounds, "this_seat", lambda: None)
    assert not own_doorbell("bash scripts/letter_doorbell.sh aether")
