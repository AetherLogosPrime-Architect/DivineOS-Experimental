# The game-walk help should name the two verdicts it accepts (rough draft)

*2026-10-08. The idea, not a plan and not a pull request.*

A picture: a form with a box labelled "cheaper-or-costlier". It reads like one word to type, so the first person to fill it in types exactly that, and the form turns them away.

The `game-walk file` command takes routes as `text | verdict | why`. Its help calls the verdict `cheaper-or-costlier`, but only `cheaper` and `costlier` are accepted (with `!closed` added for a route the mechanism already defeats). Row 1002 of the sorted pile asks for the help to name the two allowed verdicts up front so a first filing does not trip.

The repair is the help text alone, plus a test that reads the two accepted words from the code and checks the help names each of them as its own word.

Not in scope: what the command accepts or refuses, or its refusal messages.
