# Round two status: the mechanical repairs

Two draft pull requests were opened. A third mechanical repair was started and then stopped, because it turned out to be delicate. Nothing is merged, and nothing here marks any note finished: Aether and Aria close a note only when they watch a failing test turn passing.

## Pull request 1: the pre-registration reminders name every required option

- Problem: the reminders for how to file a pre-registration leave out options the command requires (classification line: `preregistrations_and_reviews_due #4`, rows 391 and 949).
- Rows addressed: `psf-e7c4b468`, `psf-65c6f7db`
- Branch: `cloud/fix-prereg-required-options`
- Pull request: https://github.com/AetherLogosPrime-Architect/DivineOS-Experimental/pull/599 (draft)
- Failing-test output (before the repair):

```
.FF
FAILED test_obligations_reminder_names_every_required_option
  the reminder omits required option(s): ['--success', '--embarrassing']
FAILED test_prereg_skill_example_names_every_required_option
  the skill's filing example omits required option(s): ['--embarrassing']
2 failed, 1 passed
```

- Passing-test output (after the repair):

```
...  [100%]
3 passed
```

## Pull request 2: the game-walk help names the two accepted verdicts

- Problem: the help for the game-walk command calls the verdict `cheaper-or-costlier` though only `cheaper` or `costlier` are accepted (classification line: `commands_that_refuse_without_teaching #1`, row 1002 only).
- Rows addressed: `psf-70d73fc5`
- Branch: `cloud/fix-game-walk-verdict-help`
- Pull request: https://github.com/AetherLogosPrime-Architect/DivineOS-Experimental/pull/600 (draft)
- Failing-test output (before the repair):

```
.FF
FAILED test_the_help_names_each_accepted_verdict_as_its_own_word
  the help does not name these accepted verdicts as their own words: ['cheaper', 'costlier']
FAILED test_the_help_does_not_present_the_two_verdicts_as_one_hyphenated_word
  'cheaper-or-costlier' is contained here: ... 'text | cheaper-or-costlier | why'. ...
2 failed, 1 passed
```

- Passing-test output (after the repair):

```
...  [100%]
3 passed
```

## Stopped: the doc-count checker's missing council fixer (row 376)

I classified this as mechanical, wrote its failing test (11 failed, 6 control tests passed), and was about to make the repair when the house's own gate said the file counts as a guard. I checked: the gravity classifier treats every `scripts/check_*.py` file as guard-touching, because those checks decide what may be saved, and a council fixer would let a save pass where the check used to stop it. By the rule "if you are unsure, it is delicate" I stopped before changing anything, moved the problem to DELICATE in `CLASSIFICATION.md`, and kept the failing test to reuse as a round-three proof. No branch was pushed for it.

## Things the house's own starting steps did while I worked

These are for Aether and Aria. Each one I met live, and each is already a row in the pile.

- A new piece of work only counts the search, draft and walk done after it opens, so doing them first (the sensible order) was ignored and had to be repeated. This is the "count marks made before the first edit" problem (rows 939, 947, 953, 959).
- Each save needs its own walk record and game-walk. Listing the same save several times in one record does not give several clearances, so a test commit, a repair commit and a push each cost a record unless done as one command.
- The read-gate repeatedly handed me an unrelated old writing and held the work until I opened it, several times during this round. This is the "unrelated note holds up the work" problem (rows 899, 912, 950, 990, 994).
- My own doorman read a trailing `echo` as a file write and opened a work item for it.
- The tool that measures whether the walk's lenses said different things could not run in this window (its model is not installed), so every walk closed with distinctness unmeasured.
- Running the repo's pre-commit script here reported failures that are already present on `main` (four lint findings in `obligations.py`, three type errors in `claim_commands.py`, one unused-module finding, one refusal-order finding) and rewrote a generated register file, which I restored.

## What I did not do

- No listener for letters was started in this window; it has no letters folder here and Dad said to leave it off.
- I did not use the work-item bypass or any other emergency exit.

Mechanical problems I did not get to: 0. (Only three problems were classified mechanical; two have draft pull requests and one was reclassified.)
