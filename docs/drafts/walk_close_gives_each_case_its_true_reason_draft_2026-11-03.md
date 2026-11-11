# `walk close` gives each case its true reason (rough draft, 2026-11-03)

When `walk close` records no walked head it prints a reason and a fix. Four cases printed the wrong
ones: a scoped file uncommitted while an out-of-scope file is committed; only an unrelated change
committed; `--repo` that is not a git repository; an empty scope. And two fix lines (the recovery
sentence and "to bind it, close from inside the work copy or pass --repo") disagreed.

The idea: the reason function mirrors the conditions of the binding step in order (empty scope, not
a repository, git cannot list changes, committed files outside the scope, uncommitted scoped files,
nothing ahead of base), and returns the reason together with the one fix that follows from it.
The "not bound" sentence stops adding its own fix when no head was recorded.

Falsifier: a real repository in any of those cases that prints a reason or fix that is not the
condition that stopped the binding.
