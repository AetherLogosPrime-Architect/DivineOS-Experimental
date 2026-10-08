# The cut-away check runs by itself, so a fake test cannot join the suite

**Draft, 2026-10-07. The idea, not a plan. Builds the first step named in `a_test_must_notice_when_its_code_is_cut_away_draft_2026-10-07.md`.**

## What he said

Dad, 2026-10-07, when I asked whether to move the checking tools into the project so they run by themselves and a fake test cannot sneak back in: "yes go ahead". And what it is for: "to help find hidden broken systems that are claiming they work so we can fix them properly". And on the fix shape: "we just have to find the root cause, and automate it so they are avoided without you having to remember".

## What exists

Three instruments already look at tests, each asking a different question, found by reading and not by remembering:

- `scripts/check_test_substance.py` asks whether a test is CAPABLE of failing, from the syntax tree.
- `scripts/check_tests_pin.py` asks whether a test written to pin a fix was red against the code before the fix, using version control.
- `scripts/run_mutmut.py` changes a line at a time in eight modules.

None of them asks whether a test DEPENDS on the product at run time. That is the cut-away: replace the code under test with a stub that crashes, only while the test body runs, and see whether the test turns red. It found 22 tests that passed on a crash. Its scratch version lives in a temporary folder that vanishes when the session ends, which is the failure shape Dad keeps naming: a tool that only exists if someone remembers it.

## The shape

1. `scripts/cutaway_plugin.py`: the pytest plugin that cuts, in place, only during the test body. `scripts/cutaway.py`: the driver that runs a test file twice (once untouched, once cut), classifies each test, sweeps many files in parallel, and compares against a baseline.
2. A baseline, `scripts/cutaway_baseline.json`: per file, how many tests are DISCONNECTED or SWALLOWED today. It is a ratchet, as the repo already uses (`retired_rules_baseline.txt`, `orphan_modules_baseline.txt`): the count for a file may fall, never rise, so the existing ~1,100 unread candidates do not block anyone but a new weak test cannot join them. A rise requires a stated reason, stored beside the count.
3. Wired into `precommit.sh` for the staged test files only (cheap), and available as a full sweep. Enforcement at the push is the next step and is Aether's to weigh, since it touches `check_push_readiness.sh`.
4. Its own tests are cases whose answers are known from outside: deliberate fakes, honest tests, a re-exported function, a script loaded without registering, a click command defined in a closure, a test that spawns a process, a baseline that must not rise, a file that collects nothing.

## What it will not do

It measures dependence, not correctness. DISCONNECTED means a person should read it, never that it is fake: many are honest scans of repo files or checks that a name exists. Code run in a child process is labeled OUT-OF-PROCESS and is not measured. Mutation testing (one line at a time) and the per-line coverage map it needs are separate instruments and stay separate; they are the next piece, not part of this one.

## Cost

Two scripts, a baseline, about forty tests, one section in the commit script. Running it on a commit costs two pytest runs per staged test file, tens of seconds. The full sweep is about half an hour of machine time on four workers. Every child process it starts passes the no-window flag, because the version that did not covered Dad's screen with windows tonight.
