# The "don't run the whole test suite" refusal: what it does, what pins it, what the old notes want, and three ways it could go

*Round ten, errand five. 2026-10-09, cloud helper. For Dad, Aether and Aria. Read-only: I changed nothing in the guard or its test. I recommend none of the three ways; it is a decision for the three of you.*

## In plain words, first

**A picture.** There is a door in front of every command I type. One of its jobs is a sign that says "do not wheel out the whole library to check one book". If I type the command that would run every test in the house by hand, the door stops me and says to run only the tests for what I changed, because the push does the whole library itself. Dad asked for this three times (the file quotes him: 2026-06-24, 2026-09-09, 2026-10-03), and it kept coming back, so it became a door and not a promise.

The door does its job. The trouble is at the edges: it is deliberately jumpy. When it cannot tell whether a command runs one test or all of them, it assumes all of them. That is on purpose, and it is also why a harmless command sometimes gets stopped.

## What the guard does

It lives in `src/divineos/core/full_suite_by_hand.py` (334 lines) and is plugged in before every shell command (`hook_surfaces.py`, registered as `full_suite_by_hand`). It reads the command I am about to run and refuses it if it would run the **whole tests folder** by hand.

- **Refused:** `pytest` with no target; `pytest tests/` or `tests`; `.` or a path that resolves to the tests folder however it is spelled; a glob like `tests/*` (the shell expands it after the guard has looked); `-k ""` or `-k "not …"` (an expression that narrows nothing); `cd` somewhere and then run pytest with a target the guard cannot place.
- **Allowed:** named test files and test ids; `-k` or `-m` with a real expression; `--collect-only` (nothing runs); anything that only *talks about* pytest (`grep`, `cat`, `ls`, `echo`, `head`, `git log`, a commit message).
- **Fails closed on purpose:** if the guard cannot see what a command will do, it counts as the whole suite. That covers a `cd` it cannot follow (`cd $SOMEWHERE`, `cd ~`, `cd -`), a run inside `( … )`, `{ … }`, `bash -c "…"` or `python -c "…"`, and text piped into a shell or interpreter. The file's own comments say each of these came from an audit round (Aletheia's rounds on 2026-10-03/04, Aria's three on 2026-10-04).
- **Not covered, and said so in the file:** a script that calls pytest itself. The push runs the suite inside git's own process, which never passes through this door.
- When it refuses, it prints Dad's 2026-09-09 question and, if it can map your changed files to tests, the exact command to run instead; otherwise "No changed file maps to a test file here. Name the test files you mean."

## What the test that pins it says

`tests/test_full_suite_by_hand.py` (169 lines, 97 checks, a one-line statement at the top: *"a hand-run of the whole tests folder is refused, named files and narrowed runs pass"*). Two long lists:

- **REFUSED** (62 commands). Among them, in the test's own words, two entries are labelled as choices and not accidents:
  - `cd $SOMEWHERE && pytest tests/test_a.py`, under "Aria's three, 2026-10-04. A cd moves where the shell stands."
  - `(pytest tests/test_a.py)` and `bash -c "pytest tests/test_a.py"`, under *"The price of failing closed, pinned so it stays a choice: a named file inside a wrapper is refused too. Run it unwrapped."*
- **PASSED** (31 commands): named files, narrowed runs, a runner word in front of a named file (`timeout 600 pytest tests/test_a.py`), `grep -rn pytest tests/`, `git commit -m "run pytest tests/ later"`, `cd docs && pytest ../tests/test_a.py`.

Four more checks: the refusal hands over the changed tests; it says so when nothing maps; it is registered before every command; and the real router refuses a bare suite run.

## What the old notes ask for instead

Three old notes ask for a *narrower* guard. They are cut short in the pile, so I quote what is left:

- `psf-520b5ba3` (reflection, the trigger is the refusal text itself): *"full_suite_by_hand should judge only the command it's given. A pytest naming specific test files is never the full suite, wherever it runs, so the guard should refuse only a bare `pytest` or `pytest t…"* (the note stops there).
- `psf-28521a67` (reflection): *"the full-suite detector should tell a named test file apart from a bare `tests/` run, so a single-file command is not refused."*
- `psf-55c61797` (reflection): *"the check should tell the difference between a chain of two named targets and a whole-suite run, so a false alarm doesn't make me split work for no reason."*

So the notes say: **a named test file should pass wherever it runs**. The test says the opposite for one case: a named file after a `cd` the guard cannot read, or inside a wrapper, stays refused, and it is pinned that way. The two have never been put side by side until this note. (Two other old notes mention the full suite for different reasons, a wrongly reported "tests failing" at the push gate and two heavy jobs crashing each other; they do not bear on this guard.)

## What I met, and one false fire I found

- In round eight I hit the `cd $S/… && python3 -m pytest <three named files>` shape twice; the folder written out in full instead of `$S` passes. That is the pinned case above, working as designed.
- **This round, a different thing, and I think it is a false fire, not a design choice.** I ran `grep -nE "…|pytest.skip|…|BASH is None" file` to *search* test files, and it was refused with the full-suite message. I reproduced it in a small script (calling `decide()` directly) and narrowed it:
  - `grep -nE "pytest|bash" a.py` is **refused**. `grep -nE "pytest|sh" a.py` is **refused**. `grep -nE "pytest|shutil" a.py` **passes**, and so do `grep "pytest"` alone and `grep "skip|bash"` alone.
  - The cause I read in the source (`full_suite_by_hand.py` lines 293–295): the guard has a rule for `echo pytest | sh` (text piped into a shell is a program). Its pattern looks for the word *pytest* anywhere in the command, plus a `|` followed by a shell name or `python`, `xargs`, `eval` and so on. In a search written `"pytest|bash"`, the `|` is a plain character inside quotes, but the pattern does not know about quotes. So a *search for two words* reads as a *pipe into a shell*.
  - None of the 97 checks pins this either way: `grep -rn pytest tests/` is in the PASSED list, but no case has a pipe sign inside a quoted pattern.
  - Cost I observed: one refused command and one rewrite. I do not know how often others meet it.

## Three ways it could go

**One. Leave it exactly as it is, and write the way round where people will see it.**
- What it is: the guard and its test stay. Add the working rewrites to the refusal message or a short note (write the folder out in full instead of `$VAR`; run a named file from the repository root with its full path; run inside no wrapper).
- What it costs: nothing in the guard. But the refusal keeps stopping valid commands in the cases above, each stop costs a turn and an annoyed reader, and the false fire on searches stays. The old notes stay "live" and unmet. The upside: six audit rounds of closed doors stay closed.

**Two. Narrow it so a named test file passes wherever it runs, as the old notes ask.**
- What it is: a target that is plainly one file (ends in `.py`, or has `::`) passes even after a `cd` the guard cannot read, or inside a wrapper. Folders, `.`, globs, and unplaceable targets stay refused. The pinned entries `cd $SOMEWHERE && pytest tests/test_a.py`, `(pytest tests/test_a.py)` and `bash -c "pytest tests/test_a.py"` move from REFUSED to PASSED.
- What it costs: it reverses two deliberate rulings written into the test (Aria's three and "the price of failing closed, pinned so it stays a choice"), so it needs their say. Each earlier narrowing in this file was followed by an audit round that found a new way past (six rounds, per the comments), so I would expect it to need another one. I have not tried to build it or find a way past it. Upside: the cases I met in round eight stop being refused.

**Three. Keep every rule, but make the refusal say *which rule fired*, and fix the quoted-pipe false fire.**
- What it is: the message names the reason (for example "I cannot see where this `cd` leads" or "this looks like text piped into a shell") and the exact rewrite for that reason; and the pipe rule learns that a `|` inside quotes is not a pipe.
- What it costs: it is a change to a parser that was hardened by audits, so the quote handling is the delicate part (an unbalanced or odd quote has to fail closed, like the rest). It does not make any refused command pass except the false fire; it only makes the refusal easier to act on. A new case or two would go in the test.

(These are not exclusive; two and three could be done together. I am not recommending any of them.)

## What I did not do

- I did not change the guard or its test, and did not run the full suite (the one command I ran for this was the guard's own function on made-up text, plus the test file's contents read, not run this round).
- I do not know how often the false fire or the pinned case is met by anyone but me; I have only my own rounds eight and ten.
- I have not tried to build option two or find a way past it.
- I read the old notes as stored; three of them are cut short, so I cannot say what the full wish was beyond the part I quote.
