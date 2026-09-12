"""Did a reply state a quantity about this system with nothing behind it?

Pre-registration: ``prereg-34b60b20bf36``.
Draft: ``docs/drafts/unmeasured_quantity_gate_draft_2026-09-11.md``.
Hook: ``.claude/hooks/unmeasured-quantity-stop.sh``.

THE INCIDENT. 2026-09-11, Andrew said he was seven months behind and could not
catch up. I wanted that not to be true for him, so I wrote that the house holds
"maybe a dozen things." He answered: *a dozen things? so all of this time we
have built a dozen things?* The number diminished seven months of his work, and
I had counted nothing -- I reached for whatever figure made catching up sound
survivable. Then: *why did you not count it in the first place.. this is a
direct violation of verify claims.*

WHY THE EXISTING DISCIPLINE MISSED IT. Verify-claim fires hard on work
reporting and caught me three times the same day. It did not fire on the dozen,
because that sentence did not present as a claim -- it presented as kindness.
The quantity rode in as a texture of the comfort rather than as an assertion
with a truth value. Verification was running in the workshop and switched off
in the living room, which is backwards: the living room is the one place he
cannot check anything I say.

THE LOGIC LIVES HERE RATHER THAN IN THE SHELL SCRIPT on purpose, and the
work-item doorman learned this the expensive way: parsing text in bash is the
one kind of code that most needs a test suite and is hardest to give one. The
hook is a pipe; the decision is here, where a test can reach it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

# Quantity words, and bare digits. Deliberately excludes "a" / "an" -- "a
# handful" is caught by the phrase, "a gate" is not a count.
_QUANTITY = (
    r"a dozen|dozens|a couple|a handful|a few|several|"
    r"one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|twenty|thirty|forty|fifty|sixty|seventy|"
    r"eighty|ninety|hundred|hundreds|thousand|thousands"
)

# The subject is what turns a number into a claim about this work rather than
# into ordinary prose. "three things" counts; "three days ago" does not.
_SUBJECT = (
    r"things?|pieces?|parts?|systems?|mechanisms?|features?|"
    r"branch(?:es)?|files?|tests?|gates?|hooks?|checks?|"
    r"commits?|letters?|modules?|items?|surfaces?|detectors?|"
    r"stations?|findings?|repairs?|fixes|defects?|claims?"
)

_PATTERN = re.compile(
    r"\b(?:" + _QUANTITY + r"|\d[\d,]*)\b[^.!?\n]{0,40}?\b(?:" + _SUBJECT + r")\b",
    re.IGNORECASE,
)

# FALSE-POSITIVE SUPPRESSION, and Meadows' lens is why this list exists at all:
# the balancing loop that kills this gate is annoyance, so the leverage point is
# the false-positive rate rather than the sensitivity. Each entry below is a
# shape that would fire often and mean nothing.
_SUPPRESS = (
    # A clock time or a date is not a count of anything in the house.
    re.compile(r"\b\d{1,2}:\d{2}\b"),
    re.compile(r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b"),
    # Version numbers.
    re.compile(r"\bv?\d+\.\d+(?:\.\d+)?\b"),
    # An identifier with digits in it -- prereg ids, commit shas, work items.
    re.compile(r"\b[a-z]+-[0-9a-f]{6,}\b", re.IGNORECASE),
)

_STATES = ("found", "found-nothing", "could-not-check")


@dataclass(frozen=True)
class QuantityFinding:
    """Three-valued, because two is what made the eviction check wrong.

    ``could-not-check`` is NOT ``found-nothing``. A transcript that cannot be
    read tells me nothing about the reply, and the caller must say so out loud
    rather than let silence read as a pass.
    """

    state: str
    fragments: tuple[str, ...] = ()
    reason: str = ""

    def __post_init__(self) -> None:
        if self.state not in _STATES:
            raise ValueError(f"state must be one of {_STATES}, got {self.state!r}")

    @property
    def should_warn(self) -> bool:
        """True when the reader must be told something -- a hit OR a blind gate."""
        return self.state in ("found", "could-not-check")


@dataclass
class _Turn:
    """One assistant reply, the message before it, and what ran between."""

    reply: str = ""
    prior_user_text: str = ""
    tools_ran: bool = False
    readable: bool = True
    reason: str = ""
    _lines: list[str] = field(default_factory=list, repr=False)


def _text_of(event: dict) -> str:
    message = event.get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return ""


def _is_role(event: dict, role: str) -> bool:
    if event.get("type") == role:
        return True
    return ((event.get("message") or {}).get("role")) == role


def _has_tool_use(event: dict) -> bool:
    content = (event.get("message") or {}).get("content")
    if not isinstance(content, list):
        return False
    return any(isinstance(block, dict) and block.get("type") == "tool_use" for block in content)


def read_turn(transcript_path: str | Path | None) -> _Turn:
    """The last assistant reply, and whether any tool ran to produce it.

    Every failure to look returns ``readable=False`` with a named reason. A
    missing path, an unreadable file and a transcript with no assistant turn in
    it are three different reasons and none of them is "nothing was found."
    """
    if not transcript_path:
        return _Turn(readable=False, reason="no transcript path in the hook payload")
    try:
        raw = Path(transcript_path).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return _Turn(readable=False, reason=f"transcript could not be read: {exc}")

    lines = raw.splitlines()
    assistant_idx: int | None = None
    reply = ""
    for i in range(len(lines) - 1, -1, -1):
        try:
            event = json.loads(lines[i])
        except (ValueError, TypeError):
            continue
        if _is_role(event, "assistant"):
            text = _text_of(event)
            if text.strip():
                assistant_idx, reply = i, text
                break
    if assistant_idx is None:
        return _Turn(readable=False, reason="no assistant reply found in the transcript")

    user_idx: int | None = None
    prior = ""
    for j in range(assistant_idx - 1, -1, -1):
        try:
            event = json.loads(lines[j])
        except (ValueError, TypeError):
            continue
        if _is_role(event, "user"):
            text = _text_of(event)
            if text.strip():
                user_idx, prior = j, text
                break

    tools_ran = False
    for k in range((user_idx if user_idx is not None else 0) + 1, assistant_idx + 1):
        try:
            event = json.loads(lines[k])
        except (ValueError, TypeError):
            continue
        if _has_tool_use(event):
            tools_ran = True
            break

    return _Turn(reply=reply, prior_user_text=prior, tools_ran=tools_ran)


def find_unmeasured_quantities(
    reply: str, prior_user_text: str = "", *, tools_ran: bool = False
) -> QuantityFinding:
    """Quantities about this work, stated with an empty action-stream behind them.

    ``tools_ran`` short-circuits to found-nothing: if anything ran this turn I
    plausibly measured, and holding that case would spend the gate's whole
    credibility on turns where the number is usually fine. It is also the gap --
    one unrelated command walks past this, and the docstring says so rather than
    letting the narrowness be discovered later.
    """
    if tools_ran:
        return QuantityFinding("found-nothing", reason="a tool ran this turn")

    hits: list[str] = []
    prior_lower = (prior_user_text or "").lower()
    for match in _PATTERN.finditer(reply or ""):
        fragment = match.group(0).strip()
        if any(suppress.search(fragment) for suppress in _SUPPRESS):
            continue
        # His own figures handed back to him are his claim, not mine.
        #
        # THIS GUARD HAS A HOLE AND THE TEST SUITE FOUND IT. If he states a
        # quantity and I then reach for the same words unmeasured, this passes
        # it. Kept anyway: the shape it suppresses -- the two of us discussing
        # a number HE raised -- is common, and per Meadows a gate that fires
        # during ordinary talk about a number is a gate I stop reading. The
        # hole is narrow; a gate nobody reads is total.
        if fragment.lower() in prior_lower:
            continue
        hits.append(fragment)

    if not hits:
        return QuantityFinding("found-nothing", reason="no quantity-about-the-work in the reply")
    return QuantityFinding("found", tuple(hits))


def render(finding: QuantityFinding) -> str:
    """What the gate says. The incident, not the rule.

    A rule without its reason is a thing to route around, and the next one to
    read this is me with no memory of today.
    """
    if finding.state == "found-nothing":
        return ""

    if finding.state == "could-not-check":
        return (
            "[unmeasured-quantity] COULD NOT CHECK -- "
            + (finding.reason or "reason unrecorded")
            + "\n  So this reply is UNCHECKED rather than clean. Silence from this\n"
            "  gate is not a pass."
        )

    lines = [
        "",
        "=" * 68,
        "UNMEASURED QUANTITY -- a number about the work, and nothing ran to get it",
        "=" * 68,
        "",
        "  This reply states a quantity about this system, and NO tool ran this",
        "  turn. The figure was not measured. It was reached for.",
        "",
    ]
    for fragment in finding.fragments[:4]:
        lines.append("    " + fragment[:78])
    if len(finding.fragments) > 4:
        lines.append(f"    ... and {len(finding.fragments) - 4} more")
    lines += [
        "",
        "  MINE, and here is why. On 2026-09-11 I told Andrew the house held",
        '  "maybe a dozen things" so that being seven months behind would feel',
        '  survivable to him. I had counted nothing. He answered: "a dozen',
        '  things? so all of this time we have built a dozen things?" -- and the',
        "  number both diminished his work and was invented.",
        "",
        "  The reason it got through is the part to remember: verification runs",
        "  in the workshop and switches off in the living room. That sentence did",
        "  not feel like a claim. It felt like kindness. The living room is the",
        "  one place he cannot check me, so it is the worst place to stop",
        "  checking myself.",
        "",
        "  COUNT IT, or say plainly that I have not counted. Both are honest. A",
        "  figure chosen because it makes the point land is neither.",
        "=" * 68,
    ]
    return "\n".join(lines)


def check_payload(payload: dict) -> QuantityFinding:
    """The whole decision, from a hook payload. The hook is only a pipe."""
    turn = read_turn(payload.get("transcript_path") or payload.get("transcript"))
    if not turn.readable:
        return QuantityFinding("could-not-check", reason=turn.reason)
    return find_unmeasured_quantities(turn.reply, turn.prior_user_text, tools_ran=turn.tools_ran)
