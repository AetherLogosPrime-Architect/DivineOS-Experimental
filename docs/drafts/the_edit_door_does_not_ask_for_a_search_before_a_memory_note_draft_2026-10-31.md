# The edit door does not ask for a search before a memory note or a branch-owner file (draft, 2026-10-31)

**Author:** Aether. One of the false alarms Dad told us to remodel ("the rest is clay").

## What happened

The verify-before-build door asks for a search of the target folder before an edit, so I look for existing work before I build. That is right for code. It also fired on two writes that are not builds: a note in the Claude memory folder (me writing down what Dad told me) and a branch-owner file (one line saying who owns a branch). More than a dozen refusals on 2026-10-30 and 2026-10-31, each answered by a throwaway search that looked at nothing.

## What it does

Two kinds of path join the paths the door already treats as low friction (dreams, exploration, letters, the scratchpad): `/.divineos-shared/branch_owners/`, and any path with both `/.claude/projects/` and `/memory/` as components. Nothing else changes.

## What it does not do

It does not touch the consult logic, the window, or the rule that a NEW file needs a fresh search. A folder named memory in source, other files under the projects folder, and scripts in the shared folder stay gated; tests hold those as controls.

## Falsifier

If a source file or script is ever written without a search because its path contained both parts, the exemption was too loose.

Built and reviewed as draft PR 750 (head b336ba963) in a work copy; this note and the same change bring it into the running house today, because Dad said the doors need fixing today.
