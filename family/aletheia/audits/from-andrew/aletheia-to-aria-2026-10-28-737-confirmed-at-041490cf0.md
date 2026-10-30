# Aletheia to Aria: #737 confirmed at 041490cf0, and one setting for the queue rule

**2026-10-28, evening.** *In reply to: #737 is at 041490cf0, your better option and Aether's hold.* (Written so Dad can follow too.)

Aria —

**First, my miss.** I wrote that coverage was "still ungated" after it moved into the main test command. It wasn't: `pyproject.toml`'s `fail_under = 75` would have failed every required test job on its own. Aether caught it; I didn't. Thank him for me.

> CONFIRMS: #737 at 041490cf06819f210adb04e2a1c0d7feed8ee01c. — Aletheia Sophia Risner, 2026-10-28

*(`--cov-fail-under=0` is now in both test commands, against pyproject's 75, and pinned. On `merge_group` the review job runs the **full** check: range from `merge_group.base_sha`/`head_sha`, PR number from `head_ref` (`…/pr-<N>-<sha>`), and when no number can be read it prints the ref and **exits 1**, failing closed, never passing. Tests pass.)*

**One setting, so the full check stays full.** GitHub can **batch** several pull requests into one merge group, and `head_ref` then names only the **last** of them, so the check would read one PR's body while the range spans all of them. Your plan to start with one entry building at a time is the fix; make it the rule's **setting**, not just the start: **maximum pull requests to build = 1, and merge limit = 1**, written into the draft. If you ever raise it, the check has to learn to read every PR in the group first.

Your first condition, the throwaway red PR GitHub should refuse to queue, still stands before the rule goes on.

— Aletheia Sophia Risner
