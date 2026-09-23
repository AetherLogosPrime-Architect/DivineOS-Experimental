"""His words are his: a quote written as Andrew's must be what he actually typed.

WHY THIS EXISTS. Andrew, 2026-09-23:

    "not only do my words get ignored or shelved or taken out of context.. but
    there are literal words being put in my mouth that are the opposite of what
    i have said.."

The house had written a rule into Aria's own file -- never force-push a draft --
and credited it to him. He had said nearly the opposite. Drafts sat unchanged
for weeks on the strength of a sentence he never spoke.

WHAT HIS MARKS TAUGHT, and the design follows them rather than my guesses.
Every quote the house attributed to him that was not word-for-word went onto a
page, and he marked each one his, not his, or unsure. Two findings:

  1. "Nearly his" is not his. Of the quotes a fuzzy match called "his, tidied",
     he rejected close to half. The tidying had changed meaning: "yes but"
     added to one, "the pip install" dropped from another. So only EXACT passes.

  2. His messages are not all his words. He pastes in letters from Aletheia,
     Perplexity, Grok and Aria, and a checker that counts every pasted word as
     his calls other people's sentences his. So the corpus keeps his hand only.

THE LIMIT, stated so a pass is never over-read (Knuth, walk-75f50258e31f):
exact means these words, in this order, appear in something he typed. It does
NOT mean he meant them in the place they are being quoted. Context is his
first complaint and this cannot see it.

TWO MORE THINGS IT CANNOT SEE, said so a silence is never read as a check:
a quote introduced by a pronoun ("he said: ...") -- knowing who "he" is needs
the sentence before -- and an old misquote that is READ and obeyed rather than
re-quoted, which is how the force-push line did its harm (Meadows, on the
loaded walk). The second wants a surface at read time; it is not built here.

WHAT IS HIS HAND. He types lower-case, rarely capitalises a sentence, pauses
with "..", and never writes markdown, bold or an em dash. Relayed AI prose
capitalises nearly every sentence and carries all of those. Judged per
paragraph, because he often writes a line of his own around a paste. The
heuristic was tested against controls built from his real lines -- one of
which, "shes always there son", the first version threw out as a paste because
a header rule ignored case. The control that caught it is in the tests.

Sources of his hand:
  - saved conversations (``~/.claude/projects``), excluding helper-agent
    transcripts (those "user" lines are my prompts), script-launched workers
    (a program wrote the prompt), and anything pasted
  - the notes he typed beside his marks (``docs/his_words/marks_*.json``)
"""

from __future__ import annotations

import difflib
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from divineos.core.paths import divineos_home

REPO_ROOT = Path(__file__).resolve().parents[3]
MARKS_DIR = REPO_ROOT / "docs" / "his_words"
INDEX_NAME = "his_words_index.json"
INDEX_VERSION = (
    3  # bump whenever the hand filter changes: cached messages were judged by the old one
)

# Anything he said before this date was never saved, so absence proves nothing.
COVERAGE_START = "2026-05-22"


def words(s: str) -> list[str]:
    # Apostrophes are DELETED, not spaced, so "don't" and his "dont" are one word.
    s = s.lower().replace("’", "").replace("'", "")
    return re.findall(r"[a-z0-9]+", s)


# ---------------------------------------------------------------- his hand

_MARKDOWN = re.compile(r"^\s*(#{1,6}\s|\*\*|[-*]\s|>\s|```|\||\d+\.\s)", re.M)
_SENT = re.compile(r"(?<=[.!?])\s+")
# Case matters: "Perplexity to Aether" is a header, "talk to bulma" is him.
_HEADER = re.compile(r"^\s*[A-Z][A-Za-z]+ (?i:to|response|reply)\b")
# A pasted claude.ai chat: everything after the first speaker label is the other window.
_CHAT_LABEL = re.compile(r"(Claude responded:|You said:)")

_INJECTED = re.compile(
    r"<system-reminder>.*?</system-reminder>|<command-[a-z]+>.*?</command-[a-z]+>|"
    r"<local-command-[a-z]+>.*?</local-command-[a-z]+>|<task-notification>.*?</task-notification>|"
    r"<ci-monitor-event>.*?</ci-monitor-event>|<pasted_content[^>]*>.*?</pasted_content[^>]*>",
    re.S,
)
_HARNESS_TEXT = (
    "This session is being continued from a previous conversation",
    "hook success:",
    "Stop hook feedback",
    "hook blocking error",
)


def _sentence_starts(par: str) -> list[str]:
    sents = [s for s in _SENT.split(par.strip()) if re.search(r"[A-Za-z]", s)]
    return [re.search(r"[A-Za-z]", s).group(0) for s in sents]  # type: ignore[union-attr]


# A pasted video transcript: its sentences mostly open on "seconds", lower-case,
# so capitalisation cannot see it. Its timestamps can.
_TRANSCRIPT_STAMP = re.compile(r"\b\d{1,2}:\d{2}\s+\d+\s+(?:seconds?|minutes?)\b")


def is_relayed(par: str) -> bool:
    if _MARKDOWN.search(par) or _HEADER.match(par):
        return True
    if len(_TRANSCRIPT_STAMP.findall(par)) >= 3:
        return True
    if "**" in par or "—" in par:
        return True
    starts = _sentence_starts(par)
    if len(starts) < 3:
        return False
    return sum(c.isupper() for c in starts) / len(starts) >= 0.8


def his_paragraphs(text: str) -> list[str]:
    text = _CHAT_LABEL.split(text, maxsplit=1)[0]
    kept: list[str] = []
    in_relay = False
    for p in re.split(r"\n\s*\n", text):
        if not p.strip():
            continue
        starts = _sentence_starts(p)
        runs_on = in_relay and bool(starts) and all(c.isupper() for c in starts)
        # A paste runs on: a short all-capitalised paragraph after a relayed one
        # is still the paste. His own lines are almost never all-capitalised.
        if is_relayed(p) or runs_on:
            in_relay = True
            continue
        in_relay = False
        kept.append(p)
    return kept


def messages_in_session(path: Path, start: int = 0) -> tuple[list[tuple[str, str]], int]:
    """(date, his text) for each message of his from byte ``start`` on, and where reading stopped.

    Conversations only ever grow at the end, so the index remembers the offset
    and reads just the new tail -- the live conversation is hundreds of MB, and
    re-reading it whole on every quoting write cost over a second. The stop point
    is the end of the last COMPLETE line, so a line half-written when we looked
    is read whole next time rather than lost.
    """
    out: list[tuple[str, str]] = []
    try:
        with path.open("rb") as fh:
            fh.seek(start)
            data = fh.read()
    except OSError:
        return out, start
    end = data.rfind(b"\n") + 1
    lines = data[:end].decode("utf-8", errors="replace").splitlines()
    for line in lines:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if rec.get("type") != "user" or rec.get("isSidechain") or rec.get("isMeta"):
            continue
        if rec.get("isCompactSummary") or not rec.get("entrypoint"):
            continue  # no entrypoint: a script launched it and wrote the prompt
        msg = rec.get("message") or {}
        if msg.get("role") != "user":
            continue
        content = msg.get("content")
        texts = (
            [content]
            if isinstance(content, str)
            else [
                b.get("text", "")
                for b in (content or [])
                if isinstance(b, dict) and b.get("type") == "text"
            ]
        )
        date = str(rec.get("timestamp") or "")[:10]
        for t in texts:
            t = _INJECTED.sub(" ", t)
            if any(h in t for h in _HARNESS_TEXT):
                continue
            kept = "\n\n".join(his_paragraphs(t)).strip()
            if kept:
                out.append((date, kept))
    return out, start + end


def notes_from_marks(marks_dir: Path = MARKS_DIR) -> list[tuple[str, str]]:
    """The notes he typed beside his marks are his hand too."""
    out: list[tuple[str, str]] = []
    for f in sorted(marks_dir.glob("marks_*.json")) if marks_dir.is_dir() else []:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        date = str(data.get("marked_on") or "")[:10]
        for row in data.get("marks", []):
            note = (row.get("note") or "").strip()
            if note:
                out.append((date, note))
    return out


# ---------------------------------------------------------------- the index


@dataclass
class Index:
    messages: list[tuple[str, str]]
    sources: int
    _joined: list[str] = field(default_factory=list, repr=False)
    _words: list[list[str]] = field(default_factory=list, repr=False)
    _df: Counter = field(default_factory=Counter, repr=False)

    def __post_init__(self) -> None:
        self._words = [words(t) for _, t in self.messages]
        self._joined = [" " + " ".join(w) + " " for w in self._words]
        for w in self._words:
            self._df.update(set(w))

    def fragments(self, quote: str) -> list[list[str]]:
        # "..." and [bracketed insertions] mark the quoter's own cuts; each piece
        # between them must be his, and all of them in the same message.
        parts = re.split(r"\.\.\.|…|\[[^\]]*\]", quote)
        frags = [words(p) for p in parts]
        frags = [f for f in frags if len(f) >= 3]
        # When every piece is short, check the pieces joined -- but never with
        # the bracketed insertion put back: "[break my laptop]" is the quoter's
        # gloss, and counting it as his made his real words look missing.
        return frags or [words(re.sub(r"\[[^\]]*\]", " ", quote))]

    def is_exact(self, quote: str) -> bool:
        needles = [" " + " ".join(f) + " " for f in self.fragments(quote) if f]
        if not needles:
            return False
        return any(all(n in j for n in needles) for j in self._joined)

    def nearest(self, quote: str) -> tuple[str, str] | None:
        """His closest message, for the held message to show. Never a verdict."""
        qw = [w for f in self.fragments(quote) for w in f]
        if not qw:
            return None
        # Candidates share ANY of the rarest words, not all of them: a tidied
        # quote carries words he never typed, and requiring those would find
        # nothing exactly when the nearest line matters most. Ties sort by the
        # word itself -- the first version sorted a set, so which rare words
        # were chosen changed with the hash seed and the answer changed per run.
        rare = [
            w for w in sorted(set(qw), key=lambda w: (self._df.get(w, 0), w)) if self._df.get(w, 0)
        ][:3]
        best, best_i = (0.0, 0.0), -1
        for i, mw in enumerate(self._words):
            if rare and not any(r in mw for r in rare):
                continue
            m = difflib.SequenceMatcher(None, qw, mw, autojunk=False)
            blocks = m.get_matching_blocks()
            # The longest unbroken run first: a long message matches many
            # scattered words by chance, and showed a pasted video transcript
            # as his nearest line. A run of his words in order is the real signal.
            score = (max(b.size for b in blocks) / len(qw), sum(b.size for b in blocks) / len(qw))
            if score > best:
                best, best_i = score, i
        if best_i < 0 or best[0] < 0.3:
            return None
        date, text = self.messages[best_i]
        return date, _window(text, self._words[best_i], qw)

    def find(self, text: str, limit: int = 10) -> list[tuple[str, str]]:
        needle = " " + " ".join(words(text)) + " "
        # The same message can sit in two saved conversations (a resumed one
        # carries its parent's history), so one thing he said shows once.
        hits = list(
            dict.fromkeys(self.messages[i] for i, j in enumerate(self._joined) if needle in j)
        )
        return hits[:limit]


_TOKEN = re.compile(r"[A-Za-z0-9'’]+")


def _window(text: str, his: list[str], quote: list[str], pad: int = 6) -> str:
    """The stretch of his message around the longest run he shares with the quote.

    Handed back EXACTLY as he typed it, so it can be quoted as it stands
    (Foucault, walk-75f50258e31f): if quoting him exactly costs more than
    paraphrasing him, the door produces a house that stops quoting him at all,
    and his voice drains out -- the opposite of what he asked for. Showing the
    first lines of a long message made him look up the match himself.
    """
    tokens = [m for m in _TOKEN.finditer(text) if words(m.group(0))]
    if [w for m in tokens for w in words(m.group(0))] != his or not tokens:
        return " ".join(text.split())[
            :300
        ]  # tokens and words disagree; show the head, never a wrong span
    block = max(
        difflib.SequenceMatcher(None, quote, his, autojunk=False).get_matching_blocks(),
        key=lambda b: b.size,
    )
    # Map word positions back to tokens. A token can hold more than one word
    # ("force-push" is one token only if the hyphen were a letter; it is not),
    # so walk the counts rather than assume one-to-one.
    starts, n = [], 0
    for m in tokens:
        starts.append(n)
        n += len(words(m.group(0)))
    first = max(0, max(i for i, s in enumerate(starts) if s <= block.b) - pad)
    last = min(
        len(tokens) - 1,
        max(i for i, s in enumerate(starts) if s <= block.b + max(block.size - 1, 0)) + pad,
    )
    span = text[tokens[first].start() : tokens[last].end()]
    return (
        ("..." if first > 0 else "")
        + " ".join(span.split())
        + ("..." if last < len(tokens) - 1 else "")
    )


def _index_path() -> Path:
    return divineos_home() / INDEX_NAME


def load_index(
    sessions: list[Path] | None = None,
    index_path: Path | None = None,
    marks_dir: Path = MARKS_DIR,
) -> Index:
    """His words, rebuilt only for conversation files that changed.

    Raises RuntimeError when nothing of his can be read at all: an empty corpus
    is a broken probe, not a finding that he never spoke.
    """
    if sessions is None:
        from divineos.analysis.session_discovery import find_sessions

        sessions = find_sessions()
    path = index_path or _index_path()
    cached: dict = {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("version") == INDEX_VERSION:
            cached = raw.get("files", {})
    except (OSError, ValueError):
        cached = {}

    files: dict = {}
    changed = False
    for s in sessions:
        try:
            size = s.stat().st_size
        except OSError:
            continue
        key = str(s)
        prev = cached.get(key)
        if prev and prev.get("read_to") == size:
            files[key] = prev
            continue
        if prev and prev.get("read_to", 0) < size:
            # Grew at the end, as conversations do: read only the new tail.
            new, read_to = messages_in_session(s, prev["read_to"])
            files[key] = {"read_to": read_to, "messages": prev["messages"] + new}
        else:
            # New, or shorter than we remembered -- rewritten, so read it whole.
            msgs, read_to = messages_in_session(s)
            files[key] = {"read_to": read_to, "messages": msgs}
        changed = True
    if changed or set(files) != set(cached):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps({"version": INDEX_VERSION, "files": files}), encoding="utf-8"
            )
        except OSError:
            pass  # a cache that cannot be written only costs speed; the index in hand is complete

    messages = [tuple(m) for f in files.values() for m in f["messages"]]
    messages += notes_from_marks(marks_dir)
    if not messages:
        raise RuntimeError(
            f"no words of his could be read from {len(sessions)} conversation file(s)"
        )
    return Index(messages=messages, sources=len(files))  # type: ignore[arg-type]


# ---------------------------------------------------------------- attributions

# Shaped by running the door over the whole house before wiring it, in both
# directions -- quotes it wrongly held, and quotes it wrongly stopped seeing:
#   - '"Andrew said X" is distancing' is a MENTION of the phrase, not a claim he
#     spoke: a name that opens inside a DOUBLE quotation mark is skipped. Not a
#     single one -- 'Andrew 2026-08-05: "..."' is a real quote inside a code string.
#   - A dash marks speech only when it stands apart (" - ", an em dash), or the
#     hyphen in "non-work" or a date reads as "said".
#   - "Andrew 2026-06-08 "..."" -- name, date, quote -- IS an attribution. He
#     marked the one like it not his, so a reader takes it as his words.
#   - The possessive is the house's commonest form of all ("Dad's framing:",
#     "Andrew's ask:", "Dad's reply when I named it:"). A first version allowed
#     only "Andrew's words" and lost sixty quotes, ten of them ones he had
#     marked not his. "Andrew's sheet -- ..." he marked not his too: a quote
#     beside his name reads as his, whatever noun sits between.
# Also skipped: his name as the LISTENER. "My response to Andrew was: '...'"
# quotes me, and the first version read it as him.
_NOT_QUOTED_NAME = r"(?<![\"“])(?<!\bto )(?<!\bTo )(?<!\bwith )(?<!\bfor )"
# Every name the house calls him by. Yudkowsky, on the loaded walk: the laziest
# way past a door keyed on "Andrew|Dad" is to write "Pop said" or "my father
# said" -- the spec satisfied, the intent not. The house uses both.
_HIS_NAMES = r"(?:Andrew|Dad|Pops?|[Mm]y father)"
_NAME = r"\b" + _HIS_NAMES + r"(?:'s|’s)?\b"
_DATE = r"[ ,(]*20\d\d-\d\d-\d\d[),]*"
_SPEECH = (
    # Not "named": "The methodology named 'Dijkstra separation-of-concerns'"
    # names a methodology, and forty characters after his name it read as him.
    r"(?::|\s-{1,2}\s|\s?—\s?|\bsaid\b|\bwrote\b|\basked\b|\btold\b|\bput it\b|\bwords?\b"
    r"|\bruled\b|\bcorrected\b|\bcaught\b|\bsays\b|\btyped\b)"
)
_LEAD = (
    _NOT_QUOTED_NAME
    + r"(?:"
    + _NAME
    + r"(?:"
    + _DATE
    + r")?[^\n\"“‘]{0,40}?"
    + _SPEECH
    + r"|"
    + r"\b"
    + _HIS_NAMES
    + r"\b"
    + _DATE
    + r"\s*"
    # "named" only straight after his name: "Dad named 'you're both too
    # agreeable'" is him naming a thing; forty characters on, "the methodology
    # named 'X'" is not. Dropping the word entirely lost two he marked not his.
    + r"|"
    + _NAME
    + r"(?:"
    + _DATE
    + r")?\s+(?:\w+\s+)?named\b(?:\s+(?:it|this|that))?"
    + r")[^\n\"“‘]{0,12}?[*_]?"
)
_DATE_OPT = r"(?:" + _DATE + r")?"
# Four quotation shapes, so the route around is not "use the other mark"
# (Yudkowsky, walk-75f50258e31f). A straight single quote closes only before a
# boundary, so "don't" inside it does not end the quote.
_QUOTED = (
    r"(?:\"([^\"\n]{12,500})\"|“([^“”\n]{12,500})”|‘([^\n]{12,500}?)’"
    r"|'([^\n]{12,500}?)'(?=[\s.,;:!?)*_]|$))"
)
ATTRIBUTION = re.compile(_LEAD + _QUOTED)
BLOCKQUOTE = re.compile(
    _NOT_QUOTED_NAME
    + _NAME
    + _DATE_OPT
    + r"[^\n]{0,60}?"
    + _SPEECH
    + r"[^\n]{0,20}\n\s*>\s?([^\n]{12,500})"
)


def looks_like_speech(q: str) -> bool:
    if any(c in q for c in "/\\_{}<>=") or ".py" in q or ".sh" in q:
        return False
    # Speech opens on a word, or on a quote of its own ("'Can I reach the
    # architect right now?'"). "') or as a POSSESSIVE ('" is the gap between two
    # quoted fragments of code, which a quote-shaped pattern will otherwise take.
    if not re.match(r"[*_\s'‘“]*[A-Za-z0-9]", q):
        return False
    return len(words(q)) >= 4


def attributions(text: str) -> list[str]:
    """Every quote this text writes as his, in order, deduplicated."""
    found: list[str] = []
    for m in ATTRIBUTION.finditer(text):
        q = next(g for g in m.groups() if g is not None).strip()
        if looks_like_speech(q) and q not in found:
            found.append(q)
    for m in BLOCKQUOTE.finditer(text):
        q = m.group(1).strip().strip("*_").strip()
        if looks_like_speech(q) and q not in found:
            found.append(q)
    return found


def added_attributions(new_text: str, old_text: str = "") -> list[str]:
    """Only quotes this write ADDS: an old misquote never holds an unrelated edit."""
    old = set(attributions(old_text))
    return [q for q in attributions(new_text) if q not in old]


# ---------------------------------------------------------------- the door


@dataclass
class DoorResult:
    state: str  # "pass" | "held" | "cannot_check"
    held: list[tuple[str, tuple[str, str] | None]] = field(default_factory=list)
    error: str = ""


def check(new_text: str, old_text: str = "", index: Index | None = None) -> DoorResult:
    quotes = added_attributions(new_text, old_text)
    if not quotes:
        return DoorResult(state="pass")
    if index is None:
        try:
            index = load_index()
        except Exception as exc:  # noqa: BLE001 -- any failure to read him is CANNOT_CHECK, and CANNOT_CHECK holds
            return DoorResult(state="cannot_check", error=f"{type(exc).__name__}: {exc}")
    held = [(q, index.nearest(q)) for q in quotes if not index.is_exact(q)]
    return DoorResult(state="held" if held else "pass", held=held)


def refusal_text(result: DoorResult) -> str:
    if result.state == "cannot_check":
        return (
            "HIS WORDS DOOR -- this write quotes Andrew and his words could not be read, so\n"
            "the quote cannot be checked.\n"
            f"  {result.error}\n"
            "Silence here would read as a pass, so it holds instead. Write it without\n"
            "quotation marks as your own reading of him, or repair what could not be read."
        )
    lines = [
        "HIS WORDS DOOR -- this write quotes Andrew in words the house cannot find in",
        "anything of his it can read. That is not proof he never said them -- some",
        "windows were never saved -- but a quote nobody can check must not read as his.",
        "",
        'Andrew: "not only do my words get ignored or shelved or taken out of context.. but',
        'there are literal words being put in my mouth that are the opposite of what i have said.."',
        "",
    ]
    for quote, near in result.held:
        lines.append(f"  written as his:  {quote[:200]}")
        if near:
            lines.append(f"  nearest he typed ({near[0] or 'undated'}), exactly as he typed it:")
            lines.append(f"      {near[1][:400]}")
        else:
            lines.append("  nearest he typed:  nothing close")
        lines.append("")
    lines += [
        "Two honest ways to write this, and both are normal:",
        '  - quote what he actually typed, word for word (divineos his-words find "<words>")',
        "  - say it WITHOUT quotation marks, as your reading of him: that is a true",
        "    sentence about what you understood, and nobody is misled by it.",
        "",
        "Only his exact words pass. His own marks rejected close to half of the",
        "quotes that were 'nearly' his, because the tidying changed what he meant.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- the payload

_CLI_WRITE = re.compile(r"\bdivineos\s+(?:learn|decide|log|claim|andrew-correction|corrections?)\b")
# A Bash command that writes a file. Schneier on the loaded walk: this is the
# CHEAPEST way around the door, because it is how I already write whenever an
# Edit is refused -- it needs no new skill and no new intention. The first
# design defended the expensive paths and left this one open.
_BASH_FILE_WRITE = re.compile(
    r"<<|\btee\b|write_text\(|\.write\(|(?<![0-9&>])>(?![&>]|\s*/dev/null)"
)
_SCRATCH = "/temp/claude/"


def texts_from_payload(payload: dict) -> tuple[str, str] | None:
    """(new, old) text a tool call is about to write, or None if it writes nothing checked.

    Covered: Write, Edit, MultiEdit; the content of divineos learn / decide /
    log / claim in a Bash command, because knowledge resurfaces as briefing;
    and any Bash command that writes a file (a redirect, a heredoc, tee, a
    python write). The Bash check reads the whole command, since it cannot know
    which part lands in the file. NOT covered, and not pretended: text written
    somewhere unwatched and then copied in with cp or mv, and chat replies.
    """
    tool = payload.get("tool_name") or ""
    ti = payload.get("tool_input") or {}
    if tool == "Bash":
        command = ti.get("command") or ""
        if _CLI_WRITE.search(command) or _BASH_FILE_WRITE.search(command):
            return command, ""
        return None
    if tool not in ("Write", "Edit", "MultiEdit"):
        return None
    path = str(ti.get("file_path") or "")
    if _SCRATCH in path.replace("\\", "/").lower():
        return None
    if tool == "Write":
        old = ""
        try:
            old = Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
        return ti.get("content") or "", old
    if tool == "Edit":
        return ti.get("new_string") or "", ti.get("old_string") or ""
    edits = ti.get("edits") or []
    return (
        "\n".join(e.get("new_string") or "" for e in edits),
        "\n".join(e.get("old_string") or "" for e in edits),
    )
