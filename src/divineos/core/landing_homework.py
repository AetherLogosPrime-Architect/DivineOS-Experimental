"""A clerk for the author's side of landing a fix.

Dad, 2026-10-10: "yes you can build the helper". Asking the house's own check
about five fixes she had confirmed showed her yes and his yes are the last two
stations, and before them sit author-side stations nobody does automatically.

This prepares the mechanical part and leaves the thinking to the seat
(walk-4fbd1daa1539): it never writes a walk finding, never declares an owner,
never merges. The error costs are unequal, so every ambiguity refuses: a false
confirm on the record is a fake review, a refusal costs one command.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path

from divineos.core.landing_status import confirms_from_letters

_MIN_SHA = 7
_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
_MIN_WORDS_OF_HIS = 20


class ClerkRefused(Exception):
    """The clerk will not prepare or file this; the message says why."""


_DAD_CORPUS = Path.home() / ".divineos-shared" / "dad_corpus" / "dad_all.jsonl"


def _squash(text: str) -> str:
    return " ".join(text.casefold().split())


def _as_utc(stamp: object) -> datetime | None:
    try:
        when = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError:
        return None
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


def her_confirm_filed_at(
    round_notes: str, findings: Sequence[object], tree: str
) -> datetime | None:
    """When the audit store recorded her confirm for this tree; None if it cannot be told.

    A commit date is set by whoever makes the commit (Aletheia, 2026-10-15: a backdated
    head makes every yes he ever typed 'later'), so it cannot bind his yes. The audit
    store stamps a finding itself, at filing, and his confirm exists only to say that her
    audit was done (his words, 2026-10-15), so his yes counts only if typed after that.
    The round must name this tree, and only her external confirm in it counts.
    """
    if f"tree-hash: {tree}" not in round_notes:
        return None
    stamps = [
        getattr(f, "created_at")
        for f in findings
        if getattr(f, "actor", "") == "aletheia" and "external-confirm" in getattr(f, "tags", [])
    ]
    if not stamps:
        return None
    return datetime.fromtimestamp(max(stamps), tz=timezone.utc)


def his_words_were_typed(
    words: str, corpus: Path | None = None, after: datetime | None = None
) -> bool | None:
    """Whether these quoted words are found inside a message he actually typed.

    With ``after`` set, only messages typed later than that moment count (Aletheia's
    hold on #660: his confirms are short and general, so a real yes from yesterday
    would otherwise file today for a different fix; the words cannot say what they
    were about, the time can). A message with no readable time cannot be placed, so
    it does not count.

    ``--andrew-said`` only checked length, so a made-up sentence went straight onto
    the record as his (Aria's cold read of this clerk, 2026-10-14: "Dad said it is
    all fine, go ahead and land everything on main today." was accepted). The house
    keeps every message he types in one file; the quote must be a stretch of one of
    them, compared in lower case with spaces collapsed.

    ``None`` means could not look (no corpus, unreadable), which is not a pass and
    not a fail: the caller refuses on it.
    """
    wanted = _squash(words.strip().strip("\"'“”‘’"))
    if not wanted:
        return False
    path = corpus or _DAD_CORPUS
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    if not lines:
        return None
    for line in lines:
        try:
            row = json.loads(line)
            text = row.get("text", "")
            stamp = row.get("ts")
        except (ValueError, AttributeError):
            continue
        if after is not None:
            when = _as_utc(stamp)
            if when is None or when <= after:
                continue
        if wanted in _squash(str(text)):
            return True
    return False


def her_confirmed_sha(letters: Mapping[str, str], pr: int, head_sha: str) -> str | None:
    """The short sha she confirmed for this fix, if it names the live head.

    Read only from her own letters (confirms_from_letters). A confirm at any
    other head, or an unknown head, is nothing.
    """
    if not head_sha:
        return None
    for sha in confirms_from_letters(letters).get(pr, []):
        if len(sha) >= _MIN_SHA and head_sha.lower().startswith(sha):
            return sha
    return None


def walk_open_command(question: str, files: Sequence[str]) -> str:
    """The `walk open` line scoping EVERY changed file.

    The council station reads only the single closest walk and walks do not add
    up, so a walk that names some of the files satisfies nothing.
    """
    if not files:
        raise ClerkRefused("no changed files were read, so there is nothing to scope a walk to")
    safe_question = question.replace('"', "'")
    scopes = " ".join(f"--scope {f}" for f in files)
    return f'divineos walk open "{safe_question}" --gravity normal {scopes}'


def explain_station(
    station: str,
    detail: str,
    pr: int,
    files: Sequence[str],
    her_confirmed: bool,
) -> list[str]:
    """What one unproven station needs, in plain words, with the ready command."""
    lines = [f"{station}: {detail}"]
    if station == "2-council":
        lines += [
            "Needs one closed council walk whose scope names every changed file. The "
            "check reads only the single closest walk and walks do not add up, so "
            "several smaller walks never satisfy it.",
            "Open it with: "
            + walk_open_command(f"Does PR {pr} hold across every file it changes?", files),
            "The findings are yours: read the diff, then apply each seated lens.",
        ]
    elif station == "8-audit":
        if her_confirmed:
            lines += [
                "Her own letter names this exact head. The round and both confirms can be filed:",
                f'divineos landing file-confirm {pr} --andrew-said "<his words, quoted>"',
            ]
        else:
            lines.append(
                "She has not confirmed this head in a letter I can see, so there is "
                "nothing to file. Ask her for a confirm of this exact head."
            )
    elif station == "4-cold-read":
        lines.append(
            "Someone has to be declared the owner of this branch so a fresh-eyes reader "
            "can be told apart from the author. Declare it; do not infer it from the "
            "branch name."
        )
    elif station == "4-aria":
        lines.append(
            "Needs a reading by Aria that names this branch, or an 'Author: <name>' "
            "line in the request body when the board cannot tell who wrote it."
        )
    elif station == "7-draft":
        lines.append("The request must stay a draft until it is stamped.")
    elif station == "6-more-council":
        lines.append(
            "The walk's lenses must have seen the current shape: a walk older than the "
            "last commit, or timestamps the board cannot read, need a fresh walk."
        )
    elif station == "9-merge":
        lines.append("This only restates what else is held. Nothing to do here.")
    else:
        lines.append(
            "No plain-words note for this station yet; the board's words are what is known."
        )
    return lines


def round_step(
    *, pr: int, title: str, branch: str, tree: str, patch_id: str, her_short: str
) -> list[str]:
    focus = (
        f"PR {pr} {title[:80]}, branch {branch} at {her_short}: Aletheia CONFIRMS, Andrew confirms"
    )
    notes = (
        f"tree-hash: {tree}; patch-id: {patch_id}; her line: CONFIRMS: #{pr} at "
        f"{her_short} in her own letter, filed by the landing clerk."
    )
    return [
        "divineos",
        "audit",
        "submit-round",
        focus,
        "--actor",
        "aletheia",
        "--source-ref",
        branch,
        "--notes",
        notes,
    ]


def confirm_steps(
    *,
    pr: int,
    title: str,
    branch: str,
    tip: str,
    tree: str,
    patch_id: str,
    her_short: str,
    andrew_said: str | None,
    round_id: str,
) -> dict[str, list[str]]:
    """Her external confirm, and his when his words are given, built from git and his words.

    His step is left out until his words exist: hers is filed first, so the store's own
    clock can say when his yes had to be typed after.
    """
    for name, value in (("tip", tip), ("tree", tree), ("patch-id", patch_id)):
        if not _FULL_SHA.match(value):
            raise ClerkRefused(f"the {name} is not a full fingerprint: {value[:12]!r}")
    words = (andrew_said or "").strip()
    if andrew_said is not None and len(words) < _MIN_WORDS_OF_HIS:
        raise ClerkRefused(
            "his confirm needs his own words quoted (at least a sentence); "
            "a bare yes is not enough to put on the record for him"
        )
    external = [
        "divineos",
        "audit",
        "file-external-confirm",
        "--round",
        round_id,
        "--actor",
        "aletheia",
        "--branch",
        branch,
        "--claimed-tree",
        tree,
        "--claimed-patch-id",
        patch_id,
        "--claimed-tip",
        tip,
        "--pr",
        str(pr),
        "--basis",
        f"CONFIRMS: #{pr} at {her_short}, Aletheia, in her own letter",
    ]
    if andrew_said is None:
        return {"external": external}
    user = [
        "divineos",
        "audit",
        "submit",
        f"CONFIRMS: PR {pr} at {her_short}, Andrew",
        "--round",
        round_id,
        "--actor",
        "user",
        "--severity",
        "info",
        "--category",
        "integrity",
        "-d",
        f"Andrew said, in chat: {words} (his standing confirm attests that external "
        f"review happened). tree-hash: {tree}",
    ]
    return {"external": external, "user": user}


def parse_round_id(output: str) -> str:
    match = re.search(r"round-[0-9a-f]{6,}", output)
    if match is None:
        raise ClerkRefused("the round id could not be read from the audit command's output")
    return match.group(0)


def parse_patch_id_output(output: str) -> tuple[str, str, str]:
    """(tip, tree, patch-id) from `divineos audit patch-id --branch`."""
    found: list[str] = []
    for label in ("tip:", "tree-hash:", "patch-id:"):
        match = re.search(rf"^{re.escape(label)}\s+([0-9a-f]{{40}})", output, re.MULTILINE)
        if match is None:
            raise ClerkRefused(f"could not read {label} from the fingerprint output")
        found.append(match.group(1))
    return found[0], found[1], found[2]


def render_header(pr: int) -> str:
    return (
        f"Landing homework for #{pr}. This prepared paperwork and reviewed nothing: no "
        "station below is satisfied until a person does the work it points at."
    )
