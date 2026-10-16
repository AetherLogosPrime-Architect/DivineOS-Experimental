"""Moving the journal out of the gate lists must not move a single entry.

2026-10-12: the comments above the shared shell pattern and above the build gate's own tuple
had grown into diaries. They moved into docs/gate_list_history/ and each list kept one short
current note. A comment move cannot change behaviour unless it changes quoting or line
structure, so this pins what the code DOES: the real tuple and the real pattern, lifted out of
the real files, compared with a stored copy. Adding a command on purpose means changing the
stored copy in the same diff, which is the decision the lists ask for.
"""

import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[1]
HOOK = REPO / ".claude" / "hooks" / "check-council-required.sh"
LIB = REPO / ".claude" / "hooks" / "lib" / "remedy_allowlist.sh"
NL = chr(10)

EXPECTED_FILING_COMMANDS = (
    "divineos council log",
    "divineos council walk",
    "divineos council authorize-bypass",
    "divineos council emergency-skip",
    "divineos game-walk file",
    "divineos prereg assess",
    "divineos prereg file",
    "divineos prereg reviewing",
    "divineos audit submit",
    "divineos audit file-external-confirm",
    "divineos learn",
    "divineos correction",
    "python scripts/clear_correction_marker.py",
)

EXPECTED_PATTERN = (
    "^[[:space:]]*(divineos[[:space:]]+(briefing|preflight|goal[[:space:]]+add|"
    "reach[[:space:]]+(open|dispose)|learn|correction|corrections[[:space:]]+integrate|"
    "andrew-correction[[:space:]]+(integrate|defer)|compass-ops[[:space:]]+(observe|dismiss)|"
    "prereg[[:space:]]+(assess|overdue|file|reviewing)|game-walk[[:space:]]+file|"
    "his[[:space:]]+(pending|sort)|integrate|claims[[:space:]]+assess|"
    "audit[[:space:]]+submit-round|ask|recall|context|decide|extract|sleep|"
    "council[[:space:]]+(log|walk|authorize-bypass))|python[[:space:]]+.*clear_correction_marker\\.py)"
)


def _lifted_tuple() -> tuple:
    src = HOOK.read_text(encoding="utf-8")
    start = src.index("_ARTIFACT_FILING_COMMANDS = (")
    end = src.index(NL + ")" + NL, start) + 2
    namespace: dict = {}
    exec(compile(src[start:end], "hook", "exec"), namespace)
    return namespace["_ARTIFACT_FILING_COMMANDS"]


def _lifted_pattern() -> str:
    src = LIB.read_text(encoding="utf-8")
    found = re.search(r"^_REMEDY_PATTERNS='(.*)'$", src, re.MULTILINE)
    assert found, "the shared pattern line could not be found, so nothing was compared"
    return found.group(1)


def test_the_build_gate_filing_list_is_exactly_what_it_was():
    assert _lifted_tuple() == EXPECTED_FILING_COMMANDS


def test_the_shared_remedy_pattern_is_exactly_what_it_was():
    assert _lifted_pattern() == EXPECTED_PATTERN


def test_control_the_lift_can_see_a_difference():
    """CONTROL: the comparison fails when an entry differs, so a pass above means something."""
    assert _lifted_tuple() != EXPECTED_FILING_COMMANDS + ("divineos extra",)
    assert _lifted_pattern() != EXPECTED_PATTERN.replace("briefing|", "")
