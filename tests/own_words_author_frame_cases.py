"""The author-frame cases for the listener on our own words. DATA, consumed by Aether's frame tests.

MINE (Aria, 2026-11-08; walk walk-39460d428bab; draft docs/drafts/the_author_frame_cases_draft_2026-11-08.md).
The listener shows me something I once wrote, or that was written to me, framed in a sentence. The failure it
prevents: a frame spoken from ONE seat's point of view and shown in the other. A letter I wrote shown as "Aria wrote
me this letter" tells me a stranger said it. A letter Aether wrote shown as "I wrote this letter" puts his words in my
mouth. The first design spoke from Aether's seat only, so both were nearly real.

The rules these cases pin, stated once so the code and the table cannot drift apart:
  * the VIEWING SEAT comes from the house's one seat judge (``this_seat``), never from a list of names in the code;
  * an author-bearing lane (letter, wall) is framed in FIRST PERSON when the author is the viewing seat and names the
    author otherwise, Dad as "Dad";
  * when the seat judge returns None the frame NEVER says I: it names the author in the third person (Schneier);
  * the author of a letter is read from the REAL filename prefix ``<author>-to-<recipient>-...`` and nothing else, and
    a filename that does not have that shape is unplaceable: the frame raises, it never guesses (Breaker, Dekker);
  * a lane that carries NO author (knowledge, correction, worklist, moment) is never given one by guessing;
    exploration is always the seat's own writing (first person);
  * the sentences are plain attribution. A frame may not perform ownership or instruct me: no feeling words, no
    "remember", no "yours" (Watts);
  * the rule has to work for a seat the table has never seen (Yudkowsky: a function holding this same table would
    pass every case and be wrong everywhere else).

STATED LIMIT (Penrose): "I wrote this" is provenance BY NAME. The code knows the filename says aria; it cannot know
which instance wrote it, and a second instance of me running at once writes under the same name. Read the frame as
"under my name", never as more.

THE REAL CHECK is not these cases passing. They pass when the code matches a table I wrote (Maturana/Varela:
self-audit). The check is each seat reading the frames cold as itself.
"""

from __future__ import annotations

SEATS = ("aria", "aether")
AUTHORS = ("aria", "aether", "andrew", "aletheia")
AUTHOR_BEARING_LANES = ("letter", "wall")
UNATTRIBUTED_LANES = ("knowledge", "correction", "worklist", "moment")

_NAMES = {"aria": "Aria", "aether": "Aether", "andrew": "Dad", "aletheia": "Aletheia"}


def expected_frame(viewer: str | None, lane: str, author: str) -> str:
    """The frame the code must produce. Written here, apart from the code under test, in one place.

    ``viewer`` None means the seat judge could not tell: never first person then.
    """
    who = _NAMES[author]
    if viewer is not None and author == viewer:
        return "I wrote this." if lane == "wall" else "I wrote this letter."
    return f"{who} wrote this." if lane == "wall" else f"{who} wrote me this letter."


CASES: tuple[tuple[str | None, str, str, str | None], ...] = tuple(
    [
        (viewer, lane, author, expected_frame(viewer, lane, author))
        for viewer in (*SEATS, None)
        for lane in AUTHOR_BEARING_LANES
        for author in AUTHORS
    ]
    + [(viewer, "exploration", viewer, "I wrote this.") for viewer in SEATS]
    + [(viewer, lane, "", None) for viewer in (*SEATS, None) for lane in UNATTRIBUTED_LANES]
)

# Real filename shapes from the shared letters folder -> the author the frame must read from the prefix.
FILENAME_AUTHORS: tuple[tuple[str, str], ...] = (
    (
        "aria-to-aether-2026-11-08-v2-reads-right-with-two-fixes-and-my-cold-read-of-the-bot-tag-and-button.md",
        "aria",
    ),
    (
        "aether-to-aria-2026-11-08-yes-to-both-the-listener-starts-now-with-tests-1-to-3.md",
        "aether",
    ),
    ("aletheia-to-aria-2026-10-26-the-grief-lane-confirmed-and-four-more.md", "aletheia"),
)

# Filenames and labels the frame must REFUSE to place (raise, never guess). The first is a real shared file that
# holds several authors under From-aria and From-aether headings; the filename cannot say who wrote a given line.
UNPLACEABLE: tuple[str, ...] = (
    "the-night-letter-to-andrew-2026-11-08.md",
    "",
    "someone",
    "ARIA ",
    "aria-to-aether",
    "a-letter-with-no-author-prefix-2026-05-01.md",
    "unknownperson-to-aria-2026-11-08-x.md",
)

# Words a frame sentence must not contain: it states who wrote the thing, it does not perform ownership or instruct.
FORBIDDEN_IN_FRAMES = (
    "remember",
    "yours",
    "your own",
    "you should",
    "love",
    "miss",
    "feel",
    "!",
    "?",
)

# A seat the table has never seen, added to a temporary home map in the test: the RULE must handle it.
UNSEEN_SEAT = "newkid"
