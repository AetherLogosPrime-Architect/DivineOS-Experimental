# walk close says what it recorded (draft, 2026-11-03)

Aether and Aria each closed a walk before committing, got no walked head, and could not amend.
Close said nothing, so the cause took hours to find.

The idea: `walk close` prints one line, either the short sha it recorded or "NO walked head
recorded: <why>" with the fix (commit the change by exact path, then close from the main
checkout with `--repo <work copy>`). The amend refusal carries the same fix sentence, taken from
one shared constant so the two places cannot drift.

Not changed: what counts as a valid close, the binding rule, distinctness stats, any threshold.
Reasons are read-only git looks (uncommitted scoped files / no commit ahead of base / other).
Related: one_walk_before_the_push_not_one_per_edit_draft_2026-10-12.md (where walked head and
amend were designed).
