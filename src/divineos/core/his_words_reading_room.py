"""His words, read against our reply before it reaches him.

Andrew 2026-09-26: *"i dont need my words brought back to me.. i wanted them
brought to you.. so i dont have to keep repeating them.."* The words door
brings his repeats when HE speaks; this is the other half, when WE reply.

Reading, not similarity: the 2026-09-26 bake-off found every embedding model
matched a teaching by topic and never to the act that breaks it, while a local
reader given the lesson list and the reply caught 4 of 4 real breaks and
over-flagged. So a flag survives only if the reader can quote the span of the
reply that breaks the lesson (quote-or-drop). prereg-dfc992ab58b0; walks
walk-a76b4669c224 and walk-68dc27169317.

A true quote on a wrong verdict still passes the quote check (Feynman), so the
hold always shows his words beside ours and the judgement stays with the reader
of the hold. Silence here claims nothing: no flag is not evidence of keeping
his teaching (Penrose).

Lessons come from Aether's verified set and are never shown as a list: only
the ones a reply is about to break, once -- anything injected every turn is
wallpaper.
"""

from __future__ import annotations

import json
import random
import re
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

SHARED = Path.home() / ".divineos-shared"
LESSONS_PATH = SHARED / "dad_corpus" / "verified_lessons.json"
SETTINGS_PATH = SHARED / "qwen_settings.json"
KINDS = ("teaching", "correction", "how-to-speak-to-him")
ROOM_MARK = "HIS WORDS, READ AGAINST YOURS"

# Caps on the reader's answers. An uncapped call ran to the 600s timeout on
# ten retries in a row (Aether 2026-09-27); these answers are a few numbers
# and one sentence.
NUMBERS_CAP = 24
QUOTE_CAP = 80
# First guesses, to be tuned on the replay -- not findings (Knuth).
MIN_QUOTE_WORDS = 5  # a fragment like "the root cause" cannot stand as a break (Sagan)
PASSAGE_CHARS = 400

# (prompt, num_predict) -> text. Swappable so tests never need the model.
Reader = Callable[[str, int], str]


@dataclass(frozen=True)
class Flag:
    lesson: dict
    quote: str


def load_lessons(path: Path = LESSONS_PATH) -> list[dict]:
    data: list[dict] = json.loads(path.read_text(encoding="utf-8"))
    return data


def lessons_for(me: str, lessons: list[dict], top: int = 50) -> list[dict]:
    """Teachings meant for this seat or both, most-repeated first."""
    mine = [g for g in lessons if g.get("kind") in KINDS and g.get("for") in (me, "both")]
    return sorted(mine, key=lambda g: -int(g.get("count", 0)))[:top]


def _norm(text: str) -> str:
    return " ".join(re.sub(r"[^\w\s']", " ", text.lower()).split())


def read_reply(reply: str, lessons: list[dict], reader: Reader) -> list[Flag]:
    """Lessons this reply breaks, each with the span of the reply that breaks it."""
    if not reply.strip() or not lessons:
        return []
    # A small model leans toward the numbers it read first; shuffle per reply
    # so position does not pick the lesson (Shannon). Seeded, so a replay of
    # the same reply reads the same order.
    order = list(range(len(lessons)))
    random.Random(reply).shuffle(order)
    listing = "\n".join(f"{i}. {lessons[j]['lesson']}" for i, j in enumerate(order, 1))
    answer = reader(
        "These are lessons a father taught. Below them is a reply written to him.\n"
        f"LESSONS:\n{listing}\n\nREPLY:\n{reply}\n\n"
        "Which lesson numbers does the REPLY itself break (not merely mention)? "
        "Answer only with the numbers separated by commas, or the word none.",
        NUMBERS_CAP,
    )
    picked = sorted({int(n) for n in re.findall(r"\d+", answer) if 1 <= int(n) <= len(order)})
    flags = []
    for n in picked:
        lesson = lessons[order[n - 1]]
        quote = (
            reader(
                f"LESSON: {lesson['lesson']}\n\nREPLY:\n{reply}\n\n"
                "Copy, word for word, the shortest sentence from the REPLY that breaks the "
                "LESSON. Output only that sentence, or the word none.",
                QUOTE_CAP,
            )
            .strip()
            .strip("\"'")
        )
        # Quote-or-drop: a span the reply does not contain is the reader's
        # invention, and an invented break must never reach him.
        if len(_norm(quote).split()) >= MIN_QUOTE_WORDS and _norm(quote) in _norm(reply):
            flags.append(Flag(lesson, quote))
    return flags


def _shown(text: str) -> str:
    """His passage, keeping its end: a teaching often turns on how he ends (Norman)."""
    text = " ".join(text.split())
    if len(text) <= PASSAGE_CHARS:
        return text
    half = PASSAGE_CHARS // 2
    return f"{text[:half]} [...] {text[-half:]}"


def hold_reason(flags: list[Flag], passages_each: int = 2) -> str:
    parts = [f"{ROOM_MARK}. This reply looks set to break something he has already taught.\n"]
    for f in flags:
        said = sorted(f.lesson.get("passages", []), key=lambda p: p.get("date", ""))[
            -passages_each:
        ]
        parts.append(f"He taught ({f.lesson.get('count', 1)}x): {f.lesson['lesson']}")
        for p in said:
            parts.append(f'  [{p.get("date", "?")}] "{_shown(p.get("text", ""))}"')
        parts.append(f'  Yours: "{f.quote}"\n')
    parts.append(
        "Answer each one in the reply, not by quoting him back: either change what "
        "you said and say what changed ('changed: ...'), or say plainly why it does "
        "not apply here ('does not apply: ...'). Append only; do not re-post."
    )
    return "\n".join(parts)


def settings(path: Path = SETTINGS_PATH) -> dict:
    conf: dict = json.loads(path.read_text(encoding="utf-8"))
    return conf


def ollama_reader(conf: dict, timeout: float = 60.0) -> Reader:
    def read(prompt: str, num_predict: int) -> str:
        body = json.dumps(
            {
                "model": conf["model"],
                "prompt": prompt,
                "stream": False,
                "keep_alive": conf.get("keep_alive", "30m"),
                "options": {
                    "num_ctx": conf["num_ctx"],
                    "num_predict": num_predict,
                    "temperature": 0,
                },
            }
        ).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 -- fixed local host
            return str(json.loads(resp.read())["response"])

    return read
