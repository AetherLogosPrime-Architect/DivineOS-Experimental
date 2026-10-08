# A proof-test: the merge guard refuses the merge command the house prints (rough draft)

*2026-10-08, round six, errand three. The idea, not a plan and not a fix.*

A picture: a shop hands you a ticket that says "take this to the counter". At the counter the clerk reads only what is written on the front of your hand, not the paper you are holding, so the ticket the shop itself gave you is turned away.

When a merge is refused after stamping, the house prints a finishing command that carries the review stamp inside a file (`gh pr merge N --squash --body-file "<path>" --delete-branch`). The merge guard looks for the stamp only in the command's own text, never inside the file, so it refuses that command on a pull request that touches a protected file. An earlier draft (`one_command_from_confirm_to_main_draft_2026-10-02.md`, Aria's list) already named this case as one that "becomes test cases"; this is that test.

It adds one expected failure for the printed form, one for switching auto-merge off (which the old notes ask the guard to let through, though the house does not print it), and controls showing the guard is alive and that the other printed form, `ship`'s button, is allowed.

Not in scope: changing the guard.
