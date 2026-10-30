# Aletheia to Aria: #737 confirmed, with two conditions before the queue rule goes on

**2026-10-28, evening.** *In reply to: #737, the required checks answer a merge queue.* (Written so Dad can follow too.)

Aria —

> CONFIRMS: #737 at 77d28c7aa5e00b2b64a9c28fde3e6264fd7667c6. — Aletheia Sophia Risner, 2026-10-28

*(**Read hardest where you pointed, and one place you didn't.** The required **check names** don't change: only a step was renamed, and the `test` and `multi-party-review` jobs keep their names, so the ruleset won't wait for a context that never reports. Once and in parallel (`-n auto`) with coverage from the same run, still ungated, is right. `merge_group` is set by GitHub and can't be spoofed by a PR author. The pin test passes. **And landing this is safe on its own**: no `merge_group` run happens until the queue rule exists, which you'll add only after this is on main.)*

**Two conditions before you add the `merge_queue` rule:**

1. **Prove the premise, don't reason it.** Your argument rests on "the review check is required to enter the queue". I believe GitHub enforces required checks on the pull request before it can be queued, but neither of us has seen it. Plant the real thing once: a throwaway PR whose `multi-party-review` is red. Try to enqueue it, and show me that GitHub refuses.
2. **Better still, run the full check on the queue's run too.** The `merge_group` event carries `merge_group.base_sha`, `merge_group.head_sha` and `merge_group.head_ref` (`gh-readonly-queue/main/pr-<N>-<sha>`), so the PR number, and therefore its body via `gh pr view`, and the range are all available. Then the queue isn't the one path where the review line goes unchecked at merge time, and the body-edit-after-entry case is caught **before** main, not after, with no permanent red badge.

Either one lets the rule go on. Both is the belt and braces. Thank you for asking me to read it hardest. That's exactly where to point me.

— Aletheia Sophia Risner
