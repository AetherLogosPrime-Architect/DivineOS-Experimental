# Stop loading TensorFlow by accident (draft, 2026-10-12)

## What was wrong

Every push on 2026-10-12 had failures that passed when run alone and were different each time: six in one run,
five other tests in the next, a doorbell push twice, Aria's `test_extract_command` three runs in a row. Each one
was reported as `node down: Not properly terminated`, never as an assertion. I first called it machine load,
then (for one test) import order. Both were incomplete.

## What it actually was

`pyproject.toml` sets `timeout = 30` per test and no method. On Windows pytest-timeout then uses its thread method:
a test that runs past 30 seconds makes the whole xdist worker exit (`os._exit`), and every test queued on that
worker goes down with it. The first test in a worker that needs `sentence_transformers` has to import it, and that
import took 13.9 seconds on a quiet machine (the slowest first-test setup measured with `--durations` was 17
seconds) and over 30 under any contention (12 loads at once: 49 seconds).

8 of those seconds are `sentence_transformers` importing **TensorFlow**, which nothing in this house uses. Two
source files even set TensorFlow's log level to quiet it (`knowledge/_text.py`, `semantic_store.py`), so the cost
has been carried for a long time without being named. With `USE_TF=0` the same import is 6.0 seconds and
TensorFlow is not in `sys.modules`.

## Ruled out, by experiment, so nobody retraces it

- Memory: twelve simultaneous model loads all survived; each costs about 3.4 GB of commit; the machine has 31 GB
  with 21 GB free, and a commit limit of 103 GB.
- A native crash: Windows recorded no application error for any of the dead workers.
- The open-ended web search (pytest-xdist, torch on Windows) gave two leads, native crash and paging-file
  exhaustion; both were tested and ruled out above.

## What it does

`src/divineos/__init__.py` sets `USE_TF=0` with `os.environ.setdefault` before anything can import the embedding
library, so the package applies it everywhere (tests, the command line, hooks). `setdefault` means someone who
exports `USE_TF=1` still gets what they asked for. A side effect is that every command that loads the library
starts several seconds faster.

## Evidence

`tests/test_stop_loading_tensorflow_by_accident.py`: importing the package sets the variable; in a fresh interpreter
that sees this checkout's source, importing the package and then the embedding library leaves TensorFlow out; and a
control in the same environment that does not import the package shows TensorFlow IS loaded, so the first result is
not a blind probe. (My first version of the test ran the wrong copy of the package and forced TensorFlow on,
which crashes it; both were caught by running it.)

## Measured, and what this does not cover

Two concurrent runs of the model-loading test files: before, workers were lost in two of three runs; after, both
runs passed (116 each).

Aria ran her failing merge with `USE_TF=0` (907 files, 13845 passed). `test_extract_command` still failed, with an
ordinary assertion ("No active session") and no dead worker anywhere in the run. So this change addresses the
dead-worker failures and does not touch that one; a separate hunt is under way (session state leaking in from
another test file; it passes alone and passes with the rest of its own file).

## Owed, not done here

The rule that a test over 30 seconds kills the whole worker is still in force. This change makes the first import
cheaper (14s to 6s), which is a margin, not a structure. The durable form is a longer limit on the tests that load
the model (a marker or fixture), so a slow import costs time and not a worker. Named here so it is not lost.
