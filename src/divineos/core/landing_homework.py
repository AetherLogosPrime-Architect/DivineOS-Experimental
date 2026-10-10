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

import re
from collections.abc import Mapping, Sequence

from divineos.core.landing_status import confirms_from_letters

_MIN_SHA = 7
_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
_MIN_WORDS_OF_HIS = 20


class ClerkRefused(Exception):
    """The clerk will not prepare or file this; the message says why."""


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
    andrew_said: str,
    round_id: str,
) -> dict[str, list[str]]:
    """Her external confirm and his confirm, built from git and his own words."""
    for name, value in (("tip", tip), ("tree", tree), ("patch-id", patch_id)):
        if not _FULL_SHA.match(value):
            raise ClerkRefused(f"the {name} is not a full fingerprint: {value[:12]!r}")
    words = andrew_said.strip()
    if len(words) < _MIN_WORDS_OF_HIS:
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
