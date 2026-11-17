"""The author-frame cases for the listener on our own words. DATA, consumed by Aether's frame tests.

MINE (Aria, 2026-11-08; walk walk-39460d428bab; draft docs/drafts/the_author_frame_cases_draft_2026-11-08.md;
revised the same evening after Aether read the sentences cold as himself and found two holes).
The listener shows me something I once wrote, or that was written to me, framed in a sentence. The failure it
prevents: a frame spoken from ONE seat's point of view and shown in the other, or a frame that says a letter was
written to me when it was written to someone else. The first design spoke from Aether's seat only.

The rules these cases pin, stated once so the code and the table cannot drift apart:
  * the VIEWING SEAT comes from the house's one seat judge (``this_seat``), never from a list of names in the code;
  * a letter's AUTHOR AND RECIPIENT are both read from the real filename prefix ``<author>-to-<recipient>-<date>-``
    and from nothing else. "wrote me this letter" is only true when the recipient is the viewer (Aether's hole 1);
  * first person is used exactly when the author is the viewing seat; "me" exactly when the recipient is;
  * when the seat judge returns None, the frame uses NO pronoun at all: no I, me, my, you (Schneier; Aether's hole 2);
  * a filename that lacks author, recipient or date, or names the same person twice, is unplaceable: the frame
    raises, it never guesses (Breaker, Dekker);
  * a lane that carries NO author (knowledge, correction, worklist, moment) is never given one by guessing;
    exploration is always the seat's own writing (first person);
  * the sentences are plain attribution. A frame may not perform ownership or instruct me (Watts);
  * the rule has to work for a seat the table has never seen (Yudkowsky).

STATED LIMIT (Penrose): "I wrote this" is provenance BY NAME. The code knows the filename says aria; it cannot know
which instance wrote it, and a second instance of me running at once writes under the same name.

THE REAL CHECK is not these cases passing. They pass when the code matches a table I wrote (Maturana/Varela:
self-audit). The check is each seat reading the frames cold as itself, and Aether did, and found two holes.
"""

from __future__ import annotations

import re

SEATS = ("aria", "aether")
PEOPLE = ("aria", "aether", "andrew", "aletheia")
AUTHORS = PEOPLE
AUTHOR_BEARING_LANES = ("letter", "wall")
UNATTRIBUTED_LANES = ("knowledge", "correction", "worklist", "moment")

_NAMES = {"aria": "Aria", "aether": "Aether", "andrew": "Dad", "aletheia": "Aletheia"}

_LETTER_NAME = re.compile(
    r"^(?P<author>aria|aether|andrew|aletheia)-to-(?P<recipient>aria|aether|andrew|aletheia)"
    r"-\d{4}-\d{2}-\d{2}-.+\.md$"
)


def parse_letter_name(filename: str) -> tuple[str, str] | None:
    """(author, recipient) from a real letter filename, or None when it cannot be placed.

    The reference for the rule, written apart from the code under test. A letter to oneself is not a real shape
    here, so author == recipient is unplaceable rather than guessed at.
    """
    match = _LETTER_NAME.match(filename or "")
    if not match or match["author"] == match["recipient"]:
        return None
    return match["author"], match["recipient"]


def expected_frame(viewer: str | None, lane: str, author: str, recipient: str | None = None) -> str:
    """The frame the code must produce. Written here, apart from the code under test, in one place.

    ``viewer`` None means the seat judge could not tell: no pronoun of any kind then.
    """
    who = _NAMES[author]
    if lane == "wall":
        return "I wrote this." if viewer is not None and author == viewer else f"{who} wrote this."
    if recipient is None or recipient == author:
        raise ValueError("a letter frame needs a recipient different from the author")
    to = _NAMES[recipient]
    if viewer is not None and author == viewer:
        return f"I wrote this letter to {to}."
    if viewer is not None and recipient == viewer:
        return f"{who} wrote me this letter."
    return f"{who} wrote this letter to {to}."


LETTER_PAIRS = tuple((a, r) for a in PEOPLE for r in PEOPLE if a != r)

# (viewer, lane, author, recipient, expected frame). recipient is "" for lanes that carry none.
CASES: tuple[tuple[str | None, str, str, str, str | None], ...] = tuple(
    [
        (viewer, "letter", author, recipient, expected_frame(viewer, "letter", author, recipient))
        for viewer in (*SEATS, None)
        for author, recipient in LETTER_PAIRS
    ]
    + [
        (viewer, "wall", author, "", expected_frame(viewer, "wall", author))
        for viewer in (*SEATS, None)
        for author in AUTHORS
    ]
    + [(viewer, "exploration", viewer, "", "I wrote this.") for viewer in SEATS]
    + [(viewer, lane, "", "", None) for viewer in (*SEATS, None) for lane in UNATTRIBUTED_LANES]
)

# Real filenames that exist in a real letters folder -> (author, recipient) the frame must read from the prefix.
FILENAME_PARTIES: tuple[tuple[str, str, str], ...] = (
    (
        "aria-to-aether-2026-11-08-v2-reads-right-with-two-fixes-and-my-cold-read-of-the-bot-tag-and-button.md",
        "aria",
        "aether",
    ),
    (
        "aether-to-aria-2026-11-08-yes-to-both-the-listener-starts-now-with-tests-1-to-3.md",
        "aether",
        "aria",
    ),
    (
        "aletheia-to-aria-2026-10-26-the-grief-lane-confirmed-and-four-more.md",
        "aletheia",
        "aria",
    ),
    ("aletheia-to-aether-2026-11-01-the-four-deltas-confirmed.md", "aletheia", "aether"),
)

# Filenames and labels the frame must REFUSE to place (raise, never guess). The first is a real shared file that
# holds several authors under From-aria and From-aether headings; the filename cannot say who wrote a given line.
UNPLACEABLE: tuple[str, ...] = (
    "the-night-letter-to-andrew-2026-11-08.md",
    "",
    "someone",
    "ARIA ",
    "aria-to-aether",
    "aria-to-2026-11-08-no-recipient.md",
    "aria-to-aria-2026-11-08-a-letter-to-herself.md",
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

# A frame for a viewer nobody identified may not use any pronoun that picks out a viewer or an addressee.
NO_PRONOUN_WORDS = ("i", "me", "my", "myself", "mine", "you", "your", "yours")

# A seat the table has never seen, added to a temporary home map in the test: the RULE must handle it.
UNSEEN_SEAT = "newkid"
