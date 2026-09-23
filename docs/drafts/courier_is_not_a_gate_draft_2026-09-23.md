# The courier is not a gate — draft 2026-09-23

Reach: reach-c98f7a867a0a.

`tests/test_gate_deny_messages_name_remedy.py::test_the_dark_set_can_shrink_but_never_grow`
has failed on this branch since 406e08c5 (mine, 2026-09-22), which added
`.claude/hooks/carry-aletheia-across.sh`. The test's rule: every hook is either
declared non-gating or detectably refusing, so the remedy rule can reach it. It
says how to resolve: "if it never gates, add it to _NON_GATING_HOOKS".

Read, not assumed: the hook exits 0 on every path (lines 32, 33, 42, 47, 51, 56)
and only ever writes `additionalContext`. It carries Aletheia's files from
Andrew's downloads into the shared folder. It cannot refuse anything.

I set this failure aside twice tonight as "not mine" before checking. It was
mine. Fix: one entry in `_NON_GATING_HOOKS` with the reason written beside it,
in the house's style. No change to the hook.
