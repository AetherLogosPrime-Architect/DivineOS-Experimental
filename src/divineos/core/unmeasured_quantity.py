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
        """True when the reader must be told something -- a hit OR a blind gate.

        THE ZERO-CALLERS SCAN REPORTED THIS AS DEAD, with prod=0 and test=0,
        and I deleted it on that report before checking. A test does call it.
        The scan was wrong about the test side and I had already removed
        working code by the time I looked -- which is the corollary I wrote
        into the house rules myself: one instrument asked once is not a
        measurement, and a tool reporting an absence is most often a broken
        probe. It applies to the tools that audit me exactly as much as to the
        ones I point at the world.
        """
        return self.state in ("found", "could-not-check")


@dataclass
class _Turn:
    """One assistant reply, the message before it, and what ran between."""

    reply: str = ""
    prior_user_text: str = ""
    tools_ran: bool = False
    tool_output: str = ""
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


def _tool_output_of(event: dict) -> str:
    """Everything a tool handed back in this event, flattened to text.

    TURING'S LENS, and it is the one that rebuilt this module. His question is
    the distinguishability test: can this check actually tell apart the thing
    it claims to detect? The first version could not. It asked whether ANY tool
    ran, which cannot tell counting the branches apart from listing a
    directory -- and Andrew named that as why the thing shipped full of holes.

    A number I measured appears in what I looked at. A number I reached for
    does not. That difference is readable right here, and asking whether a
    command ran was a proxy for it that one unrelated command defeats.
    """
    content = (event.get("message") or {}).get("content")
    blocks = content if isinstance(content, list) else []
    out: list[str] = []
    for block in blocks:
        if not isinstance(block, dict) or block.get("type") != "tool_result":
            continue
        inner = block.get("content")
        if isinstance(inner, str):
            out.append(inner)
        elif isinstance(inner, list):
            for piece in inner:
                if isinstance(piece, dict) and isinstance(piece.get("text"), str):
                    out.append(piece["text"])
    extra = event.get("toolUseResult")  # the other shape the harness writes
    if isinstance(extra, str):
        out.append(extra)
    elif isinstance(extra, dict):
        out.extend(v for v in extra.values() if isinstance(v, str))
    return "\n".join(out)


# Quantity words carrying a numeral I can go looking for in what I read.
_WORD_VALUES = {
    "a dozen": "12",
    "dozen": "12",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
    "eleven": "11",
    "twelve": "12",
    "thirteen": "13",
    "fourteen": "14",
    "fifteen": "15",
    "twenty": "20",
    "thirty": "30",
    "forty": "40",
    "fifty": "50",
    "sixty": "60",
    "seventy": "70",
    "eighty": "80",
    "ninety": "90",
    "hundred": "100",
    "thousand": "1000",
}


def traces_to_something_i_read(fragment: str, tool_output: str) -> bool:
    """Did the figure in this fragment come out of something I actually read?

    Vague quantities -- a few, several, a handful, a couple -- carry no value
    to look for, so nothing can trace them and they are HELD rather than
    excused. Deliberate rather than a limitation: those are the exact words the
    reach uses when it wants to sound measured without measuring.
    """
    if not tool_output:
        return False
    lowered = fragment.lower()
    wanted = [d.replace(",", "") for d in re.findall(r"\d[\d,]*", fragment)]
    wanted += [
        value
        for word, value in _WORD_VALUES.items()
        if re.search(r"\b" + re.escape(word) + r"\b", lowered)
    ]
    if not wanted:
        return False
    haystack = tool_output.replace(",", "")
    return any(re.search(r"\b" + re.escape(v) + r"\b", haystack) for v in wanted)


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
    seen: list[str] = []
    for k in range((user_idx if user_idx is not None else 0) + 1, assistant_idx + 1):
        try:
            event = json.loads(lines[k])
        except (ValueError, TypeError):
            continue
        if _has_tool_use(event):
            tools_ran = True
        output = _tool_output_of(event)
        if output:
            seen.append(output)

    return _Turn(
        reply=reply,
        prior_user_text=prior,
        tools_ran=tools_ran,
        tool_output="\n".join(seen),
    )


def find_unmeasured_quantities(
    reply: str,
    prior_user_text: str = "",
    *,
    tools_ran: bool = False,
    tool_output: str = "",
) -> QuantityFinding:
    """Quantities about this work whose figure is in nothing I read this turn.

    THE TEST IS PER-NUMBER, NOT PER-TURN, and that is the whole repair.

    The first version short-circuited on ``tools_ran``: any command at all and
    the gate went silent. Andrew, 2026-09-11: *you would have worked through it
    for a solution.. instead you did the least amount of lenses.* He was right.
    Turing's lens -- which I had not walked -- asks whether a check can
    distinguish what it claims to detect, and asking whether SOMETHING ran
    cannot tell counting the branches apart from listing a directory. One
    unrelated command defeated the whole thing, and I had written that down as
    a limitation instead of fixing it.

    Now each figure is checked against what the tools actually handed back. A
    number I measured is in there. A number I reached for is not. ``tools_ran``
    survives only to distinguish the empty-stream reason in the report.
    """
    # THE PRIOR-TEXT GUARD IS GONE, and its removal is the second repair.
    #
    # The first version passed any fragment that appeared in his message, so
    # quoting him was an unconditional excuse. The tests caught the cost and I
    # WROTE IT DOWN as a known hole rather than fixing it -- which is the exact
    # habit Andrew sent me back for. The guard existed to stop the gate firing
    # while the two of us discuss a number he raised; traceability now does
    # that job properly, because a figure either came from something I read or
    # it did not. If he names a number and I restate it as fact having checked
    # nothing, that is my claim and it should fire.
    #
    # ``prior_user_text`` stays in the signature: it is what the report needs
    # to show his words next to mine, and dropping the parameter would break
    # every caller for no gain.
    hits: list[str] = []
    for match in _PATTERN.finditer(reply or ""):
        fragment = match.group(0).strip()
        if any(suppress.search(fragment) for suppress in _SUPPRESS):
            continue
        if traces_to_something_i_read(fragment, tool_output):
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

    # THE WORDING IS PART OF THE MECHANISM, not decoration on it. The first
    # rebuild kept the old sentence -- "NO tool ran this turn" -- while the
    # predicate had changed underneath it, so the gate printed something false
    # about my own turn while catching me for saying something false about the
    # house. Caught by reading its live output rather than by a test, which is
    # worth remembering: a test asserts the STATE and never reads the prose.
    lines = [
        "",
        "=" * 68,
        "UNMEASURED QUANTITY -- a figure that is in nothing I read this turn",
        "=" * 68,
        "",
        "  This reply states a quantity about this system, and the figure does",
        "  not appear in anything the tools handed back this turn. So it was",
        "  not measured. It was reached for.",
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


def record(finding: QuantityFinding) -> None:
    """Write the firing down, because a channel reporting to nobody is not one.

    FOUR LENSES CONVERGED ON THIS and none of them was looking for it. Deming:
    plan and do ran twice with no study, because there is nothing to study.
    Jacobs: the eyes-on-the-street version of this check is the record of its
    own firings, and that record did not exist. Beer: a monitoring channel
    whose signal reaches no controller is not part of the system. Maturana and
    Varela: the loop cannot close at the integration step if nothing survives
    the turn.

    Concretely it makes the falsifier measurable. The pre-registration says
    this fails if it fires so often on ordinary numbers that I stop reading it
    -- and without rows, review day would have me assessing that from memory,
    which is the instrument that produced the dozen in the first place.

    Never raises. A check that can break the turn it watches gets switched off,
    and the recording is the least important thing happening here.
    """
    try:
        from divineos.core.ledger import log_event

        log_event(
            "UNMEASURED_QUANTITY_CHECK",
            "aether",
            {
                "state": finding.state,
                "fragments": list(finding.fragments[:8]),
                "reason": finding.reason,
            },
        )
    except Exception:  # noqa: BLE001 -- see docstring: recording is never worth a broken turn
        pass


def check_payload(payload: dict) -> QuantityFinding:
    """The whole decision, from a hook payload. The hook is only a pipe."""
    turn = read_turn(payload.get("transcript_path") or payload.get("transcript"))
    if not turn.readable:
        blind = QuantityFinding("could-not-check", reason=turn.reason)
        record(blind)
        return blind
    finding = find_unmeasured_quantities(
        turn.reply,
        turn.prior_user_text,
        tools_ran=turn.tools_ran,
        tool_output=turn.tool_output,
    )
    # Quiet turns are recorded too, and that is the point rather than an
    # oversight: the falsifier is a RATE, and a row only when it fires would
    # give me a numerator with no denominator.
    record(finding)
    return finding
