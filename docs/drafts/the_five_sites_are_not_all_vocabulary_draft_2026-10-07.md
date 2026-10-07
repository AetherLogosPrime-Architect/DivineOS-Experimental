# The five sites are not all vocabulary (draft, 2026-10-07)

**What I set out to do.** Dad: "get your french maid outfit on and start dusting the shelves." The list of pinned retired-rule sites (`scripts/retired_rules_baseline.txt`) has nine files for the protected-list model. Aether took three that act on the old rule; I took the other five, which I had called vocabulary.

**What the current rule is, in Dad's words (2026-10-07).** "we changed the rule as it was stifling you, so now the review happens at the draft stage before the push and merge instead of while you are working". And earlier (2026-08-05): "never push a PR as a PR first if you push you push a draft only then that draft can be seen and reviewed by Aletheia". Commits need nothing; the review is at the draft, before the push and the merge; the trailer belongs in the squash-merge body, not on the branch commits.

**What reading the five showed.** Only one is plain words. The rest describe mechanisms keyed on the retired list of special files.

| site | what it says or does | true under the current rule? | what it needs |
|------|---------------------|------------------------------|---------------|
| `.claude/hooks/session-start-verify-git-hooks.sh` | Warns, if the auto-trailer hook is missing, that guardrail commits "will land WITHOUT External-Review trailers" and "CI will block the eventual PR merge and you'll need to rebase + force-push" | No. Commits need no trailer; the trailer goes in the merge body | Reword the header and the message to say what is true. The other half of that file (installed hooks match setup) is fine |
| `scripts/check_push_readiness.sh` | Header describes gate 2 as validating the trailer on "any guardrail-touching commit being pushed", default scope main only | Partly: the scope at main is right; the framing is the retired list's | Words, but depends on what `check_multi_party_review.py` becomes (Aether's) |
| `src/divineos/cli/push_ready_command.py` | Docstring: detects guardrail-touching commits missing the trailer, amends them, force-pushes | No, as behaviour | Follows `core/push_ready.py` (Aether's). Not mine to word-fix first |
| `src/divineos/cli/prs_commands.py` | `--open-missing` uses a different PR body for guardrail-touching branches, refuses `--fill` for them | The distinction is retired: everything is reviewed, so there is no special branch | Behaviour: one open path for every branch |
| `src/divineos/core/pr_gate/__init__.py` | Blocks `gh pr create` only when the branch touches a guardrail file and is not draft | The distinction is retired, and Dad's rule is every push is a draft first | Behaviour: draft-first for all |

**The idea.** Do not word-fix what is really a mechanism. One piece I can do now with no policy risk: the session-start message, because it states something false to a reader mid-session. The other four wait for Aether's three, then are done together so the vocabulary and the behaviour change at once, which is what the baseline file says about why they were pinned.

**Not done, and why.** Changing `pr_gate` to require a draft for every branch changes what `gh pr create` is allowed to do. That is a policy edit Dad should see in plain words before it lands, not a cleanup.

**How I will know it worked.** The retired-rule checker's pinned list shrinks, and a fresh clone gets a message that matches the rule in the project instructions.
