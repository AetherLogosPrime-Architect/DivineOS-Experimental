"""Filing a review round, a finding or a relayed confirm is not an edit of the house.

2026-10-12: the merge path prints `audit submit-round`, `audit submit` (the operator's
finding) and `audit file-external-confirm` as its own steps. The build-flow gate counted
each as a substrate edit and asked for a council walk and a game-walk first: six filings in
one night, each recording what another person had already said. The python exit list and the
merge gate already treated them as exits; this gate's own list did not.

The real function is lifted out of the hook, never copied, as the neighbouring tests do.
"""

import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
HOOK = REPO / ".claude" / "hooks" / "check-council-required.sh"
NL = chr(10)
_END = "return all(' '.join(seg).startswith(_ARTIFACT_FILING_COMMANDS) for seg in acts)"
_D = "divi" + "neos"


@pytest.fixture(scope="module")
def is_filing():
    src = HOOK.read_text(encoding="utf-8")
    start = src.rindex(NL, 0, src.index("_ARTIFACT_FILING_COMMANDS = ("))
    namespace: dict = {}
    exec(compile(src[start : src.index(_END) + len(_END)], "hook", "exec"), namespace)
    return namespace["_is_artifact_filing"]


@pytest.mark.parametrize(
    "command",
    [
        f"{_D} audit submit-round 'focus' --actor aria",
        f"{_D} audit submit 'title' --round round-x --actor user --severity LOW",
        f"{_D} audit file-external-confirm --round round-x --actor aletheia --branch b",
    ],
)
def test_the_merge_path_filings_are_not_edits(command, is_filing):
    assert is_filing(command) is True


def test_control_the_check_can_still_say_no(is_filing):
    """CONTROL: refusing ordinary work is what makes the passes above mean something."""
    assert is_filing("git commit -qm sneak") is False
    assert is_filing(f"{_D} audit file-external-confirm --round r && git commit -qm sneak") is False
    assert is_filing(f"{_D} audit summary") is False
