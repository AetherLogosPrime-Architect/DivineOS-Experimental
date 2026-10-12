# Import the embedding library before any test timer runs (draft, 2026-10-12)

## What was wrong, in one picture

Each test worker has a stopwatch of 30 seconds per test, and a test that goes over takes its whole worker (and the
tests queued on it) down. The first test in a worker that needed the embedding library paid for unpacking it
inside its own 30 seconds. That unpacking is the biggest single cost in the first test: 6s alone even after the
TensorFlow fix, more under contention.

## What this does

`tests/conftest.py` imports the library once when a worker starts (`_warm_the_embedding_library`, called from
`pytest_configure`), before any test exists, so the cost lands where no stopwatch is running. The controller
process of a parallel run skips it: it runs no tests. It imports `divineos` first so the TensorFlow switch from
the companion change is applied before the library loads. A machine without the library is untouched.

## What it does not do

It moves the import, not the model load. Loading the model's weights still happens inside the first test that
needs it (about 14s alone in my measurement, and growing under load). This is the larger half of the first-test
cost removed, not the whole of it. A longer limit on tests that load the model remains the fuller structure; this
is the part that needs no list of which tests those are.

## Evidence

`tests/test_embedding_library_is_loaded_before_any_test_timer.py`: a test that imports nothing itself and asserts
the library is already loaded. Before/after of the first-test cost is measured in the pull request.

## Depends on

The TensorFlow change (separate PR). This works without it, only slower; the order of the two does not matter.
