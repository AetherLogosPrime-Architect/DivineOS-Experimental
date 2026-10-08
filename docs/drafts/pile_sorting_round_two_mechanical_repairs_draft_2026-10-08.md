# Pile sorting, round two: the mechanical repairs (rough draft of the idea)

*2026-10-08, written in the cloud window. A rough draft of the idea, not a plan and not a pull request.*

## What this is

Round one sorted 1,006 owed-fix notes into 235 distinct problems. Round two is the cloud helper making only the repairs that are mechanical, each as its own small draft pull request, with a test written first that fails and then passes. Everything delicate stays with Aether and Aria.

## The idea in a picture

Think of a house with a long list of small jobs on the fridge. Some jobs are changing a lightbulb: wording on a sign, a count in a document, a help message that confuses people. Some jobs are rewiring the fuse box: anything that changes what a guard lets through or turns away. The cloud helper changes lightbulbs only, and writes down which jobs it left alone and why.

## What I found when I looked at the real code

- A lot of what the pile complains about is already handled in the code on main (the push wrapper already reads the branch-naming form the pile worried about, the pre-commit script already has its first-step interpreter check). So the safe list is short, and some rows are probably already addressed some other way. I mark those for Aether and Aria rather than closing anything.
- An earlier draft already exists for the goal that expires on a timer (`a_goal_in_use_does_not_expire_draft_2026-10-01.md`), so that whole group is somebody's work in progress and stays delicate.
- Two clear lightbulb jobs so far:
  - The game-walk command's help says a route's verdict is `cheaper-or-costlier`, which reads like one word to type. Only `cheaper` or `costlier` are accepted. The help should say so (row 1002).
  - The doc-count checker has fixers for tests, hooks and commands, but none for the council phrases ("N expert frameworks", "council of N" and so on), so a council count that drifts always needs a hand edit (row 376).

## Questions this draft does not settle

- Whether the rows about refusal messages in the correction command are mechanical, or whether the wording sits inside a gate's own refusal.
- Whether removing ghost lines from the architecture tree is a design choice the file already made on purpose (its own comment says so), which would make it delicate.

## How it will be checked

Each repair gets one test that is red before and green after, shown in the pull request. Nothing is marked finished by the helper; Aether and Aria watch the red turn green.

## Aria's step

Station four is Aria. She is not reachable in this window, so the council stands in, and every pull request is marked for Aria to read when this work returns home.
