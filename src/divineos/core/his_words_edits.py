"""Edits to his words: typo fixes he confirmed, logged, never replacing what he typed.

WHY THIS EXISTS. Andrew, 2026-10-07, on the door that holds a quote of him
unless it is his exact words:

    "show the fixed spelling, but always check with me first"

and earlier, on the same rule: his words "are editable by me or if there are
obvious spelling errors or typos that they are corrected as well, the editing of
them can be logged but they cannot be made uneditable".

That was the rule until 2026-10-28, when he added the other half, in his words:
"for any simple spelling errors or typos? they can be corrected automatically.. its
only for whole word typos that need my correction" (he typed "sky is blu" as the
slip to fix quietly and "sky is red" for "blue" as the one to ask about). So now:

  - a SLIP (his word is not a whole word, the quoted one is, one obvious fix) passes
    on its own, and every such pass is logged beside the edits so he can look later;
  - a REAL WORD in place of another real word is held and asked about, as before.
    When he says yes, the edit goes into an append-only log with his own words of
    yes beside it, and the corrected wording is added to the index BESIDE the
    original: what he typed still passes, and nothing he typed is ever removed.

WHAT THIS CAN AND CANNOT SEE, so a quiet is never read as a check:
a slip needs his word to not be a whole vocabulary word and the quoted word to be,
sharing a first letter, differing by at most one letter of length, and alike enough
(ratio 0.8). Words under five letters count only as the last letter forgotten
("blu"), never otherwise, and his contractions without the apostrophe (dont, thats,
cant) are never slips. A real word swapped for another real word is never a slip,
which is the safe direction. Only quotes of a single run of words are judged; a
quote cut with "..." is held as before. Where this guesses wrong, he sees the
quote later and corrects it.
"""

from __future__ import annotations

import difflib
import json
from pathlib import Path

from divineos.core import light_embedder
from divineos.core.his_words import MARKS_DIR, words

EDITS_PATH = MARKS_DIR / "edits_log.jsonl"
AUTO_FIXES_PATH = MARKS_DIR / "auto_fixes_log.jsonl"
MIN_TYPO_LEN = 5
MIN_DROPPED_LETTER_LEN = 3
USED_IN_MESSAGES = 3
MAX_FIXES = 2
_MIN_RATIO = 0.8
# His contractions without the apostrophe: how he writes, never a slip.
_CONTRACTIONS = frozenset(
    "dont cant wont isnt arent wasnt werent didnt doesnt hasnt havent hadnt couldnt "
    "shouldnt wouldnt im ive ill youre theyre whats thats".split()
)


def is_typo_of(typed: str, meant: str, used: frozenset[str] = frozenset()) -> bool:
    """Whether ``typed`` looks like a slip for ``meant``, by the rules in the docstring.

    ``used`` is the words he writes in many messages: a forgotten last letter that
    is one of those ("car" for "care") is a real word of his, so it is asked about.
    The vocabulary alone cannot decide it, because it holds fragments like "blu".
    """
    if typed == meant or typed in _CONTRACTIONS:
        return False
    if typed[0] != meant[0] or abs(len(typed) - len(meant)) > 1:
        return False
    # The last letter forgotten ("blu" for "blue") is the one short slip he named.
    dropped_last = len(meant) == len(typed) + 1 and meant.startswith(typed)
    if len(typed) < (MIN_DROPPED_LETTER_LEN if dropped_last else MIN_TYPO_LEN):
        return False
    # "thats" is "that" plus a letter, which is how he writes a contraction, not a slip.
    if (typed.startswith(meant) or meant.startswith(typed)) and not dropped_last:
        return False
    if difflib.SequenceMatcher(None, typed, meant).ratio() < _MIN_RATIO:
        return False
    meant_is_word = light_embedder.is_whole_word(meant) is True
    if dropped_last:
        return meant_is_word and typed not in used
    return light_embedder.is_whole_word(typed) is False and meant_is_word


def typed_window(
    quote: str, message_words: list[str], used: frozenset[str] = frozenset()
) -> list[str] | None:
    """The words he typed where ``quote`` means them, if every difference is a slip."""
    qw = words(quote)
    n = len(qw)
    if n < 3 or n > len(message_words):
        return None
    wanted = set(qw)
    for i in range(len(message_words) - n + 1):
        window = message_words[i : i + n]
        misses = [(a, b) for a, b in zip(window, qw) if a != b]
        if not misses or len(misses) > MAX_FIXES:
            continue
        if len(wanted & set(window)) < n - MAX_FIXES:
            continue
        if all(is_typo_of(a, b, used) for a, b in misses):
            return window
    return None


def read_edits(path: Path = EDITS_PATH) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out: list[dict] = []
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("was") and row.get("now") and row.get("proof"):
            out.append(row)
    return out


def append_edit(was: str, now: str, proof: str, when: str, path: Path = EDITS_PATH) -> dict:
    """Add one edit. Append only: nothing in the log is rewritten or removed."""
    row = {"when": when, "was": " ".join(words(was)), "now": " ".join(words(now)), "proof": proof}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    return row


def log_auto_fixes(fixes: list[tuple[str, str]], when: str, path: Path = AUTO_FIXES_PATH) -> None:
    """Record each slip the door passed on its own, so he can look later. Append only."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for quote, typed in fixes:
            fh.write(json.dumps({"when": when, "quote": quote, "he_typed": typed}) + "\n")


def _contains(joined: list[str], phrase: str) -> bool:
    needle = " " + " ".join(words(phrase)) + " "
    return any(needle in j for j in joined)


def corrected_copies(
    messages: list[tuple[str, str]], joined: list[str], edits: list[dict]
) -> list[tuple[str, str]]:
    """The original message with each proven edit applied, to sit BESIDE the original.

    An edit counts only when the words he typed (``was``) and his words of yes
    (``proof``) are both exact inside something he typed. A row written by hand
    with neither is ignored, so the log cannot be used to launder a misquote.
    """
    proven = [e for e in edits if _contains(joined, e["was"]) and _contains(joined, e["proof"])]
    out: list[tuple[str, str]] = []
    for (date, _), j in zip(messages, joined):
        fixed = j
        for e in proven:
            was = " " + " ".join(words(e["was"])) + " "
            now = " " + " ".join(words(e["now"])) + " "
            fixed = fixed.replace(was, now)
        if fixed != j:
            out.append((date, fixed.strip()))
    return out
