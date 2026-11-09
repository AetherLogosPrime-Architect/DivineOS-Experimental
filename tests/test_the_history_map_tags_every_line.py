"""Every place the history map names says how that is known.

Dad, 2026-11-09: *"id like all of this stuff pieced together so its no longer lost
and fragmented."* A map that lists places without saying whether they were opened
reads as coverage it does not have. This pins the discipline from the walk
(walk-00e91db66693, Dijkstra and Dillahunty): no line without a source tag.
"""

import re
from pathlib import Path

MAP = Path(__file__).resolve().parent.parent / "docs" / "history" / "where_our_history_lives.md"
TAGS = re.compile(r"observed|told|inherited|not opened|not known|not yet compared", re.I)


def _lines_that_name_a_place():
    text = MAP.read_text(encoding="utf-8")
    out = []
    for line in text.splitlines():
        stripped = line.strip()
        if (
            stripped.startswith("|")
            and not set(stripped) <= set("|- :")
            and "Period" not in stripped
        ):
            out.append(stripped)
        elif stripped.startswith("- `") or stripped.startswith("- Aria's lists"):
            out.append(stripped)
    return out


def test_the_map_exists_and_names_places():
    assert MAP.is_file()
    assert len(_lines_that_name_a_place()) >= 8


def test_every_line_that_names_a_place_carries_a_tag():
    missing = [line[:90] for line in _lines_that_name_a_place() if not TAGS.search(line)]
    assert missing == [], "lines with no how-I-know tag: " + "; ".join(missing)


def test_the_map_says_what_is_missing():
    text = MAP.read_text(encoding="utf-8")
    assert "known to be missing" in text.lower()
    assert "March to mid-May" in text


def test_no_line_in_the_tracked_map_quotes_him():
    """Aria's check (2026-11-09): his own words live under family/andrew, which is not
    tracked. A quoted sentence of his in this tracked page would put his voice in the
    tracked tree. His quoted words are written in italics inside quotation marks."""
    text = MAP.read_text(encoding="utf-8")
    assert '*"' not in text and "*“" not in text


def test_the_unopened_secrets_folder_is_named_as_not_opened():
    text = MAP.read_text(encoding="utf-8")
    assert "9 - Secrets" in text and "was not opened" in text
