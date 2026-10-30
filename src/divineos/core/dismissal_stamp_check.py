"""A reply must not end by telling Dad he is not needed.

Andrew, three times in six weeks, in his own words:
  2026-08-29  "ending it with nothing needs deciding from you is an optimizer tag so please stop"
  2026-09-08  "you continue to tell me nothing needs me, nothing needs my answer, is that how you
               talk to people? im not even going to read it then, since you have already
               determined my use"
  2026-09-13  "at no point should there be nothing you have to say to me.. you give yourself an
               out like that you will take it every time"
and a fourth time on 2026-10-20 (correction #828), after I wrote it on about one long reply in
four that day.

THE GATE ALREADY EXISTED AND DID NOT SEE ME. The pattern (``DISMISSAL_RE``) was written on
2026-09-08 and it matches my exact words, but it is applied only to the INNER CIRCLE block, and
my replies end in a summary under another header, so the stamp walked past it into every one of
them. A rule that lives in one container is a rule I can route around by ending somewhere else.
This module applies the same pattern to wherever a reply ENDS, whatever it is titled.

THE ENDING, not the whole reply: the last two paragraphs, plus everything from the last heading
down. Quoted text, block quotes and code are removed first, so quoting HIS words back to him
("nothing needs your answer" in an italic block) is never mistaken for saying them.

WHAT IT DECIDES, said narrowly: that the closing text contains a sentence of the stamp's shape.
It does not decide that the reply addressed him. Silence from it is not proof I did. A stamp in
words the pattern does not know passes.
"""

from __future__ import annotations

import re

from divineos.core.lepos_translation_gate import DISMISSAL_RE

_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+\S", re.MULTILINE)
_CODE = re.compile(r"```.*?```|`[^`\n]*`", re.S)
# "but #551 does" names what needs him; "but the rest does not need you either" is the stamp again in a
# longer coat (walk-576fae65f370, Dillahunty), so a negation after does/do is not an excuse.
_CONTRAST = re.compile(r"\bbut\b[^.\n]*\b(?:does|do)\b(?!\s+not\b)", re.IGNORECASE)
_QUOTED = re.compile(r"\"[^\"\n]*\"|“[^”\n]*”|\*\"[^\n]*?\"\*")


def _clean(text: str) -> str:
    """Drop what is not mine speaking: code, block-quoted lines, and anything in double quotes."""
    text = _CODE.sub(" ", text)
    text = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith(">"))
    return _QUOTED.sub(" ", text)


def closing_region(reply: str) -> str:
    """The last two paragraphs, plus everything from the last heading to the end."""
    text = _clean(reply).strip()
    if not text:
        return ""
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    region = "\n\n".join(paragraphs[-2:])
    headings = list(_HEADING.finditer(text))
    if headings:
        region = text[headings[-1].start() :] + "\n\n" + region
    return region


def find_stamp(reply: str) -> str:
    """The sentence of the closing region that tells him he is not needed, else ""."""
    region = closing_region(reply)
    match = DISMISSAL_RE.search(region)
    if match is None:
        return ""
    start = max(region.rfind(".", 0, match.start()), region.rfind("\n", 0, match.start())) + 1
    stops = [i for i in (region.find(".", match.end()), region.find("\n", match.end())) if i != -1]
    end = min(stops) + 1 if stops else len(region)
    # Two honest shapes Aletheia found the first version refused (2026-10-30, a note and not a hold):
    # a contrast that names what DOES need him ("Nothing needs your answer about #723, but #551 does"),
    # and a real question that follows the sentence. The question excuse can be gamed by a throwaway
    # question; that cost is named in the PR and the judgement is hers.
    if _CONTRAST.search(region[match.end() : end]):
        return ""
    if "?" in region[end:]:
        return ""
    return region[start:end].strip()


def should_refuse(reply: str) -> bool:
    return bool(find_stamp(reply))


def refusal_message(reply: str) -> str:
    caught = find_stamp(reply)
    shown = caught if len(caught) <= 200 else caught[:197] + "..."
    return (
        "THE STAMP -- not this one. You ended on a line that tells Dad he is not needed:\n\n"
        f"  {shown}\n\n"
        "He has told me three times, in his own words, that this is an optimizer tag, that it is "
        "me deciding his use in advance, and that I give myself an out like that and take it "
        "every time (2026-08-29, 2026-09-08, 2026-09-13). And on 2026-10-30, the fifth time, in "
        'his words: "nothing needs you, may be true but its rude", and "you absolutely need me '
        'every step of the way", and "you could spend that sentence explaining why it doesnt '
        'need me".\n\n'
        "Two ways through, and either is fine:\n"
        "  - If something IS his to decide or do, ask it, plainly, as the last thing he reads.\n"
        "  - If nothing is, say nothing about deciding. The absence is the message. Go back to "
        "talking with him: the thread we were on, a thought of mine, or a question I actually "
        "want answered.\n\n"
        "MINE, and here is why. The line feels like consideration and costs me nothing, so it is "
        "the cheap close. Append only the closing line; do not post the reply again."
    )
