"""Open pull requests as prior art for `reach open`.

A fix was once rebuilt that already existed as a draft PR, because the reach
check looked at code, git and the CLI but not at open PRs. The matching is pure
and takes the PR list as data; the network call is injected.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable

HEADER = "Open PRs that may already do this:"
MIN_SHARED = 2
MIN_LEN = 4

STOP_WORDS = frozenset(
    "this that with from have has had does not what when where which while will would "
    "should could into onto over than then them they their there these those been being "
    "were your just only also each such some more most very about after before again "
    "because between both under until upon".split()
)


def stem(word: str) -> str:
    """Crude suffix stripping so gates/gate and checking/check/ending/endings meet."""
    if word.endswith("s") and not word.endswith("ss"):
        word = word[:-1]
    for suffix in ("ing", "ed"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            word = word[: -len(suffix)]
            break
    if word.endswith("e") and len(word) > 3:
        word = word[:-1]
    return word


def content_words(text: str) -> set[str]:
    words = re.split(r"[^a-z]+", text.lower())
    return {stem(w) for w in words if len(w) >= MIN_LEN and w not in STOP_WORDS}


def matching_prs(symptom: str, prs: list[dict]) -> list[dict]:
    """PRs whose title or head branch share >= 2 content words with SYMPTOM."""
    wanted = content_words(symptom)
    hits = []
    for pr in prs:
        theirs = content_words(f"{pr.get('title', '')} {pr.get('headRefName', '')}")
        if len(wanted & theirs) >= MIN_SHARED:
            hits.append(pr)
    return hits


def gh_open_prs() -> list[dict]:
    """Real runner. Raises on any failure so the caller can say so loudly."""
    try:
        proc = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--state",
                "open",
                "--limit",
                "100",
                "--json",
                "number,title,headRefName",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("gh not installed") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("gh timed out") from exc
    if proc.returncode != 0:
        raise RuntimeError(f"gh exited {proc.returncode}: {proc.stderr.strip()[:120]}")
    prs: list[dict] = json.loads(proc.stdout)
    return prs


def format_open_pr_section(symptom: str, runner: Callable[[], list[dict]] = gh_open_prs) -> str:
    """The text to print. Never empty: a failed look says so."""
    try:
        prs = runner()
    except Exception as exc:  # noqa: BLE001 - any failure must surface, never go silent
        return f"Could not look at open PRs ({exc}): this is not a clean bill."
    hits = matching_prs(symptom, prs)
    if not hits:
        return (
            f"{HEADER}\n  none found among {len(prs)} open PR(s) "
            "(only titles and branch names were searched, not descriptions or code)."
        )
    lines = [HEADER]
    lines += [f"  #{p['number']}  {p['title']}   ({p['headRefName']})" for p in hits]
    return "\n".join(lines)
