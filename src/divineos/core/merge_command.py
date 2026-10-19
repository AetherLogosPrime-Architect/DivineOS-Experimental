"""What a shell command merges: the one reader every gate on a merge asks.

Three open holes had one cause. The merge-freshness refusal (#692) and the review gate beside
it (`pr_merge_gate`) each carried its own pattern for "this command merges a pull request",
and each pattern was a little narrower than the ways people type one. Aria found flag-first
(`gh pr merge --squash 42`); probing found a chained pair (`... 1 && gh pr merge 2`);
Aletheia found two more doors (`gh api -X PUT repos/o/r/pulls/42/merge`, and the program typed
with a path, `/usr/bin/gh pr merge 42`). Fixing a pattern in one gate leaves the same hole in
the other, so the reading is here, once, and a gate asks it and nothing else.

``merge_targets(command)`` returns every merge the command performs, in order, each as a
``MergeTarget``: the pull request as ``gh pr view`` accepts it (a number, a URL, a branch name,
or "" meaning the pull request of the checked-out branch), the repository the command names
("" when it names none), and whether it went by ``pr`` (the merge command) or ``api`` (the
direct REST call, which never says `gh pr merge`).

WHERE THE COMMAND ENDS is decided on the quote-scrubbed text, where a `;` or `&&` inside a
quoted body is not a separator and an `echo "gh pr merge 1"` is not a merge. WHAT THE COMMAND
SAYS is read from the original text split the way a shell splits it, because the scrubber
blanks quoted values (a quoted `-R "o/r"` becomes spaces). The scrubber keeps every character
in place, so the two line up.

NOT SEEN, and named so nobody reads silence as coverage: a merge typed from the web page's
button, a merge made through the GraphQL API (`mergePullRequest`), a program whose path is
quoted because it contains a space, and a merge typed from a folder that is not the repository.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass

from divineos.core.command_match import at_command_position, strip_quoted

# The program may be named by a path (`/usr/bin/gh`, `C:\tools\gh.exe`): Aletheia's second door.
_PROGRAM = r"(?:\S*[/\\])?gh(?:\.exe)?"
_PR_MERGE = re.compile(rf"{_PROGRAM}\s+pr\s+merge\b")
_API = re.compile(rf"{_PROGRAM}\s+api\b")
_SEPARATORS = re.compile(r"&&|\|\||[;|)\n]")
_MERGE_ENDPOINT = re.compile(r"^/?repos/(?P<repo>[^/\s]+/[^/\s]+)/pulls/(?P<number>\d+)/merge/?$")

# `gh pr merge` flags that take a value, so the value is not mistaken for the pull request.
_PR_VALUE_FLAGS = frozenset(
    {
        "-t",
        "--subject",
        "-b",
        "--body",
        "-F",
        "--body-file",
        "-A",
        "--author-email",
        "--match-head-commit",
        "-R",
        "--repo",
    }
)
_REPO_FLAGS = frozenset({"-R", "--repo"})
# `gh api` flags that take a value, so the value is not mistaken for the endpoint.
_API_VALUE_FLAGS = frozenset(
    {
        "-H",
        "--header",
        "-f",
        "--raw-field",
        "-F",
        "--field",
        "--input",
        "-q",
        "--jq",
        "-t",
        "--template",
        "--hostname",
        "--cache",
        "-p",
        "--preview",
    }
)


@dataclass(frozen=True)
class MergeTarget:
    selector: str  # what `gh pr view` accepts; "" means the checked-out branch's pull request
    repo: str  # "owner/repo" as typed, or "" when the command names none
    via: str  # "pr" for `gh pr merge`, "api" for the direct REST merge


def _tokens(command: str, scrubbed: str, start: int) -> list[str]:
    """The words of the one command that begins at ``start``, as a shell would split them."""
    end = _SEPARATORS.search(scrubbed, start)
    rest = command[start : end.start() if end else len(scrubbed)]
    try:
        return shlex.split(rest)
    except ValueError:
        pass
    # The closing quote of a `bash -c "..."` body is not part of the code inside it, but the
    # command ends before it and it sticks to the last word (`.../merge"`), so try once
    # without it before falling back to plain whitespace.
    try:
        return shlex.split(rest.rstrip("'\" "))
    except ValueError:
        return rest.split()


def _pr_target(command: str, scrubbed: str, start: int) -> MergeTarget:
    selector, repo = "", ""
    take_repo = skip_value = False
    for token in _tokens(command, scrubbed, start):
        if take_repo:
            repo, take_repo = token, False
        elif skip_value:
            skip_value = False
        elif token.startswith("--repo="):
            repo = token.split("=", 1)[1]
        elif token.startswith("-"):
            take_repo = token in _REPO_FLAGS
            skip_value = token in _PR_VALUE_FLAGS and not take_repo
        elif not selector:
            selector = token[1:] if token.startswith("#") and token[1:].isdigit() else token
    return MergeTarget(selector, repo, "pr")


def _api_target(command: str, scrubbed: str, start: int) -> MergeTarget | None:
    """A PUT to repos/<o>/<r>/pulls/<n>/merge, in any of the spellings `gh api` accepts."""
    method, endpoint = "", ""
    take_method = skip_value = False
    for token in _tokens(command, scrubbed, start):
        if take_method:
            method, take_method = token, False
        elif skip_value:
            skip_value = False
        elif token in ("-X", "--method"):
            take_method = True
        elif token.startswith("--method="):
            method = token.split("=", 1)[1]
        elif token.startswith("-X") and len(token) > 2:
            method = token[2:]
        elif token.startswith("-"):
            skip_value = token in _API_VALUE_FLAGS
        elif not endpoint:
            endpoint = token
    found = _MERGE_ENDPOINT.match(endpoint) if method.upper() == "PUT" else None
    if not found:
        return None
    repo = found["repo"]
    return MergeTarget(found["number"], "" if "{" in repo else repo, "api")


def merge_targets(command: str) -> list[MergeTarget]:
    """Every merge ``command`` performs, in the order it performs them."""
    if not isinstance(command, str) or not command.strip():
        return []
    scrubbed = strip_quoted(command)
    found: list[tuple[int, MergeTarget]] = []
    for pattern, read in ((_PR_MERGE, _pr_target), (_API, _api_target)):
        for match in pattern.finditer(scrubbed):
            if not at_command_position(scrubbed, match.start()):
                continue
            target = read(command, scrubbed, match.end())
            if target is not None:
                found.append((match.start(), target))
    return [target for _, target in sorted(found, key=lambda pair: pair[0])]
