# The cut-away check also runs at push (draft, 2026-10-08)

The check now runs at commit for staged test files, through the pre-commit text that setup writes. That can be skipped (`--no-verify`), is only installed where setup was run, and Aether measured that `precommit.sh` is wired to nothing. Aether asked for the same check at push, over the changed tests of the whole branch, as the backstop for a skipped commit hook.

Idea: in `check_push_readiness.sh`, next to the existing warn-only "do the changed tests pin anything" step, list the test files changed on this branch against its merge-base with main and run `python scripts/cutaway.py --files ... --check`. Blocking, because unlike the pin check it is a ratchet against recorded floors, so it fails only when a file's weak-test count rises. If the base cannot be found or the tool cannot run, say COULD NOT CHECK and do not call it a pass. An env var skips it, loudly, like the other steps.

No new mechanism: one step in an existing script, using a tool that already has tests.
