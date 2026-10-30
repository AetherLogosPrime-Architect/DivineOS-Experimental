# The review gate reads every spelling of a merge (draft, 2026-10-19)

**Author: aether**

## What is wrong

`core/pr_merge_gate.py` refuses `gh pr merge N` for a pull request that touches a guardrail file and carries no `External-Review:` line. It finds the merge with one pattern, `\bgh\s+pr\s+merge\s+(\d+)\b`, and takes only the first match. I measured it on 2026-10-18 with a stand-in guardrail lookup (PR 99 touches a guardrail file, no review line): the plain `gh pr merge 99 --squash` is refused, and these are allowed: `gh pr merge --squash 99` (flag before the number), `/usr/bin/gh pr merge 99 --squash` (program named by a path), `gh api -X PUT .../pulls/99/merge`, `gh api --method PUT .../pulls/99/merge -f merge_method=squash`, and `gh pr merge 1 --squash && gh pr merge 99 --squash` (a second merge in a chain). Five of six spellings pass the one gate whose whole job is this. Aletheia re-ran the same probes against the freshness gate on 2026-10-19 and the shared reader refused all of them, which is the evidence the reader is the right home.

## What it will do

Replace the single pattern with `merge_command.merge_targets(command)`, the reader #692 added, which already reads every spelling above plus `-R/--repo`, URLs, branch names, `bash -c` and `bash -lc` wrappers, and a merge in any position of a chain. For each target it resolves a pull request number (a number is used as it is; a URL or branch name is resolved with `gh pr view --json number`), and runs the existing guardrail check on each. Everything after the match is unchanged: the guardrail list, the trailer pattern, the ready-to-paste body, the wording of the refusal.

## Its own fail behaviour, kept on purpose

The review gate fails OPEN today: when `gh` cannot be reached, or a selector cannot be resolved to a number, it lets the command through, because it enforces a binding only where it can see a touch. The freshness gate fails CLOSED. These are different questions (is this PR reviewed, and is this PR current), and merging the two behaviours would be a change to what the gate promises. So the reader changes, the failure behaviour does not. A selector that cannot be resolved is still allowed, and is now a named case in the code and a test, not a silent one.

## What it still cannot see (so silence is not read as coverage)

The web page's button; GraphQL `mergePullRequest`; the same REST call made by `curl` or a script; a merge launched from a quoted string of another language; a program whose path is quoted because it contains a space; a merge typed from a folder that is not the repository. And one narrower thing that is new to say aloud: the trailer check looks at the whole command, so `gh pr merge 1 --body "External-Review: round-x" && gh pr merge 99` has a trailer somewhere in the command and clears both merges. Per-target trailers would close it; that is a larger change to what counts as a trailer for which merge, and is left for its own piece.

## Falsifier

If any of the six measured spellings still passes a guardrail-touching pull request with no review line, or if a command that is not a merge is refused, the change is wrong. The tests pin: all six spellings refused; a plain read (`gh api repos/o/r/pulls/99`) and an `echo` that mentions a merge allowed; the existing 22 tests in `test_pr_merge_gate.py` unchanged; an unresolvable selector allowed and named.

## Order

Wait for #692 to land (the reader lives there), then branch the code off main. Tests first, red; then the change; then the walks; then Aletheia and Aria.
