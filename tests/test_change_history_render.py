"""The change history page lists every pull request once, newest month first, and says so when a change has no description."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "render_change_history", _ROOT / "scripts" / "render_change_history.py"
)
render_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(render_mod)


def _row(n, state="MERGED", merged="", created="2026-10-01", is_="", did=""):
    return {
        "n": n,
        "title": f"title {n}",
        "state": state,
        "created": created,
        "merged": merged,
        "closed": "",
        "kind": "fix",
        "is": is_,
        "did": did,
    }


def test_every_row_appears_exactly_once():
    rows = [
        _row(1, merged="2026-09-03", is_="a", did="b"),
        _row(2, merged="2026-10-02", is_="c", did="d"),
    ]
    text = render_mod.render(rows)
    assert text.count("**#1**") == 1 and text.count("**#2**") == 1


def test_newest_month_comes_first():
    rows = [
        _row(1, merged="2026-09-03", is_="a", did="b"),
        _row(2, merged="2026-10-02", is_="c", did="d"),
    ]
    text = render_mod.render(rows)
    assert text.index("## October 2026") < text.index("## September 2026")


def test_a_change_with_no_description_says_so():
    text = render_mod.render([_row(5, merged="2026-10-02")])
    assert "(not yet described)" in text


def test_prose_never_states_the_state_the_tag_already_carries():
    rows = [
        _row(1, merged="2026-10-02", is_="a", did="Does a thing. Still open, awaiting a decision."),
        _row(2, merged="2026-10-02", is_="a", did="Does a thing; still waiting."),
        _row(3, merged="2026-10-02", is_="a", did="Does a thing. Not yet connected. Still open."),
        _row(4, merged="2026-10-02", is_="a", did="Does a thing. First slice, still open."),
    ]
    text = render_mod.render(rows).lower()
    assert (
        "still open" not in text and "still waiting" not in text and "not yet connected" not in text
    )
    assert text.count("does a thing.") == 4


def test_the_committed_rows_describe_every_change():
    rows = json.loads((_ROOT / "docs" / "change_history" / "rows.json").read_text(encoding="utf-8"))
    assert rows, "the committed history is empty"
    assert [r for r in rows if not r["is"] or not r["did"]] == []
