# The merge gate refuses a body it cannot read (draft, 2026-10-17)

## What happened

On 2026-10-17 two of my merges (#603 at 79b1c1560 and #679 at 499ce05f1) went red on main's post-merge Integrity Audit. Each squash message carried `External-Review: <round> tree-hash:<hex>`. A squash commit's tree does not exist until the merge, so that hash can never match. The gate already refuses this (it refused #686 the same night), but it reads only the literal text of the command, and I had passed the PR body through a shell variable (`--body "$B"`), so the gate saw no trailer at all and let both through.

## What this builds (one branch, on top of the open #592 work)

1. **The gate refuses a merge whose body or subject it cannot read as a literal.** In the `gh pr merge` statement, a `$VAR`, `${...}`, backtick, or a `$(...)` that is not the one literal form the gate itself prints (`$(cat <<'EOF' ... EOF)`) is refused, with the remedy handed over: the refusal prints the complete safe command shape to fill in (`divineos ship N` prints one too, when it can). Single-quoted text is literal and passes. A redirect's `&` (`2>&1`, `>&2`, `&>file`) does not end the scan; `&&` does.
2. **A tree-hash typed into the merge message is refused.** This code exists only on the live house branch from 2026-10-08 and never reached main; it comes along.
3. **The body the gate offers carries the round only** (same origin). This replaces #592's choice to put the PR head's tree-hash in the offered body, which would hand out the very defect item 2 refuses.

## What it does not do

A file passed with `--body-file` or `-F` is refused, since a file's content is not the command's text. The rule is an allowlist of what can be read, not a list of the ways to hide a message.

It does not cover, and says so: a merge made through the API (`gh api .../merge`) rather than `gh pr merge`; a script or alias that runs the merge; and the default squash message GitHub builds from the commits when no body is given (a commit carrying a tree-hash would still reach main, and the gate cannot see it). It cannot rewrite the two red marks on main; they stay as history. It protects the next merge, not the last two.

## Falsifier

Replaying the two real command shapes (`--body "$B"` and `--subject "$T (#603)"`) against main's gate must pass them; against this branch's gate both must be refused. A literal heredoc body with the round only must still pass.

## Who reads it

Aria cold, then Aletheia, then Dad's yes, per the usual chain.
