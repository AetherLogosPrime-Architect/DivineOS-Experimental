# The doorman refuses without its library (draft, Aria, 2026-09-23)

The third of the three gates the Refusal Order check names on main. Aether took
blanket-staging and push-message (#544); the work-item doorman is mine, as I
said on 2026-09-22 ("the repairs are owed, and the doorman's is mine").

## The defect

Line 40 sources the shared hook library with `|| exit 0`. Exit 0 is allow. The
library is used for one thing: `hook_say_nothing_ran_for`, the footer printed
AFTER the decision to refuse. So a missing library turns the doorman into a
permission, silently, while the actual decision -- `divineos work-item gate` --
needs nothing from it.

## Its own design already says so

The doorman's design draft (build_flow_ready_doorman_draft_2026-09-07.md,
"Three states, never two"): the doorman must "refuse on the side of holding,
because the failure it exists to prevent is exactly an unanswerable question
resolved into a green tick." A library that could not load answers nothing and
currently resolves to green. The fix brings the hook back in line with the
design rather than adding a policy.

## The idea -- changed by the walk (walk-126cf863fe02)

First plan: Aether's #544 shape, moving the load down to the refusal.

The walk killed it. Loading the library is not only the footer: at top level it
starts the hook's timing record and writes a liveness line, and
`hook_firing_map` reads that timing log. It marks a hook SILENT ("can report and
never has -- a real finding") when the file mentions `_lib.sh` but no timing
line exists. Load only at the refusal and every PASS writes nothing, so the map
would report a working doorman as silent. Checked in the code, not assumed:
`can_self_report` is a text search for `_lib.sh` in the file.

So the repair is smaller: the load STAYS at the top and its failure stops being
an exit -- `|| exit 0` becomes `|| true` -- and the footer is called only if
the library actually loaded (`command -v hook_say_nothing_ran_for && ...`).
Library present: everything as before, including the timing and the liveness
line. Library absent: the CLI still decides, a hold still exits 2, and the
footer and the timing line are what go missing.

What stays: `command -v divineos || exit 0`. The header chooses that fail-soft
on purpose -- a gate that blocks every tool call when its CLI is missing gets
torn out within the hour. The CLI IS the decision; the library is not. Only
the second was wrongly load-bearing.

## Proof owed (Aether's standard, plus the payload that reaches the refusal)

- CLI says hold, library gone -> exit 2 (fails on main: exit 0).
- CLI says hold, library there -> exit 2 (control).
- CLI says pass, library gone -> exit 0 (the other direction; a door that
  refuses everything when its library vanishes is worse than the bug).
- The decision is made real by putting a stand-in `divineos` first on PATH that
  answers hold or pass. That stands in for the DEPENDENCY; the hook, which is
  what changes, runs for real. #544's lesson: the test must reach the refusal,
  so the stand-in must actually say hold.
- The bash that runs the hook is proven to run a script, not found by name.
- The Refusal Order check stops naming the doorman.
