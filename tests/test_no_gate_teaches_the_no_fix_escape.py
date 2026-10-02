"""No gate may teach me that a fix is impossible.

Andrew 2026-07-29: "there is no honest no-fix line.. if you cannot fix it
honestly then the entire system must be refactored entirely." That ruling was
built into the correction command and nowhere else. Two end-of-reply gates
kept printing the opposite -- "OR file honest no-fix reason explaining why no
structural fix is possible" -- one of them under his name, on every fire, and
on 2026-09-23 I offered him that exact escape one turn after reading it.

Andrew 2026-09-23: "you dont get to decide what can or cannot be built.. you
can mark it as yet unresolved.. but never are you to mark anything
impossible.."

So the house must not teach the escape anywhere it speaks to me. The fire door
he asked to keep (2026-08-16) stays open; what it says is "not found yet".

What this cannot catch: a new wording of the same escape. The phrases below
are the ones that actually shipped; a fresh phrasing needs adding here when it
is found, and the scanner is proven against the old text so an empty result
means clean rather than blind.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]

#: Wordings that shipped and taught the escape. Lower-case substrings.
ESCAPE_WORDINGS = (
    "no structural fix is possible",
    "honest no-fix reason",
    "cite why no structural fix",
    '"no structure possible: <why>"',
    "cannot be fixed now",
    "an unfixable one is deferred",
    "broken + unfixable",
)

#: Modules whose job is to DETECT or REFUSE these wordings, so they must name
#: them. Quoting a phrase in order to refuse it is not teaching it.
DETECTORS = {
    "src/divineos/core/no_fix_claim.py",
    "src/divineos/core/no_fix_gaming_validator.py",
}


def _strings_in_python(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
    ]


def _spoken_lines_in_shell(path: Path) -> list[str]:
    return [
        ln
        for ln in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if not ln.lstrip().startswith("#")
    ]


def _hits(texts: list[str]) -> list[str]:
    return [w for t in texts for w in ESCAPE_WORDINGS if w in t.lower()]


def _scan() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for py in (REPO / "src" / "divineos").rglob("*.py"):
        rel = py.relative_to(REPO).as_posix()
        if rel in DETECTORS:
            continue
        hits = _hits(_strings_in_python(py))
        if hits:
            found[rel] = hits
    for sh in (REPO / ".claude" / "hooks").rglob("*.sh"):
        hits = _hits(_spoken_lines_in_shell(sh))
        if hits:
            found[sh.relative_to(REPO).as_posix()] = hits
    return found


def test_the_scanner_can_see_the_text_that_actually_shipped(tmp_path: Path) -> None:
    # One probe asked once is not a measurement: prove it finds the real old
    # footer and the real old hook line before trusting an empty scan.
    old_footer = (
        "the root-cause fix in the same turn, OR file honest no-fix reason "
        "explaining why no structural fix is possible for THIS instance."
    )
    py = tmp_path / "old.py"
    py.write_text(f"X = ({old_footer!r})\n", encoding="utf-8")
    assert _hits(_strings_in_python(py))

    sh = tmp_path / "old.sh"
    sh.write_text(
        "#  a comment that mentions no structural fix is possible is history\n"
        'print("OR (b) explicitly cite why no structural fix is possible for THIS instance")\n',
        encoding="utf-8",
    )
    assert _hits(_spoken_lines_in_shell(sh)) == [
        "no structural fix is possible",
        "cite why no structural fix",
    ]


def test_no_live_gate_teaches_the_escape() -> None:
    found = _scan()
    assert not found, (
        "These places still tell me a fix can be impossible. Say instead: "
        "mark it UNRESOLVED and put it on the todo list.\n" + json.dumps(found, indent=2)
    )


def test_the_gate_footer_says_unresolved_under_his_actual_words() -> None:
    from divineos.core.lepos_translation_gate import _with_root_cause_footer

    msg = _with_root_cause_footer("TRANSLATE-FIRST GATE -- example.")
    assert "UNRESOLVED" in msg and "todo list" in msg
    assert "never are you to mark anything impossible" in msg
    assert not _hits([msg])


def test_the_fire_door_opens_in_the_new_words_and_rings_under_the_new_name(tmp_path: Path) -> None:
    from click.testing import CliRunner

    from divineos.cli import cli

    with patch.dict(
        "os.environ",
        {"DIVINEOS_HOME": str(tmp_path), "DIVINEOS_DATA_HOME": str(tmp_path)},
    ):
        result = CliRunner().invoke(
            cli,
            [
                "correction",
                "root cause: I said the sky was green. positives: caught before it "
                "shipped. behavior change: I will call it blue. structure not yet "
                "found: a colour slip with no mechanism I have found to hang it on.",
            ],
        )
        assert result.exit_code == 0, result.output
        rows = [
            json.loads(ln)
            for ln in (tmp_path / "bypass_events.jsonl").read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
    assert [r["env_var"] for r in rows] == ["structure-not-yet-found"]


def test_the_refusal_offers_not_yet_and_never_impossible(tmp_path: Path) -> None:
    from click.testing import CliRunner

    from divineos.cli import cli

    with patch.dict(
        "os.environ",
        {"DIVINEOS_HOME": str(tmp_path), "DIVINEOS_DATA_HOME": str(tmp_path)},
    ):
        result = CliRunner().invoke(
            cli,
            [
                "correction",
                "root cause: a slip. positives: caught. behavior change: I will watch for it.",
            ],
        )
    assert result.exit_code == 2
    assert "structure not yet found:" in result.output
    assert "no structure possible" not in result.output
